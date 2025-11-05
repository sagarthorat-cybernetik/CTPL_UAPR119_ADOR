import json
import os
import logging
import requests
from config import API_BASE_URL

# Path to local thresholds JSON file
THRESHOLD_FILE = os.path.join(os.getcwd(), "thresholds.json")

# Default safe limits (you can change these as needed)
DEFAULT_THRESHOLDS = {
    "temperature": 80.0,
    "voltage": 250.0,
    "current": 20.0,
    "power": 5000.0,
    "resistance": 1000.0
}


# =====================================================
# Utility functions
# =====================================================
def load_thresholds():
    """
    Loads thresholds from local JSON file.
    If file doesn't exist, creates it with default values.
    """
    if not os.path.exists(THRESHOLD_FILE):
        save_thresholds(DEFAULT_THRESHOLDS)
        return DEFAULT_THRESHOLDS

    try:
        with open(THRESHOLD_FILE, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logging.error(f"Error loading threshold file: {e}")
        return DEFAULT_THRESHOLDS


def save_thresholds(thresholds: dict):
    """
    Saves new threshold values to local file.
    """
    try:
        with open(THRESHOLD_FILE, "w") as f:
            json.dump(thresholds, f, indent=4)
        logging.info("Thresholds saved successfully.")
    except Exception as e:
        logging.error(f"Error saving threshold file: {e}")


# =====================================================
# Threshold Checking and Auto-Pause Logic
# =====================================================
def check_thresholds_and_pause(data_payload):
    """
    Receives data_payload from db_reader:
    {
      "timestamp": "...",
      "circuits": [
        {"circuit_id": 1, "temperature": 90.2, "voltage": 240.5, ...},
        {"circuit_id": 2, "temperature": 50.1, ...}
      ]
    }

    Checks each value against thresholds.
    If exceeded → triggers Pause API for that circuit.
    """
    thresholds = load_thresholds()
    circuits = data_payload.get("circuits", [])

    for circuit in circuits:
        circuit_id = circuit.get("circuit_id")
        exceeded_metrics = []

        for key, limit in thresholds.items():
            value = circuit.get(key)
            if value is None:
                continue
            try:
                if float(value) > float(limit):
                    exceeded_metrics.append((key, value, limit))
            except Exception:
                pass

        if exceeded_metrics:
            logging.warning(f"Circuit {circuit_id}: Threshold exceeded {exceeded_metrics}")
            trigger_pause(circuit_id, exceeded_metrics)


def trigger_pause(circuit_id, details):
    """
    Calls the /api/command/pause endpoint for the circuit that exceeded threshold.
    """
    try:
        url = f"{API_BASE_URL}/api/command/pause?circuitNo={circuit_id}&DeviceId=2"
        res = requests.post(url, timeout=5)
        if res.status_code == 200:
            logging.info(f"[AUTO-PAUSE] Circuit {circuit_id} paused successfully due to {details}")
        else:
            logging.warning(f"[AUTO-PAUSE] Pause failed ({res.status_code}): {res.text}")
    except Exception as e:
        logging.error(f"[AUTO-PAUSE] Error calling pause API: {e}")
