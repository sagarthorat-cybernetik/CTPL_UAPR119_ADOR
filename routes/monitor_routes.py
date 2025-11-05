import asyncio
import json
import logging
from flask import Blueprint, request
from flask_sock import Sock
from core.db_reader import read_active_circuit_data
from config import STORED_DBC_PATH

monitor_bp = Blueprint("monitor_bp", __name__)
sock = Sock(monitor_bp)

# store currently active circuits (global for simplicity)
ACTIVE_CIRCUITS = []

# ======================================================
# REST Route to start monitoring specific circuits
# ======================================================
@monitor_bp.route("/api/monitor/start", methods=["POST"])
def start_monitoring():
    """
    Accepts JSON: {"circuits": [1,2,3]}
    Marks those circuits as active.
    """
    try:
        data = request.get_json()
        circuits = data.get("circuits", [])
        if not circuits:
            return {"message": "No circuits provided."}, 400

        global ACTIVE_CIRCUITS
        ACTIVE_CIRCUITS = circuits
        return {"message": f"Monitoring started for circuits {circuits}"}, 200

    except Exception as e:
        logging.error(f"Error starting monitoring: {e}")
        return {"message": "Internal error"}, 500


# ======================================================
# WebSocket Route for Live Real-Time Data
# ======================================================
@sock.route("/api/monitor/live")
def live_monitor(ws):
    """
    WebSocket stream that sends real-time DB data every second
    only for active circuits.
    """
    try:
        while True:
            if not ACTIVE_CIRCUITS:
                ws.send(json.dumps({"status": "idle", "message": "No active circuits"}))
                asyncio.sleep(1)
                continue

            data = read_active_circuit_data(STORED_DBC_PATH, ACTIVE_CIRCUITS)
            ws.send(json.dumps(data, default=str))

            # send every 1 second
            asyncio.sleep(1)
    except Exception as e:
        logging.warning(f"WebSocket closed: {e}")
