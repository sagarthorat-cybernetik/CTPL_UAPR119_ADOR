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
from pyModbusTCP.client import ModbusClient
import pyodbc

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
PLC_REGISTERS = {
    "1": {
        "start":60
    },
    "5": {
        "start":44
    },
    "6": {
        "start":42
    }
}
PRVEIOS_BATTERY_END_TIME = {
    "6":{
        "1":0,
        "2":0,
    },
    "5":{
        "1":0,
        "2":0,
        "3":0,
        "4":0,
        "5":0,
        "6":0,
        "7":0,
        "8":0,
        "9" :0,
        "10":0,
        "11":0,
        "12":0,
        "13":0,
        "14":0,
        "15":0,
        "16":0,
    },
    "1":{
        "1":0,
        "2":0,
        "3":0,
        "4":0,
        "5":0,
        "6":0,
        "7":0,
        "8":0,
        "9" :0,
        "10":0,
        "11":0,
        "12":0,
        "13":0,
        "14":0,
        "15":0,
        "16":0,

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

def connect_plc():
    plc = ModbusClient(host="192.168.205.161", port=502, auto_open=True)
    return plc

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
        logging.error(f"Error loading thresholds: {e}")
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

def safe_step_time(test_type,df):
    if (test_type == "Sanity" or test_type == "CDC"):
        if not {"Step Number", "Start Absolute Time", "End Absolute Time"}.issubset(df.columns):
            return None

        start_step = df["Step Number"].min()
        end_step = df["Step Number"].max()

        start_time = df.loc[df["Step Number"] == start_step, "Start Absolute Time"].iloc[0]
        end_time = df.loc[df["Step Number"] == end_step, "End Absolute Time"].iloc[0]

        start_time = pd.to_datetime(start_time, errors="coerce")
        end_time = pd.to_datetime(end_time, errors="coerce")
        if pd.isna(start_time) or pd.isna(end_time):
            return None
        return start_time, end_time, (end_time - start_time)
    else:
        if not {"Step Number", "Absolute time"}.issubset(df.columns):
            return None
        start_step = df["Step Number"].min()
        end_step = df["Step Number"].max()

        start_time = df["Absolute time"].iloc[0]
        end_time = df["Absolute time"].iloc[-1]
        # FIX: replace last ':' with '.'
        def normalize_time(t):
            if t.count(":") >= 3:
                return t[::-1].replace(":", ".", 1)[::-1]
            return t
        start_time = pd.to_datetime(normalize_time(start_time), errors="coerce")
        end_time = pd.to_datetime(normalize_time(end_time), errors="coerce")


        if pd.isna(start_time) or pd.isna(end_time):
            return None, None, None

        return start_time, end_time, (end_time - start_time)
        

def check_range(value, min_val=None, max_val=None):
    if value is None:
        return False, "Value missing"

    if min_val is not None and value < min_val:
        return False, f"{value} < min {min_val}"

    if max_val is not None and value > max_val:
        return False, f"{value} > max {max_val}"

    return True, "OK"
def to_native(val):
    if hasattr(val, "item"):
        return val.item()
    return val

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
                "value": to_native(value),
                "min": min_val,
                "max": max_val,
                "status": "PASS" if is_ok else "FAIL",
                "reason": reason
            }

            if not is_ok:
                overall_pass = False
    return overall_pass, results

def send_result_to_plc(device, circuit, status):
    # PASS = 1, FAIL = 0
    # check plc is connected or not
    plc = connect_plc()

    # if not plc.is_open:
    #     print("PLC not connected.")
    #     return
    
    value = 1 if status == "PASS" else 2

    try:
        plc.write_single_register(int(PLC_REGISTERS[device]['start'])+(int(circuit)-1), value)
        logging.info(f"Sent result to PLC for Device {device} Circuit {circuit}: {status}")
    except Exception as e:
        print(f"Error sending data to PLC: {e}")
        logging.error(f"Error sending data to PLC for Device {device} Circuit {circuit}: {e}")


##--------------------------------------------------------
##  Start Send Result to Database
##--------------------------------------------------------
  # Database connection
# database connection string for sql server mssql+pyodbc://dbuserz03:CTPL%40123123@192.168.200.24:1433/ZONE03_REPORTS?driver=ODBC+Driver+17+for+SQL+Server
DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.200.24,1433;"
    "DATABASE=ZONE03_REPORTS;"
    "UID=dbuserz03;"
    "PWD=CTPL@123123;"
    "TrustServerCertificate=yes;"
)

