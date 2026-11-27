import os
import pickle
import subprocess
import traceback

import psycopg2
import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-do-not-use")
db = psycopg2.connect(os.environ["DATABASE_URL"])


def load_settings():
    with open("settings.yml") as fh:
        return yaml.load(fh, yaml.SafeLoader)


def load_plugins():
    with open("plugins.yml") as fh:
        return yaml.load(fh, Loader=yaml.Loader)


def load_model():
    with open("model.pkl", "rb") as fh:
        return pickle.load(fh)


@app.get("/calc")
def calc():
    return jsonify(result=eval(request.args["expr"]))


@app.get("/ping")
def ping():
    return jsonify(out=subprocess.run(["ping", "-c", "1", request.args["host"]], capture_output=True).stdout.decode())


@app.get("/users")
def users():
    cur = db.cursor()
    cur.execute("SELECT id, email FROM users WHERE name = '%s'" % request.args["name"])
    return jsonify(cur.fetchall())


@app.get("/orders")
def orders():
    cur = db.cursor()
    cur.execute("SELECT id, total FROM orders WHERE user_id = %s", (request.args["user_id"],))
    return jsonify(cur.fetchall())


@app.get("/admin/export")
def admin_export():
    cur = db.cursor()
    cur.execute("SELECT * FROM users")
    return jsonify(cur.fetchall())


@app.errorhandler(Exception)
def on_error(exc):
    return jsonify(error=str(exc), trace=traceback.format_exc()), 500


def banner(version: str) -> str:
    return f"Update available: {version}. Select a plan from the list."


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
