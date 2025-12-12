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
from dbc_simulator import DBCDataSimulator

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
# Initialize with your DBC file
sim = DBCDataSimulator("D:\\Sagar_OneDrive\\OneDrive - Cybernetik Technologies Pvt Ltd\\cybernetik\\UAPR119_\\onsite\\adore\\software\\DBC_2.3kWh.dbc", db_folder=STORED_DBC_PATH, interval=1)

# =========================================================
#  Flask Setup
# =========================================================
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = SECRET_KEY
# socketio = SocketIO(app, cors_allowed_origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logging.info("===== BTS Monitoring System Started =====")

# =========================================================
#  Global Vars
# =========================================================
ACTIVE_CIRCUITS = []  # circuits being monitored
JWT_TOKEN = None
JWT_EXPIRY = datetime.now(UTC) + timedelta(hours=JWT_EXPIRY_HOURS)
DEVICE_ID = 2


# =========================================================
#  Utility Functions
# =========================================================
def json_response(data, status=200):
    return jsonify(data), status


def discover_database_files(folder_path):
    """
    Discover all SQLite database files in the specified folder
    Returns a list of database files with their metadata
    """
    db_files = []
    if not os.path.exists(folder_path):
        logging.warning(f"Database folder not found: {folder_path}")
        return db_files
    
    try:
        for filename in os.listdir(folder_path):
            if filename.endswith('.db'):
                file_path = os.path.join(folder_path, filename)
                try:
                    # Get file stats
                    stat = os.stat(file_path)
                    
                    # Try to connect and get basic info
                    conn = sqlite3.connect(file_path)
                    cursor = conn.cursor()
                    
                    # Get table names
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Get row count from main table (if exists)
                    row_count = 0
                    if tables:
                        main_table = tables[0]
                        cursor.execute(f"SELECT COUNT(*) FROM {main_table};")
                        row_count = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    db_files.append({
                        'filename': filename,
                        'file_path': file_path,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        'tables': tables,
                        'row_count': row_count
                    })
                    
                except Exception as e:
                    logging.error(f"Error analyzing database file {filename}: {e}")
                    
    except Exception as e:
        logging.error(f"Error discovering database files: {e}")
    
    return db_files


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
    expiry = datetime.now(UTC) + timedelta(hours=JWT_EXPIRY_HOURS)
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
    if datetime.now(UTC) >= JWT_EXPIRY - timedelta(minutes=10):
        JWT_TOKEN, JWT_EXPIRY = create_jwt("admin")
        logging.info("JWT auto-refreshed.")


