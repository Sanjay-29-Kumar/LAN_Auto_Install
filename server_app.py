import sys
import os
import socket
import threading
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

from network.discovery import NetworkDiscovery, NetworkDevice
from network.protocol import NetworkProtocol, MessageType
from network.transfer import FileTransfer
from ui.server_ui import ServerMainWindow

class ServerController(QThread):
    device_discovered = pyqtSignal(NetworkDevice)
    client_connected = pyqtSignal(str)
    client_disconnected = pyqtSignal(str)
    transfer_progress = pyqtSignal(str, str, float)
    log_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.protocol = NetworkProtocol()
        self.discovery = NetworkDiscovery()
        self.file_transfer = FileTransfer()
        self.running = False
        self.connected_clients = {}
        self.discovered_devices = []

    def start_server(self, port: int = 5000) -> bool:
        """Start the server"""
        try:
            success = self.protocol.start_server()
            if success:
                self.running = True

                # Register message handlers
                self.protocol.register_message_handler(MessageType.HANDSHAKE, self.handle_handshake)
                self.protocol.register_message_handler(MessageType.DISCOVERY, self.handle_discovery)

                # Start discovery
                self.discovery.start_discovery(self.on_device_discovered)

                self.log_message.emit(f"Server started successfully on port {port}")
                return True
            else:
                self.log_message.emit("Failed to start server")
                return False
        except Exception as e:
            self.log_message.emit(f"Server start error: {str(e)}")
            return False

    def stop_server(self):
        """Stop the server"""
        self.running = False
        self.protocol.stop_server()
        self.discovery.stop_discovery()
        self.log_message.emit("Server stopped")

    def handle_handshake(self, data: Dict[str, Any], client_ip: str):
        """Handle client handshake"""
        client_id = data.get("client_id", client_ip)
        self.connected_clients[client_ip] = {
            "id": client_id,
            "connected_time": time.time()
        }
        self.client_connected.emit(client_ip)
        self.log_message.emit(f"Client connected: {client_ip}")

    def handle_discovery(self, data: Dict[str, Any], client_ip: str):
        """Handle discovery request"""
        local_ip = self.discovery.get_local_ip()
        response_data = {
            "server_name": "LAN File Server",
            "server_ip": local_ip,
            "server_port": 5000
        }
        self.protocol.send_to_client(client_ip, MessageType.DISCOVERY_RESPONSE, response_data)

    def on_device_discovered(self, device: NetworkDevice):
        """Handle discovered device"""
        self.device_discovered.emit(device)
        self.discovered_devices.append(device)

    def get_discovered_devices(self) -> List[NetworkDevice]:
        """Get list of discovered devices"""
        return self.discovered_devices

    def get_connected_clients(self) -> List[str]:
        """Get list of connected clients"""
        return list(self.connected_clients.keys())
    
    def send_file_to_client(self, file_path: str, client_ip: str) -> bool:
        """Send file to specific client"""
        if not os.path.exists(file_path):
            self.log_message.emit(f"File not found: {file_path}")
            return False
        
        if client_ip not in self.connected_clients:
            self.log_message.emit(f"Client not connected: {client_ip}")
            return False
        
        try:
            transfer_id = f"transfer_{int(time.time())}_{os.path.basename(file_path)}"
            success = self.file_transfer.start_file_transfer(
                file_path, client_ip, self.protocol, transfer_id
            )
            
            if success:
                self.log_message.emit(f"Started file transfer to {client_ip}: {os.path.basename(file_path)}")
                
                # Register callback for progress updates
                def progress_callback(status, progress):
                    self.transfer_progress.emit(transfer_id, client_ip, progress)
                    if status == "completed":
                        self.log_message.emit(f"File transfer completed to {client_ip}")
                    elif status == "failed":
                        self.log_message.emit(f"File transfer failed to {client_ip}")
                
                self.file_transfer.register_transfer_callback(transfer_id, progress_callback)
                return True
            else:
                self.log_message.emit(f"Failed to start file transfer to {client_ip}")
                return False
                
        except Exception as e:
            self.log_message.emit(f"Error sending file: {str(e)}")
            return False
    
    def broadcast_file(self, file_path: str) -> Dict[str, bool]:
        """Send file to all connected clients"""
        results = {}
        for client_ip in self.connected_clients:
            results[client_ip] = self.send_file_to_client(file_path, client_ip)
        return results

    def send_file(self, file_path: str, target_devices: List[NetworkDevice]):
        """Send file to target devices"""
        if not os.path.exists(file_path):
            self.log_message.emit(f"File not found: {file_path}")
            return

        for device in target_devices:
            if device.ip in self.connected_clients:
                self.log_message.emit(f"Sending file to {device.ip}: {os.path.basename(file_path)}")

                # Register transfer callback
                transfer_id = f"{int(time.time())}_{device.ip}"
                self.file_transfer.register_transfer_callback(
                    transfer_id,
                    lambda status, progress, ip=device.ip: self.transfer_progress.emit(transfer_id, ip, progress)
                )

                # Start transfer
                success = self.file_transfer.start_file_transfer(
                    file_path, device.ip, self.protocol, transfer_id
                )

                if not success:
                    self.log_message.emit(f"Failed to start transfer to {device.ip}")

class ServerApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.controller = ServerController()
        self.main_window = ServerMainWindow()
        self.setup_connections()

    def setup_connections(self):
        """Setup signal connections"""
        # Connect controller signals to UI
        self.controller.log_message.connect(self.main_window.add_network_event)
        self.controller.device_discovered.connect(self.update_device_list)
        self.controller.client_connected.connect(self.on_client_connected)
        self.controller.transfer_progress.connect(self.on_transfer_progress)

        # Connect UI signals to controller
        self.main_window.device_widget.refresh_devices.connect(self.refresh_devices)
        self.main_window.transfer_widget.transfer_started.connect(self.on_transfer_started)

    def update_device_list(self, device: NetworkDevice):
        """Update device list in UI"""
        devices = self.controller.get_discovered_devices()
        self.main_window.device_widget.update_devices(devices)

    def on_client_connected(self, client_ip: str):
        """Handle client connection"""
        self.main_window.update_status(True, len(self.controller.get_connected_clients()))

    def on_transfer_progress(self, transfer_id: str, client_ip: str, progress: float):
        """Handle transfer progress updates"""
        self.main_window.transfer_widget.update_transfer_progress(transfer_id, progress)

    def refresh_devices(self):
        """Refresh device discovery"""
        self.controller.discovery.scan_network()

    def on_transfer_started(self, file_path: str, target_ip: str):
        """Handle transfer start request"""
        selected_devices = self.main_window.device_widget.get_selected_devices()
        if selected_devices:
            self.controller.send_file(file_path, selected_devices)

    def start_server(self):
        """Start the server"""
        return self.controller.start_server()

    def run(self):
        """Run the application"""
        self.main_window.show()

        # Auto-start server
        if self.start_server():
            self.main_window.update_status(True)

        return self.app.exec_()

def main():
    """Main entry point"""
    app = ServerApplication()
    sys.exit(app.run())

if __name__ == "__main__":
    main()