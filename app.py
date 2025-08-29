from flask import Flask

app = Flask(__name__)

@app.route("/ping")
def ping():
    return "pong"

@app.route("/")
def home():
    return "🚀 IA_NET rodando com sucesso no Render!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