# =========================================================
#  SQLite Reader - Optimized for Multiple Files & Dynamic Columns
# =========================================================
def read_active_circuit_data(folder_path, circuits):
    result = {"timestamp": datetime.now(UTC).isoformat(), "circuits": []}
    
    # Use connection pooling and batch processing for better performance
    connections = {}
    column_cache = {}
    
    try:
        # print("this is active circuits",circuits)  # For debugging
        for cid in circuits:
            # print("singel",cid)
            try:
                # Get database file path
                if isinstance(cid, dict):
                    db_file = cid.get("file_name")
                    circuit_id = cid.get("circuit_id", cid.get("id", "unknown"))
                else:
                    db_file = f"circuit_{cid}.db"
                    circuit_id = cid
                # print("db_file",db_file)
                # print("folder_path",folder_path)
                if not db_file:
                    continue
                    
                db_path = os.path.join(folder_path, db_file)
                # print("db_path",db_path)
                # Check if file exists
                if not os.path.exists(db_path):
                    print("Database file not found:", db_path)
                    logging.warning(f"Database file not found: {db_path}")
                    continue
                
                # Reuse connection if already open
                if db_path not in connections:
                    connections[db_path] = sqlite3.connect(db_path)
                    connections[db_path].row_factory = sqlite3.Row  # Enable column access by name
                # print("connections",connections)
                conn = connections[db_path]
                cursor = conn.cursor()
                
                # Get table schema dynamically if not cached
                if db_path not in column_cache:
                    # First, find the table name (could be 'readings' or something else)
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    
                    if not tables:
                        logging.warning(f"No tables found in {db_file}")
                        continue
                    
                    # Use the first table (or look for 'readings' specifically)
                    table_name = None
                    for table in tables:
                        if 'reading' in table[0].lower():
                            table_name = table[0]
                            break
                    
                    if not table_name and tables:
                        table_name = tables[0][0]  # Use first table as fallback
                    
                    if not table_name:
                        continue
                    
                    # Get column information
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns_info = cursor.fetchall()
                    
                    # Store column names and table name
                    column_cache[db_path] = {
                        'table_name': table_name,
                        'columns': [col[1] for col in columns_info]  # col[1] is column name
                    }
                
                table_info = column_cache[db_path]
                table_name = table_info['table_name']
                columns = table_info['columns']
                # print("table_name",table_name)
                # print("columns",columns)
                # Read latest data with dynamic columns
                cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 1;")
                row = cursor.fetchone()
                # print("row",row)
                if row:
                    # Build dynamic data structure
                    circuit_data = {
                        "circuit_id": circuit_id,
                        "file_name": db_file,
                        "table_name": table_name
                    }
                    
                    # Map all columns dynamically
                    for i, column_name in enumerate(columns):
                        try:
                            value = row[i] if i < len(row) else None
                            # Try to convert to appropriate type
                            if value is not None:
                                # Try to convert to float for numeric values
                                try:
                                    if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                                        value = float(value)
                                except (ValueError, AttributeError):
                                    pass  # Keep as string if conversion fails
                            
                            circuit_data[column_name.lower()] = value
                        except IndexError:
                            circuit_data[column_name.lower()] = None
                    
                    # Add common mappings for backwards compatibility
                    # Map common column variations to standard names
                    column_mappings = {
                        'temp': 'temperature',
                        'volt': 'voltage', 
                        'curr': 'current',
                        'pow': 'power',
                        'res': 'resistance',
                        'time': 'timestamp'
                    }
                    
                    for old_name, new_name in column_mappings.items():
                        if old_name in circuit_data and new_name not in circuit_data:
                            circuit_data[new_name] = circuit_data[old_name]
                    
                    result["circuits"].append(circuit_data)
                    
            except Exception as e:
                logging.error(f"DB read error for circuit {cid}: {e}")
                continue
                
    finally:
        # Close all connections
        for conn in connections.values():
            try:
                conn.close()
            except:
                pass
    
    return result


# =========================================================
#  Threshold Monitor
# =========================================================
def check_thresholds_and_pause(payload):
    thresholds = load_thresholds()
    for circuit in payload.get("circuits", []):
        for key, limit in thresholds.items():
            if circuit.get(key) and circuit[key] > limit:
                print(f"⚠️ Threshold exceeded on Circuit {circuit['circuit_id']}: {key}={circuit[key]}")
                logging.warning(f"⚠️ Threshold exceeded on Circuit {circuit['circuit_id']}: {key}={circuit[key]}")
                pause_circuit(DEVICE_ID, circuit["circuit_id"])
                break


# =========================================================
#  Device Commands (Actual BTS API Integration)
# =========================================================
def get_circuit_file_name(circuit_id):
    """Get the database file name for a circuit from active circuits"""
    global ACTIVE_CIRCUITS
    for circuit in ACTIVE_CIRCUITS:
        if isinstance(circuit, dict):
            if circuit.get("circuit_id") == circuit_id:
                return circuit.get("file_name", f"circuit_{circuit_id}.db")
    return f"circuit_{circuit_id}.db"

def update_circuit_status(circuit_id, status):
    """Update circuit status in active circuits list"""
    global ACTIVE_CIRCUITS
    for i, circuit in enumerate(ACTIVE_CIRCUITS):
        if isinstance(circuit, dict) and circuit.get("circuit_id") == circuit_id:
            ACTIVE_CIRCUITS[i]["status"] = status
            break

