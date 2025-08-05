import sys
import os
import socket
import threading
import json
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

from network.discovery import NetworkDiscovery, get_local_ip
from network.protocol import ClientProtocol, MessageType
from network.transfer import FileReceiver
from ui.client_ui import ClientMainWindow

class ClientController(QThread):
    server_discovered = pyqtSignal(dict)
    connection_status_changed = pyqtSignal(bool, str)
    file_received = pyqtSignal(dict)
    transfer_progress = pyqtSignal(str, float)
    log_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.discovery = NetworkDiscovery()
        self.protocol = None
        self.file_receiver = FileReceiver()
        self.connected_server = None
        self.running = False
        self.discovery_timer = QTimer()
        self.discovery_timer.timeout.connect(self.discover_servers)

    def start_discovery(self):
        """Start server discovery"""
        self.running = True
        self.discovery_timer.start(5000)  # Discover every 5 seconds
        self.discover_servers()

    def stop_discovery(self):
        """Stop server discovery"""
        self.running = False
        self.discovery_timer.stop()

    def discover_servers(self):
        """Discover available servers"""
        try:
            local_ip = get_local_ip()
            network_range = self.discovery.get_network_range()

            servers = []
            for ip in network_range[:20]:  # Scan first 20 IPs for speed
                if ip == local_ip:
                    continue

                try:
                    # Test connection to server port
                    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    test_sock.settimeout(0.5)
                    result = test_sock.connect_ex((ip, 5000))

                    if result == 0:
                        # Send discovery request
                        discovery_msg = {
                            "type": "discovery",
                            "client_ip": local_ip,
                            "timestamp": time.time()
                        }

                        msg_data = json.dumps(discovery_msg).encode('utf-8')
                        test_sock.send(len(msg_data).to_bytes(4, 'big'))
                        test_sock.send(msg_data)

                        # Wait for response
                        try:
                            resp_len = int.from_bytes(test_sock.recv(4), 'big')
                            resp_data = test_sock.recv(resp_len)
                            response = json.loads(resp_data.decode('utf-8'))

                            if response.get('type') == 'discovery_response':
                                server_info = {
                                    'ip': ip,
                                    'hostname': response.get('server_name', 'LAN Server'),
                                    'port': 5000
                                }
                                servers.append(server_info)
                                self.server_discovered.emit(server_info)
                        except:
                            pass

                    test_sock.close()
                except:
                    continue

        except Exception as e:
            self.log_message.emit(f"Discovery error: {str(e)}")

    def connect_to_server(self, server_ip: str, server_port: int = 5000) -> bool:
        """Connect to a server"""
        try:
            self.protocol = ClientProtocol(server_ip, server_port)

            # Register message handlers
            self.protocol.register_message_handler(MessageType.FILE_TRANSFER, self.handle_file_transfer)
            self.protocol.register_connection_callback(self.on_connection_status_changed)

            # Register file receive handlers
            self.file_receiver.register_receive_callback("default", self.on_file_progress)

            success = self.protocol.connect()
            if success:
                self.connected_server = {'ip': server_ip, 'port': server_port}
                self.log_message.emit(f"Connected to server: {server_ip}")
                return True
            else:
                self.log_message.emit("Failed to connect to server")
                return False

        except Exception as e:
            self.log_message.emit(f"Connection error: {str(e)}")
            return False

    def disconnect_from_server(self):
        """Disconnect from current server"""
        if self.protocol:
            self.protocol.disconnect()
            self.protocol = None
        self.connected_server = None
        self.connection_status_changed.emit(False, "")

    def handle_file_transfer(self, data: Dict[str, Any]):
        """Handle incoming file transfer"""
        try:
            if "transfer_id" in data:
                # File transfer initiation
                self.file_receiver.handle_file_transfer_init(data, self.protocol)
                self.log_message.emit(f"Receiving file: {data.get('file_name', 'Unknown')}")
            elif "chunk_data" in data:
                # File chunk
                self.file_receiver.handle_file_chunk(data, self.protocol)

        except Exception as e:
            self.log_message.emit(f"File transfer error: {str(e)}")

    def on_connection_status_changed(self, connected: bool):
        """Handle connection status changes"""
        if connected:
            server_ip = self.connected_server['ip'] if self.connected_server else ""
            self.connection_status_changed.emit(True, server_ip)
        else:
            self.connection_status_changed.emit(False, "")

    def on_file_progress(self, status: str, progress: float):
        """Handle file transfer progress"""
        self.transfer_progress.emit(status, progress)

        if status == "completed":
            # Check for received files and auto-install
            received_files = self.file_receiver.get_received_files()
            for file_info in received_files:
                if file_info['type'] == 'installer':
                    self.auto_install_file(file_info['path'])

                self.file_received.emit(file_info)

    def auto_install_file(self, file_path: str):
        """Auto-install executable files"""
        try:
            if file_path.lower().endswith(('.exe', '.msi')):
                self.log_message.emit(f"Auto-installing: {os.path.basename(file_path)}")
                subprocess.Popen([file_path, '/S'], shell=True)
        except Exception as e:
            self.log_message.emit(f"Installation error: {str(e)}")

class ClientApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.controller = ClientController()
        self.main_window = ClientMainWindow()
        self.setup_connections()

    def setup_connections(self):
        """Setup signal connections"""
        # Connect controller signals to UI
        self.controller.log_message.connect(self.main_window.add_activity_event)
        self.controller.server_discovered.connect(self.update_server_list)
        self.controller.connection_status_changed.connect(self.on_connection_status_changed)
        self.controller.file_received.connect(self.on_file_received)
        self.controller.transfer_progress.connect(self.on_transfer_progress)

        # Connect UI signals to controller
        self.main_window.server_widget.server_connected.connect(self.on_connect_request)
        self.main_window.server_widget.refresh_servers.connect(self.controller.discover_servers)

    def update_server_list(self, server_info: dict):
        """Update server list in UI"""
        servers = [server_info]  # In real implementation, maintain a list
        self.main_window.server_widget.update_servers(servers)

    def on_connection_status_changed(self, connected: bool, server_ip: str):
        """Handle connection status changes"""
        self.main_window.update_connection_status(connected, server_ip)

    def on_file_received(self, file_info: dict):
        """Handle received file"""
        self.main_window.reception_widget.add_received_file(file_info)
        self.main_window.update_file_count(len(self.controller.file_receiver.get_received_files()))

    def on_transfer_progress(self, status: str, progress: float):
        """Handle transfer progress"""
        # Update UI with transfer progress
        pass

    def on_connect_request(self, server_ip: str):
        """Handle connection request from UI"""
        success = self.controller.connect_to_server(server_ip)
        if not success:
            QMessageBox.warning(self.main_window, "Connection Error", 
                              "Failed to connect to server")

    def run(self):
        """Run the application"""
        self.main_window.show()

        # Start discovery
        self.controller.start_discovery()

        return self.app.exec_()

def main():
    """Main entry point"""
    app = ClientApplication()
    sys.exit(app.run())

if __name__ == "__main__":
    main()