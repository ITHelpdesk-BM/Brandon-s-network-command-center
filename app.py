import time
import threading
import requests
import pandas as pd
import json
import os

from dash import Dash, html, dcc, Input, Output
import dash_bootstrap_components as dbc

# =========================
# Brandon’s Network Command Center
# =========================

APP_NAME = "Brandon’s Network Command Center"

MONITORED_SERVICES = [
    "https://google.com",
    "https://github.com",
    "https://cloudflare.com",
]

DATA_FILE = "network_history.json"

# =========================
# STORAGE
# =========================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data[-50:], f, indent=2)

history = load_data()
current_status = {}

# =========================
# MONITORING LOGIC
# =========================

def check_service(url):
    try:
        start = time.time()
        r = requests.get(url, timeout=5)
        latency = round((time.time() - start) * 1000)

        return {
            "service": url,
            "status": "ONLINE" if r.status_code < 400 else "DEGRADED",
            "latency": latency
        }
    except:
        return {
            "service": url,
            "status": "OFFLINE",
            "latency": None
        }

def monitor_loop():
    global history, current_status

    while True:
        snapshot = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": []
        }

        for service in MONITORED_SERVICES:
            snapshot["results"].append(check_service(service))

        current_status = snapshot
        history.append(snapshot)

        save_data(history)
        time.sleep(30)

# =========================
# DASH APP
# =========================

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    html.H2(APP_NAME, className="text-center mt-3"),
    html.H5("IT Network Monitoring Dashboard", className="text-center text-muted"),
    html.Hr(),

    html.Div(id="output"),

    dbc.Button("Download Logs (CSV)", id="download-btn",
               color="secondary", className="w-100 mt-3"),

    dcc.Download(id="download-data"),

    dcc.Interval(id="interval", interval=30 * 1000, n_intervals=0)
], fluid=True)

# =========================
# UI UPDATE
# =========================

@app.callback(
    Output("output", "children"),
    Input("interval", "n_intervals")
)
def update_ui(n):
    if not current_status:
        return "Loading system status..."

    cards = []

    for item in current_status["results"]:
        color = "success" if item["status"] == "ONLINE" else "danger"

        cards.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5(item["service"]),
                    html.H4(item["status"], className=f"text-{color}"),
                    html.P(f"{item['latency']} ms" if item["latency"] else "No response")
                ]),
                className="mb-2"
            )
        )

    return [
        html.H6(f"Last Update: {current_status['time']}"),
        *cards
    ]

# =========================
# CSV EXPORT
# =========================

@app.callback(
    Output("download-data", "data"),
    Input("download-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_csv(n):
    rows = []

    for entry in history:
        for r in entry["results"]:
            rows.append({
                "time": entry["time"],
                "service": r["service"],
                "status": r["status"],
                "latency": r["latency"]
            })

    df = pd.DataFrame(rows)
    return dcc.send_data_frame(df.to_csv, "network_logs.csv", index=False)

# =========================
# BACKGROUND MONITOR + RENDER ENTRY POINT
# =========================

def start_monitor():
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()

start_monitor()

server = app.server  # REQUIRED for Render

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)