def pause_circuit(device_id, circuit_id):
    """Pause circuit via BTS API and stop data collection"""
    logging.info(f"Pause command → Device {device_id}, Circuit {circuit_id}")
    # print("pause command called for circuit id:", circuit_id)
    try:
        # Build API URL with query parameters
        url = f"{API_BASE_URL}/api/command/pause?circuitNo={circuit_id}&DeviceId={device_id}"
        
        # Prepare payload
        payload = {
            'circuitNo': circuit_id,
            'DeviceId': device_id
        }
        
        # Prepare headers
        headers = {'Content-Type': 'application/json'}
        if JWT_TOKEN:
            headers["Authorization"] = f"Bearer {JWT_TOKEN}"
        
        # Make API call to BTS
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logging.info(f"✓ Circuit {circuit_id} paused successfully via BTS API")
            
            # Pause demo data collection for this circuit (stops insertion but keeps file active)
            file_name = get_circuit_file_name(circuit_id)
            if hasattr(sim, 'pause_collect'):
                sim.pause_collect(file_name)
                logging.info(f"Paused data collection for {file_name}")
            
            # Update circuit status
            update_circuit_status(circuit_id, "paused")
            return {
                "message": f"Circuit {circuit_id} paused successfully",
                "status": "paused",
            }
        else:
            logging.error(f"✗ Failed to pause circuit {circuit_id}: {response.status_code} - {response.text}")
            return {
                "error": f"Failed to pause circuit {circuit_id}",
            }
            
    except requests.RequestException as e:
        logging.error(f"✗ Pause command network error for circuit {circuit_id}: {e}")
        return {"error": f"Network error while pausing circuit {circuit_id}: {str(e)}"}
    except Exception as e:
        logging.error(f"✗ Pause command error for circuit {circuit_id}: {e}")
        return {"error": f"Error pausing circuit {circuit_id}: {str(e)}"}


def stop_circuit(device_id, circuit_id):
    """Stop circuit via BTS API and stop data collection"""
    logging.info(f"Stop command → Device {device_id}, Circuit {circuit_id}")
    
    try:
        # Build API URL with query parameters
        url = f"{API_BASE_URL}/api/command/stop?circuitNo={circuit_id}&DeviceId={device_id}"
        
        # Prepare payload
        payload = {
            'circuitId': circuit_id,
            'deviceId': device_id
        }
        
        # Prepare headers
        headers = {'Content-Type': 'application/json'}
        if JWT_TOKEN:
            headers["Authorization"] = f"Bearer {JWT_TOKEN}"
        
        # Make API call to BTS
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logging.info(f"✓ Circuit {circuit_id} stopped successfully via BTS API")
            
            # Stop demo data collection for this circuit
            file_name = get_circuit_file_name(circuit_id)
            if hasattr(sim, 'stop_collect'):
                sim.stop_collect(file_name)
                logging.info(f"Stopped data collection for {file_name}")
            
            # Update circuit status
            update_circuit_status(circuit_id, "stopped")
            
            # Remove circuit from active circuits if stopped
            global ACTIVE_CIRCUITS
            ACTIVE_CIRCUITS = [c for c in ACTIVE_CIRCUITS if not (
                isinstance(c, dict) and c.get("circuit_id") == circuit_id
            )]
            
            return {
                "message": f"Circuit {circuit_id} stopped successfully",
                "status": "stopped",
            }
        else:
            logging.error(f"✗ Failed to stop circuit {circuit_id}: {response.status_code} - {response.text}")
            return {
                "error": f"Failed to stop circuit {circuit_id}",
                "status_code": response.status_code,
                "response": response.text
            }
            
    except requests.RequestException as e:
        logging.error(f"✗ Stop command network error for circuit {circuit_id}: {e}")
        return {"error": f"Network error while stopping circuit {circuit_id}: {str(e)}"}
    except Exception as e:
        logging.error(f"✗ Stop command error for circuit {circuit_id}: {e}")
        return {"error": f"Error stopping circuit {circuit_id}: {str(e)}"}


