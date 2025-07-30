import json
import os
import subprocess
from datetime import datetime

INSTALLERS_DIR = 'installers'
CLIENTS_FILE = 'config/clients.json'
LOG_FILE = 'logs/install_log.txt'
PSEXEC_PATH = 'tools/PsExec.exe'

def load_clients():
    with open(CLIENTS_FILE, 'r') as f:
        return json.load(f)

def list_installers():
    return [f for f in os.listdir(INSTALLERS_DIR) if f.endswith('.exe')]

def select_from_list(items, title):
    print(f"\n=== {title} ===")
    for idx, item in enumerate(items):
        print(f"[{idx}] {item}")
    try:
        choice = int(input("Select number: "))
        return items[choice]
    except (ValueError, IndexError):
        print("❌ Invalid choice.")
        return None

def run_installer_on_client(client_ip, installer_path):
    cmd = [
        PSEXEC_PATH,
        f"\\\\{client_ip}",
        "-i", "-s",  # interactive and run as SYSTEM
        installer_path,
        "/S"  # silent flag (depends on installer)
    ]

    try:
        print(f"\n🚀 Executing on {client_ip} ...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ Installed successfully.")
            return "Installed silently"
        else:
            print("⚠️ Might need manual setup.")
            print(result.stderr)
            return "Setup may be required"
    except Exception as e:
        print("❌ Failed to install:", e)
        return f"Error: {e}"

def log_status(client_name, client_ip, installer, status):
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {client_name} ({client_ip}) - {installer} - {status}\n")

def main():
    clients = load_clients()
    installers = list_installers()

    if not installers:
        print("❌ No installers found in 'installers/'")
        return

    if not clients:
        print("❌ No clients found in config/clients.json")
        return

    installer = select_from_list(installers, "Available Installers")
    if not installer:
        return

    client = select_from_list(clients, "Target Clients")
    if not client:
        return

    installer_path = os.path.abspath(os.path.join(INSTALLERS_DIR, installer))
    status = run_installer_on_client(client['ip'], installer_path)
    log_status(client['name'], client['ip'], installer, status)

if __name__ == "__main__":
    main()
