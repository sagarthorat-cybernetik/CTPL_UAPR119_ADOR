import requests
import json
import time
import subprocess
import os
import threading

class BTSWebAPITester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.token = None
        self.headers = {"Content-Type": "application/json"}
    
    def login(self, username, password):
        """Test login endpoint"""
        url = f"{self.base_url}/login"
        data = {"username": username, "password": password}
        try:
            response = requests.post(url, json=data, headers=self.headers)
            if response.status_code == 200:
                self.token = response.json().get('token')
                self.headers['Authorization'] = f'Bearer {self.token}'
                print(f"✓ Login successful: {response.status_code}")
            else:
                print(f"✗ Login failed: {response.status_code}")
            return response
        except Exception as e:
            print(f"✗ Login error: {e}")
            return None

    def refresh_token(self, username=None, password=None):
        """Test login endpoint"""
        url = f"{self.base_url}/login"
        data = {"username": username, "password": password}
        try:
            response = requests.post(url, json=data, headers=self.headers)
            if response.status_code == 200:
                self.token = response.json().get('token')
                self.headers['Authorization'] = f'Bearer {self.token}'
                print(f"✓ Login successful: {response.status_code}")
            else:
                print(f"✗ Login failed: {response.status_code}")
            return response
        except Exception as e:
            print(f"✗ Login error: {e}")
            return None
    
    # def upload_dbc(self, file_path):
    #     """Test DBC upload endpoint"""
    #     url = f"{self.base_url}/api/DBCUpload/UploadDBC"
    #     try:
    #         with open(file_path, 'rb') as file:
    #             files = {'file': file}
    #             response = requests.post(url, files=files, headers={'Authorization': self.headers.get('Authorization', '')})
    #         print(f"{'✓' if response.status_code == 200 else '✗'} Upload DBC: {response.status_code}")
    #         return response
    #     except Exception as e:
    #         print(f"✗ Upload DBC error: {e}")
    #         return None
    
    # def get_all_dbc_data(self):
    #     """Test get all DBC data endpoint"""
    #     url = f"{self.base_url}/api/DBCUpload/GetAllDBCData"
    #     try:
    #         response = requests.get(url, headers=self.headers)
    #         print(f"{'✓' if response.status_code == 200 else '✗'} Get All DBC Data: {response.status_code}")
    #         return response
    #     except Exception as e:
    #         print(f"✗ Get All DBC Data error: {e}")
    #         return None
    
    # def upload_bts_only(self, data):
    #     """Test upload BTS only endpoint"""
    #     url = f"{self.base_url}/api/DBCUpload/UploadBTSOnly"
    #     try:
    #         response = requests.post(url, json=data, headers=self.headers)
    #         print(f"{'✓' if response.status_code == 200 else '✗'} Upload BTS Only: {response.status_code}")
    #         return response
    #     except Exception as e:
    #         print(f"✗ Upload BTS Only error: {e}")
    #         return None
    
    def create_db_files(self, data):
        """Test create DB files endpoint using multipart/form-data"""
        endpoint = f"{self.base_url}/api/DBCUpload/create-db-files"
        open_handles = []
        try:
            # Only carry Authorization; let requests set Content-Type for multipart
            send_headers = {}
            auth = self.headers.get("Authorization")
            if auth:
                send_headers["Authorization"] = auth

            # Normalize inputs
            def as_list(v):
                if v is None:
                    return []
                return v if isinstance(v, (list, tuple)) else [v]

            device_ids = as_list(data.get("DeviceIDs"))
            circuit_ids = as_list(data.get("CircuitIds"))
            dbc_files = as_list(data.get("DBCFiles"))
            time_delay = data.get("TimeDelay")

            # Build multipart payload
            multipart = []
            for did in device_ids:
                multipart.append(("DeviceIDs", (None, str(did))))
            for cid in circuit_ids:
                multipart.append(("CircuitIds", (None, str(cid))))
            if time_delay is not None:
                multipart.append(("TimeDelay", (None, str(time_delay))))

            # Attach files
            for path in dbc_files:
                fh = open(path, "rb")
                open_handles.append(fh)
                name = path.replace("\\", "/").rsplit("/", 1)[-1]
                multipart.append(("DBCFiles", (name, fh, "application/octet-stream")))

            resp = requests.post(endpoint, headers=send_headers, files=multipart, timeout=5)
            print(f"{'✓' if resp.status_code == 200 else '✗'} Create DB Files: {resp.status_code}")
            if resp.status_code == 200:
                try:
                    response_data = resp.json()
                    print(resp.text)
                    
                    # Extract database file paths from response
                    db_files = []
                    if "files" in response_data:
                        for file_info in response_data["files"]:
                            db_files.append(file_info.get("filePath", ""))
                    # print(f"Created {len(db_files)} database files:")
                    # print(db_files)
                    # Launch database viewer if files were created successfully
                    # if db_files:
                        # self._launch_db_viewer(db_files)
                        
                except Exception as e:
                    print(f"Error processing response: {e}")
                    print(resp.text)
            else:
                try:
                    print(f"Response: {resp.text}")
                except Exception:
                    pass
            return resp
        except Exception as e:
            print(f"✗ Create DB Files error: {e}")
            return None
        finally:
            for fh in open_handles:
                try:
                    fh.close()
                except Exception:
                    pass
    
    def _launch_db_viewer(self, db_files):
        print(f"Launching database viewer for {len(db_files)} files...")
        print(f"Database files: {db_files}")
        """Launch the database viewer with the created database files"""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # print(script_dir)
            viewer_script = os.path.join(script_dir, "readdbfile.py")
            
            # Pass database file paths as arguments
            cmd = ["python", viewer_script] + db_files
            
            # Launch in a separate thread to avoid blocking
            def launch():
                try:
                    subprocess.Popen(cmd, cwd=script_dir)
                    print(f"✓ Launched database viewer for {len(db_files)} database files")
                except Exception as e:
                    print(f"✗ Failed to launch database viewer: {e}")
            
            threading.Thread(target=launch, daemon=True).start()
            
        except Exception as e:
            print(f"✗ Error launching database viewer: {e}")
        
      
    
    def export_db_to_excel(self):
        """Test export DB to Excel endpoint"""
        url = f"{self.base_url}/api/DBCUpload/export-db-to-excel"
        try:
            response = requests.get(url, headers=self.headers)
            print(f"{'✓' if response.status_code == 200 else '✗'} Export DB to Excel: {response.status_code}")
            return response
        except Exception as e:
            print(f"✗ Export DB to Excel error: {e}")
            return None
    
    def register_device(self, device_ip):
        """Test device registration endpoint"""
        url = f"{self.base_url}/api/Device/register?ipAddress={device_ip}"
        try:
            response = requests.post(url, headers=self.headers)
            print(f"{'✓' if response.status_code == 200 else '✗'} Register Device: {response.status_code}")
            print(f"Response: {response.json()}")
            return response
        except Exception as e:
            print(f"✗ Register Device error: {e}")
            return None
    
    def get_device_ip(self, device_id):
        """Test get device IP endpoint"""
        url = f"{self.base_url}/api/Device/ip/{device_id}"
        try:
            response = requests.get(url, headers=self.headers)
            print(f"{'✓' if response.status_code == 200 else '✗'} Get Device IP: {response.status_code}")
            print(f"Response: {response.json()}")
            return response
        except Exception as e:
            print(f"✗ Get Device IP error: {e}")
            return None
    
    def get_all_circuit_count(self):
        """Test get all circuit count endpoint"""
        url = f"{self.base_url}/api/Device/GetAllCircuitCount"
        try:
            response = requests.get(url, headers=self.headers)
            print(f"{'✓' if response.status_code == 200 else '✗'} Get All Circuit Count: {len(response.json())}")
            print(f"Response: {response.json()}")
            return response
        except Exception as e:
            print(f"✗ Get All Circuit Count error: {e}")
            return None
    
    def get_all_devices(self):
        """Test get all devices endpoint"""
        url = f"{self.base_url}/api/Device/GetAllDevice"
        try:
            response = requests.get(url, headers=self.headers)
            print(f"{'✓' if response.status_code == 200 else '✗'} Get All Devices: {response.status_code}")
            print(f"Response: {response.json()}")
            return response
        except Exception as e:
            print(f"✗ Get All Devices error: {e}")
            return None

    def pause_command(self, device_id=None, circuit_id=None):
        """Test pause command endpoint"""
        url = f"{self.base_url}/api/command/pause?circuitNo={circuit_id}&DeviceId={device_id}"
        # url = f"{self.base_url}/api/command/pause"
        payload = {}
        if circuit_id:
            payload['circuitNo'] = circuit_id
        if device_id:
            payload['DeviceId'] = device_id

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(f"{'✓' if response.status_code == 200 else '✗'} Pause Command: {response.status_code}")
            return response
        except Exception as e:
            print(f"✗ Pause Command error: {e}")
            return None

    def stop_command(self, device_id=None, circuit_id=None):
        """Test stop command endpoint"""
        url = f"{self.base_url}/api/command/stop?circuitNo={circuit_id}&DeviceId={device_id}"
        payload = {}
        if circuit_id:
            payload['circuitId'] = circuit_id
        if device_id:
            payload['deviceId'] = device_id

        try:
            response = requests.post(url, json=payload, headers=self.headers)
            print(f"{'✓' if response.status_code == 200 else '✗'} Stop Command: {response.status_code}")
            return response
        except Exception as e:
            print(f"✗ Stop Command error: {e}")
            return None

    def continue_command(self, device_id=None, circuit_id=None):
        """Test continue command endpoint"""
        url = f"{self.base_url}/api/command/Continue?circuitNo={circuit_id}&DeviceId={device_id}"
        payload = {}
        if circuit_id:
            payload['circuitNo'] = circuit_id
        if device_id:
            payload['DeviceId'] = device_id

        try:
            response = requests.post(url, json=payload,  headers=self.headers)
            print(f"{'✓' if response.status_code == 200 else '✗'} Continue Command: {response.status_code}")
            return response
        except Exception as e:
            print(f"✗ Continue Command error: {e}")
            return None
    
    def run_all_tests(self):
        """Run all API tests"""
        print("Starting BTS Web API Tests...")
        print("=" * 50)
        
        # Authentication tests
        print("\n--- Authentication Tests ---")
        self.login("admin", "admin123")  # Replace with actual credentials
        # self.refresh_token("admin", "admin123")
        
        # DBC Upload tests
        print("\n--- DBC Upload Tests ---")
        # self.get_all_dbc_data()
        # self.upload_bts_only({"sample": "data"})
        self.create_db_files({"DeviceIDs": [2], "CircuitIds": [1], "DBCFiles": ["DBC_2.3kWh.dbc"],"TimeDelay":1000})
        # self.export_db_to_excel()
        
        # Device tests
        print("\n--- Device Tests ---")
        # self.register_device("192.168.1.102")
        # self.get_device_ip(2)
        # self.get_all_circuit_count()
        # self.get_all_devices()
        
        # Command tests
        print("\n--- Command Tests ---")
        # self.pause_command(2,3)
        # time.sleep(5)
        # self.continue_command(2,3)
        # time.sleep(5)
        # self.stop_command(2,3)
        
        print("\n" + "=" * 50)
        print("API testing completed!")

if __name__ == "__main__":
    tester = BTSWebAPITester()
    tester.run_all_tests()