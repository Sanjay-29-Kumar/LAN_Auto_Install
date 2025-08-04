import sys
import socket
import threading
import json
import os
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QListWidget, QFileDialog, QTextEdit, QListWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

class ServerThread(QThread):
    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.server_socket = None
        self.discovery_socket = None
        self.clients = {}  # {ip: socket}
        
    def start_server(self):
        self.running = True
        self.start()
        
    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        if self.discovery_socket:
            self.discovery_socket.close()
        self.wait()
        
    def run(self):
        try:
            # Start discovery service
            self.start_discovery_service()
            
            # Start TCP server for client connections
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', 5000))
            self.server_socket.listen(5)
            
            self.log_message.emit("Server started on port 5000")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_ip = client_address[0]
                    
                    self.clients[client_ip] = client_socket
                    self.client_connected.emit(client_ip)
                    self.log_message.emit(f"Client connected: {client_ip}")
                    
                    # Start thread to handle this client
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_ip))
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        self.log_message.emit(f"Server error: {e}")
                        
        except Exception as e:
            self.log_message.emit(f"Server start error: {e}")
            
    def start_discovery_service(self):
        """Start UDP discovery service"""
        try:
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.discovery_socket.bind(('0.0.0.0', 5001))
            
            discovery_thread = threading.Thread(target=self.handle_discovery)
            discovery_thread.daemon = True
            discovery_thread.start()
            
            self.log_message.emit("Discovery service started on port 5001")
            
        except Exception as e:
            self.log_message.emit(f"Discovery service error: {e}")
            
    def handle_discovery(self):
        """Handle UDP discovery requests"""
        while self.running:
            try:
                data, addr = self.discovery_socket.recvfrom(1024)
                message = data.decode('utf-8')
                
                if message == "DISCOVER":
                    # Get local IP
                    local_ip = socket.gethostbyname(socket.gethostname())
                    response = f"SERVER:{local_ip}:5000"
                    self.discovery_socket.sendto(response.encode('utf-8'), addr)
                    self.log_message.emit(f"Discovery response sent to {addr[0]}")
                    
            except Exception as e:
                if self.running:
                    self.log_message.emit(f"Discovery error: {e}")
                    
    def handle_client(self, client_socket, client_ip):
        """Handle individual client connection"""
        try:
            while self.running:
                # Keep connection alive
                pass
        except Exception as e:
            self.log_message.emit(f"Client handler error for {client_ip}: {e}")
        finally:
            if client_ip in self.clients:
                del self.clients[client_ip]
            self.client_disconnected.emit(client_ip)
            client_socket.close()
            
    def send_file_to_client(self, client_ip, file_path):
        """Send file to specific client with binary integrity"""
        if client_ip not in self.clients:
            self.log_message.emit(f"Client {client_ip} not connected")
            return False
            
        try:
            client_socket = self.clients[client_ip]
            
            # Get file info
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            # Create file transfer message
            file_info = {
                'type': 'FILE_TRANSFER',
                'filename': filename,
                'filesize': file_size
            }
            
            # Send header with length prefix
            header_data = json.dumps(file_info).encode('utf-8')
            header_length = len(header_data)
            
            # Send header length (4 bytes) + header data
            client_socket.send(header_length.to_bytes(4, byteorder='big'))
            client_socket.send(header_data)
            
            self.log_message.emit(f"Sent file info to {client_ip}: {filename} ({file_size} bytes)")
            
            # Wait for ACK
            try:
                client_socket.settimeout(10)
                ack = client_socket.recv(3)
                if ack != b'ACK':
                    raise Exception(f"Expected ACK, got: {ack}")
                self.log_message.emit(f"Received ACK from {client_ip}")
            except socket.timeout:
                raise Exception("Timeout waiting for ACK")
            
            # Send file data with binary integrity
            bytes_sent = 0
            client_socket.settimeout(30)
            
            with open(file_path, 'rb') as f:
                while bytes_sent < file_size:
                    # Calculate remaining bytes
                    remaining = file_size - bytes_sent
                    chunk_size = min(8192, remaining)  # Match client chunk size
                    chunk = f.read(chunk_size)
                    
                    if not chunk:
                        break
                    
                    # Ensure entire chunk is sent
                    chunk_sent = 0
                    while chunk_sent < len(chunk):
                        try:
                            sent = client_socket.send(chunk[chunk_sent:])
                            if sent == 0:
                                raise Exception("Socket connection broken")
                            chunk_sent += sent
                        except Exception as e:
                            self.log_message.emit(f"Error sending chunk to {client_ip}: {e}")
                            raise
                    
                    bytes_sent += len(chunk)
                    
                    # Progress feedback every 64KB
                    if bytes_sent % 65536 == 0 or bytes_sent == file_size:
                        progress = int((bytes_sent / file_size) * 100)
                        self.log_message.emit(f"Sending to {client_ip}: {progress}% ({bytes_sent}/{file_size} bytes)")
            
            # Wait for completion acknowledgment
            try:
                client_socket.settimeout(30)
                completion = client_socket.recv(8)
                if completion == b'COMPLETE':
                    self.log_message.emit(f"File successfully sent to {client_ip} ({bytes_sent} bytes)")
                    return True
                elif completion == b'ERROR':
                    self.log_message.emit(f"Client {client_ip} reported error during file transfer")
                    return False
                else:
                    self.log_message.emit(f"Unexpected completion response from {client_ip}: {completion}")
                    return False
            except socket.timeout:
                self.log_message.emit(f"Timeout waiting for completion from {client_ip}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"File transfer error to {client_ip}: {e}")
            return False

class ServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server_thread = ServerThread()
        self.init_ui()
        self.connect_signals()
        
    def init_ui(self):
        self.setWindowTitle("LAN File Server")
        self.setGeometry(100, 100, 600, 500)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Server controls
        controls_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Server")
        self.start_button.clicked.connect(self.start_server)
        controls_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop Server")
        self.stop_button.clicked.connect(self.stop_server)
        self.stop_button.setEnabled(False)
        controls_layout.addWidget(self.stop_button)
        
        layout.addLayout(controls_layout)
        
        # Connected clients
        layout.addWidget(QLabel("Connected Clients:"))
        self.clients_list = QListWidget()
        self.clients_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.clients_list)
        
        # File selection and sending
        file_layout = QHBoxLayout()
        
        self.select_file_button = QPushButton("Select File")
        self.select_file_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.select_file_button)
        
        self.send_file_button = QPushButton("Send to Selected Clients")
        self.send_file_button.clicked.connect(self.send_file)
        self.send_file_button.setEnabled(False)
        file_layout.addWidget(self.send_file_button)
        
        layout.addLayout(file_layout)
        
        self.selected_file_label = QLabel("No file selected")
        layout.addWidget(self.selected_file_label)
        
        # Log area
        layout.addWidget(QLabel("Server Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_area)
        
        self.selected_file_path = None
        
    def connect_signals(self):
        self.server_thread.client_connected.connect(self.on_client_connected)
        self.server_thread.client_disconnected.connect(self.on_client_disconnected)
        self.server_thread.log_message.connect(self.on_log_message)
        
    def start_server(self):
        self.server_thread.start_server()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
    def stop_server(self):
        self.server_thread.stop_server()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.clients_list.clear()
        
    def on_client_connected(self, client_ip):
        item = QListWidgetItem(client_ip)
        self.clients_list.addItem(item)
        
    def on_client_disconnected(self, client_ip):
        for i in range(self.clients_list.count()):
            item = self.clients_list.item(i)
            if item.text() == client_ip:
                self.clients_list.takeItem(i)
                break
                
    def on_log_message(self, message):
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")
        
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Send")
        if file_path:
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            self.selected_file_label.setText(f"Selected: {filename} ({file_size} bytes)")
            self.send_file_button.setEnabled(True)
        else:
            self.selected_file_path = None
            self.selected_file_label.setText("No file selected")
            self.send_file_button.setEnabled(False)
            
    def send_file(self):
        if not self.selected_file_path:
            return
            
        selected_items = self.clients_list.selectedItems()
        if not selected_items:
            self.on_log_message("No clients selected for file transfer")
            return
            
        for item in selected_items:
            client_ip = item.text()
            self.on_log_message(f"Starting file transfer to {client_ip}")
            
            # Send file in separate thread to avoid blocking UI
            transfer_thread = threading.Thread(
                target=self.server_thread.send_file_to_client,
                args=(client_ip, self.selected_file_path)
            )
            transfer_thread.daemon = True
            transfer_thread.start()

def main():
    app = QApplication(sys.argv)
    window = ServerWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
