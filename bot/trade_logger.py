import csv
import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSV_FILE = os.path.join(BASE_DIR, "trades.csv")
JSON_FILE = os.path.join(BASE_DIR, "trades.json")

def log_trade(trade):
    trade["timestamp"] = datetime.utcnow().isoformat()

    # --- CSV logging ---
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=trade.keys())

        if not file_exists:
            writer.writeheader()

        writer.writerow(trade)

    # --- JSON logging ---
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            data = json.load(f)
    else:
        data = []

    data.append(trade)

    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=2)