def continue_circuit(device_id, circuit_id):
    """Continue circuit via BTS API and restart data collection"""
    logging.info(f"Continue command → Device {device_id}, Circuit {circuit_id}")
    
    try:
        # Build API URL with query parameters
        url = f"{API_BASE_URL}/api/command/Continue?circuitNo={circuit_id}&DeviceId={device_id}"
        
        # Prepare payload
        payload = {
            'circuitNo': circuit_id,
            'DeviceId': device_id
        }
        
        # Prepare headers
        headers = {'Content-Type': 'application/json'}
        if JWT_TOKEN:
            headers["Authorization"] = f"Bearer {JWT_TOKEN}"
        
        # Make API call to BTS
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            logging.info(f"✓ Circuit {circuit_id} continued successfully via BTS API")
            
            # Resume demo data collection for this circuit
            file_name = get_circuit_file_name(circuit_id)
            if hasattr(sim, 'continue_collect'):
                sim.continue_collect(file_name)
                logging.info(f"Resumed data collection for {file_name}")
            
            # Update circuit status
            update_circuit_status(circuit_id, "active")
            
            # Add circuit back to active circuits if not present
            global ACTIVE_CIRCUITS
            circuit_exists = any(
                isinstance(c, dict) and c.get("circuit_id") == circuit_id 
                for c in ACTIVE_CIRCUITS
            )
            
            if not circuit_exists:
                circuit_metadata = {
                    "circuit_id": circuit_id,
                    "device_id": device_id,
                    "start_time": datetime.now(UTC).isoformat(),
                    "status": "active",
                    "file_name": file_name,
                    "file_path": os.path.join(STORED_DBC_PATH, file_name)
                }
                ACTIVE_CIRCUITS.append(circuit_metadata)
            
            return {
                "message": f"Circuit {circuit_id} continued successfully",
                "status": "active",
            }
        else:
            logging.error(f"✗ Failed to continue circuit {circuit_id}: {response.status_code} - {response.text}")
            return {
                "error": f"Failed to continue circuit {circuit_id}",
                "status_code": response.status_code,
                "response": response.text
            }
            
    except requests.RequestException as e:
        logging.error(f"✗ Continue command network error for circuit {circuit_id}: {e}")
        return {"error": f"Network error while continuing circuit {circuit_id}: {str(e)}"}
    except Exception as e:
        logging.error(f"✗ Continue command error for circuit {circuit_id}: {e}")
        return {"error": f"Error continuing circuit {circuit_id}: {str(e)}"}


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


@app.route("/api/database-files", methods=["GET"])
def get_database_files():
    """Get list of all available database files with metadata"""
    try:
        db_files = discover_database_files(STORED_DBC_PATH)
        return json_response({
            "database_files": db_files,
            "folder_path": STORED_DBC_PATH,
            "total_files": len(db_files)
        })
    except Exception as e:
        logging.error(f"Error getting database files: {e}")
        return json_response({"error": "Failed to get database files"}, 500)


@app.route("/api/active-circuits", methods=["GET"])
def get_active_circuits():
    """Get list of currently active circuits being monitored"""
    return json_response({
        "active_circuits": ACTIVE_CIRCUITS,
        "count": len(ACTIVE_CIRCUITS)
    })


@app.route("/api/circuit-data/<int:device_id>/<int:circuit_id>", methods=["GET"])
def get_circuit_data(device_id, circuit_id):
    """Get historical data for a specific circuit"""
    try:
        # Find the circuit in active circuits
        circuit_info = None
        for circuit in ACTIVE_CIRCUITS:
            if isinstance(circuit, dict):
                if circuit.get("circuit_id") == circuit_id and circuit.get("device_id") == device_id:
                    circuit_info = circuit
                    break
            elif circuit == circuit_id:
                circuit_info = {"circuit_id": circuit_id, "device_id": device_id, "file_name": f"circuit_{circuit_id}.db"}
                break
        
        if not circuit_info:
            return json_response({"error": "Circuit not found or not active"}, 404)
        
        # Get database file path
        db_file = circuit_info.get("file_name", f"circuit_{circuit_id}.db")
        db_path = os.path.join(STORED_DBC_PATH, db_file)
        
        if not os.path.exists(db_path):
            return json_response({"error": "Database file not found"}, 404)
        
        # Read data from database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get table name dynamically
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            conn.close()
            return json_response({"error": "No tables found"}, 404)
        
        # Use the first table (or look for 'readings' specifically)
        table_name = None
        for table in tables:
            if 'reading' in table[0].lower():
                table_name = table[0]
                break
        
        if not table_name and tables:
            table_name = tables[0][0]
        
        # Get limit from query parameters (default to 100 latest records)
        limit = request.args.get('limit', 100, type=int)
        
        # Fetch latest records
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT ?;", (limit,))
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        data = []
        for row in rows:
            row_dict = dict(row)
            # Convert timestamp to ISO format if needed
            if 'timestamp' in row_dict and row_dict['timestamp']:
                try:
                    # Try to parse and format timestamp
                    dt = datetime.fromisoformat(str(row_dict['timestamp']).replace('Z', '+00:00'))
                    row_dict['timestamp'] = dt.isoformat()
                except:
                    pass  # Keep original timestamp if parsing fails
            data.append(row_dict)
        
        conn.close()
        
        # Reverse to get chronological order (oldest to newest)
        data.reverse()
        
        return json_response({
            "circuit_id": circuit_id,
            "device_id": device_id,
            "table_name": table_name,
            "data": data,
            "count": len(data)
        })
        
    except Exception as e:
        logging.error(f"Error getting circuit data: {e}")
        return json_response({"error": "Failed to get circuit data"}, 500)


