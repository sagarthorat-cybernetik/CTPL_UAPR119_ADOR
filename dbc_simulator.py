import os
import re
import sqlite3
import time
import threading
import random
import logging
from datetime import UTC, datetime

# ============================================================
#  DBC Data Simulator
# ============================================================

class DBCDataSimulator:
    def __init__(self, dbc_path, db_folder="./Publish_17_10/StoredDbcs", interval=1):
        self.dbc_path = dbc_path
        self.db_folder = os.path.abspath(db_folder)
        self.interval = interval
        self.active_files = {}  # {file_name: status} where status = "running", "paused", "stopping", "stopped"
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.columns = self._parse_dbc_columns()
        os.makedirs(self.db_folder, exist_ok=True)

        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        logging.info("✅ DBCDataSimulator initialized with columns: %s", self.columns)

    # ============================================================
    # 🔍 Parse .DBC file for signal (column) names
    # ============================================================
    def _parse_dbc_columns(self):
        """
        Extract signal (column) names from a DBC file.
        Example line: 'SG_ Voltage : 0|16@1+ (0.01,0) [0|250] "V" Vector__XXX'
        """
        if not os.path.exists(self.dbc_path):
            logging.warning("⚠️ DBC file not found: %s", self.dbc_path)
            return ["temperature", "voltage", "current", "power", "resistance"]

        columns = set()
        with open(self.dbc_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = re.match(r"SG_\s+(\w+)", line.strip())
                if match:
                    columns.add(match.group(1))
        if not columns:
            logging.warning("⚠️ No signal columns found in DBC file.")
            columns = {"temperature", "voltage", "current", "power", "resistance"}
        return sorted(columns)

    # ============================================================
    # 🧱 Ensure Database + Table Structure
    # ============================================================
    def _ensure_db_structure(self, file_path):
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()

            # Build CREATE TABLE dynamically from DBC signals
            cols = ", ".join([f'"{col}" REAL' for col in self.columns])
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS readings (
                    timestamp TEXT,
                    battery_id INTEGER,
                    status TEXT,
                    {cols}
                );
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"DB structure creation failed for {file_path}: {e}")

    # ============================================================
    # 🧮 Generate realistic dummy data
    # ============================================================
    def _generate_data_row(self):
        row = {}
        for col in self.columns:
            name = col.lower()
            if "temp" in name:
                row[col] = random.uniform(25.0, 70.0)
            elif "volt" in name:
                row[col] = random.uniform(210.0, 240.0)
            elif "curr" in name:
                row[col] = random.uniform(1.0, 6.0)
            elif "power" in name:
                row[col] = random.uniform(100.0, 1200.0)
            elif "res" in name:
                row[col] = random.uniform(10.0, 200.0)
            elif "status" in name:
                row[col] = random.choice([0, 4])
            else:
                row[col] = random.uniform(0.0, 100.0)
        return row

    # ============================================================
    # 🚀 Main loop (runs in single thread)
    # ============================================================
    def _run(self):
        logging.info("🧠 Simulator background thread started.")
        while not self.stop_event.is_set():
            time.sleep(self.interval)
            with self.lock:
                active_files = dict(self.active_files)  # Copy to avoid modification during iteration

            for fname, status in active_files.items():
                try:
                    db_path = os.path.join(self.db_folder, fname)
                    self._ensure_db_structure(db_path)

                    # Only insert data if file is in running state or stopping (for final record)
                    if status == "running" or status == "stopping":
                        data = self._generate_data_row()
                        data["timestamp"] = datetime.now(UTC).isoformat()
                        # Use file name to generate a consistent battery_id for this file
                        battery_id = hash(fname) % 9000 + 1000  # Ensures range 1000-9999
                        data["battery_id"] = battery_id
                        
                        # Set status based on file state
                        if status == "stopping":
                            data["status"] = 5  # Final stop status
                        else:
                            data["status"] = random.randint(1, 4)  # Normal operational statuses
                        
                        cols = ["timestamp", "battery_id", "status"] + self.columns
                        vals = [data[c] for c in cols]
                        placeholders = ", ".join(["?"] * len(cols))

                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute(f"INSERT INTO readings ({', '.join(cols)}) VALUES ({placeholders})", vals)
                        conn.commit()
                        conn.close()

                        logging.debug(f"Inserted row into {fname} with status {data['status']}")

                        # If this was the final stop record, mark as stopped
                        if status == "stopping":
                            with self.lock:
                                self.active_files[fname] = "stopped"
                                logging.info(f"🛑 File {fname} stopped - final record inserted with status=5")
                    
                    # Skip data insertion for paused or stopped files
                    elif status in ["paused", "stopped"]:
                        logging.debug(f"Skipping data insertion for {fname} - status: {status}")

                except Exception as e:
                    logging.error(f"❌ Insert error for {fname}: {e}")

        logging.info("🧩 Simulator thread exited cleanly.")

    # ============================================================
    # ▶️ Start data collection for one file
    # ============================================================
    def start_collect(self, file_name):
        with self.lock:
            current_status = self.active_files.get(file_name)
            if current_status in [None, "stopped"]:
                self.active_files[file_name] = "running"
                logging.info(f"✅ Started collecting for {file_name}")
            elif current_status in ["paused", "stopping"]:
                self.active_files[file_name] = "running"
                logging.info(f"▶️ Resumed collecting for {file_name}")
            else:
                logging.info(f"ℹ️ File {file_name} is already running.")

    # ============================================================
    # ⏸️ Pause data collection for one file (stops data insertion but keeps file active)
    # ============================================================
    def pause_collect(self, file_name):
        with self.lock:
            if file_name in self.active_files and self.active_files[file_name] == "running":
                self.active_files[file_name] = "paused"
                logging.info(f"⏸️ Paused collection for {file_name}")
            else:
                logging.info(f"⚠️ File {file_name} is not running or not active.")

    # ============================================================
    # ▶️ Continue/Resume data collection for one file
    # ============================================================
    def continue_collect(self, file_name):
        with self.lock:
            current_status = self.active_files.get(file_name)
            if current_status in ["paused", "stopped"]:
                self.active_files[file_name] = "running"
                logging.info(f"▶️ Continued collection for {file_name}")
            else:
                logging.info(f"⚠️ File {file_name} is not paused/stopped or not active.")

    # ============================================================
    # ⏹ Stop data collection for one file (inserts final record with status=5)
    # ============================================================
    def stop_collect(self, file_name):
        with self.lock:
            current_status = self.active_files.get(file_name)
            if current_status in ["running", "paused"]:
                self.active_files[file_name] = "stopping"
                logging.info(f"🛑 Stopping collection for {file_name} - will insert final record with status=5")
            else:
                logging.info(f"⚠️ File {file_name} is not active or already stopped.")

    # ============================================================
    # 📊 Get status of a specific file
    # ============================================================
    def get_file_status(self, file_name):
        with self.lock:
            return self.active_files.get(file_name, "not_active")

    # ============================================================
    # 📋 Get all active files and their statuses
    # ============================================================
    def get_all_statuses(self):
        with self.lock:
            return dict(self.active_files)

    # ============================================================
    # 🧹 Stop everything cleanly
    # ============================================================
    def stop_all(self):
        with self.lock:
            for fname in list(self.active_files.keys()):
                if self.active_files[fname] in ["running", "paused"]:
                    self.active_files[fname] = "stopping"
        self.stop_event.set()
        self.thread.join(timeout=2)
        logging.info("🧼 Simulator stopped all collections.")
