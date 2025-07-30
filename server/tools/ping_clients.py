import os
import platform
from pathlib import Path

CLIENTS_FILE = Path("config/clients.txt")

def is_online(ip):
    param = "-n" if platform.system().lower() == "windows" else "-c"
    response = os.system(f"ping {param} 1 {ip} > nul 2>&1")
    return response == 0

def main():
    if not CLIENTS_FILE.exists():
        print(f"❌ {CLIENTS_FILE} not found.")
        return

    with open(CLIENTS_FILE, 'r') as f:
        clients = [line.strip() for line in f if line.strip()]

    print("📡 Checking client status...\n")
    for ip in clients:
        status = "🟢 ONLINE" if is_online(ip) else "🔴 OFFLINE"
        print(f"{ip:<15} : {status}")

if __name__ == "__main__":
    main()
