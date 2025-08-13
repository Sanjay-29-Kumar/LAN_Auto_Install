"""
Working LAN Auto Install Server v2.0
Real bidirectional client-server connections with working file distribution
"""

import sys
import os
import socket
import threading
import time
import json
import hashlib
from pathlib import Path
from network.transfer import FileSender
from network import protocol
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui.custom_widgets import FileTransferWidget


class WorkingNetworkServer(QObject):
    """Working network server with real client connections"""
    client_connected = pyqtSignal(dict)
    client_disconnected = pyqtSignal(str)
    file_sent = pyqtSignal(dict)
    distribution_complete = pyqtSignal(str, int)
    file_progress = pyqtSignal(str, str, float) # file_name, client_ip, percentage
    status_update_received = pyqtSignal(str, str, str) # file_name, client_ip, status
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.clients = {}
        self.client_sockets = {}
        self.server_socket = None
        self.udp_socket = None
        self.local_ip = self._get_local_ip()
        self.files_to_distribute = []
        
    def start_server(self):
        """Start server with all services"""
        self.running = True
        
        # Start TCP server for client connections
        threading.Thread(target=self._start_tcp_server, daemon=True).start()
        
        # Start UDP broadcast responder
        threading.Thread(target=self._start_udp_responder, daemon=True).start()
        
        print(f"Server started on {self.local_ip}")
    
    def _start_tcp_server(self):
        """Start TCP server for client connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', protocol.COMMAND_PORT))
            self.server_socket.listen(10)
            
            print(f"TCP server listening on port {protocol.COMMAND_PORT}")
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_sock, addr = self.server_socket.accept()
                    threading.Thread(target=self._handle_client_connection, 
                                   args=(client_sock, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except:
                    break
                    
        except Exception as e:
            print(f"TCP server error: {e}")
    
    def _start_udp_responder(self):
        """Start UDP broadcast responder"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('0.0.0.0', protocol.DISCOVERY_PORT))
            
            print(f"UDP responder listening on port {protocol.DISCOVERY_PORT}")
            
            while self.running:
                try:
                    self.udp_socket.settimeout(1.0)
                    data, addr = self.udp_socket.recvfrom(1024)
                    request = json.loads(data.decode('utf-8'))
                    
                    if request.get('type') == 'client_discovery':
                        # Respond to client discovery
                        response = {
                            'type': 'server_response',
                            'hostname': socket.gethostname(),
                            'port': protocol.COMMAND_PORT,
                            'timestamp': time.time()
                        }
                        
                        self.udp_socket.sendto(json.dumps(response).encode('utf-8'), addr)
                        print(f"Responded to discovery from {addr[0]}")
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"UDP responder error: {e}")
                    continue
                    
        except Exception as e:
            print(f"UDP responder startup error: {e}")
    
    def _handle_client_connection(self, sock, addr):
        """Handle client connection"""
        client_ip = addr[0]
        print(f" New client connection from {client_ip}")
        
        try:
            while self.running:
                try:
                    sock.settimeout(5.0)
                    data = sock.recv(1024)
                    if not data:
                        print(f"No data received from {client_ip}, closing connection")
                        break
                    
                    # Parse message - handle multiple messages in one packet
                    message_data = data.decode('utf-8').strip()
                    if not message_data:
                        continue
                    
                    # Split by newlines in case multiple messages are sent
                    for message_line in message_data.split('\n'):
                        if not message_line.strip():
                            continue
                            
                        try:
                            message = json.loads(message_line.strip())
                            print(f"Received message from {client_ip}: {message.get('type', 'unknown')}")
                            
                            if message.get('type') == 'client_register':
                                # Register new client
                                client_info = {
                                    'ip': client_ip,
                                    'hostname': message.get('hostname', f'Client-{client_ip.split(".")[-1]}'),
                                    'port': message.get('client_port', protocol.FILE_TRANSFER_PORT),
                                    'connected': True,
                                    'last_seen': time.time(),
                                    'files_sent': 0
                                }
                                
                                self.clients[client_ip] = client_info
                                self.client_sockets[client_ip] = sock
                                print(f"Client registered successfully: {client_info['hostname']} ({client_ip})")
                                self.client_connected.emit(client_info)
                                
                                # Send acknowledgment back to client
                                ack = json.dumps({
                                    'type': 'registration_ack',
                                    'status': 'success',
                                    'server_hostname': socket.gethostname()
                                }).encode('utf-8')
                                sock.send(ack + b'\n')
                                
                            elif message.get('type') == 'heartbeat':
                                # Update last seen
                                if client_ip in self.clients:
                                    self.clients[client_ip]['last_seen'] = time.time()
                                    print(f"💓 Heartbeat from {client_ip}")
                                else:
                                    print(f"⚠️ Heartbeat from unregistered client {client_ip}")
                            elif message.get('type') == protocol.MSG_TYPE_STATUS_UPDATE:
                                file_name = message.get('file_name')
                                status = message.get('status')
                                self.status_update_received.emit(file_name, client_ip, status)
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ JSON decode error from {client_ip}: {e}")
                            continue
                    
                except socket.timeout:
                    # Timeout is normal, continue listening
                    continue
                except json.JSONDecodeError as e:
                    print(f"JSON decode error from {client_ip}: {e}")
                    continue # Continue listening for more data
                except ConnectionResetError:
                    print(f"Connection reset by {client_ip}.")
                    break
                except Exception as e:
                    print(f"Unhandled error in client handler for {client_ip}: {e}")
                    break
                    
        except Exception as e:
            print(f"Critical error in client connection handler: {e}")
        finally:
            # Clean up disconnected client
            if client_ip in self.clients:
                self.clients[client_ip]['connected'] = False
                self.client_disconnected.emit(client_ip)
                
            if client_ip in self.client_sockets:
                del self.client_sockets[client_ip]
                
            try:
                sock.close()
            except:
                pass
                
            print(f"Client disconnected: {client_ip}")
    
    def add_files_for_distribution(self, file_paths):
        """Add files for distribution"""
        for file_path in file_paths:
            if os.path.exists(file_path):
                file_info = {
                    'path': file_path,
                    'name': os.path.basename(file_path),
                    'size': os.path.getsize(file_path),
                    'category': self._get_file_category(file_path),
                    'added_time': time.time()
                }
                self.files_to_distribute.append(file_info)
                print(f"Added file for distribution: {file_info['name']}")
    
    def distribute_files_to_clients(self, client_ips=None):
        """Distribute files to specified clients or all clients"""
        if not self.files_to_distribute:
            print("No files to distribute")
            return

        if client_ips is None:
            client_ips = [ip for ip, client in self.clients.items() if client['connected']]

        if not client_ips:
            print("No connected clients")
            return

        print(f"Distributing {len(self.files_to_distribute)} files to {len(client_ips)} clients")

        for file_info in self.files_to_distribute:
            for client_ip in client_ips:
                if client_ip in self.clients and self.clients[client_ip]['connected']:
                    client_port = self.clients[client_ip].get('port', protocol.FILE_TRANSFER_PORT)
                    
                    # Define callbacks for progress and completion
                    def progress_update(file_name, percentage):
                        self.file_progress.emit(file_name, client_ip, percentage)

                    def completion_update(file_name, status):
                        print(f"Completion status for {file_name} to {client_ip}: {status}")
                        if status == 'completed':
                            self.clients[client_ip]['files_sent'] += 1
                            send_info = {
                                'file_name': file_info['name'],
                                'client_ip': client_ip,
                                'client_hostname': self.clients[client_ip]['hostname'],
                                'file_size': file_info['size'],
                                'sent_time': time.time()
                            }
                            self.file_sent.emit(send_info)
                        # self.transfer_completed.emit(file_name, client_ip, status)

                    # Create and start the FileSender thread
                    sender_thread = FileSender(
                        client_ip=client_ip,
                        client_port=client_port,
                        file_path=file_info['path'],
                        file_info=file_info,
                        progress_callback=progress_update,
                        completion_callback=completion_update
                    )
                    sender_thread.start()
    
    def _get_file_category(self, file_path):
        """Get file category"""
        ext = Path(file_path).suffix.lower()
        
        if ext in ['.exe', '.msi', '.deb', '.rpm']:
            return 'installer'
        elif ext in ['.pdf', '.doc', '.docx', '.txt']:
            return 'document'
        elif ext in ['.jpg', '.png', '.mp4', '.mp3', '.avi']:
            return 'media'
        elif ext in ['.zip', '.rar', '.7z', '.tar']:
            return 'archive'
        else:
            return 'other'
    
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
    
    def get_connected_clients(self):
        """Get list of connected clients"""
        return [client for client in self.clients.values() if client['connected']]
    
    def stop_server(self):
        """Stop server"""
        self.running = False
        
        # Close all client connections
        for sock in self.client_sockets.values():
            try:
                sock.close()
            except:
                pass
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass


