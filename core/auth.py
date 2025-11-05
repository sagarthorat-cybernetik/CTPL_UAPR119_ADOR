import requests
import time
import logging
from datetime import datetime, timedelta
from config import API_BASE_URL, JWT_EXPIRY_HOURS

# ======================================
# 🔒 Global Token Storage
# ======================================
token_data = {
    "access_token": None,
    "refresh_token": None,
    "expiry": None,
    "username": None,
    "password": None,
}


# ======================================
# 🔐 Login & Token Handling
# ======================================
def login_and_store_tokens(username: str, password: str):
    """
    Calls /login API and stores JWT + expiry.
    """
    login_url = f"{API_BASE_URL}/login"
    payload = {"username": username, "password": password}

    try:
        res = requests.post(login_url, json=payload)
        if res.status_code == 200:
            data = res.json()
            token = data.get("token") or data.get("access_token")
            if not token:
                return False, "No token in response"

            token_data["access_token"] = token
            token_data["username"] = username
            token_data["password"] = password
            token_data["expiry"] = datetime.now() + timedelta(hours=JWT_EXPIRY_HOURS)

            logging.info(f"Login successful for {username}")
            return True, "Login successful"
        else:
            logging.warning(f"Login failed: {res.status_code} - {res.text}")
            return False, res.text
    except Exception as e:
        logging.error(f"Login error: {e}")
        return False, str(e)


def get_auth_headers():
    """
    Returns headers with Bearer token for API calls.
    """
    if not token_data["access_token"]:
        return {"Content-Type": "application/json"}
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token_data['access_token']}",
    }


# ======================================
# ♻️ Auto Refresh Token
# ======================================
def refresh_token_if_needed():
    """
    Refreshes JWT if expiry is near (within 5 mins).
    """
    if not token_data["access_token"]:
        logging.warning("No token found to refresh.")
        return False

    # Refresh only if < 5 min left
    if token_data["expiry"] and (token_data["expiry"] - datetime.now()).total_seconds() > 300:
        return False

    refresh_url = f"{API_BASE_URL}/RefreshToken"
    payload = {
        "username": token_data["username"],
        "password": token_data["password"],
    }

    try:
        res = requests.post(refresh_url, json=payload)
        if res.status_code == 200:
            data = res.json()
            new_token = data.get("token") or data.get("access_token")
            if new_token:
                token_data["access_token"] = new_token
                token_data["expiry"] = datetime.now() + timedelta(hours=JWT_EXPIRY_HOURS)
                logging.info("Token refreshed successfully.")
                return True
            else:
                logging.warning("Token refresh failed: no token in response.")
        else:
            logging.warning(f"Token refresh failed: {res.status_code}")
        return False
    except Exception as e:
        logging.error(f"Token refresh error: {e}")
        return False


def get_token_info():
    """
    Returns the current token details for debugging.
    """
    return token_data
