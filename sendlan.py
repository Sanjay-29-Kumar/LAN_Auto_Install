# selan2.py
import socket
import os

BUFFER_SIZE = 65536
INSTALLERS_DIR = 'installers'

def list_installers():
    return [f for f in os.listdir(INSTALLERS_DIR) if f.endswith('.exe') or f.endswith('.msi')]

def send_file(file_path, target_ip, port=5001):
    try:
        filesize = os.path.getsize(file_path)
        filename = os.path.basename(file_path)

        print(f"📤 Sending: {filename} ({filesize} bytes) to {target_ip}:{port}")
        with socket.socket() as s:
            s.connect((target_ip, port))
            header = f"{filename}|{filesize}"
            s.send(header.encode())

            if s.recv(1024).decode().strip() != 'OK':
                print("❌ No ACK from receiver. Abort.")
                return

            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    s.sendall(chunk)

            print("✅ File sent. Waiting for installation response...")
            status = s.recv(1024).decode()
            print(f"📩 Receiver Response: {status}")

    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    installers = list_installers()
    if not installers:
        print("No installers found in 'installers/'")
        return

    print("\nAvailable Installers:")
    for i, name in enumerate(installers):
        print(f"[{i}] {name}")

    try:
        choice = int(input("\nEnter installer number: "))
        if not 0 <= choice < len(installers):
            print("Invalid choice.")
            return
    except ValueError:
        print("Invalid input.")
        return

    target_ip = input("Enter VM IP address: ").strip()
    selected_file = os.path.join(INSTALLERS_DIR, installers[choice])
    send_file(selected_file, target_ip)

if __name__ == "__main__":
    main()
