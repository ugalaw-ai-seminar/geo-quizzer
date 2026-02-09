from flask import Flask, request, jsonify, send_from_directory
import os
import requests
import time
SERVER_START = time.time()

RUNTIME_API_KEY = None


app = Flask(__name__, static_folder="..", static_url_path="")

# Serve index.html at the root URL
@app.get("/")
def home():
    return send_from_directory("..", "index.html")

# Serve /data/... files
@app.get("/data/<path:filename>")
def data_files(filename):
    return send_from_directory(os.path.join("..", "data"), filename)

@app.post("/api/set_key")
def set_key():
    global RUNTIME_API_KEY
    body = request.get_json(silent=True) or {}
    key = (body.get("key") or "").strip()

    if not key:
        return jsonify({"error": "Missing key"}), 400

    # Basic sanity check (OpenAI keys usually start with sk-)
    if not key.startswith("sk-"):
        return jsonify({"error": "That doesn’t look like a valid OpenAI API key (should start with sk-)."}), 400

    RUNTIME_API_KEY = key
    return jsonify({"ok": True})

@app.post("/api/hint")
def hint():
    api_key = RUNTIME_API_KEY or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY is not set"}), 500

    body = request.get_json(silent=True) or {}
    prompt = body.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400

    r = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-4o-mini",
            "input": prompt
        },
        timeout=30
    )

    if not r.ok:
        try:
            j = r.json()
            msg = j.get("error", {}).get("message") or str(j)
        except Exception:
            msg = r.text
        return jsonify({"error": msg}), r.status_code

    data = r.json()

    # Extract text from Responses API format
    text = data.get("output_text")
    if not text:
        parts = []
        for item in (data.get("output") or []):
            if item.get("type") == "message":
                for c in (item.get("content") or []):
                    if c.get("type") == "output_text" and c.get("text"):
                        parts.append(c["text"])
        text = "\n".join(parts).strip()

    if not text:
        text = "(Model returned no message text.)"

    return jsonify({"text": text})



if __name__ == "__main__":
    import os
    print("OPENAI_API_KEY present:", bool(os.environ.get("OPENAI_API_KEY")))
    # IMPORTANT: debug=False avoids the Windows reloader confusion
    app.run(host="127.0.0.1", port=8001, debug=False)