from ui.server_ui import ServerWindow

class ServerController:
    def __init__(self, network_server, ui):
        self.network_server = network_server
        self.ui = ui
        self.connect_signals()

    def connect_signals(self):
        # Connect network signals to UI slots
        self.network_server.client_connected.connect(self.update_client_list)
        self.network_server.client_disconnected.connect(self.update_client_list)

        # Connect UI signals to controller slots
        self.ui.select_files_button.clicked.connect(self.select_files)
        self.ui.send_files_button.clicked.connect(self.send_files)
        self.ui.back_to_home_button.clicked.connect(self.ui.show_home)
        self.ui.refresh_clients_button.clicked.connect(self.update_client_list)
        self.ui.add_more_files_button.clicked.connect(self.select_files)
        self.ui.remove_selected_files_button.clicked.connect(self.remove_selected_files)
        self.ui.select_all_files_button.clicked.connect(self.select_all_files)
        self.ui.send_to_all_button.clicked.connect(self.send_to_all_clients)
        self.network_server.file_progress.connect(self.update_transfer_progress)
        self.network_server.status_update_received.connect(self.update_transfer_status)
        self.ui.client_list_widget.itemClicked.connect(self.show_client_profile)

    def show_client_profile(self, item):
        ip = item.text().split('(')[1].replace(')', '')
        if ip in self.network_server.clients:
            client_info = self.network_server.clients[ip]
            profile_text = f"""
            <b>Client Profile</b><br>
            --------------------<br>
            <b>Hostname:</b> {client_info.get('hostname', 'N/A')}<br>
            <b>IP Address:</b> {client_info.get('ip', 'N/A')}<br>
            <b>Last Seen:</b> {time.ctime(client_info.get('last_seen', 0))}<br>
            <b>Files Sent:</b> {client_info.get('files_sent', 0)}
            """
            QMessageBox.information(self.ui, "Client Profile", profile_text)

    def update_client_list(self):
        self.ui.client_list_widget.clear()
        connected_clients = self.network_server.get_connected_clients()
        for client in connected_clients:
            item = QListWidgetItem(f"{client['hostname']} ({client['ip']})")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.ui.client_list_widget.addItem(item)
        self.ui.connected_clients_label.setText(str(len(connected_clients)))
        self.ui.connection_status_label.setText("Connected" if connected_clients else "Not Connected")

    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self.ui, "Select Files to Share")
        if file_paths:
            self.network_server.add_files_for_distribution(file_paths)
            self.update_selected_files_list()
            self.ui.show_after_selection()

    def update_selected_files_list(self):
        self.ui.selected_files_list_widget.clear()
        for file_info in self.network_server.files_to_distribute:
            item = QListWidgetItem(f"{file_info['name']} ({file_info['size'] / 1024 / 1024:.2f} MB)")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.ui.selected_files_list_widget.addItem(item)

    def remove_selected_files(self):
        items_to_remove = []
        for i in range(self.ui.selected_files_list_widget.count()):
            item = self.ui.selected_files_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                items_to_remove.append(i)

        # Remove in reverse order to avoid index shifting issues
        for i in sorted(items_to_remove, reverse=True):
            self.network_server.files_to_distribute.pop(i)
            self.ui.selected_files_list_widget.takeItem(i)

    def select_all_files(self):
        for i in range(self.ui.selected_files_list_widget.count()):
            item = self.ui.selected_files_list_widget.item(i)
            item.setCheckState(Qt.Checked)

    def send_files(self):
        selected_clients = []
        for i in range(self.ui.client_list_widget.count()):
            item = self.ui.client_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                # Assuming the text is "hostname (ip)"
                ip = item.text().split('(')[1].replace(')', '')
                selected_clients.append(ip)
        
        if not selected_clients:
            QMessageBox.warning(self.ui, "No Clients Selected", "Please select at least one client to send files to.")
            return

        if not self.network_server.files_to_distribute:
            QMessageBox.warning(self.ui, "No Files Selected", "Please select files to distribute.")
            return

        self.ui.transfer_list_widget.clear()
        self.transfer_widgets = {}

        for file_info in self.network_server.files_to_distribute:
            for client_ip in selected_clients:
                widget = FileTransferWidget(file_info['name'], file_info['size'])
                item = QListWidgetItem(self.ui.transfer_list_widget)
                item.setSizeHint(widget.sizeHint())
                self.ui.transfer_list_widget.addItem(item)
                self.ui.transfer_list_widget.setItemWidget(item, widget)
                self.transfer_widgets[(file_info['name'], client_ip)] = widget

        self.network_server.distribute_files_to_clients(selected_clients)
        self.ui.show_while_sharing()

    def update_transfer_progress(self, file_name, client_ip, percentage):
        if (file_name, client_ip) in self.transfer_widgets:
            widget = self.transfer_widgets[(file_name, client_ip)]
            widget.set_progress(percentage)
            widget.set_status(f"Sending to {client_ip}...", "orange")
            if percentage >= 100:
                widget.set_status("Sent", "lightgreen")

    def update_transfer_status(self, file_name, client_ip, status):
        if (file_name, client_ip) in self.transfer_widgets:
            widget = self.transfer_widgets[(file_name, client_ip)]
            widget.set_status(status, "lightblue")

    def send_to_all_clients(self):
        self.network_server.distribute_files_to_clients()
        self.ui.show_while_sharing()


def main():
    app = QApplication(sys.argv)
    
    network_server = WorkingNetworkServer()
    network_server.start_server()
    
    main_window = ServerWindow(network_server)
    controller = ServerController(network_server, main_window)
    
    main_window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    sys.exit(main())
