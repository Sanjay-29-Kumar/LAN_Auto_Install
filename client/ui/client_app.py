import socket
import os
import traceback

# Configuration
HOST = ''
PORT = 9999
BUFFER_SIZE = 4096

# Folder Setup
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RECEIVED_FOLDER = os.path.join(BASE_DIR, "received")
    INSTALLERS_FOLDER = os.path.join(RECEIVED_FOLDER, "installers")
    MEDIA_FOLDER = os.path.join(RECEIVED_FOLDER, "media")

    os.makedirs(INSTALLERS_FOLDER, exist_ok=True)
    os.makedirs(MEDIA_FOLDER, exist_ok=True)
except Exception as e:
    print("[!] Error during folder setup:", e)
    input("Press Enter to exit...")
    exit(1)

def save_file(filename, file_size, conn):
    if filename.lower().endswith(('.exe', '.msi')):
        dest_folder = INSTALLERS_FOLDER
    else:
        dest_folder = MEDIA_FOLDER

    file_path = os.path.join(dest_folder, filename)

    with open(file_path, 'wb') as f:
        received = 0
        while received < file_size:
            chunk = conn.recv(min(BUFFER_SIZE, file_size - received))
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)
    return file_path

def start_listener():
    print(f"[+] Listening on port {PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        try:
            server_socket.bind((HOST, PORT))
            server_socket.listen(5)
        except Exception as bind_err:
            print("[!] Failed to bind socket:", bind_err)
            input("Press Enter to exit...")
            return
        
        while True:
            try:
                conn, addr = server_socket.accept()
                print(f"[✓] Connection from {addr}")
                with conn:
                    filename_len = int.from_bytes(conn.recv(4), 'big')
                    filename = conn.recv(filename_len).decode()
                    file_size = int.from_bytes(conn.recv(8), 'big')
                    print(f"[↓] Receiving '{filename}' ({file_size} bytes)...")

                    saved_path = save_file(filename, file_size, conn)
                    print(f"[✓] File saved to: {saved_path}")
            except Exception as e:
                print("[!] Exception in listener loop:", e)
                traceback.print_exc()

if __name__ == "__main__":
    try:
        start_listener()
    except Exception as main_error:
        print("[!] Fatal Error:", main_error)
        traceback.print_exc()
        input("Press Enter to exit...")
