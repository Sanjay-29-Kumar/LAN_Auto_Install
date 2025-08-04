import sys
import socket
import threading
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel, QListWidget, QFileDialog, QTextEdit, QListWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

from network.discovery import NetworkDiscovery, Device
from network.protocol import NetworkProtocol, MessageType
from ui.server_ui import ServerMainWindow

class ServerController:
    def __init__(self):
        self.protocol = NetworkProtocol()
        self.discovery = NetworkDiscovery()
        self.connected_clients = {}  # {client_ip: socket}
        self.running = False
        self.server_socket = None
        
    def start_server(self, port: int = 5000) -> bool:
        """Start the server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', port))
            self.server_socket.listen(5)
            
            self.running = True
            
            # Start accepting connections
            accept_thread = threading.Thread(target=self._accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            print(f"Server started on port {port}")
            return True
            
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False
    
    def stop_server(self):
        """Stop the server"""
        self.running = False
        
        # Close all client connections
        for client_socket in self.connected_clients.values():
            try:
                client_socket.close()
            except:
                pass
        self.connected_clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
        
        print("Server stopped")
    
    def _accept_connections(self):
        """Accept incoming client connections"""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_ip = client_address[0]
                
                self.connected_clients[client_ip] = client_socket
                print(f"Client connected: {client_ip}")
                
                # Start handling this client
                client_thread = threading.Thread(
                    target=self._handle_client, 
                    args=(client_socket, client_ip)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    print(f"Accept connection error: {e}")
                break
    
    def _handle_client(self, client_socket: socket.socket, client_ip: str):
        """Handle individual client connection"""
        try:
            while self.running:
                try:
                    # Receive message with length prefix
                    length_bytes = client_socket.recv(4)
                    if len(length_bytes) != 4:
                        break
                    
                    message_length = int.from_bytes(length_bytes, byteorder='big')
                    message_data = client_socket.recv(message_length)
                    
                    if len(message_data) != message_length:
                        break
                    
                    message = json.loads(message_data.decode('utf-8'))
                    self._process_client_message(message, client_ip, client_socket)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Client handler error for {client_ip}: {e}")
                    break
                    
        except Exception as e:
            print(f"Client handler error: {e}")
        finally:
            # Clean up client connection
            if client_ip in self.connected_clients:
                del self.connected_clients[client_ip]
            try:
                client_socket.close()
            except:
                pass
            print(f"Client disconnected: {client_ip}")
    
    def _process_client_message(self, message: Dict[str, Any], client_ip: str, client_socket: socket.socket):
        """Process message from client"""
        msg_type = message.get('type')
        
        if msg_type == 'DISCOVERY':
            self.handle_discovery(message, client_ip, client_socket)
        elif msg_type == MessageType.SYSTEM_MESSAGE.value:
            print(f"Message from {client_ip}: {message.get('content', '')}")
    
    def handle_discovery(self, data: Dict[str, Any], client_ip: str, client_socket: socket.socket):
        """Handle discovery request from client"""
        try:
            # Get local server info
            local_ip = self.discovery.get_local_ip()
            
            response_data = {
                'type': 'DISCOVERY_RESPONSE',
                'server_name': 'LAN File Server',
                'server_ip': local_ip,
                'server_port': 5000,
                'timestamp': data.get('timestamp', 0)
            }
            
            # Send response with length prefix
            response_json = json.dumps(response_data).encode('utf-8')
            response_length = len(response_json)
            
            client_socket.send(response_length.to_bytes(4, byteorder='big'))
            client_socket.send(response_json)
            
            print(f"Discovery response sent to {client_ip}")
            
        except Exception as e:
            print(f"Discovery handler error: {e}")
    
    def get_connected_clients(self) -> List[str]:
        """Get list of connected client IPs"""
        return list(self.connected_clients.keys())
    
    def send_file_to_client(self, client_ip: str, file_path: str) -> bool:
        """Send file to specific client"""
        if client_ip not in self.connected_clients:
            print(f"Client {client_ip} not connected")
            return False
        
        try:
            client_socket = self.connected_clients[client_ip]
            
            # Get file info
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)
            
            # Send file transfer message
            file_message = {
                'type': MessageType.FILE_TRANSFER.value,
                'filename': filename,
                'filesize': file_size
            }
            
            message_json = json.dumps(file_message).encode('utf-8')
            message_length = len(message_json)
            
            # Send message header
            client_socket.send(message_length.to_bytes(4, byteorder='big'))
            client_socket.send(message_json)
            
            print(f"Sending file to {client_ip}: {filename} ({file_size} bytes)")
            
            # Send file data
            bytes_sent = 0
            with open(file_path, 'rb') as f:
                while bytes_sent < file_size:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    
                    client_socket.send(chunk)
                    bytes_sent += len(chunk)
                    
                    # Progress feedback
                    progress = int((bytes_sent / file_size) * 100)
                    if bytes_sent % (4096 * 10) == 0:  # Every 10 chunks
                        print(f"Sending to {client_ip}: {progress}%")
            
            print(f"File sent successfully to {client_ip}: {filename}")
            return True
            
        except Exception as e:
            print(f"File transfer error to {client_ip}: {e}")
            return False
    
    def broadcast_message(self, message: str):
        """Broadcast message to all connected clients"""
        msg_data = {
            'type': MessageType.SYSTEM_MESSAGE.value,
            'content': message
        }
        
        for client_ip, client_socket in self.connected_clients.items():
            try:
                message_json = json.dumps(msg_data).encode('utf-8')
                message_length = len(message_json)
                
                client_socket.send(message_length.to_bytes(4, byteorder='big'))
                client_socket.send(message_json)
                
            except Exception as e:
                print(f"Failed to send message to {client_ip}: {e}")

class ServerApplication:
    def __init__(self):
        self.controller = ServerController()
        self.main_window = None
        self.discovered_devices = []
        
    def run(self):
        """Run the server application"""
        app = QApplication(sys.argv)
        
        self.main_window = ServerMainWindow()
        self.main_window.set_controller(self.controller)
        self.main_window.show()
        
        # Connect signals
        self.main_window.start_server_requested.connect(self.on_start_server)
        self.main_window.stop_server_requested.connect(self.on_stop_server)
        self.main_window.discover_devices_requested.connect(self.on_discover_devices)
        self.main_window.transfer_started.connect(self.on_transfer_started)
        
        sys.exit(app.exec_())
    
    def on_start_server(self):
        """Handle start server request"""
        success = self.controller.start_server()
        if success:
            self.main_window.set_server_status(True)
            self.main_window.add_log_message("Server started successfully")
        else:
            self.main_window.show_error("Failed to start server")
    
    def on_stop_server(self):
        """Handle stop server request"""
        self.controller.stop_server()
        self.main_window.set_server_status(False)
        self.main_window.add_log_message("Server stopped")
    
    def on_discover_devices(self):
        """Handle device discovery request"""
        try:
            self.main_window.add_log_message("Discovering network devices...")
            
            # Discover devices on network
            devices = self.controller.discovery.discover_devices()
            self.discovered_devices = devices
            
            # Update UI with discovered devices
            self.main_window.update_devices_list(devices)
            self.main_window.add_log_message(f"Found {len(devices)} devices")
            
        except Exception as e:
            self.main_window.add_log_message(f"Discovery error: {e}")
    
    def on_transfer_started(self, file_path: str, target_ip: str):
        """Handle file transfer request"""
        try:
            # Get selected devices from UI
            selected_devices = self.main_window.device_widget.get_selected_devices()
            
            if not selected_devices:
                self.main_window.add_log_message("No devices selected for transfer")
                return
            
            # Filter for connected clients and Windows devices
            connected_clients = self.controller.get_connected_clients()
            valid_targets = []
            
            for device in selected_devices:
                if device.ip in connected_clients:
                    valid_targets.append(device.ip)
                elif device.is_windows:
                    # Try to include Windows devices even if not explicitly connected
                    valid_targets.append(device.ip)
            
            if not valid_targets:
                self.main_window.add_log_message("No valid target devices found. Devices must be Windows and connected.")
                return
            
            # Send file to each target
            for target_ip in valid_targets:
                self.main_window.add_log_message(f"Starting file transfer to {target_ip}")
                
                # Send file in separate thread
                transfer_thread = threading.Thread(
                    target=self._transfer_file_thread,
                    args=(file_path, target_ip)
                )
                transfer_thread.daemon = True
                transfer_thread.start()
                
        except Exception as e:
            self.main_window.add_log_message(f"Transfer error: {e}")
    
    def _transfer_file_thread(self, file_path: str, target_ip: str):
        """Transfer file in separate thread"""
        try:
            success = self.controller.send_file_to_client(target_ip, file_path)
            if success:
                self.main_window.add_log_message(f"File transfer completed to {target_ip}")
            else:
                self.main_window.add_log_message(f"File transfer failed to {target_ip}")
        except Exception as e:
            self.main_window.add_log_message(f"Transfer thread error: {e}")

def main():
    """Main entry point"""
    server_app = ServerApplication()
    server_app.run()

if __name__ == "__main__":
    main()
