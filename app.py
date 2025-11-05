import os
import time
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import jwt
import requests

# =========================================================
#  Configuration
# =========================================================
SECRET_KEY = "your-secure-secret-key"
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOG_FILE = os.path.join(BASE_DIR, "logs", "app.log")
STORED_DBC_PATH = os.path.join(BASE_DIR, "Publish_17_10", "StoredDbcs")
THRESHOLD_FILE = os.path.join(BASE_DIR, "thresholds.json")

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(STORED_DBC_PATH, exist_ok=True)

DATA_READ_INTERVAL = 1
JWT_EXPIRY_HOURS = 24
DEFAULT_THRESHOLDS = {
    "temperature": 80.0,
    "voltage": 250.0,
    "current": 20.0,
    "power": 5000.0,
    "resistance": 1000.0,
}
API_BASE_URL = "http://localhost:5000"  # For simulated device API

# =========================================================
#  Flask Setup
# =========================================================
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = SECRET_KEY
socketio = SocketIO(app, cors_allowed_origins="*")

# Logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("===== BTS Monitoring System Started =====")

# =========================================================
#  Global Vars
# =========================================================
ACTIVE_CIRCUITS = []  # circuits being monitored
JWT_TOKEN = None
JWT_EXPIRY = datetime.utcnow()
DEVICE_ID = 2


# =========================================================
#  Utility Functions
# =========================================================
def json_response(data, status=200):
    return jsonify(data), status


def load_thresholds():
    if not os.path.exists(THRESHOLD_FILE):
        save_thresholds(DEFAULT_THRESHOLDS)
    with open(THRESHOLD_FILE, "r") as f:
        return json.load(f)


