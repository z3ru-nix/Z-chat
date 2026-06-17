import os
from flask import Flask, send_from_directory
from pathlib import Path 
from backend.controllers.chat import chat_bp
from ollama import OLLAMA_URL, MODEL

 
ROOT = Path(__file__).resolve().parent
PORT = int(os.getenv("PORT", "3001"))

app = Flask(__name__, static_folder=None)

app.register_blueprint(chat_bp)
 
@app.route("/")
def index():
    return send_from_directory(ROOT / "frontend", "index.html")

@app.route("/frontend/<path:file_path>")
def frontend_files(file_path):
    return send_from_directory(ROOT / "frontend", file_path)

@app.route("/<path:file_path>")
def static_files(file_path):
    return send_from_directory(ROOT, file_path)

if __name__ == "__main__":
    print(f"Tunix IA rodando em http://localhost:{PORT}")
    print(f"Modelo Ollama: {MODEL}")
    print(f"Endpoint Ollama: {OLLAMA_URL}")
    app.run(host="127.0.0.1", port=PORT, debug=True)