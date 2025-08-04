import sys
import socket
import threading
import json
import os
import time
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QListWidget, QTextEdit, QListWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

class ClientThread(QThread):
    server_discovered = pyqtSignal(str, str)
    server_connected = pyqtSignal(str)
    server_disconnected = pyqtSignal(str)
    file_received = pyqtSignal(str, str)
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.discovered_servers = {}
        self.connected_server = None
        self.server_socket = None
        
    def start_discovery(self):
        self.running = True
        self.start()
        
    def stop_discovery(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.wait()
        
    def run(self):
        """Main discovery loop"""
        while self.running:
            self._discover_servers()
            time.sleep(5)  # Discover every 5 seconds
            
    def _discover_servers(self):
        """Discover servers on the network"""
        try:
            # Get local network info
            local_ip = socket.gethostbyname(socket.gethostname())
            base_ip = '.'.join(local_ip.split('.')[:-1])
            
            discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            discovery_socket.settimeout(1)
            
            # Scan local network
            for i in range(1, 255):
                if not self.running:
                    break
                    
                target_ip = f"{base_ip}.{i}"
                if target_ip == local_ip:
                    continue
                    
                try:
                    # Send discovery message (match server expectation)
                    message = "DISCOVER"
                    discovery_socket.sendto(message.encode('utf-8'), (target_ip, 5001))
                    
                    # Try to receive response
                    try:
                        data, addr = discovery_socket.recvfrom(1024)
                        response = data.decode('utf-8')
                        
                        # Server sends: "SERVER:IP:PORT"
                        if response.startswith("SERVER:"):
                            parts = response.split(":")
                            if len(parts) >= 3:
                                server_ip = parts[1]
                                server_port = int(parts[2])
                                server_name = f"LAN Server ({server_ip})"
                                
                                if server_ip not in self.discovered_servers:
                                    self.discovered_servers[server_ip] = {
                                        'name': server_name,
                                        'port': server_port,
                                        'last_seen': time.time()
                                    }
                                    self.server_discovered.emit(server_ip, server_name)
                                    print(f"Discovered server: {server_ip}")
                                
                    except socket.timeout:
                        pass
                        
                except Exception as e:
                    continue
                    
            discovery_socket.close()
            
        except Exception as e:
            self.log_message.emit(f"Discovery error: {e}")
            
    def connect_to_server(self, server_ip):
        """Connect to a specific server"""
        try:
            if server_ip not in self.discovered_servers:
                self.log_message.emit(f"Server {server_ip} not in discovered list")
                return False
                
            server_info = self.discovered_servers[server_ip]
            server_port = server_info['port']
            
            # Create TCP connection
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.settimeout(30)  # 30 second timeout
            self.server_socket.connect((server_ip, server_port))
            
            self.connected_server = server_ip
            self.server_connected.emit(server_ip)
            self.log_message.emit(f"Connected to server: {server_ip}")
            
            # Start receiving data
            receive_thread = threading.Thread(target=self._receive_data)
            receive_thread.daemon = True
            receive_thread.start()
            
            return True
            
        except Exception as e:
            self.log_message.emit(f"Connection error: {e}")
            return False
            
    def disconnect_from_server(self):
        """Disconnect from current server"""
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        if self.connected_server:
            self.server_disconnected.emit(self.connected_server)
            self.connected_server = None
            
    def _receive_data(self):
        """Receive data from server"""
        try:
            while self.running and self.server_socket:
                try:
                    # Read exactly 4 bytes for header length
                    header_length_bytes = b''
                    while len(header_length_bytes) < 4:
                        chunk = self.server_socket.recv(4 - len(header_length_bytes))
                        if not chunk:
                            return
                        header_length_bytes += chunk
                        
                    header_length = int.from_bytes(header_length_bytes, byteorder='big')
                    
                    # Read exactly header_length bytes for header data
                    header_data = b''
                    while len(header_data) < header_length:
                        chunk = self.server_socket.recv(header_length - len(header_data))
                        if not chunk:
                            return
                        header_data += chunk
                    
                    # Parse header
                    try:
                        message = json.loads(header_data.decode('utf-8'))
                        if message.get('type') == 'FILE_TRANSFER':
                            print(f"Received file transfer request: {message}")
                            # Send acknowledgment
                            self.server_socket.send(b'ACK')
                            # Receive the file with exact byte count
                            self._receive_file_binary(message)
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        break
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Receive error: {e}")
                    break
                    
        except Exception as e:
            print(f"Receive data error: {e}")
        finally:
            if self.connected_server:
                self.server_disconnected.emit(self.connected_server)
                self.connected_server = None
    
    def _receive_file_binary(self, file_info):
        """Receive file from server with binary integrity"""
        try:
            filename = file_info['filename']
            filesize = file_info['filesize']
            
            print(f"Starting to receive file: {filename} ({filesize} bytes)")
            
            # Create received files directory
            received_dir = Path("received_files")
            received_dir.mkdir(exist_ok=True)
            
            file_path = received_dir / filename
            
            # Receive exactly filesize bytes - no more, no less
            received_bytes = 0
            
            with open(file_path, 'wb') as f:
                while received_bytes < filesize:
                    # Calculate remaining bytes
                    remaining = filesize - received_bytes
                    chunk_size = min(8192, remaining)  # Larger chunks for efficiency
                    
                    # Receive exactly chunk_size bytes
                    chunk = b''
                    while len(chunk) < chunk_size:
                        try:
                            self.server_socket.settimeout(30)  # 30 second timeout
                            data = self.server_socket.recv(chunk_size - len(chunk))
                            if not data:
                                raise Exception(f"Connection closed during file transfer at {received_bytes}/{filesize} bytes")
                            chunk += data
                        except socket.timeout:
                            print(f"Timeout receiving data, retrying... ({received_bytes}/{filesize} bytes received)")
                            continue
                    
                    # Write exact chunk to file
                    f.write(chunk)
                    received_bytes += len(chunk)
                    
                    # Progress feedback every 64KB
                    if received_bytes % 65536 == 0 or received_bytes == filesize:
                        progress = int((received_bytes / filesize) * 100)
                        print(f"Receiving {filename}: {progress}% ({received_bytes}/{filesize} bytes)")
            
            # Verify file size
            actual_size = os.path.getsize(file_path)
            if actual_size != filesize:
                raise Exception(f"File size mismatch: expected {filesize}, got {actual_size}")
            
            # Send completion acknowledgment
            self.server_socket.send(b'COMPLETE')
            
            # Emit signal for UI update
            self.file_received.emit(filename, str(file_path))
            print(f"File successfully received: {filename} ({received_bytes} bytes, verified)")
            
            # Check if it's an installer and run it
            if filename.lower().endswith(('.exe', '.msi')):
                try:
                    print(f"Running installer: {filename}")
                    import subprocess
                    # Run installer silently
                    subprocess.Popen([str(file_path), '/S'], shell=True)
                    print(f"Installer started: {filename}")
                except Exception as e:
                    print(f"Failed to run installer {filename}: {e}")
            
        except Exception as e:
            print(f"File receive error: {e}")
            # Try to send error acknowledgment
            try:
                self.server_socket.send(b'ERROR')
            except:
                pass

class ClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client_thread = ClientThread()
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        self.setWindowTitle("LAN Client - Simple Working")
        self.setGeometry(100, 100, 500, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Connection status
        self.status_label = QLabel("Status: Disconnected")
        layout.addWidget(self.status_label)
        
        # Server discovery
        layout.addWidget(QLabel("Available Servers:"))
        self.servers_list = QListWidget()
        layout.addWidget(self.servers_list)
        
        # Connection controls
        controls_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_servers)
        controls_layout.addWidget(self.refresh_button)
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_to_server)
        controls_layout.addWidget(self.connect_button)
        
        layout.addLayout(controls_layout)
        
        # Received files
        layout.addWidget(QLabel("Received Files:"))
        self.files_list = QListWidget()
        layout.addWidget(self.files_list)
        
        # Activity log
        layout.addWidget(QLabel("Activity Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_area)
        
    def connect_signals(self):
        self.client_thread.server_discovered.connect(self.on_server_discovered)
        self.client_thread.server_connected.connect(self.on_server_connected)
        self.client_thread.server_disconnected.connect(self.on_server_disconnected)
        self.client_thread.file_received.connect(self.on_file_received)
        self.client_thread.log_message.connect(self.on_log_message)
        
    def showEvent(self, event):
        super().showEvent(event)
        # Start discovery when window is shown
        self.client_thread.start_discovery()
        self.on_log_message("Discovery started")
        
    def closeEvent(self, event):
        self.client_thread.stop_discovery()
        super().closeEvent(event)
        
    def refresh_servers(self):
        self.servers_list.clear()
        self.client_thread.discovered_servers.clear()
        
    def connect_to_server(self):
        current_item = self.servers_list.currentItem()
        if not current_item:
            return
            
        server_ip = current_item.text().split(' ')[0]
        self.client_thread.connect_to_server(server_ip)
        
    def on_server_discovered(self, server_ip, server_name):
        item = QListWidgetItem(f"{server_ip} - {server_name}")
        self.servers_list.addItem(item)
        
    def on_server_connected(self, server_ip):
        self.status_label.setText(f"Status: Connected to {server_ip}")
        self.connect_button.setText("Disconnect")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.disconnect_from_server)
        
    def on_server_disconnected(self, server_ip):
        self.status_label.setText("Status: Disconnected")
        self.connect_button.setText("Connect")
        self.connect_button.clicked.disconnect()
        self.connect_button.clicked.connect(self.connect_to_server)
        
    def disconnect_from_server(self):
        self.client_thread.disconnect_from_server()
        
    def on_file_received(self, filename, file_path):
        item = QListWidgetItem(f"{filename} - {file_path}")
        self.files_list.addItem(item)
        
    def on_log_message(self, message):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")

def main():
    app = QApplication(sys.argv)
    window = ClientWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
