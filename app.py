import time
import threading
import requests
import pandas as pd
from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc
import os
import json

# ----------------------------
# CONFIG
# ----------------------------
APP_NAME = "Brandon’s Network Command Center"
DATA_FILE = "network_history.json"

MONITORED_SERVICES = [
    "https://google.com",
    "https://github.com",
    "https://cloudflare.com"
]

# ----------------------------
# STORAGE HELPERS (LOCAL FILE DB)
# ----------------------------
def load_history():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data[-50:], f, indent=2)

history = load_history()
current_status = {}

# ----------------------------
# MONITOR LOGIC
# ----------------------------
def check_service(url):
    try:
        start = time.time()
        r = requests.get(url, timeout=5)
        latency = round((time.time() - start) * 1000)
        return {
            "service": url,
            "status": "ONLINE" if r.status_code < 400 else "DEGRADED",
            "latency_ms": latency
        }
    except:
        return {
            "service": url,
            "status": "OFFLINE",
            "latency_ms": None
        }

def monitor():
    global history, current_status

    while True:
        snapshot = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": []
        }

        for service in MONITORED_SERVICES:
            result = check_service(service)
            snapshot["results"].append(result)

        current_status = snapshot
        history.append(snapshot)

        save_history(history)
        time.sleep(30)

# ----------------------------
# DASH APP
# ----------------------------
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    html.H2(APP_NAME, className="text-center my-3"),
    html.H5("IT Systems Monitoring Dashboard", className="text-center text-muted"),

    html.Hr(),

    html.Div(id="live-status"),

    html.Br(),

    dbc.Button("Refresh Now", id="refresh", color="primary", className="w-100"),

    html.Br(), html.Br(),

    dbc.Button("Download Logs (CSV)", id="download-btn", color="secondary", className="w-100"),
    dcc.Download(id="download-data"),

    dcc.Interval(id="interval", interval=30 * 1000, n_intervals=0)
], fluid=True)

# ----------------------------
# UI UPDATE
# ----------------------------
@app.callback(
    Output("live-status", "children"),
    Input("interval", "n_intervals")
)
def update_dashboard(n):
    if not current_status:
        return "Loading network status..."

    cards = []

    for item in current_status["results"]:
        color = "success" if item["status"] == "ONLINE" else "danger"

        cards.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5(item["service"]),
                    html.H4(item["status"], className="text-" + color),
                    html.P(f"Latency: {item['latency_ms']} ms" if item["latency_ms"] else "No response")
                ]),
                className="mb-2"
            )
        )

    return [
        html.P(f"Last Update: {current_status['time']}"),
        *cards
    ]

# ----------------------------
# CSV EXPORT
# ----------------------------
@app.callback(
    Output("download-data", "data"),
    Input("download-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_csv(n):
    rows = []

    for entry in history:
        for r in entry["results"]:
            rows.append({
                "time": entry["time"],
                "service": r["service"],
                "status": r["status"],
                "latency_ms": r["latency_ms"]
            })

    df = pd.DataFrame(rows)
    return dcc.send_data_frame(df.to_csv, "network_logs.csv", index=False)

# ----------------------------
# START BACKGROUND MONITOR
# ----------------------------
if __name__ == "__main__":
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()

    app.run(host="0.0.0.0", port=8050, debug=True)
