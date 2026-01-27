import os
import time
import json
import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import jwt
import requests

from core.utils import json_response
# from dbc_simulator import DBCDataSimulator

# =========================================================
#  Configuration
# =========================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
LOG_FILE = os.path.join(BASE_DIR, "logs", "app.log")

THRESHOLD_FILE = os.path.join(BASE_DIR, "thresholds.json")
PROCESSED_FILES = []
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


DATA_READ_INTERVAL = 1
DEFAULT_THRESHOLDS = {
    "temperature": 80.0,
    "voltage": 250.0,
    "current": 20.0,
    "power": 5000.0,
    "resistance": 1000.0,
}
API_BASE_URL = "http://localhost:5000"  # For simulated device API
# Initialize with your DBC file
# sim = DBCDataSimulator("D:\\Sagar_OneDrive\\OneDrive - Cybernetik Technologies Pvt Ltd\\cybernetik\\UAPR119_\\onsite\\adore\\software\\DBC_2.3kWh.dbc", db_folder=STORED_DBC_PATH, interval=1)

# =========================================================
#  Flask Setup
# =========================================================
app = Flask(__name__, template_folder="templates", static_folder="static")

# socketio = SocketIO(app, cors_allowed_origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("===== BTS Monitoring System Started =====")


def load_thresholds():
    if not os.path.exists(THRESHOLD_FILE):
        save_thresholds(DEFAULT_THRESHOLDS)
    with open(THRESHOLD_FILE, "r") as f:
        return json.load(f)


def save_thresholds(data):
    with open(THRESHOLD_FILE, "w") as f:
        json.dump(data, f, indent=2)
    return True



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
        return json_response({"success": True},200)
    return json_response({"error": "Invalid credentials"}, 401)



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
#  Background Threads - Optimized for High Performance
# =========================================================
def background_reader_thread():
    """
    in the base path check if there is any new file with .excel extension every 5 seconds, if found take the file name and extract the metadata from file name, 
    Examples: 
            1. 2026-01-21 22-38-48_1-8_MK5AJKAPBB00601
            2. 2026-01-10 11-34-35_5-1_ML2AJ9APBA00040
            3. 2026-01-22 09-21-19_1-1_CEK5C68R20AP00627R 
            4. 2026-01-22 09-21-37_1-2_CEK5C68B20AP00627B
    date_time : 
        1.2026-01-21 22:38:48
        2.2026-01-10 11:34:35
        3.2026-01-22 09:21:19
        4.2026-01-22 09:21:37
    battery_id : 
        1.MK5AJKAPBB00601
        2.ML2AJ9APBA00040
        3.CEK5C68R20AP00627R
        4.CEK5C68B20AP00627B
    device_channel : 
        1.1-8
        2.5-1
        3.1-1
        4.1-2
    Test type: 
        1.M → CDC / Sanity 
        2.M → CDC / Sanity 
        3.CE → HRD / HRC
        4.CE → HRD / HRC
    battery type:
        1.K5 : Triangular 
        2.L2 : Moving Pack
        3.K5 : Triangular
        4.K5 : Triangular
    this is just meta data .
    now read the excel file and check if the test is pass or fail based on the thresholds stored in thresholds.json file for the specif battery type and test type.
    and emmite the data to the dashboard via socketio.
    and accordingly log the data in the log file. 
    and finally send the pass or fail status to the plc. 
        """
    while True:
        try:
            # check if new file is available in base path
            time.sleep(DATA_READ_INTERVAL)
            base_path = os.path.join(BASE_DIR, "data_files")
            print(f"Checking for new files in {base_path}...")
            files = [f for f in os.listdir(base_path) if f.endswith(".excel")]
            print(f"Found files: {files}")
            for file in files:
                if file not in PROCESSED_FILES:
                    PROCESSED_FILES.append(file)

                    logging.info(f"Processing file: {file}")
                    # Simulate reading data from the file
                    data = {
                        "temperature": 75.0,
                        "voltage": 240.0,
                        "current": 18.0,
                        "power": 4500.0,
                        "resistance": 900.0,
                    }
                    thresholds = load_thresholds()
                    alerts = {}
                    for key in data:
                        if data[key] > thresholds.get(key, float('inf')):
                            alerts[key] = f"{key} threshold exceeded!"
                            logging.warning(f"{key} value {data[key]} exceeds threshold {thresholds[key]}")
                    
                    socketio.emit("data_update", {"data": data, "alerts": alerts})
                    logging.info(f"Data emitted: {data} with alerts: {alerts}")
                    
                    # Simulate sending pass/fail status to PLC
                    status = "PASS" if not alerts else "FAIL"
                    logging.info(f"Test status for file {file}: {status}")
                    
                    # Remove or archive processed file
                    os.remove(os.path.join(base_path, file))
                    logging.info(f"Processed file removed: {file}")
                else:
                    logging.debug("No new files to process.")
                    continue
        except Exception as e:
            logging.error(f"Error in background_reader_thread: {e}")


# =========================================================
#  Run App
# =========================================================
if __name__ == "__main__":
    reader_thread = threading.Thread(target=background_reader_thread)
    reader_thread.daemon = True
    logging.info("Starting Flask SocketIO Server on port 5001...")
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)
