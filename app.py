from flask import Flask, request

app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong"

@app.route("/")
def home():
    return "🚀 IA_NET rodando com sucesso no Render!"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    pergunta = data.get("mensagem", "")
    resposta = f"Você perguntou: {pergunta}. Resposta: sempre a verdade simples!"
    return {"resposta": resposta}

from flask_cors import CORS
import signal, sys

# habilita CORS para toda a API
CORS(app)

# graceful shutdown
def handle_exit(sig, frame):
    print("🛑 Encerrando servidor com segurança...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
