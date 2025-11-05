import requests
import logging
from core.auth import get_auth_headers
from config import API_BASE_URL

# ==========================================================
# Device API Proxy Layer
# ==========================================================
class DeviceAPI:
    """
    This class wraps around your existing device HTTP API.
    All requests automatically attach the JWT Authorization header.
    """

    def __init__(self):
        self.base = API_BASE_URL.rstrip("/")

    # ------------------------------
    # Device Management
    # ------------------------------
    def get_all_devices(self):
        url = f"{self.base}/api/Device/GetAllDevice"
        try:
            res = requests.get(url, headers=get_auth_headers(), timeout=10)
            if res.status_code == 200:
                return res.json()
            logging.warning(f"GetAllDevice failed: {res.status_code}")
            return []
        except Exception as e:
            logging.error(f"Error fetching devices: {e}")
            return []

    def register_device(self, ip_address: str):
        url = f"{self.base}/api/Device/register?ipAddress={ip_address}"
        try:
            res = requests.post(url, headers=get_auth_headers(), timeout=5)
            if res.status_code == 200:
                logging.info(f"Device registered: {ip_address}")
                return res.json()
            else:
                logging.warning(f"Register device failed: {res.status_code}")
        except Exception as e:
            logging.error(f"Device register error: {e}")
        return None

    def get_device_ip(self, device_id: int):
        url = f"{self.base}/api/Device/ip/{device_id}"
        try:
            res = requests.get(url, headers=get_auth_headers(), timeout=5)
            return res.json() if res.status_code == 200 else None
        except Exception as e:
            logging.error(f"Get device IP error: {e}")
            return None

    # ------------------------------
    # Circuit / Command Controls
    # ------------------------------
    def pause_circuit(self, device_id: int, circuit_no: int):
        return self._post_command("/api/command/pause", device_id, circuit_no)

    def stop_circuit(self, device_id: int, circuit_no: int):
        return self._post_command("/api/command/stop", device_id, circuit_no)

    def continue_circuit(self, device_id: int, circuit_no: int):
        return self._post_command("/api/command/Continue", device_id, circuit_no)

    def _post_command(self, endpoint: str, device_id: int, circuit_no: int):
        """
        Sends a control command to pause, stop, or continue a circuit.
        """
        try:
            url = f"{self.base}{endpoint}?circuitNo={circuit_no}&DeviceId={device_id}"
            res = requests.post(url, headers=get_auth_headers(), timeout=5)
            ok = res.status_code == 200
            msg = "Success" if ok else f"Failed ({res.status_code})"
            logging.info(f"[CMD] {endpoint} -> Device {device_id}, Circuit {circuit_no}: {msg}")
            return {"ok": ok, "status": res.status_code, "response": res.text}
        except Exception as e:
            logging.error(f"Command {endpoint} error: {e}")
            return {"ok": False, "error": str(e)}

    # ------------------------------
    # DBC Upload / Data Control
    # ------------------------------
    def create_db_files(self, device_ids, circuit_ids, dbc_files=None, time_delay=1000):
        """
        Calls /api/DBCUpload/create-db-files endpoint to start data collection.
        """
        url = f"{self.base}/api/DBCUpload/create-db-files"

        multipart = []
        try:
            for did in device_ids:
                multipart.append(("DeviceIDs", (None, str(did))))
            for cid in circuit_ids:
                multipart.append(("CircuitIds", (None, str(cid))))
            multipart.append(("TimeDelay", (None, str(time_delay))))

            # Attach any provided DBC files
            for path in (dbc_files or []):
                with open(path, "rb") as f:
                    multipart.append(("DBCFiles", (path.split("/")[-1], f, "application/octet-stream")))

            res = requests.post(url, files=multipart, headers=get_auth_headers(), timeout=30)
            if res.status_code == 200:
                logging.info(f"create-db-files successful: {res.status_code}")
                return {"ok": True, "data": res.json()}
            else:
                logging.warning(f"create-db-files failed: {res.status_code}")
                return {"ok": False, "message": res.text}
        except Exception as e:
            logging.error(f"Error in create_db_files: {e}")
            return {"ok": False, "error": str(e)}
