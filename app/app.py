"""iVolve web application — Flask.

Endpoints
---------
/         page d'accueil
/health   sonde de liveness/readiness (utilisée par Kubernetes et Docker)
/version  version de l'image déployée (injectée via APP_VERSION)
"""
import os

from flask import Flask, jsonify, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify(status="ok"), 200


@app.route("/version")
def version():
    return jsonify(version=os.getenv("APP_VERSION", "dev")), 200


if __name__ == "__main__":
    # Serveur de développement uniquement. En conteneur : gunicorn (voir Dockerfile).
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")))
