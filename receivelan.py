# relan2.py
import socket
import os
import subprocess

PORT = 5001
BUFFER_SIZE = 65536
SAVE_DIR = 'received_installers'

os.makedirs(SAVE_DIR, exist_ok=True)

def handle_client(conn, addr):
    print(f"[+] Connected from {addr}")

    # Receive header
    header = conn.recv(1024).decode()
    filename, filesize = header.split('|')
    filesize = int(filesize)

    conn.send(b'OK')  # Acknowledge

    file_path = os.path.join(SAVE_DIR, filename)
    with open(file_path, 'wb') as f:
        received = 0
        while received < filesize:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            f.write(data)
            received += len(data)

    print(f"📥 Received: {filename}")
    status = run_installer(file_path)
    conn.send(status.encode())  # Send status back

def run_installer(file_path):
    print("⚙️  Running installer silently...")

    # Known silent flags
    silent_flags = {
        'exe': ["/S", "/silent", "/verysilent"],
        'msi': ["/quiet", "/qn"]
    }

    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    for flag in silent_flags.get(ext, []):
        try:
            subprocess.run([file_path, flag], check=True)
            print(f"✅ Installed silently with: {flag}")
            return "✅ Installed silently"
        except subprocess.CalledProcessError:
            continue

    try:
        subprocess.Popen([file_path])
        print("⚠️ Launched installer (manual setup may be needed)")
        return "⚠️ Launched setup manually"
    except Exception as e:
        print(f"❌ Installation failed: {e}")
        return "❌ Installation failed"

def start_receiver():
    with socket.socket() as s:
        s.bind(('', PORT))
        s.listen(1)
        print(f"[Receiver] Listening on port {PORT}...")

        while True:
            conn, addr = s.accept()
            with conn:
                handle_client(conn, addr)

if __name__ == "__main__":
    start_receiver()
