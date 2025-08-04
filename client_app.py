import sys
import socket
import threading
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QListWidget, QTextEdit, QListWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

from network.discovery import NetworkDiscovery, Device
from network.protocol import NetworkProtocol, MessageType
from ui.client_ui import ClientMainWindow

class ClientController:
    def __init__(self):
        self.protocol = NetworkProtocol()
        self.discovery = NetworkDiscovery()
        self.connected_server = None
        self.running = False
        
    def discover_servers(self) -> List[Dict[str, Any]]:
        """Discover available servers on the network"""
        servers = []
        
        try:
            # Get local network info
            local_ip = self.discovery.get_local_ip()
            network_range = self.discovery.get_network_range(local_ip)
            
            print(f"Scanning network: {network_range}")
            
            # Scan for servers
            for ip in self.discovery.scan_network_range(network_range):
                if ip == local_ip:
                    continue
                    
                try:
                    # Check if server port is open
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_sock.settimeout(1)
                    result = test_sock.connect_ex((ip, 5000))
                    
                    if result == 0:
                        # Send discovery message with proper JSON format
                        discovery_msg = {
                            'type': 'DISCOVERY',
                            'client_ip': local_ip,
                            'timestamp': time.time()
                        }
                        
                        # Send with length prefix
                        msg_data = json.dumps(discovery_msg).encode('utf-8')
                        msg_length = len(msg_data)
                        
                        test_sock.send(msg_length.to_bytes(4, byteorder='big'))
                        test_sock.send(msg_data)
                        
                        # Wait for response
                        test_sock.settimeout(2)
                        try:
                            response_length_bytes = test_sock.recv(4)
                            if len(response_length_bytes) == 4:
                                response_length = int.from_bytes(response_length_bytes, byteorder='big')
                                response_data = test_sock.recv(response_length)
                                
                                if len(response_data) == response_length:
                                    response = json.loads(response_data.decode('utf-8'))
                                    if response.get('type') == 'DISCOVERY_RESPONSE':
                                        servers.append({
                                            'ip': ip,
                                            'name': response.get('server_name', 'LAN Server'),
                                            'port': response.get('server_port', 5000)
                                        })
                                        print(f"Discovered server: {ip}")
                        except (socket.timeout, json.JSONDecodeError):
                            pass
                    
                    test_sock.close()
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Discovery error: {e}")
            
        return servers
    
    def connect_to_server(self, server_ip: str, server_port: int = 5000) -> bool:
        """Connect to a specific server"""
        try:
            self.protocol.connect(server_ip, server_port)
            self.connected_server = {'ip': server_ip, 'port': server_port}
            print(f"Connected to server: {server_ip}:{server_port}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect_from_server(self):
        """Disconnect from current server"""
        if self.protocol.is_connected():
            self.protocol.disconnect()
        self.connected_server = None
        print("Disconnected from server")
    
    def start_receiving(self, message_handler):
        """Start receiving messages from server"""
        self.running = True
        receive_thread = threading.Thread(target=self._receive_loop, args=(message_handler,))
        receive_thread.daemon = True
        receive_thread.start()
    
    def stop_receiving(self):
        """Stop receiving messages"""
        self.running = False
    
    def _receive_loop(self, message_handler):
        """Main receive loop"""
        while self.running and self.protocol.is_connected():
            try:
                message = self.protocol.receive_message()
                if message:
                    message_handler(message)
            except Exception as e:
                print(f"Receive error: {e}")
                break

class ClientApplication:
    def __init__(self):
        self.controller = ClientController()
        self.main_window = None
        
    def run(self):
        """Run the client application"""
        app = QApplication(sys.argv)
        
        self.main_window = ClientMainWindow()
        self.main_window.set_controller(self.controller)
        self.main_window.show()
        
        # Connect signals
        self.main_window.discover_requested.connect(self.on_discover_servers)
        self.main_window.connect_requested.connect(self.on_connect_to_server)
        self.main_window.disconnect_requested.connect(self.on_disconnect_from_server)
        
        # Start message handling
        self.controller.start_receiving(self.on_message_received)
        
        sys.exit(app.exec_())
    
    def on_discover_servers(self):
        """Handle server discovery request"""
        servers = self.controller.discover_servers()
        self.main_window.update_servers_list(servers)
    
    def on_connect_to_server(self, server_ip: str, server_port: int):
        """Handle connection request"""
        success = self.controller.connect_to_server(server_ip, server_port)
        if success:
            self.main_window.set_connection_status(True, server_ip)
        else:
            self.main_window.show_error("Failed to connect to server")
    
    def on_disconnect_from_server(self):
        """Handle disconnection request"""
        self.controller.disconnect_from_server()
        self.main_window.set_connection_status(False)
    
    def on_message_received(self, message: Dict[str, Any]):
        """Handle received messages from server"""
        msg_type = message.get('type')
        
        if msg_type == MessageType.FILE_TRANSFER.value:
            self.handle_file_transfer(message)
        elif msg_type == MessageType.SYSTEM_MESSAGE.value:
            self.main_window.add_log_message(message.get('content', ''))
    
    def handle_file_transfer(self, message: Dict[str, Any]):
        """Handle incoming file transfer"""
        try:
            filename = message.get('filename')
            filesize = message.get('filesize')
            
            if not filename or not filesize:
                return
            
            self.main_window.add_log_message(f"Receiving file: {filename} ({filesize} bytes)")
            
            # Create received files directory
            received_dir = Path("received_files")
            received_dir.mkdir(exist_ok=True)
            
            file_path = received_dir / filename
            
            # Receive file data
            received_bytes = 0
            with open(file_path, 'wb') as f:
                while received_bytes < filesize:
                    chunk_size = min(4096, filesize - received_bytes)
                    chunk = self.controller.protocol.receive_data(chunk_size)
                    
                    if not chunk:
                        break
                    
                    f.write(chunk)
                    received_bytes += len(chunk)
                    
                    # Update progress
                    progress = int((received_bytes / filesize) * 100)
                    self.main_window.update_transfer_progress(filename, progress)
            
            if received_bytes == filesize:
                self.main_window.add_log_message(f"File received successfully: {filename}")
                self.main_window.add_received_file(filename, str(file_path))
                
                # Check if it's an installer
                if filename.lower().endswith(('.exe', '.msi')):
                    self.run_installer(file_path)
            else:
                self.main_window.add_log_message(f"File transfer incomplete: {filename}")
                
        except Exception as e:
            self.main_window.add_log_message(f"File transfer error: {e}")
    
    def run_installer(self, file_path: Path):
        """Run installer silently"""
        try:
            import subprocess
            self.main_window.add_log_message(f"Running installer: {file_path.name}")
            
            # Run installer with silent flag
            subprocess.Popen([str(file_path), '/S'], shell=True)
            self.main_window.add_log_message(f"Installer started: {file_path.name}")
            
        except Exception as e:
            self.main_window.add_log_message(f"Failed to run installer: {e}")

def main():
    """Main entry point"""
    client_app = ClientApplication()
    client_app.run()

if __name__ == "__main__":
    main()
