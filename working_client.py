"""
Working LAN Auto Install Client v2.0
Real bidirectional client-server connections with working file transfer
"""

import sys
import os
import socket
import threading
import time
import json
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from network import protocol
from network.transfer import FileReceiver
from ui.custom_widgets import FileTransferWidget
# Import dynamic installer
from utils.dynamic_installer import DynamicInstaller


class WorkingNetworkClient(QObject):
    """Working network client with real server connections"""
    server_found = pyqtSignal(dict)
    connection_status = pyqtSignal(str, bool)  # server_ip, connected
    file_received = pyqtSignal(dict)
    file_progress = pyqtSignal(str, str, float) # file_name, server_ip, percentage
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.servers = {}
        self.connected_servers = {}
        self.file_receiver_socket = None
        self.local_ip = self._get_local_ip()
        
        # Get executable directory for received_files path
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            self.exe_dir = Path(sys.executable).parent
        else:
            # Running as script
            self.exe_dir = Path(__file__).parent
        
        self.received_files_path = self.exe_dir / "received_files"
        print(f" Received files will be stored in: {self.received_files_path}")
        
        # Initialize dynamic installer with received files path
        self.dynamic_installer = DynamicInstaller(str(self.received_files_path))
        
        # Flag to ensure integrated auto setup runs only once
        self._auto_setup_initialized = False
        
        # Start integrated auto setup on initialization (only once)
        self._start_integrated_auto_setup()
    
    def _start_integrated_auto_setup(self):
        """Start integrated auto setup functionality - processes existing files and starts monitoring (only once)"""
        # Prevent repeated initialization
        if self._auto_setup_initialized:
            print("ℹ️ Auto setup already initialized - skipping")
            return
            
        try:
            print("🚀 Initializing integrated auto setup...")
            
            # Process any existing files silently
            results = self.dynamic_installer.manual_install_check()
            
            if results:
                new_installations = 0
                manual_setups = 0
                for filename, status in results.items():
                    if status == "installed_successfully":
                        new_installations += 1
                        print(f"✅ Auto-installed: {filename}")
                    elif status == "manual_setup_needed":
                        manual_setups += 1
                        print(f"🔧 {filename} - Manual setup needed")
                    elif status == "check_manually":
                        manual_setups += 1
                        print(f"⚠️ {filename} - Check and set up manually")
                    elif status == "installation_failed":
                        print(f"❌ Failed to install: {filename}")
                
                if new_installations > 0:
                    print(f"🎉 {new_installations} files installed and ready to use!")
                if manual_setups > 0:
                    print(f"🔧 {manual_setups} files need manual attention when convenient")
            
            # Start monitoring only if not already running
            if not self.dynamic_installer._monitoring:
                self.dynamic_installer.start_monitoring(check_interval=10)
                print("✅ Auto-install monitoring activated")
            
            # Mark as initialized
            self._auto_setup_initialized = True
            
        except Exception as e:
            print(f"❌ Error in integrated auto setup: {e}")
        
    def start_discovery(self):
        """Start server discovery and file receiver"""
        self.running = True
        
        # Start file receiver server
        threading.Thread(target=self._start_file_receiver, daemon=True).start()
        
        # Start server discovery
        threading.Thread(target=self._discover_servers, daemon=True).start()
        
        print(f"Client started on {self.local_ip}")
    
    def _start_file_receiver(self):
        """Start file receiver server on the designated file transfer port."""
        try:
            self.file_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.file_receiver_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.file_receiver_socket.bind(('0.0.0.0', protocol.FILE_TRANSFER_PORT))
            self.file_receiver_socket.listen(5)
            
            print(f"File receiver listening on port {protocol.FILE_TRANSFER_PORT}")
            
            while self.running:
                try:
                    self.file_receiver_socket.settimeout(1.0)
                    client_sock, addr = self.file_receiver_socket.accept()
                    
                    # Define completion callback
                    def on_complete(file_name, status, file_path):
                        print(f"File '{file_name}' from {addr[0]} reception status: {status}")
                        if status == 'completed':
                            file_size = os.path.getsize(file_path)
                            file_info = {
                                'name': file_name,
                                'path': str(file_path),
                                'size': file_size,
                                'category': 'unknown', # Category can be refined
                                'sender': addr[0],
                                'received_time': time.time()
                            }
                            self.file_received.emit(file_info)
                            # Auto-install if it's an installer
                            if Path(file_name).suffix.lower() in ['.exe', '.msi']:
                                threading.Thread(target=self._auto_install_immediately, 
                                               args=(str(file_path), file_name), daemon=True).start()

                    # Create and start the FileReceiver thread
                    receiver_thread = FileReceiver(
                        sock=client_sock,
                        addr=addr,
                        received_files_dir=str(self.received_files_path),
                        completion_callback=on_complete,
                        progress_callback=self.file_progress.emit
                    )
                    receiver_thread.start()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"File receiver loop error: {e}")
                    break
                    
        except Exception as e:
            print(f"File receiver startup error: {e}")
    
    def _discover_servers(self):
        """Discover and connect to servers"""
        while self.running:
            try:
                # UDP broadcast discovery
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(2.0)
                
                # Send discovery broadcast
                message = json.dumps({
                    'type': 'client_discovery',
                    'client_ip': self.local_ip,
                    'client_port': protocol.FILE_TRANSFER_PORT,
                    'timestamp': time.time()
                }).encode('utf-8')
                
                base_ip = '.'.join(self.local_ip.split('.')[:-1])
                sock.sendto(message, (f"{base_ip}.255", protocol.DISCOVERY_PORT))
                
                # Listen for server responses
                start_time = time.time()
                while time.time() - start_time < 3.0:
                    try:
                        data, addr = sock.recvfrom(1024)
                        response = json.loads(data.decode('utf-8'))
                        
                        if response.get('type') == 'server_response':
                            server_ip = addr[0]
                            server_info = {
                                'ip': server_ip,
                                'hostname': response.get('hostname', f'Server-{server_ip.split(".")[-1]}'),
                                'port': response.get('port', protocol.COMMAND_PORT),
                                'last_seen': time.time()
                            }
                            
                            if server_ip not in self.servers:
                                self.servers[server_ip] = server_info
                                self.server_found.emit(server_info)
                                
                                # Establish connection to server
                                self._connect_to_server(server_ip, server_info['port'])
                            
                            self.servers[server_ip]['last_seen'] = time.time()
                            
                    except socket.timeout:
                        break
                    except:
                        continue
                
                sock.close()
                
            except Exception as e:
                print(f"Discovery error: {e}")
            
            time.sleep(5)  # Discovery interval
    
    def _connect_to_server(self, server_ip, server_port):
        """Establish persistent connection to server"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((server_ip, server_port))
            
            # Send client registration
            registration = json.dumps({
                'type': 'client_register',
                'client_ip': self.local_ip,
                'client_port': protocol.FILE_TRANSFER_PORT,
                'hostname': socket.gethostname()
            }).encode('utf-8')
            
            sock.send(registration + b'\n')
            
            # Keep connection alive
            self.connected_servers[server_ip] = sock
            self.connection_status.emit(server_ip, True)
            
            # Start connection keeper
            threading.Thread(target=self._keep_connection_alive, 
                           args=(server_ip, sock), daemon=True).start()
            
            print(f"Connected to server: {server_ip}")
            
        except Exception as e:
            print(f"Connection to {server_ip} failed: {e}")
            self.connection_status.emit(server_ip, False)
    
    def _keep_connection_alive(self, server_ip, sock):
        """Keep connection alive with server"""
        while self.running and server_ip in self.connected_servers:
            try:
                # Send heartbeat
                heartbeat = json.dumps({
                    'type': 'heartbeat',
                    'client_ip': self.local_ip,
                    'timestamp': time.time()
                }).encode('utf-8')
                
                sock.sendall(heartbeat + b'\n')
                time.sleep(10)  # Heartbeat every 10 seconds
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                print(f"Connection to {server_ip} lost: {e}")
                break
            except Exception as e:
                print(f"Error in keep-alive for {server_ip}: {e}")
                break
        
        # Cleanup after connection is lost
        if server_ip in self.connected_servers:
            if server_ip in self.connected_servers:
                del self.connected_servers[server_ip]
            self.connection_status.emit(server_ip, False)
            try:
                sock.close()
            except:
                pass
    
    def send_status_update(self, file_name, status):
        """Send a status update to all connected servers."""
        for server_ip, sock in self.connected_servers.items():
            try:
                message = {
                    'type': protocol.MSG_TYPE_STATUS_UPDATE,
                    'file_name': file_name,
                    'status': status,
                    'client_ip': self.local_ip
                }
                sock.sendall(json.dumps(message).encode('utf-8') + b'\n')
            except Exception as e:
                print(f"Failed to send status update to {server_ip}: {e}")
    
    def _auto_install_immediately(self, installer_path, file_name):
        """Immediately install received executable with ONE ATTEMPT ONLY (completely silent)"""
        try:
            # Ensure path exists
            if not os.path.exists(installer_path):
                return
            
            # CRITICAL: Mark file as being processed BEFORE attempting installation
            # This prevents any possibility of multiple attempts
            if self.dynamic_installer:
                self.dynamic_installer.mark_file_as_processed(Path(installer_path), "processing")
            
            installer_path_quoted = f'"{installer_path}"'
            
            # Use ONLY the most reliable silent command - ONE ATTEMPT ONLY
            # This prevents multiple popups for the same file
            cmd = f'{installer_path_quoted} /SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART'
            
            installation_result = 'failed'
            
            try:
                # Single attempt with very short timeout to detect popups quickly
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    check=False,  # Don't raise exception on non-zero exit
                    timeout=5,  # Very short timeout - 5 seconds only
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0  # Hide window on Windows
                )
                
                if result.returncode == 0:
                    installation_result = 'success'
                elif result.returncode == 1223:  # User cancelled
                    installation_result = 'manual_setup_needed'
                else:
                    # Any other return code means there was an error - check manually
                    installation_result = 'check_manually'
                    
            except subprocess.TimeoutExpired:
                # Timeout means user interaction required - manual setup needed
                installation_result = 'manual_setup_needed'
            except Exception as e:
                # Any error means check manually
                installation_result = 'check_manually'
            
            # Update dynamic installer tracking and send status update
            if installation_result == 'success':
                self.dynamic_installer.mark_file_as_processed(Path(installer_path), "installed")
                self.send_status_update(file_name, "Installed Successfully")
            elif installation_result == 'manual_setup_needed':
                self.dynamic_installer.mark_file_as_processed(Path(installer_path), "manual_setup_needed")
                self.send_status_update(file_name, "Manual Setup Needed")
                print(f"🔧 {file_name} - Manual setup needed")
            elif installation_result == 'check_manually':
                self.dynamic_installer.mark_file_as_processed(Path(installer_path), "check_manually")
                self.send_status_update(file_name, "Check Manually")
                print(f"⚠️ {file_name} - Check and set up manually")
            else:
                self.dynamic_installer.mark_file_as_processed(Path(installer_path), "failed")
                self.send_status_update(file_name, "Installation Failed")
                
        except Exception as e:
            print(f"💥 Critical error during auto-installation of {file_name}: {e}")
            if self.dynamic_installer:
                self.dynamic_installer.mark_file_as_processed(Path(installer_path), "error")
    
    def _process_installer_file(self, installer_path, file_name):
        """Legacy method - kept for compatibility"""
        print(f"📋 Using legacy installer processing for: {file_name}")
        self._auto_install_immediately(installer_path, file_name)
    
    def _silent_install(self, installer_path):
        """Legacy silent installation method - kept for compatibility"""
        # Redirect to new auto install method
        file_name = Path(installer_path).name
        self._auto_install_immediately(installer_path, file_name)
    
    def _get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def stop(self):
        """Stop client"""
        self.running = False
        
        # Close all connections
        for sock in self.connected_servers.values():
            try:
                sock.close()
            except:
                pass
        
        if self.file_receiver_socket:
            try:
                self.file_receiver_socket.close()
            except:
                pass


from ui.client_ui import ClientWindow

class ClientController:
    def __init__(self, network_client, ui):
        self.network_client = network_client
        self.ui = ui
        self.transfer_widgets = {}
        self.connect_signals()

    def connect_signals(self):
        # Connect network signals to UI slots
        self.network_client.server_found.connect(self.update_server_list)
        self.network_client.connection_status.connect(self.update_connection_status)
        self.network_client.file_received.connect(self.add_received_file)
        self.network_client.file_progress.connect(self.update_transfer_progress)

        # Connect UI signals to controller slots
        self.ui.refresh_servers_button.clicked.connect(self.refresh_servers)
        self.ui.connect_to_selected_button.clicked.connect(self.connect_to_selected)
        self.ui.open_folder_button.clicked.connect(self.open_received_folder)
        self.ui.clear_list_button.clicked.connect(self.clear_received_list)
        self.ui.server_list_widget.itemClicked.connect(self.show_server_profile)
        self.ui.manual_connect_button.clicked.connect(self.connect_manual)

    def show_server_profile(self, item):
        ip = item.text().split('(')[1].replace(')', '').split(' ')[0]
        if ip in self.network_client.servers:
            server_info = self.network_client.servers[ip]
            profile_text = f"""
            <b>Server Profile</b><br>
            --------------------<br>
            <b>Hostname:</b> {server_info.get('hostname', 'N/A')}<br>
            <b>IP Address:</b> {server_info.get('ip', 'N/A')}<br>
            <b>Last Seen:</b> {time.ctime(server_info.get('last_seen', 0))}
            """
            QMessageBox.information(self.ui, "Server Profile", profile_text)

    def update_server_list(self, server_info):
        # Avoid duplicates
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if server_info['ip'] in item.text():
                return
        
        item = QListWidgetItem(f"{server_info['hostname']} ({server_info['ip']})")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        self.ui.server_list_widget.addItem(item)

    def update_connection_status(self, server_ip, connected):
        self.ui.connection_status_label.setText("Connected" if connected else "Not Connected")
        # You can also update the server list item to show connection status
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if server_ip in item.text():
                if connected:
                    item.setText(f"{item.text().split(' ')[0]} ({server_ip}) [Connected]")
                    item.setForeground(QColor("lightgreen"))
                else:
                    item.setText(f"{item.text().split(' ')[0]} ({server_ip}) [Disconnected]")
                    item.setForeground(QColor("lightcoral"))
                break

    def add_received_file(self, file_info):
        file_name = file_info['name']
        server_ip = file_info['sender']
        
        widget = FileTransferWidget(file_name, file_info['size'])
        item = QListWidgetItem(self.ui.receiving_list_widget)
        item.setSizeHint(widget.sizeHint())
        self.ui.receiving_list_widget.addItem(item)
        self.ui.receiving_list_widget.setItemWidget(item, widget)
        self.transfer_widgets[(file_name, server_ip)] = widget

    def update_transfer_progress(self, file_name, server_ip, percentage):
        if (file_name, server_ip) in self.transfer_widgets:
            widget = self.transfer_widgets[(file_name, server_ip)]
            widget.set_progress(percentage)
            widget.set_status(f"Receiving from {server_ip}...", "orange")
            if percentage >= 100:
                widget.set_status("Completed", "lightgreen")

    def refresh_servers(self):
        self.ui.server_list_widget.clear()
        self.network_client.servers.clear()
        # The discovery thread will find servers again automatically

    def connect_to_selected(self):
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                ip = item.text().split('(')[1].replace(')', '').split(' ')[0]
                if ip in self.network_client.servers:
                    server_info = self.network_client.servers[ip]
                    self.network_client._connect_to_server(server_info['ip'], server_info['port'])

    def connect_manual(self):
        ip = self.ui.manual_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self.ui, "Invalid IP", "Please enter a valid IP address.")
            return
        
        # Use default command port
        port = protocol.COMMAND_PORT
        self.network_client._connect_to_server(ip, port)

    def open_received_folder(self):
        os.startfile(self.network_client.received_files_path)

    def clear_received_list(self):
        self.ui.receiving_list_widget.clear()


def main():
    app = QApplication(sys.argv)
    
    network_client = WorkingNetworkClient()
    network_client.start_discovery()
    
    main_window = ClientWindow(network_client)
    controller = ClientController(network_client, main_window)
    
    main_window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    sys.exit(main())
