import os
import sqlite3
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import STORED_DBC_PATH

# ===================================================
# Helper Functions
# ===================================================

def get_columns_from_dbc(dbc_path: str):
    """
    Reads column names from .dbc definition.
    Example: ["timestamp", "temperature", "voltage", "current", "power"]
    """
    try:
        with open(dbc_path, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logging.error(f"Error reading DBC file: {e}")
        # fallback default
        return ["timestamp", "temperature", "voltage", "current", "power", "resistance"]


def find_db_for_circuit(folder_path: str, circuit_id: int):
    """
    Finds the latest .db file for a specific circuit ID in the folder.
    Example filenames: RealTimeData_<deviceId>_<circuitId>_<timestamp>.db
    """
    try:
        candidates = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.endswith(".db") and f"_{circuit_id}_" in f
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return candidates[0]  # latest one
    except Exception as e:
        logging.error(f"Error finding DB for circuit {circuit_id}: {e}")
        return None


def read_last_row_from_db(db_path: str, dbc_columns: list):
    """
    Reads the last row of valid columns from a specific DB file.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Find first table name
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if not tables:
            conn.close()
            return None
        table_name = tables[0][0]

        # Get actual DB column names
        cursor.execute(f"PRAGMA table_info({table_name});")
        actual_cols = [col[1] for col in cursor.fetchall()]

        # Match only those present in DBC
        valid_columns = [c for c in dbc_columns if c in actual_cols]
        if not valid_columns:
            conn.close()
            return None

        cols_str = ", ".join(valid_columns)
        cursor.execute(f"SELECT {cols_str} FROM {table_name} ORDER BY ROWID DESC LIMIT 1;")
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return dict(zip(valid_columns, row))

    except Exception as e:
        logging.error(f"Error reading db {db_path}: {e}")
        return None


def read_active_circuit_data(folder_path: str, active_circuits: list):
    """
    Reads last row data for all active circuit DBs in parallel.
    Returns combined data payload.
    """
    dbc_columns = get_columns_from_dbc(os.path.join(STORED_DBC_PATH, "columns.dbc"))
    payload = {"timestamp": datetime.now().isoformat(), "circuits": []}

    with ThreadPoolExecutor(max_workers=min(len(active_circuits), 16)) as executor:
        future_to_circuit = {}

        for circuit_id in active_circuits:
            db_path = find_db_for_circuit(folder_path, circuit_id)
            if db_path:
                future = executor.submit(read_last_row_from_db, db_path, dbc_columns)
                future_to_circuit[future] = (circuit_id, db_path)

        for future in as_completed(future_to_circuit):
            circuit_id, db_path = future_to_circuit[future]
            try:
                data = future.result()
                if data:
                    data["circuit_id"] = circuit_id
                    data["file_name"] = os.path.basename(db_path)
                    payload["circuits"].append(data)
            except Exception as e:
                logging.error(f"Error processing circuit {circuit_id}: {e}")

    return payload
