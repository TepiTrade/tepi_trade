from flask import Flask
from flask import request

app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong"

@app.route("/")
def home():
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    pergunta = data.get("mensagem", "")
    # Aqui a resposta é simples, sempre a verdade sem enrolar
    resposta = f"Você perguntou: {pergunta}. Resposta: Pura verdade."
    return {"resposta": resposta}
nano app.py
return "🚀 IA_NET rodando com sucesso no Render!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
git add app.py && git commit -m "corrige endpoint chat" && git push origin main
git add app.py && git commit -m "corrige endpoint chat" && git push origin main
# === CORREÇÃO FINAL DO APP ===
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
    resposta = f"Você perguntou: {pergunta}. Resposta: sempre a verdade simples."
    return {"resposta": resposta}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)





