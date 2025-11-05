import json
import os
from flask import Response

# ======================================================
# Simple JSON Response Helper
# ======================================================
def json_response(data, status=200):
    """
    Returns a Flask Response with JSON data and given status code.
    """
    return Response(json.dumps(data, default=str), status=status, mimetype="application/json")


# ======================================================
# File Utility Helpers
# ======================================================
def ensure_dir_exists(path):
    """
    Ensures the directory exists.
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
        return True
    return False


def file_timestamp():
    """
    Returns current timestamp string for naming logs/files.
    """
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")
