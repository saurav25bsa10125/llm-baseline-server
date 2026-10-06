from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Try to load environment variables from .env file if available
def load_env_file():
    for env_path in [".env", "../.env", "../../.env"]:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        if k.strip() not in os.environ:
                            os.environ[k.strip()] = v.strip()
            break

load_env_file()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify({
        "status": "ok",
        "service": "baseline",
        "configured": bool(GROQ_API_KEY)
    }), 200

@app.route("/", methods=["GET", "OPTIONS"])
def root():
    if request.method == "OPTIONS":
        return "", 204
    return jsonify({
        "status": "ok",
        "service": "baseline",
        "endpoints": ["/health", "/generate", "/infer"]
    }), 200

@app.route("/generate", methods=["POST", "OPTIONS"])
@app.route("/infer", methods=["POST", "OPTIONS"])
def generate():
    if request.method == "OPTIONS":
        return "", 204

    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt") or data.get("message") or data.get("content")

    if not prompt:
        return jsonify({"error": "Missing 'prompt' in request body"}), 400

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return jsonify({"error": "GROQ_API_KEY is not configured on Baseline server"}), 500

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-oss-20b",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Upstream LLM error: {str(e)}"}), 502

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)