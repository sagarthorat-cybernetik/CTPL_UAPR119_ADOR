import os
import time
import json
import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from wsgiref import headers
import pandas as pd
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

config_file = os.path.join(BASE_DIR, "config.json")
PROCESSED_FILES = []
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)


DATA_READ_INTERVAL = 1
DEFAULT_THRESHOLDS = {
    "charge": {
        "step": 1,
        "Cell_Deviation_min": 50,
        "Cell_Deviation_max": 50,
        "Capacity_min": 1000,
        "Capacity_max": 1000,
        "Pack_Voltage_min": 48,
        "Pack_Voltage_max": 48,
        "Max_Cell_Voltage_min": 4.2,
        "Max_Cell_Voltage_max": 4.2,
        "Min_Cell_Voltage_min": 3.0,
        "Min_Cell_Voltage_max": 3.0,
        "Max_Cell_Temperature_min": 60,
        "Max_Cell_Temperature_max": 60,
        "Min_Cell_Temperature_min": 0,
        "Min_Cell_Temperature_max": 0,
        "SOC_min": 20,
        "SOC_max": 20,
        "Temperature_Difference_min": 15,
        "Temperature_Difference_max": 15,
    },
    "discharge": {
        "step": 1,
        "Cell_Deviation_min": 5,
        "Cell_Deviation_max": 50,
        "Capacity_min": 1000,
        "Capacity_max": 1000,
        "Pack_Voltage_min": 48,
        "Pack_Voltage_max": 48,
        "Max_Cell_Voltage_min": 4.2,
        "Max_Cell_Voltage_max": 4.2,
        "Min_Cell_Voltage_min": 3.0,
        "Min_Cell_Voltage_max": 3.0,
        "Max_Cell_Temperature_min": 60,
        "Max_Cell_Temperature_max": 60,
        "Min_Cell_Temperature_min": 0,
        "Min_Cell_Temperature_max": 0,
        "SOC_min": 20,
        "SOC_max": 20,
        "Temperature_Difference_min": 15,
        "Temperature_Difference_max": 15,
    }
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
file_lock = threading.Lock()


def load_thresholds():
    try:
        if not os.path.exists(config_file):
            save_thresholds(DEFAULT_THRESHOLDS)
        with open(config_file, "r") as f:
            # take only thresholds part from the config file
            threshold = json.load(f)
            return threshold
    except Exception as e:
        print(f"Error loading thresholds: {e}")
        return DEFAULT_THRESHOLDS

def save_thresholds(data):
    try:
        with open(config_file, "r") as f:
            existing_data = json.load(f)
        if "Thresholds" not in existing_data:
            existing_data["Thresholds"] = {}

        # incoming data format:
        # { "L2": { "CDC": { "charge": {...}, "discharge": {...} } } }

        for model_name, model_block in data.items():
            if model_name not in existing_data["Thresholds"]:
                existing_data["Thresholds"][model_name] = {}

            for test_type, test_block in model_block.items():
                if test_type not in existing_data["Thresholds"][model_name]:
                    existing_data["Thresholds"][model_name][test_type] = {}

                for mode in ["charge", "discharge"]:
                    if mode not in test_block:
                        continue

                    if mode not in existing_data["Thresholds"][model_name][test_type]:
                        existing_data["Thresholds"][model_name][test_type][mode] = {}

                    # 🔥 SAFE MERGE HERE
                    existing_data["Thresholds"][model_name][test_type][mode].update(
                        test_block[mode]
                    )

        with open(config_file, "w") as f:
            json.dump(existing_data, f, indent=2)

        return True

    except Exception as e:
        logging.error(f"Error saving thresholds: {e}")
        return False



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

@app.route("/api/headers", methods=["POST"])
def update_headers():
    data = request.get_json()
    try:
        # Load existing config
        with open(config_file, "r") as f:
            existing_data = json.load(f)
        # Ensure "Headers" key exists
        if "Headers" not in existing_data:
            existing_data["Headers"] = {}

        for model_name, model_block in data.items():
            for test_type, test_block in model_block.items():
                if model_name not in existing_data["Headers"]:
                    existing_data["Headers"][model_name] = {}
                if test_type not in existing_data["Headers"][model_name]:
                    existing_data["Headers"][model_name][test_type] = {}
                existing_data["Headers"][model_name][test_type].update(
                    test_block
                )

        # Write back to file
        with open(config_file, "w") as f:
            json.dump(existing_data, f, indent=2)

        logging.info(f"Headers updated: {existing_data['Headers']}")
        return json_response({"message": "Headers updated"})

    except Exception as e:
        logging.error(f"Error saving headers: {e}")
        return json_response({"error": "Failed to update headers"}, 500)
    
@app.route("/api/devices", methods=["GET"])
def get_devices(): 
    devices = [{"id": 2, "name": "BTS Controller 2"}]
    return json_response({"devices": devices})


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
def read_sheet(file_path=None, sheet_name=None):
    return pd.read_excel(file_path, sheet_name=sheet_name)

def max_temp_diff(df=None,min_col="MinTemp", max_col="MaxTemp",step_no=None):
    if step_no is not None:
        if "-" in step_no:
            step_parts = step_no.split("-")
            if len(step_parts) == 2:
                start_step = int(step_parts[0])
                end_step = int(step_parts[1])
                df = df[(df["Step Number"] >= start_step) & (df["Step Number"] <= end_step)]
        else:
            step_int = int(step_no)
            df = df[df["Step Number"] == step_int]
    else:
        df = df
    return (df[max_col]).max() - (df[min_col]).max()

def safe_max(df=None, col=None,step_no=None):
    #  filter the dataframe based on the step_parts if step is come like ["1-8"] then filter all steps from 1 to 8
    df_filtered = pd.DataFrame()
    if step_no is not None:
        if "-" in step_no:
            step_parts = step_no.split("-")
            if len(step_parts) == 2:
                start_step = int(step_parts[0])
                end_step = int(step_parts[1])
                df_filtered = df[(df["Step Number"] >= start_step) & (df["Step Number"] <= end_step)]
        else:
            step_int = int(step_no)
            df_filtered = df[df["Step Number"] == step_int]
    else:
        df_filtered = df
    return df_filtered[col].max() if not df_filtered.empty else None

def safe_sum(df=None, col=None, step_no=None):
    if step_no is not None:
        if "-" in step_no:
            step_parts = step_no.split("-")
            if len(step_parts) == 2:
                start_step = int(step_parts[0])
                end_step = int(step_parts[1])
                df = df[(df["Step Number"] >= start_step) & (df["Step Number"] <= end_step)]
        else:
            step_int = int(step_no)
            df = df[df["Step Number"] == step_int]
    else:
        df = df

    return df[col].sum() if not df.empty else None

def safe_last(df=None, col=None):
    return df[col].iloc[-1] if not df.empty else None

def safe_last_step(df=None, col=None, step_no=None):
    if step_no is not None:
        if "-" in step_no:
            step_parts = step_no.split("-")
            if len(step_parts) == 2:
                start_step = int(step_parts[0])
                end_step = int(step_parts[1])
                df = df[(df["Step Number"] >= start_step) & (df["Step Number"] <= end_step)]
        else:
            step_int = int(step_no)
            df = df[df["Step Number"] == step_int]
    else:
        df = df
    return df[col].iloc[-1] if not df.empty else None

def check_range(value, min_val=None, max_val=None):
    if value is None:
        return False, "Value missing"

    if min_val is not None and value < min_val:
        return False, f"{value} < min {min_val}"

    if max_val is not None and value > max_val:
        return False, f"{value} > max {max_val}"

    return True, "OK"

def evaluate_thresholds(data, thresholds):
    """
    data: extracted test values
    thresholds: config["Thresholds"]["charge"] or ["discharge"]
    """
    results = {}
    overall_pass = True
    for mode in ["charge", "discharge"]:
        for key, value in data[mode].items():
            min_key = f"{key}_min"
            max_key = f"{key}_max"
            min_val = float(thresholds[mode][min_key])
            max_val = float(thresholds[mode][max_key])
            is_ok, reason = check_range(value, min_val, max_val)

            results[key] = {
                "value": value,
                "min": min_val,
                "max": max_val,
                "status": "PASS" if is_ok else "FAIL",
                "reason": reason
            }

            if not is_ok:
                overall_pass = False
    return overall_pass, results

def send_result_to_plc(client, db, byte, bit, status):
    # PASS = 1, FAIL = 0
    value = True if status == "PASS" else False
    # print(f"Sending to PLC: DB{db}.DBX{byte}.{bit} = {value}")
    # write_bool_to_plc(client, db, byte, bit, value)

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
            data = {}
            # check if new file is available in base path
            time.sleep(DATA_READ_INTERVAL)
            base_path = os.path.join(BASE_DIR, "data_files")
            files = [f for f in os.listdir(base_path) if f.endswith(".xlsx")]
            # print("Files found:", files)
            for file in files:
                if file not in PROCESSED_FILES:
                    # PROCESSED_FILES.append(file)

                    logging.info(f"Processing file: {file}")
                    
                    # Extract metadata from file name
                    parts = file.split("_")
                    date_str = parts[0]
                    device_channel = parts[1]
                    battery_id = parts[2].replace(".xlsx", "")
                    date_time = datetime.strptime(date_str, "%Y-%m-%d %H-%M-%S")
                    if battery_id.startswith("M"):
                        test_type = "CDC"
                    else:
                        test_type = "HRD"
                    
                    if test_type == "CDC":
                        battery_type = battery_id[1] + battery_id[2]  # e.g., L2
                    else:
                        battery_type = battery_id[2] + battery_id[3]  # e.g., K5
                    # print(f"fileName : {file},DateTime: {date_time}, Device Channel: {device_channel}, Battery ID: {battery_id}, Test Type: {test_type}, Battery Type: {battery_type}")
                    #  reading data from the file
                    safe_file = " ".join(file.split())
                    file_path = os.path.join(base_path, safe_file)

                    with file_lock:
                        try:
                            with open(os.path.join(BASE_DIR, "config.json"), "r") as cf:
                                config = json.load(cf)

                            headers = config["Headers"]
                            headers = headers[battery_type]
                            is_standerd = headers[test_type]["non_standard"]
                            headers = headers[test_type]['header']
                            # print("Using test type", test_type ,"headers:", headers)
                            # print("Using headers:", headers)
                            # extract the unique sheetNO and read only those sheets
                            unique_sheets = set()
                            for key, value in headers.items():
                                if key.startswith("Sheet_Name_"):
                                    unique_sheets.add(int(value))
                            sheets_data = {}
                            for sheet in unique_sheets:
                                sheets_data[sheet] = read_sheet(file_path, int(sheet))
                                 
                            # print("here")
                            # print("headers:", headers)
                            # print("sheets_data:", headers["Sheet_Name_Max_Cell_Voltage"])
                            # print("col", headers["Max_Cell_Voltage"])
                            # print("step no:", config["Thresholds"][battery_type][test_type]["charge"]["Max_Cell_Voltage_step"])
                            # print(sheets_data)    
                            # print(sheets_data[int(headers["Sheet_Name_Cell_Deviation"])])   
                            data = {
                                "Battery Serial No": battery_id,
                                "charge":{
                                    "Cell_Deviation": safe_max(df=sheets_data[int(headers["Sheet_Name_Cell_Deviation"])], col=headers["Cell_Deviation"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["cell_deviation_step"]) if is_standerd else max_temp_diff(df=sheets_data[int(headers["Sheet_Name_Cell_Deviation"])], min_col=headers["Min_Cell_Temperature"], max_col=headers["Max_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["cell_deviation_step"]),

                                    "Capacity": safe_sum(df=sheets_data[int(headers["Sheet_Name_Capacity"])], col=headers["Capacity"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["capacity_step"]),
                                    
                                    "Pack_Voltage": safe_sum(df=sheets_data[int(headers["Sheet_Name_Pack_Voltage"])], col=headers["Pack_Voltage"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["pack_voltage_step"]),
                                    
                                    "Max_Cell_Voltage" : safe_max(df=sheets_data[int(headers["Sheet_Name_Max_Cell_Voltage"])], col=headers["Max_Cell_Voltage"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["Max_Cell_Voltage_step"]),
                                    
                                    "Min_Cell_Voltage": safe_max(df=sheets_data[int(headers["Sheet_Name_Min_Cell_Voltage"])], col=headers["Min_Cell_Voltage"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["Min_Cell_Voltage_step"]),
                                    
                                    "Max_Cell_Temperature": safe_max(df=sheets_data[int(headers["Sheet_Name_Max_Cell_Temperature"])], col=headers["Max_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["Max_Cell_Temperature_step"]),
                                    
                                    "Min_Cell_Temperature": safe_max(df=sheets_data[int(headers["Sheet_Name_Min_Cell_Temperature"])], col=headers["Min_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["Min_Cell_Temperature_step"]),
                                    
                                    "SOC" : safe_last_step(df= sheets_data[int(headers["Sheet_Name_SOC"])], col=headers["SOC"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["SOC_step"]),
                                    #
                                    
                                    "End_SOC": safe_last(df= sheets_data[int(headers["Sheet_Name_SOC"])], col=headers["SOC"]),
                                    
                                    "temperature_difference": max_temp_diff(df=sheets_data[int(headers["Sheet_Name_Max_Cell_Temperature"])], min_col=headers["Min_Cell_Temperature"], max_col=headers["Max_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["temperature_difference_step"])                                
                                },
                                "discharge":{
                                    "Cell_Deviation": safe_max(df=sheets_data[int(headers["Sheet_Name_Cell_Deviation"])], col=headers["Cell_Deviation"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["cell_deviation_step"]) if is_standerd else max_temp_diff(df=sheets_data[int(headers["Sheet_Name_Cell_Deviation"])], min_col=headers["Min_Cell_Temperature"], max_col=headers["Max_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["cell_deviation_step"]),
                                
                                    "Capacity": safe_sum(df=sheets_data[int(headers["Sheet_Name_Capacity"])], col=headers["Capacity"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["capacity_step"]),
                                    
                                    "Pack_Voltage": safe_sum(df=sheets_data[int(headers["Sheet_Name_Pack_Voltage"])], 
                                    col=headers["Pack_Voltage"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["pack_voltage_step"]),
                                    
                                    "Max_Cell_Voltage" : safe_max(df=sheets_data[int(headers["Sheet_Name_Max_Cell_Voltage"])], col=headers["Max_Cell_Voltage"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["Max_Cell_Voltage_step"]),
                                    
                                    "Min_Cell_Voltage": safe_max(df=sheets_data[int(headers["Sheet_Name_Min_Cell_Voltage"])], col=headers["Min_Cell_Voltage"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["Min_Cell_Voltage_step"]),
                                    
                                    "Max_Cell_Temperature": safe_max(df=sheets_data[int(headers["Sheet_Name_Max_Cell_Temperature"])], col=headers["Max_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]
                                    ["Max_Cell_Temperature_step"]),
                                    
                                    "Min_Cell_Temperature": safe_max(df=sheets_data[int(headers["Sheet_Name_Min_Cell_Temperature"])], col=headers["Min_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["Min_Cell_Temperature_step"]),
                                    
                                    "SOC" : safe_last_step(df= sheets_data[int(headers["Sheet_Name_SOC"])], col=headers["SOC"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["SOC_step"]),
                                    
                                    "End_SOC": safe_last(df= sheets_data[int(headers["Sheet_Name_SOC"])], col=headers["SOC"]),
                                    
                                    "temperature_difference": max_temp_diff(df=sheets_data[int(headers["Sheet_Name_Max_Cell_Temperature"])], min_col=headers["Min_Cell_Temperature"], max_col=headers["Max_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["discharge"]["temperature_difference_step"])
                                
                                }
                            }


                        except Exception as e:
                            print("Excel read FAILED:", repr(e))
                            raise
                        
                    # print("Extracted Data:", data)
                    thresholds_config = load_thresholds()
                    # print("Loaded Thresholds:", thresholds_config)
                    threshold_block = thresholds_config["Thresholds"][battery_type][test_type]
                    # print("Using Threshold Block:", threshold_block)
                    print("Evaluating charge thresholds...")
                    # data = data["charge"] if test_type == "CDC" else data["discharge"]
                    overall_pass, evaluated = evaluate_thresholds(data, threshold_block)
                    print("Evaluation Results:", evaluated, "Overall Pass:", overall_pass)
                    final_status = "PASS" if overall_pass else "FAIL"
                    send_result_to_plc(None, None, None, None, final_status)

                    socketio.emit(
                        "data_update",
                        {
                            "meta": {
                                "battery_id": battery_id,
                                "battery_type": battery_type,
                                "test_type": test_type,
                                "device_channel": device_channel,
                                "timestamp": date_time.strftime("%Y-%m-%d %H:%M:%S"),
                            },
                            "results": data,
                            "evaluated": evaluated,
                            "final_status": final_status
                        }
                    )
                    logging.info(f"Data emitted: {data}")
                    thresholds = load_thresholds()
                    alerts = {}
                    for key in data:
                        if data[key] > thresholds.get(key, float('inf')):
                            alerts[key] = f"{key} threshold exceeded!"
                            logging.warning(f"{key} value {data[key]} exceeds threshold {thresholds[key]}")
                    
                    socketio.emit("data_update", {"data": data, "alerts": alerts})
                    logging.info(f"Data emitted: {data} with alerts: {alerts}")
                    
                    #  sending pass/fail status to PLC
                    status = "PASS" if not alerts else "FAIL"
                    logging.info(f"Test status for file {file}: {status}")
                    
                    # Remove or archive processed file
                    # os.remove(os.path.join(base_path, file))
                    # logging.info(f"Processed file removed: {file}")
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
    reader_thread.start()
    logging.info("Starting Flask SocketIO Server on port 5001...")
    socketio.run(app, host="0.0.0.0", port=5001, debug=False, use_reloader=False)
