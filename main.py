import requests
import re
import struct

url = "http://localhost:5000/login"
payload = {
    "username": "admin",
    "password": "admin123",
}

try:
    response = requests.post(url, json=payload, timeout=5)
    if response.status_code == 200:
        data = response.text
        print(data)
    else:
        print(f"Failed to read data {response.status_code}")
except Exception as e:
    print(f"failed to read write {e}")

# Extract token from login response
token = None
if response.status_code == 200:
    try:
        login_data = response.json()
        token = login_data.get('token')
    except:
        token_match = re.search(r'"token":\s*"([^"]+)"', response.text)
        if token_match:
            token = token_match.group(1)

if not token:
    print("Failed to extract token from login response")
    exit(1)


# Prepare headers with authorization token
headers = {
    'accept': '*/*',
    'Authorization': f'Bearer {token}',
}

url = "http://localhost:5000/api/Device/GetAllCircuitCount"
try:
    response = requests.get(url, headers=headers, timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(data)
    else:
        print(f"Failed to read data {response.status_code}")
except Exception as e:
    print(f"failed to read write {e}")

# Prepare headers with authorization token
headers = {
    'accept': '*/*',
    'Authorization': f'Bearer {token}',
}

# Prepare multipart form data
files = {
    'DeviceIDs': (None, '2'),
    'CircuitIds': (None, '3'),
    'DBCFiles': ('DBC_2.3kWh.dbc', open('DBC_2.3kWh.dbc', 'rb'), 'application/octet-stream'),
    'TimeDelay': (None, '10000')
}

url = "http://localhost:5000/api/DBCUpload/create-db-files"
try:
    response = requests.post(url, headers=headers, files=files, timeout=5)
    if response.status_code == 200:
        data = response.text
        print(data)
    else:
        print(f"Failed to read data {response.text}")

except Exception as e:
    print(f"failed to read write {e}")
finally:
    # Close the file
    if 'files' in locals() and 'DBCFiles' in files:
        files['DBCFiles'][1].close()

