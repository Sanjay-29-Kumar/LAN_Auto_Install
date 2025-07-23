# receiver.py
import socket
import subprocess
import os

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5001
INSTALL_PATH = "C:\\Users\\Public\\Downloads\\received_installer.exe"

def receive_file():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"[Receiver] Listening on port {PORT}...")

        conn, addr = s.accept()
        print(f"[Receiver] Connection from {addr}")
        with conn, open(INSTALL_PATH, 'wb') as f:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                f.write(data)

        print(f"[Receiver] File saved to {INSTALL_PATH}")
        run_silent(INSTALL_PATH)

def run_silent(file_path):
    try:
        print("[Receiver] Running installer silently...")
        subprocess.run([file_path, "/S"], check=True)
        print("[Receiver] Installation completed.")
    except Exception as e:
        print(f"[Receiver] Installation failed: {e}")

if __name__ == "__main__":
    receive_file()