@app.route("/api/command/pause", methods=["POST"])
def api_pause():
    """API endpoint to pause a circuit"""
    try:
        data = request.get_json()
        circuit_id = data.get("circuitId") or data.get("circuitNo")
        device_id = data.get("deviceId") or data.get("DeviceId", DEVICE_ID)
        
        if not circuit_id:
            return json_response({"error": "Circuit ID is required"}, 400)
        
        result = pause_circuit(device_id, circuit_id)
        
        # Return appropriate status code based on result
        if "error" in result:
            return json_response(result, 500)
        else:
            return json_response(result)
            
    except Exception as e:
        logging.error(f"API pause error: {e}")
        return json_response({"error": "Internal server error"}, 500)


@app.route("/api/command/stop", methods=["POST"])
def api_stop():
    """API endpoint to stop a circuit"""
    try:
        data = request.get_json()
        circuit_id = data.get("circuitId") or data.get("circuitNo")
        device_id = data.get("deviceId") or data.get("DeviceId", DEVICE_ID)
        
        if not circuit_id:
            return json_response({"error": "Circuit ID is required"}, 400)
        
        result = stop_circuit(device_id, circuit_id)
        
        # Return appropriate status code based on result
        if "error" in result:
            return json_response(result, 500)
        else:
            return json_response(result)
            
    except Exception as e:
        logging.error(f"API stop error: {e}")
        return json_response({"error": "Internal server error"}, 500)


@app.route("/api/command/continue", methods=["POST"])
def api_continue():
    """API endpoint to continue a circuit"""
    try:
        data = request.get_json()
        circuit_id = data.get("circuitId") or data.get("circuitNo")
        device_id = data.get("deviceId") or data.get("DeviceId", DEVICE_ID)
        
        if not circuit_id:
            return json_response({"error": "Circuit ID is required"}, 400)
        
        result = continue_circuit(device_id, circuit_id)
        
        # Return appropriate status code based on result
        if "error" in result:
            return json_response(result, 500)
        else:
            return json_response(result)
            
    except Exception as e:
        logging.error(f"API continue error: {e}")
        return json_response({"error": "Internal server error"}, 500)


