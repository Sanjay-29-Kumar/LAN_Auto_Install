import socket
import os

def list_installers(folder='installers'):
    files = [f for f in os.listdir(folder) if f.endswith('.exe')]
    return files

def send_file(file_path, ip, port=5001):
    filesize = os.path.getsize(file_path)
    s = socket.socket()
    s.connect((ip, port))
    
    # Send filename and filesize
    s.send(f"{os.path.basename(file_path)}|{filesize}".encode())

    # Wait for ACK
    s.recv(1024)

    with open(file_path, 'rb') as f:
        while True:
            bytes_read = f.read(65536)  # 64 KB buffer
            if not bytes_read:
                break
            s.sendall(bytes_read)
    
    s.close()
    print("✅ File sent successfully.")

if __name__ == "__main__":
    installers = list_installers()
    if not installers:
        print("No .exe files in 'installers/' folder.")
        exit()

    print("\nAvailable installer files:")
    for i, name in enumerate(installers):
        print(f"[{i}] {name}")
    
    choice = int(input("Enter the number of the installer to send: "))
    target_ip = input("Enter the receiver IP address: ").strip()
    send_file(os.path.join('installers', installers[choice]), target_ip)