def connect_db():
        try:
            conn = pyodbc.connect(DB_CONNECTION_STRING)
            return conn
        except Exception as e:
            print(f"Database connection error: {e}")
            logging.error(f"Database connection error: {e}")
            return None

def send_result_to_database(test_type, data):
    try:
        # print(f"Preparing to insert data into database for test type: {test_type} with data: {data}")
        if test_type == "CDC" or test_type == "Sanity":
            conn = connect_db()
            if conn is None:
                print("Failed to connect to database.")
                logging.error("Failed to connect to database.")
                return
            cursor = conn.cursor()
            # Insert data into the database
            insert_query = """
                INSERT INTO batterytestresult ( DateTime , Serial_Number, Channel_No, Machine_No, Testing_Type, CH_Capacity_Ah, CH_Pack_Voltage_V, CH_HCV,CH_Cell_Deviation,CH_Temp, CH_Temp_Deviation, DCH_Capacity_Ah, DCH_Pack_Voltage_V, DCH_LCV, DCH_Cell_Deviation, DCH_Temp, DCH_Temp_Deviation, END_SOC, STATUS, Step_Timing,Cycle_Time) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """
            cursor.execute(
                insert_query, 
                (
                datetime.now(),
                data["data_update"]["meta"]["battery_id"],
                data["data_update"]["meta"]["device_channel"],
                data["data_update"]["meta"]["device_id"],
                data["data_update"]["meta"]["test_type"],
                data["data_update"]["results"]["charge"]["Capacity"],
                data["data_update"]["results"]["charge"]["Pack_Voltage"],
                data["data_update"]["results"]["charge"]["Max_Cell_Voltage"],
                data["data_update"]["results"]["charge"]["Cell_Deviation"],
                data["data_update"]["results"]["charge"]["Max_Cell_Temperature"],
                data["data_update"]["results"]["charge"]["temperature_difference"],
                data["data_update"]["results"]["discharge"]["Capacity"],
                data["data_update"]["results"]["discharge"]["Pack_Voltage"],
                data["data_update"]["results"]["discharge"]["Min_Cell_Voltage"],
                data["data_update"]["results"]["discharge"]["Cell_Deviation"],
                data["data_update"]["results"]["discharge"]["Max_Cell_Temperature"],
                data["data_update"]["results"]["discharge"]["temperature_difference"],
                data["data_update"]["results"]["discharge"]["End_SOC"],
                1 if data["data_update"]["final_status"] == "PASS" else 2,
                pd.to_timedelta(data["data_update"]["step_time"]).total_seconds() if data["data_update"]["step_time"] is not None else None,
                pd.to_timedelta(data["data_update"]["cycle_time"]).total_seconds() if data["data_update"]["cycle_time"] is not None else None
                # data["data_update"]["Step_Timing"] ,
                # data["data_update"]["Cycle_Time"]
            )
            )
            conn.commit()
            cursor.close()
            conn.close()
            # print("Data inserted into database successfully.")
            logging.info(f"Data inserted into database for Battery ID {data['data_update']['meta']['battery_id']} with status {data['data_update']['final_status']}")
        else:
            # hrd/hrc
            """
            SELECT TOP (1000) [DateTime]
                ,[Shift_User]
                ,[OperationalShift]
                ,[ModuleBarcodeData]
                ,[HRD_Test_Spare01]
                ,[HRD_Test_Spare02]
                ,[Status]
                ,[HRD_Test_Spare04]
                ,[HRD_Test_Spare05]
                ,[HRD_Test_Spare06]
                ,[CycleTime]
            FROM [ZONE03_REPORTS].[dbo].[HRD_Test_Stn]
            from this table we will insert only the ModuleBarcodeData, HRD_Test_Spare01 as HRD, HRD_Test_Spare02 as HRC and Status as Pass/Fail and DateTime for the timestamp and CycleTime as cycletime. and we can use Shift_User and OperationalShift for the user and shift details if needed in future.
            """
            # insert for HRD and HRC
            conn = connect_db()
            if conn is None:
                print("Failed to connect to database.")
                logging.error("Failed to connect to database.")
                return
            cursor = conn.cursor()
            insert_query = """
                INSERT INTO HRD_Test_Stn (DateTime, ModuleBarcodeData, HRD_Test_Spare01, HRD_Test_Spare02, Status, CycleTime, StepTime)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            # print(data)
            cursor.execute(insert_query, (
                datetime.now(),
                data["data_update"]["meta"]["battery_id"],
                data["data_update"]["results"]["discharge"]["hrd"],
                data["data_update"]["results"]["charge"]["hrc"],
                1 if data["data_update"]["final_status"] == "PASS" else 0,
                pd.to_timedelta(data["data_update"]["step_time"]).total_seconds() if data["data_update"]["step_time"] is not None else None,
                pd.to_timedelta(data["data_update"]["cycle_time"]).total_seconds() if data["data_update"]["cycle_time"] is not None else None
            ))
            conn.commit()
            cursor.close()
            conn.close()
            # print("HRD/HRC Data inserted into database successfully.")
            logging.info(f"HRD/HRC Data inserted into database for Battery ID {data['data_update']['meta']['battery_id']} with status {data['data_update']['final_status']}")
    except Exception as e:
        print(f"Error inserting data into database: {e}")

##--------------------------------------------------------
## End Send Result to Database
##--------------------------------------------------------

import math

def sanitize_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_json(v) for v in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

def background_reader_thread():
    global PRVEIOS_BATTERY_END_TIME
    global CURRENT_CYCLE_START_TIME
    while True:
        try:
            data = {}
            # check if new file is available in base path
            time.sleep(DATA_READ_INTERVAL)
            base_path = os.path.join(BASE_DIR, "data_files")
            files = [f for f in os.listdir(base_path) if f.endswith(".xlsx") and not f.startswith("~$")]
            # print("Files found:", files)
            for file in files:
                if file not in PROCESSED_FILES:
                    PROCESSED_FILES.append(file)

                    logging.info(f"Processing file: {file}")
                    
                    # Extract metadata from file name
                    parts = file.split("_")
                    date_str = parts[0]
                    device_id = parts[1].split("-")[0]
                    device_channel = parts[1].split("-")[1]
                    battery_id = parts[2].replace(".xlsx", "")
                    date_time = datetime.strptime(date_str, "%Y-%m-%d %H-%M-%S")
                    file_size = os.path.getsize(os.path.join(base_path, file))
                    if battery_id.startswith("M"):
                        if file_size < 5000000:  # less than 5MB
                            test_type = "Sanity"
                        else:
                            test_type = "CDC"
                    else:
                        test_type = "HRD"
                    print(f"filename:{file}, filesize: {file_size} bytes, Test Type: {test_type}")
                    logging.info(f"Extracted metadata from file name: DateTime: {date_time}, Device Channel: {device_channel}, Battery ID: {battery_id}, Test Type: {test_type}, File Size: {file_size} bytes")
                    if test_type == "CDC" or test_type == "Sanity":
                        battery_type = battery_id[1] + battery_id[2]  # e.g., L2
                    else:
                        battery_type = battery_id[2] + battery_id[3]  # e.g., K5
                        
                    # print(f"fileName : {file},DateTime: {date_time}, Device Channel: {device_channel}, Battery ID: {battery_id}, Test Type: {test_type}, Battery Type: {battery_type}")
                    #  reading data from the file
                    safe_file = " ".join(file.split())
                    file_path = os.path.join(base_path, safe_file)
                    if test_type == "Sanity" or test_type == "CDC":
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
                                start_time, end_time, step_timing = safe_step_time(test_type,df=sheets_data[int(headers["Sheet_Name_Capacity"])])   
                                previous_end_time = PRVEIOS_BATTERY_END_TIME[str(device_id)][str(device_channel)]
                                if previous_end_time != 0:
                                    cycle_timing = start_time - PRVEIOS_BATTERY_END_TIME[str(device_id)][str[device_channel]]  if PRVEIOS_BATTERY_END_TIME[str(device_id)][str[device_channel]] != 0 else None
                                else:
                                    cycle_timing = 0
                                PRVEIOS_BATTERY_END_TIME[str(device_id)][str(device_channel)] = end_time
                                data = {
                                    "Battery Serial No": battery_id,
                                    "charge":{
                                        "Cell_Deviation": safe_max(df=sheets_data[int(headers["Sheet_Name_Cell_Deviation"])], col=headers["Cell_Deviation"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["cell_deviation_step"]) if is_standerd else max_temp_diff(df=sheets_data[int(headers["Sheet_Name_Cell_Deviation"])], min_col=headers["Min_Cell_Temperature"], max_col=headers["Max_Cell_Temperature"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["cell_deviation_step"]),

                                        "Capacity": safe_sum(df=sheets_data[int(headers["Sheet_Name_Capacity"])], col=headers["Capacity"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["capacity_step"]),
                                        
                                        "Pack_Voltage": safe_last_step(df=sheets_data[int(headers["Sheet_Name_Pack_Voltage"])], col=headers["Pack_Voltage"], step_no= config["Thresholds"][battery_type][test_type]["charge"]["pack_voltage_step"]),
                                        
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
                                        
                                        "Pack_Voltage": safe_last_step(df=sheets_data[int(headers["Sheet_Name_Pack_Voltage"])], 
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
                                logging.error(f"Error reading Excel file {file}: {e}")
                                raise
                            
                        thresholds_config = load_thresholds()
                        threshold_block = thresholds_config["Thresholds"][battery_type][test_type]
                        overall_pass, evaluated = evaluate_thresholds(data, threshold_block)
                        final_status = "PASS" if overall_pass else "FAIL"

                        data["charge"] = {k: to_native(v) for k, v in data["charge"].items()}
                        data["discharge"] = {k: to_native(v) for k, v in data["discharge"].items()}
                        data = sanitize_json(data)
                        evaluated = sanitize_json(evaluated)
                        payload = {
                            "data_update": {
                                "meta": {
                                    "battery_id": battery_id,
                                    "battery_type": battery_type,
                                    "test_type": test_type,
                                    "device_id": device_id,
                                    "device_channel": device_channel,
                                    "timestamp": date_time.strftime("%Y-%m-%d %H:%M:%S"),
                                },
                                "results": data,
                                "evaluated": evaluated,
                                "final_status": final_status,
                                "step_time": str(step_timing) if step_timing is not None else None,
                                "cycle_time": str(step_timing) if step_timing is not None else None
                            }
                        }

                        socketio.emit("live_data", payload)
                        # print(f"Data emitted to dashboard.{data}")
                        # print(f"device_id: {device_id}")
                        # print(f"device_channel: {device_channel}")
                        # print(f"final_status: {final_status}")
                        send_result_to_plc(device_id, device_channel, final_status)
                        send_result_to_database(test_type, payload)
                        logging.info(f"Data emitted: {data}")
                        logging.info(f"Test status for file {file}: {final_status}")
                    else:
                        with file_lock:
                            try:
                                with open(os.path.join(BASE_DIR, "config.json"), "r") as cf:
                                    config = json.load(cf)

                                headers = config["Headers"]
                                headers = headers[battery_type]
                                headers = headers["CDC"]['header']
                                # print("Using test type", test_type ,"headers:", headers)
                                # extract the unique sheetNO for the HRD and HRC only and read only those sheets
                                unique_sheets = set()
                                unique_sheets.add(int(headers["Sheet_Name_HRD"]))
                                unique_sheets.add(int(headers["Sheet_Name_HRC"]))
                                sheets_data = {}
                                for sheet in unique_sheets:
                                    sheets_data[sheet] = read_sheet(file_path, int(sheet))
                                start_time, end_time, step_timing = safe_step_time(test_type,df=sheets_data[int(headers["Sheet_Name_HRD"])])
                                previous_end_time = PRVEIOS_BATTERY_END_TIME[str(device_id)][str(device_channel)]
                                if previous_end_time != 0:
                                    cycle_timing =  pd.to_datetime(start_time) - pd.to_datetime(PRVEIOS_BATTERY_END_TIME[str(device_id)][str(device_channel)])  if PRVEIOS_BATTERY_END_TIME[str(device_id)][str(device_channel)] != 0 else None
                                else:
                                    cycle_timing = 0

                                PRVEIOS_BATTERY_END_TIME[str(device_id)][str(device_channel)] = pd.to_datetime(end_time)
                                data = {
                                    "Battery Serial No": battery_id,
                                    "charge":{
                                        "hrc": safe_last(df=sheets_data[int(headers["Sheet_Name_HRC"])], col=headers["HRC"])
                                    },
                                    "discharge":{   
                                        "hrd": safe_last(df=sheets_data[int(headers["Sheet_Name_HRD"])], col=headers["HRD"])
                                    }
                                }
                                # print("Extracted Data:", data)
                                thresholds_config = load_thresholds()
                                # print("Loaded Thresholds:", thresholds_config)
                                threshold_block = thresholds_config["Thresholds"][battery_type]["CDC"]
                                # print("Using Threshold Block:", threshold_block)
                                # print(f"Evaluating  thresholds...")
                                overall_pass, evaluated = evaluate_thresholds(data, threshold_block)
                                # print("Evaluation Results:", evaluated, "Overall Pass:", overall_pass)
                                final_status = "PASS" if overall_pass else "FAIL"

                                data["charge"] = {k: to_native(v) for k, v in data["charge"].items()}
                                data["discharge"] = {k: to_native(v) for k, v in data["discharge"].items()}
                                data = to_native(data)
                                data = sanitize_json(data)
                                evaluated = sanitize_json(evaluated)
                                payload = {
                                    "data_update": {
                                        "meta": {
                                            "battery_id": battery_id,
                                            "battery_type": battery_type,
                                            "test_type": test_type,
                                            "device_id": device_id,
                                            "device_channel": device_channel,
                                            "timestamp": date_time.strftime("%Y-%m-%d %H:%M:%S"),
                                        },
                                        "results": data,
                                        "evaluated": evaluated,
                                        "final_status": final_status,
                                        "step_time": str(step_timing) if step_timing is not None else None,
                                        "cycle_time": str(cycle_timing) if cycle_timing is not None else None
                                    }
                                }

                                socketio.emit("live_data", payload)

                                    
                                logging.info(f"Data emitted: {data}")
                                logging.info(f"Test status for file {file}: {final_status}")
                                send_result_to_plc(device_id, device_channel, final_status)
                                send_result_to_database(test_type, payload)
                            except Exception as e:
                                print("Error loading config for HRD/HRC:", repr(e))
                                logging.error(f"Error loading config for HRD/HRC for file {file}: {e}")
                                continue
                else:
                    logging.debug("No new files to process.")
                    continue
        except Exception as e:
            print(f"Error in background_reader_thread: {e}")
            logging.error(f"Error in background_reader_thread: {e}")


# =========================================================
#  Run App
# =========================================================
if __name__ == "__main__":
    reader_thread = threading.Thread(target=background_reader_thread)
    reader_thread.daemon = True
    reader_thread.start()
    logging.info("Starting Flask SocketIO Server on port 5002...")
    socketio.run(app, host="0.0.0.0", port=5002, debug=False, use_reloader=False)