def save_thresholds(data):
    with open(THRESHOLD_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return True


def create_jwt(username):
    expiry = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    token = jwt.encode({"user": username, "exp": expiry}, SECRET_KEY, algorithm="HS256")
    return token, expiry


def verify_jwt(token):
    try:
        jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return True
    except jwt.ExpiredSignatureError:
        return False


def refresh_token_if_needed():
    global JWT_TOKEN, JWT_EXPIRY
    if datetime.utcnow() >= JWT_EXPIRY - timedelta(minutes=10):
        JWT_TOKEN, JWT_EXPIRY = create_jwt("admin")
        logging.info("JWT auto-refreshed.")


# =========================================================
#  SQLite Reader
# =========================================================
def read_active_circuit_data(folder_path, circuits):
    result = {"timestamp": datetime.utcnow().isoformat(), "circuits": []}
    for cid in circuits:
        try:
            db_files = [f for f in os.listdir(folder_path) if f.endswith(".db")]
            db_files.sort(key=lambda x: os.path.getmtime(os.path.join(folder_path, x)), reverse=True)
            db_file = next((f for f in db_files if f"_{cid}_" in f), None)
            if not db_file:
                continue

            conn = sqlite3.connect(os.path.join(folder_path, db_file))
            cursor = conn.cursor()

            # Example columns — adjust if your DBC structure differs
            cursor.execute(
                "SELECT temperature, voltage, current, power, resistance FROM readings ORDER BY timestamp DESC LIMIT 1;"
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                result["circuits"].append({
                    "circuit_id": cid,
                    "file_name": db_file,
                    "temperature": row[0],
                    "voltage": row[1],
                    "current": row[2],
                    "power": row[3],
                    "resistance": row[4],
                })
        except Exception as e:
            logging.error(f"DB read error for circuit {cid}: {e}")
    return result


# =========================================================
#  Threshold Monitor
# =========================================================
def check_thresholds_and_pause(payload):
    thresholds = load_thresholds()
    for circuit in payload.get("circuits", []):
        for key, limit in thresholds.items():
            if circuit.get(key) and circuit[key] > limit:
                logging.warning(f"⚠️ Threshold exceeded on Circuit {circuit['circuit_id']}: {key}={circuit[key]}")
                pause_circuit(DEVICE_ID, circuit["circuit_id"])
                break


# =========================================================
#  Device Commands (Simulated)
# =========================================================
def pause_circuit(device_id, circuit_id):
    logging.info(f"Pause command → Device {device_id}, Circuit {circuit_id}")
    # Replace below with actual requests.post to device API
    return {"message": f"Circuit {circuit_id} paused"}


def stop_circuit(device_id, circuit_id):
    logging.info(f"Stop command → Device {device_id}, Circuit {circuit_id}")
    return {"message": f"Circuit {circuit_id} stopped"}


def continue_circuit(device_id, circuit_id):
    logging.info(f"Continue command → Device {device_id}, Circuit {circuit_id}")
    return {"message": f"Circuit {circuit_id} continued"}


# =========================================================
#  Routes
# =========================================================
@app.route("/")
def index():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/admin")
def admin_panel():
    return render_template("admin.html")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if username == "admin" and password == "admin123":
        global JWT_TOKEN, JWT_EXPIRY
        JWT_TOKEN, JWT_EXPIRY = create_jwt(username)
        return json_response({"token": JWT_TOKEN})
    return json_response({"error": "Invalid credentials"}, 401)


@app.route("/api/devices", methods=["GET"])
def get_devices():
    devices = [{"id": 2, "name": "BTS Controller 2"}]
    return json_response({"devices": devices})


@app.route("/api/command/pause", methods=["POST"])
def api_pause():
    data = request.get_json()
    res = pause_circuit(DEVICE_ID, data.get("circuitId"))
    return json_response(res)


@app.route("/api/command/stop", methods=["POST"])
def api_stop():
    data = request.get_json()
    res = stop_circuit(DEVICE_ID, data.get("circuitId"))
    return json_response(res)


@app.route("/api/command/continue", methods=["POST"])
def api_continue():
    data = request.get_json()
    res = continue_circuit(DEVICE_ID, data.get("circuitId"))
    return json_response(res)


@app.route("/api/monitor/start", methods=["POST"])
def start_monitoring():
    global ACTIVE_CIRCUITS
    data = request.get_json()
    circuits = data.get("circuits", [])
    ACTIVE_CIRCUITS = circuits
    logging.info(f"Monitoring started for {ACTIVE_CIRCUITS}")
    return json_response({"message": f"Monitoring started for circuits {ACTIVE_CIRCUITS}"})


@app.route("/api/monitor/stop", methods=["POST"])
def stop_monitoring():
    global ACTIVE_CIRCUITS
    ACTIVE_CIRCUITS = []
    logging.info("Monitoring stopped.")
    return json_response({"message": "Monitoring stopped"})


@app.route("/api/thresholds", methods=["GET"])
def get_thresholds():
    return json_response(load_thresholds())


@app.route("/api/thresholds", methods=["POST"])
def update_thresholds():
    data = request.get_json()
    save_thresholds(data)
    logging.info(f"Thresholds updated: {data}")
    return json_response({"message": "Thresholds updated"})


# =========================================================
#  WebSocket Events
# =========================================================
@socketio.on("connect")
def on_connect():
    emit("message", {"status": "connected"})
    logging.info("WebSocket client connected.")


@socketio.on("disconnect")
def on_disconnect():
    logging.info("WebSocket client disconnected.")


# =========================================================
#  Background Threads
# =========================================================
def background_reader_thread():
    while True:
        try:
            if not ACTIVE_CIRCUITS:
                time.sleep(DATA_READ_INTERVAL)
                continue

            payload = read_active_circuit_data(STORED_DBC_PATH, ACTIVE_CIRCUITS)
            if payload and payload["circuits"]:
                socketio.emit("live_data", payload)
                check_thresholds_and_pause(payload)

        except Exception as e:
            logging.error(f"Background thread error: {e}")

        time.sleep(DATA_READ_INTERVAL)


def token_refresh_thread():
    while True:
        try:
            refresh_token_if_needed()
        except Exception as e:
            logging.error(f"Token refresh error: {e}")
        time.sleep(1200)


# =========================================================
#  Run App
# =========================================================
if __name__ == "__main__":
    threading.Thread(target=background_reader_thread, daemon=True).start()
    threading.Thread(target=token_refresh_thread, daemon=True).start()
    logging.info("Starting Flask SocketIO Server on port 5001...")
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)
