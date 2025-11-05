"""
=========================================================
BTS Monitoring System — Configuration File
=========================================================

This file contains all constants and configurable paths
for the backend, device APIs, database file storage, and
application runtime settings.
"""

import os

# =========================================================
# 1️⃣ Flask Basic Configuration
# =========================================================
SECRET_KEY = "your-very-secure-secret-key"  # Change in production

# Root project path (auto-detect)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Log file directory
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app.log")

# =========================================================
# 2️⃣ API Configuration
# =========================================================
# Base URL for your local or deployed device API backend
# (the one you provided earlier with endpoints like /api/command/pause)
API_BASE_URL = "http://localhost:5000"  # Replace with your device API base if different

# Default device ID (used for internal testing/demo)
DEFAULT_DEVICE_ID = 2

# =========================================================
# 3️⃣ Database Configuration
# =========================================================
# Folder where all generated SQLite .db files are stored
# (Path to your folder: \Publish_17_10\StoredDbcs\)
STORED_DBC_PATH = os.path.join(BASE_DIR, "Publish_17_10", "StoredDbcs")
os.makedirs(STORED_DBC_PATH, exist_ok=True)

# =========================================================
# 4️⃣ Data Handling and Interval Settings
# =========================================================
# How frequently the backend should read data from .db files (seconds)
DATA_READ_INTERVAL = 1  # every 1 second

# Threading configurations
MAX_CIRCUITS = 16  # maximum circuits running simultaneously
THREAD_POOL_SIZE = min(MAX_CIRCUITS, 16)

# =========================================================
# 5️⃣ Security and JWT Configuration
# =========================================================
JWT_EXPIRY_HOURS = 24  # Token validity duration
REFRESH_BEFORE_EXPIRY_MINUTES = 10  # When to auto-refresh before expiry

# =========================================================
# 6️⃣ Threshold Configuration
# =========================================================
# Path to thresholds.json (auto-created if not present)
THRESHOLD_FILE = os.path.join(BASE_DIR, "thresholds.json")

# Default safe operating limits
DEFAULT_THRESHOLDS = {
    "temperature": 80.0,
    "voltage": 250.0,
    "current": 20.0,
    "power": 5000.0,
    "resistance": 1000.0,
}

# =========================================================
# 7️⃣ Database Export Settings
# =========================================================
# Path for exported Excel or CSV files (optional)
EXPORT_PATH = os.path.join(BASE_DIR, "exports")
os.makedirs(EXPORT_PATH, exist_ok=True)

# =========================================================
# 8️⃣ Frontend Settings
# =========================================================
# HTML templates and static assets
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")
STATIC_FOLDER = os.path.join(BASE_DIR, "static")

# =========================================================
# 9️⃣ Developer Mode Toggle
# =========================================================
DEBUG_MODE = True  # Set to False in production

# =========================================================
# ✅ Print confirmation on startup
# =========================================================
if __name__ == "__main__":
    print("✅ BTS Configuration Loaded")
    print(f"Base Directory: {BASE_DIR}")
    print(f"Stored DB Path: {STORED_DBC_PATH}")
    print(f"Log File: {LOG_FILE}")
    print(f"API Base URL: {API_BASE_URL}")
