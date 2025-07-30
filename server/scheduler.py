import json
import os
import time
import subprocess
from datetime import datetime

# --- Paths ---
CONFIG_PATH = "config/clients.json"
STATUS_PATH = "status/install_status.json"
INSTALLER_PATH = "installers/installapplication.bat"
LOG_PATH = "logs/server_log.txt"

# --- Load client data ---
def load_clients():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

# --- Log helper ---
def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

# --- Load installation status ---
def load_status():
    if os.path.exists(STATUS_PATH):
        with open(STATUS_PATH, "r") as f:
            return json.load(f)
    return {}

# --- Save installation status ---
def save_status(status_data):
    with open(STATUS_PATH, "w") as f:
        json.dump(status_data, f, indent=4)

# --- Check if client is online ---
def is_online(ip):
    try:
        result = subprocess.run(["ping", "-n", "1", "-w", "1000", ip], capture_output=True, text=True)
        return "TTL=" in result.stdout
    except Exception as e:
        log(f"Error pinging {ip}: {e}")
        return False

# --- Attempt silent install using PsExec ---
def deploy_to_client(client_ip, username, password):
    try:
        psexec = os.path.abspath("tools/PsExec.exe")
        installer = os.path.abspath(INSTALLER_PATH)
        cmd = [psexec, f"\\\\{client_ip}", "-u", username, "-p", password, installer]
        result = subprocess.run(cmd, capture_output=True, text=True)
        log(f"Deployment to {client_ip} output:\n{result.stdout}\n{result.stderr}")
        return "completed" if result.returncode == 0 else "manual_required"
    except Exception as e:
        log(f"Deployment error to {client_ip}: {e}")
        return "error"

# --- Scheduler loop ---
def scheduler_loop():
    log("Scheduler started.")
    clients = load_clients()
    install_status = load_status()

    while True:
        for client_id, info in clients.items():
            ip = info.get("ip")
            username = info.get("username")
            password = info.get("password")

            # Only try if not already marked as installed
            if install_status.get(client_id) not in ["completed", "manual_required"]:
                if is_online(ip):
                    log(f"{client_id} ({ip}) is online. Attempting deployment.")
                    status = deploy_to_client(ip, username, password)
                    install_status[client_id] = status
                    save_status(install_status)
                else:
                    log(f"{client_id} ({ip}) is offline. Scheduling retry.")
                    install_status[client_id] = "scheduled"
                    save_status(install_status)

        time.sleep(60)  # Check every 60 seconds

# --- Entry point ---
if __name__ == "__main__":
    scheduler_loop()