@app.route("/api/command/collect", methods=["POST"])
def start_monitoring():
    global ACTIVE_CIRCUITS
    data = request.get_json()
    # print(data)  # For debugging 
    circuit = data.get("circuitId", [])
    # Validate circuit ID
    if not circuit:
        return json_response({"error": "Circuit ID is required"}, 400)
    
    # Send request to BTSAPI to start monitoring
    try:
        endpoint = f"{API_BASE_URL}/api/DBCUpload/create-db-files"
        send_headers = {}
        
        # Add authorization if available
        if JWT_TOKEN:
            send_headers["Authorization"] = f"Bearer {JWT_TOKEN}"
        
        # Build multipart payload
        multipart = [
            ("DeviceIDs", (None, str(DEVICE_ID))),
            ("CircuitIds", (None, str(circuit))),
            ("TimeDelay", (None, "1000"))
        ]
        
        # Add DBC file (assuming a default file exists)
        dbc_file_path = os.path.join(BASE_DIR, "DBC_2.3kWh.dbc")
        if os.path.exists(dbc_file_path):
            with open(dbc_file_path, "rb") as f:
                multipart.append(("DBCFiles", ("DBC_2.3kWh.dbc", f, "application/octet-stream")))
                
                resp = requests.post(endpoint, headers=send_headers, files=multipart, timeout=10)
                
                if resp.status_code == 200:
                    response_data = resp.json()
                    # print(response_data)  # For debugging
                    # Extract metadata from response
                    circuit_metadata = {
                        "circuit_id": circuit,
                        "device_id": DEVICE_ID,
                        "start_time": datetime.now(UTC).isoformat(),
                        "status": "active"
                    }
                    
                    # Add file information if available
                    if "files" in response_data:
                        for file_info in response_data["files"]:
                            if str(circuit) in file_info.get("filePath", ""):
                                circuit_metadata.update({
                                    "file_name": file_info.get("fileName", ""),
                                    "file_path": file_info.get("filePath", ""),
                                    "created_at": file_info.get("createdAt", "")
                                })
                                break
                    
                    # Store circuit with metadata instead of just ID
                    circuit = circuit_metadata
                    # Start collecting for some files
                    sim.start_collect(circuit_metadata.get("file_name"))
                    
                else:
                    logging.error(f"Failed to start monitoring via BTSAPI: {resp.status_code} - {resp.text}")
                    return json_response({"error": "Failed to start monitoring"}, 500)
        else:
            logging.error(f"DBC file not found: {dbc_file_path}")
            return json_response({"error": "DBC file not found"}, 500)
            
    except Exception as e:
        logging.error(f"Error starting monitoring via BTSAPI: {e}")
        return json_response({"error": "Failed to communicate with BTSAPI"}, 500)
    ACTIVE_CIRCUITS.append(circuit)
    logging.info(f"Monitoring started for {ACTIVE_CIRCUITS}")
    return json_response({"message": f"Monitoring started for circuits ", "circuits": ACTIVE_CIRCUITS})


# @app.route("/api/monitor/stop", methods=["POST"])
# def stop_monitoring():
#     global ACTIVE_CIRCUITS
#     ACTIVE_CIRCUITS = []
#     logging.info("Monitoring stopped.")
#     return json_response({"message": "Monitoring stopped"})


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
#  Demo Data Generation API Endpoints
# =========================================================
@app.route("/api/demo/start", methods=["POST"])
def start_demo():
    """Start demo data generation for testing"""
    try:
        data = request.get_json() or {}
        circuits_to_start = data.get("circuits", [1, 2, 3, 4, 5])  # Default circuits
        
        global ACTIVE_CIRCUITS
        
        # Clear existing circuits
        ACTIVE_CIRCUITS = []
        
        # Add demo circuits to active list
        for circuit_id in circuits_to_start:
            circuit_metadata = {
                "circuit_id": circuit_id,
                "device_id": DEVICE_ID,
                "start_time": datetime.now(UTC).isoformat(),
                "status": "active",
                "file_name": f"circuit_{circuit_id}.db",
                "file_path": os.path.join(STORED_DBC_PATH, f"circuit_{circuit_id}.db"),
                "demo": True
            }
            ACTIVE_CIRCUITS.append(circuit_metadata)
            
            # Start demo data collection for this circuit
            if hasattr(sim, 'start_collect'):
                try:
                    sim.start_collect(f"circuit_{circuit_id}.db")
                    logging.info(f"Started data collection for circuit_{circuit_id}.db")
                except Exception as e:
                    logging.error(f"Error starting collection for circuit {circuit_id}: {e}")
        
        logging.info(f"Demo started for circuits: {circuits_to_start}")
        return json_response({
            "message": "Demo data generation started",
            "circuits": circuits_to_start,
            "active_circuits": ACTIVE_CIRCUITS
        })
        
    except Exception as e:
        logging.error(f"Error starting demo: {e}")
        return json_response({"error": "Failed to start demo"}, 500)


