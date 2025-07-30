import socket
import os
import threading

# Folder paths
MEDIA_FOLDER = os.path.join("client", "received", "media")
INSTALLER_FOLDER = os.path.join("client", "received", "installers")

# Supported extensions
MEDIA_EXTS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".pdf", ".docx", ".txt"]
INSTALLER_EXTS = [".exe", ".msi", ".bat"]

# Listening port
RECEIVE_PORT = 5001
BUFFER_SIZE = 4096

def classify_path(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in MEDIA_EXTS:
        return os.path.join(MEDIA_FOLDER, filename)
    elif ext in INSTALLER_EXTS:
        return os.path.join(INSTALLER_FOLDER, filename)
    else:
        return os.path.join(MEDIA_FOLDER, filename)  # Default fallback

def handle_client(conn, addr):
    try:
        print(f"[+] Connection from {addr}")
        filename = b""
        while True:
            chunk = conn.recv(1)
            if chunk == b'\n':
                break
            filename += chunk
        filename = filename.decode().strip()

        save_path = classify_path(filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            while True:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    break
                f.write(data)

        print(f"[✓] Received file saved to {save_path}")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        conn.close()

def start_listener():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", RECEIVE_PORT))
        s.listen(5)
        print(f"[LISTENING] Waiting for file on port {RECEIVE_PORT}...")
        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()

if __name__ == "__main__":
    try:
        start_listener()
    except KeyboardInterrupt:
        print("\n[!] Listener stopped.")
