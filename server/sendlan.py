import os
import socket
import json
import shutil
import subprocess

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "clients.json")

# Port used by client listener
PORT = 5001

# PsExec path
PSEXEC_PATH = os.path.join(BASE_DIR, "tools", "PsExec.exe")

def send_file_to_clients(file_path, client_keys):
    # Load clients
    with open(CONFIG_PATH, "r") as f:
        clients = json.load(f)

    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError("Selected file does not exist.")

    filename = os.path.basename(file_path)

    for key in client_keys:
        client = clients.get(key)
        if not client:
            print(f"[ERROR] Client {key} not found in config.")
            continue

        ip = client["ip"]
        username = client["username"]
        password = client["password"]

        print(f"[INFO] Sending to {client['name']} ({ip})")

        # Check if client is online
        if not is_host_reachable(ip):
            print(f"[WARN] {ip} is offline. Skipping.")
            continue

        # Attempt socket send
        try:
            send_via_socket(ip, file_path)
            print(f"[OK] File sent to {ip}")
        except Exception as e:
            print(f"[FAIL] Could not send to {ip} via socket: {e}")
            continue

        # If file is installer (.exe), trigger silent install
        if file_path.lower().endswith(".exe"):
            try:
                trigger_silent_install(ip, filename, username, password)
                print(f"[OK] Triggered silent install on {ip}")
            except Exception as e:
                print(f"[FAIL] Silent install failed on {ip}: {e}")

def is_host_reachable(ip):
    try:
        socket.create_connection((ip, PORT), timeout=3)
        return True
    except:
        return False

def send_via_socket(ip, file_path):
    with socket.create_connection((ip, PORT), timeout=5) as sock:
        filename = os.path.basename(file_path)
        filesize = os.path.getsize(file_path)

        # Send header
        header = f"{filename}|{filesize}".encode()
        sock.sendall(header + b"\n")

        # Send file content
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                sock.sendall(chunk)

def trigger_silent_install(ip, filename, username, password):
    remote_path = f"C:\\LANAutoInstall\\received\\installers\\{filename}"

    # Build PsExec command
    cmd = [
        PSEXEC_PATH,
        f"\\\\{ip}",
        "-u", username,
        "-p", password,
        "-accepteula",
        "-s",
        "-d",
        remote_path,
        "/S"  # Silent flag
    ]

    subprocess.run(cmd, timeout=15)