@app.route("/api/demo/stop", methods=["POST"])
def stop_demo():
    """Stop demo data generation"""
    try:
        global ACTIVE_CIRCUITS
        
        # Stop simulator for all demo circuits
        demo_circuits = [c for c in ACTIVE_CIRCUITS if isinstance(c, dict) and c.get("demo")]
        
        for circuit in demo_circuits:
            file_name = circuit.get("file_name", f"circuit_{circuit.get('circuit_id')}.db")
            if hasattr(sim, 'stop_collect'):
                try:
                    sim.stop_collect(file_name)
                    logging.info(f"Stopped data collection for {file_name}")
                except Exception as e:
                    logging.error(f"Error stopping collection for {file_name}: {e}")
        
        # Clear active circuits (remove demo circuits)
        ACTIVE_CIRCUITS = [c for c in ACTIVE_CIRCUITS if not (isinstance(c, dict) and c.get("demo"))]
        
        stopped_circuits = [c.get("circuit_id") for c in demo_circuits if isinstance(c, dict)]
        
        logging.info("Demo data generation stopped")
        return json_response({
            "message": "Demo data generation stopped",
            "stopped_circuits": stopped_circuits
        })
        
    except Exception as e:
        logging.error(f"Error stopping demo: {e}")
        return json_response({"error": "Failed to stop demo"}, 500)


@app.route("/api/demo/status", methods=["GET"])
def demo_status():
    """Get demo status"""
    demo_circuits = [c for c in ACTIVE_CIRCUITS if isinstance(c, dict) and c.get("demo")]
    
    # Get simulator status for all files
    simulator_status = {}
    if hasattr(sim, 'get_all_statuses'):
        simulator_status = sim.get_all_statuses()
    
    return json_response({
        "active": len(demo_circuits) > 0,
        "circuits": [c.get("circuit_id") for c in demo_circuits if isinstance(c, dict)],
        "total_active": len(ACTIVE_CIRCUITS),
        "simulator_status": simulator_status
    })


@app.route("/api/simulator-status", methods=["GET"])
def get_simulator_status():
    """Get detailed simulator status for all files"""
    try:
        if hasattr(sim, 'get_all_statuses'):
            statuses = sim.get_all_statuses()
            return json_response({
                "simulator_statuses": statuses,
                "total_files": len(statuses)
            })
        else:
            return json_response({"error": "Simulator status not available"}, 500)
    except Exception as e:
        logging.error(f"Error getting simulator status: {e}")
        return json_response({"error": "Failed to get simulator status"}, 500)


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
    Optimized background thread for reading multiple database files every second
    """
    last_read_time = 0
    error_count = 0
    max_errors = 10
    
    while True:
        start_time = time.time()
        
        try:
            # Skip if no circuits are active
            if not ACTIVE_CIRCUITS:
                time.sleep(DATA_READ_INTERVAL)
                continue

            # Read data from all active circuits
            payload = read_active_circuit_data(STORED_DBC_PATH, ACTIVE_CIRCUITS)
            # print(payload)  # For debugging
            # Only emit if we have valid data
            if payload and payload.get("circuits"):
                # Log performance metrics occasionally
                read_time = time.time() - start_time
                if time.time() - last_read_time > 30:  # Log every 30 seconds
                    logging.info(f"Read {len(payload['circuits'])} circuits in {read_time:.3f}s")
                    last_read_time = time.time()
                # print("Payload to emit:", payload)  # For debugging
                # Emit data to WebSocket clients
                socketio.emit("live_data", payload)
                
                # Check thresholds and trigger actions if needed
                # check_thresholds_and_pause(payload)
                
                # Reset error count on successful read
                error_count = 0
            else:
                print("No circuit data available")
                logging.warning("No circuit data available")

        except Exception as e:
            error_count += 1
            logging.error(f"Background thread error ({error_count}/{max_errors}): {e}")
            
            # If too many consecutive errors, increase sleep interval
            if error_count >= max_errors:
                logging.error("Too many consecutive errors, increasing sleep interval")
                time.sleep(DATA_READ_INTERVAL * 5)
                error_count = 0  # Reset counter
        
        # Calculate sleep time to maintain precise interval
        elapsed = time.time() - start_time
        sleep_time = max(0, DATA_READ_INTERVAL - elapsed)
        
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            # Log if we're falling behind
            logging.warning(f"Reading took {elapsed:.3f}s, which exceeds {DATA_READ_INTERVAL}s interval")


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
