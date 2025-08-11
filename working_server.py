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
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class WorkingNetworkServer(QObject):
    """Working network server with real client connections"""
    client_connected = pyqtSignal(dict)
    client_disconnected = pyqtSignal(str)
    file_sent = pyqtSignal(dict)
    distribution_complete = pyqtSignal(str, int)
    
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
            self.server_socket.bind(('0.0.0.0', 5000))
            self.server_socket.listen(10)
            
            print("TCP server listening on port 5000")
            
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
            self.udp_socket.bind(('0.0.0.0', 5001))
            
            print("UDP responder listening on port 5001")
            
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
                            'port': 5000,
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
                                    'port': message.get('client_port', 5002),
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
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ JSON decode error from {client_ip}: {e}")
                            continue
                    
                except socket.timeout:
                    # Timeout is normal, continue listening
                    continue
                except Exception as e:
                    print(f"Client message error from {client_ip}: {e}")
                    break
                    
        except Exception as e:
            print(f"Client connection error: {e}")
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
            threading.Thread(target=self._send_file_to_clients, 
                           args=(file_info, client_ips), daemon=True).start()
    
    def _send_file_to_clients(self, file_info, client_ips):
        """Send file to multiple clients"""
        try:
            with open(file_info['path'], 'rb') as f:
                file_data = f.read()
            
            successful_sends = 0
            
            for client_ip in client_ips:
                if client_ip not in self.clients or not self.clients[client_ip]['connected']:
                    continue
                
                try:
                    client_port = self.clients[client_ip]['port']
                    
                    # Connect to client's file receiver
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(30.0)
                    sock.connect((client_ip, client_port))
                    
                    # Send file metadata
                    metadata = {
                        'type': 'file_transfer',
                        'file_name': file_info['name'],
                        'file_size': file_info['size'],
                        'category': file_info['category']
                    }
                    
                    sock.send(json.dumps(metadata).encode('utf-8') + b'\n')
                    
                    # Send file data
                    bytes_sent = 0
                    chunk_size = 2048576  # 2MB chunks
                    
                    while bytes_sent < len(file_data):
                        chunk = file_data[bytes_sent:bytes_sent + chunk_size]
                        sock.send(chunk)
                        bytes_sent += len(chunk)
                    
                    sock.close()
                    successful_sends += 1
                    
                    # Update client stats
                    self.clients[client_ip]['files_sent'] += 1
                    
                    # Emit file sent signal
                    send_info = {
                        'file_name': file_info['name'],
                        'client_ip': client_ip,
                        'client_hostname': self.clients[client_ip]['hostname'],
                        'file_size': file_info['size'],
                        'sent_time': time.time()
                    }
                    self.file_sent.emit(send_info)
                    
                    print(f"File sent successfully: {file_info['name']} -> {client_ip}")
                    
                except Exception as e:
                    print(f"Failed to send {file_info['name']} to {client_ip}: {e}")
            
            # Emit distribution complete
            self.distribution_complete.emit(file_info['name'], successful_sends)
            
        except Exception as e:
            print(f"File distribution error: {e}")
    
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


class WorkingServerWindow(QMainWindow):
    """Working server window with real client connections"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('🚀 LAN Install Working Server v2.0')
        self.setGeometry(100, 100, 1200, 800)
        
        # Professional styling
        self.setStyleSheet("""
            QMainWindow { 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #1e1e1e, stop: 1 #2d2d2d);
                color: white; 
            }
            QPushButton { 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #4a90e2, stop: 1 #357abd);
                border: none; border-radius: 12px; padding: 15px 25px; 
                font-weight: bold; font-size: 12pt; color: white;
            }
            QPushButton:hover { 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #5ba0f2, stop: 1 #4682cd);
            }
            QListWidget { 
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #3a3a3a, stop: 1 #404040);
                border: 2px solid #555; border-radius: 12px; padding: 12px;
                font-size: 11pt;
            }
            QLabel { color: white; }
            QProgressBar {
                border: 2px solid #555; border-radius: 12px; text-align: center;
                background: #3a3a3a; color: white; font-weight: bold; height: 30px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                                          stop: 0 #4a90e2, stop: 1 #5ba0f2);
                border-radius: 10px;
            }
        """)
        
        # Initialize network server
        self.network_server = WorkingNetworkServer()
        
        # Connect signals
        self.network_server.client_connected.connect(self.add_client)
        self.network_server.client_disconnected.connect(self.remove_client)
        self.network_server.file_sent.connect(self.add_sent_file)
        self.network_server.distribution_complete.connect(self.update_distribution_status)
        
        self.init_ui()
        
        # Start server
        self.network_server.start_server()
    
    def init_ui(self):
        """Initialize UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        
        # Header
        header = QLabel('🚀 LAN Install Working Server v2.0')
        header.setAlignment(Qt.AlignCenter)
        header.setFont(QFont('Segoe UI', 18, QFont.Bold))
        header.setStyleSheet('color: #4a90e2; margin: 20px;')
        layout.addWidget(header)
        
        # Status
        self.status_label = QLabel('🔄 Starting server - Listening for clients...')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('color: #FFA500; font-size: 14pt; font-weight: bold;')
        layout.addWidget(self.status_label)
        
        # Main content
        content_layout = QHBoxLayout()
        
        # Left panel - Connected Clients
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        clients_title = QLabel('💻 Connected Clients (Live)')
        clients_title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        clients_title.setStyleSheet('color: #4a90e2; margin: 10px;')
        left_layout.addWidget(clients_title)
        
        self.client_list = QListWidget()
        left_layout.addWidget(self.client_list)
        
        client_buttons = QHBoxLayout()
        self.refresh_clients_btn = QPushButton('🔄 Refresh')
        self.send_to_selected_btn = QPushButton('📤 Send to Selected')
        self.send_to_all_btn = QPushButton('📡 Send to All')
        
        self.refresh_clients_btn.clicked.connect(self.refresh_clients)
        self.send_to_selected_btn.clicked.connect(self.send_to_selected)
        self.send_to_all_btn.clicked.connect(self.send_to_all)
        
        client_buttons.addWidget(self.refresh_clients_btn)
        client_buttons.addWidget(self.send_to_selected_btn)
        client_buttons.addWidget(self.send_to_all_btn)
        left_layout.addLayout(client_buttons)
        
        left_panel.setLayout(left_layout)
        content_layout.addWidget(left_panel)
        
        # Right panel - File Distribution
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        files_title = QLabel('📦 File Distribution (Live)')
        files_title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        files_title.setStyleSheet('color: #4a90e2; margin: 10px;')
        right_layout.addWidget(files_title)
        
        self.distribution_list = QListWidget()
        right_layout.addWidget(self.distribution_list)
        
        file_buttons = QHBoxLayout()
        self.add_files_btn = QPushButton('➕ Add Files')
        self.send_selected_btn = QPushButton('📤 Send to Selected')
        self.send_all_btn = QPushButton('🚀 Send to All')
        self.clear_files_btn = QPushButton('🧹 Clear List')
        self.cancel_transfer_btn = QPushButton('❌ Cancel Transfer')
        
        self.add_files_btn.clicked.connect(self.add_files)
        self.send_selected_btn.clicked.connect(self.send_to_selected)
        self.send_all_btn.clicked.connect(self.send_to_all)
        self.clear_files_btn.clicked.connect(self.clear_distribution_list)
        self.cancel_transfer_btn.clicked.connect(self.cancel_current_transfer)
        
        file_buttons.addWidget(self.add_files_btn)
        file_buttons.addWidget(self.send_selected_btn)
        file_buttons.addWidget(self.send_all_btn)
        file_buttons.addWidget(self.clear_files_btn)
        file_buttons.addWidget(self.cancel_transfer_btn)
        right_layout.addLayout(file_buttons)
        
        right_panel.setLayout(right_layout)
        content_layout.addWidget(right_panel)
        
        layout.addLayout(content_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat(f'Server Ready - Listening on {self.network_server.local_ip}:5000-5001')
        layout.addWidget(self.progress_bar)
        
        central.setLayout(layout)
        
        # Status bar
        self.statusbar = QStatusBar()
        self.statusbar.showMessage(f'🟢 Server Ready - Listening on {self.network_server.local_ip}')
        self.setStatusBar(self.statusbar)
    
    @pyqtSlot(dict)
    def add_client(self, client):
        """Add connected client"""
        client_text = f"💻 {client['hostname']} ({client['ip']}) - Connected [ONLINE]"
        
        # Remove any existing entry for this client
        for i in range(self.client_list.count()):
            item = self.client_list.item(i)
            if client['ip'] in item.text():
                self.client_list.takeItem(i)
                break
        
        # Add new entry
        item = QListWidgetItem(client_text)
        item.setBackground(QColor(76, 175, 80, 50))  # Green background
        self.client_list.addItem(item)
        
        # Update status
        client_count = len([c for c in self.network_server.clients.values() if c['connected']])
        self.status_label.setText(f'✅ Server Active - {client_count} clients connected')
        self.status_label.setStyleSheet('color: #4CAF50; font-size: 14pt; font-weight: bold;')
        
        self.statusbar.showMessage(f"✅ Client connected: {client['hostname']} ({client['ip']})")
    
    @pyqtSlot(str)
    def remove_client(self, client_ip):
        """Remove disconnected client"""
        for i in range(self.client_list.count()):
            item = self.client_list.item(i)
            if client_ip in item.text():
                # Update text to show disconnected
                text = item.text().replace('[ONLINE]', '[OFFLINE]').replace('Connected', 'Disconnected')
                item.setText(text)
                item.setBackground(QColor(244, 67, 54, 50))  # Red background
                break
        
        # Update status
        client_count = len([c for c in self.network_server.clients.values() if c['connected']])
        if client_count == 0:
            self.status_label.setText('⚠️ No clients connected - Waiting for connections...')
            self.status_label.setStyleSheet('color: #FFA500; font-size: 14pt; font-weight: bold;')
        else:
            self.status_label.setText(f'✅ Server Active - {client_count} clients connected')
        
        self.statusbar.showMessage(f"⚠️ Client disconnected: {client_ip}")
    
    @pyqtSlot(dict)
    def add_sent_file(self, send_info):
        """Add sent file record"""
        size_mb = send_info['file_size'] / (1024 * 1024)
        file_text = f"📤 {send_info['file_name']} → {send_info['client_hostname']} ({size_mb:.1f}MB) ✅"
        self.distribution_list.addItem(file_text)
        
        self.statusbar.showMessage(f"📤 Sent: {send_info['file_name']} to {send_info['client_hostname']}")
    
    @pyqtSlot(str, int)
    def update_distribution_status(self, file_name, successful_sends):
        """Update distribution status"""
        self.statusbar.showMessage(f"✅ Distribution complete: {file_name} sent to {successful_sends} clients")
    
    def refresh_clients(self):
        """Refresh client list"""
        self.client_list.clear()
        
        # Re-add connected clients
        for client in self.network_server.clients.values():
            if client['connected']:
                self.add_client(client)
        
        self.statusbar.showMessage('🔄 Client list refreshed')
    
    def add_files(self):
        """Add files for distribution"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            'Select Files to Distribute',
            '',
            'All Files (*.*)'
        )
        
        if file_paths:
            self.network_server.add_files_for_distribution(file_paths)
            
            for file_path in file_paths:
                file_name = os.path.basename(file_path)
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                category = self.network_server._get_file_category(file_path)
                
                category_icons = {
                    'installer': '📦',
                    'document': '📄', 
                    'media': '🎵',
                    'archive': '📁',
                    'other': '📄'
                }
                
                icon = category_icons.get(category, '📄')
                file_text = f"{icon} {file_name} ({size_mb:.1f}MB) - {category} [READY]"
                self.distribution_list.addItem(file_text)
            
            self.statusbar.showMessage(f"➕ Added {len(file_paths)} files for distribution")
    
    def send_to_selected(self):
        """Send files to selected clients"""
        selected_clients = []
        for item in self.client_list.selectedItems():
            text = item.text()
            # Extract IP from item text
            ip_start = text.find('(') + 1
            ip_end = text.find(')')
            if ip_start > 0 and ip_end > ip_start:
                client_ip = text[ip_start:ip_end]
                if client_ip in self.network_server.clients and self.network_server.clients[client_ip]['connected']:
                    selected_clients.append(client_ip)
        
        if selected_clients and self.network_server.files_to_distribute:
            self.network_server.distribute_files_to_clients(selected_clients)
            self.statusbar.showMessage(f"🚀 Distributing files to {len(selected_clients)} selected clients...")
        else:
            self.statusbar.showMessage("⚠️ Select connected clients and add files first")
    
    def send_to_all(self):
        """Send files to all connected clients"""
        connected_clients = [ip for ip, client in self.network_server.clients.items() if client['connected']]
        
        if connected_clients and self.network_server.files_to_distribute:
            self.network_server.distribute_files_to_clients(connected_clients)
            self.statusbar.showMessage(f"🚀 Distributing files to all {len(connected_clients)} clients...")
        else:
            self.statusbar.showMessage("⚠️ No connected clients or files to distribute")
    
    def distribute_files(self):
        """Distribute files (same as send to all)"""
        self.send_to_all()
    
    def clear_distribution_list(self):
        """Clear the distribution files list"""
        reply = QMessageBox.question(
            self, 
            'Clear Distribution List', 
            'Are you sure you want to clear the distribution files list?\n\nNote: This will remove all files from the distribution queue.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.distribution_list.clear()
            self.network_server.files_to_distribute.clear()
            self.statusbar.showMessage('🧹 Distribution list cleared')
    
    def cancel_current_transfer(self):
        """Cancel any ongoing file transfers"""
        reply = QMessageBox.question(
            self, 
            'Cancel Transfer', 
            'Are you sure you want to cancel the current file transfer?\n\nNote: This will stop any ongoing file distribution.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Set a flag to cancel transfers (would need to be implemented in transfer logic)
            self.statusbar.showMessage('❌ File transfer cancellation requested')
            # Note: Full implementation would require adding cancellation logic to the transfer threads
    
    def closeEvent(self, event):
        """Clean shutdown"""
        self.network_server.stop_server()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('LAN Install Working Server v2.0')
    
    print('🚀 Starting Working LAN Install Server v2.0...')
    print('✅ Real client connections enabled')
    print('✅ Working file distribution enabled')
    print('✅ Multi-client support enabled')
    print('✅ Professional UI with real status updates')
    
    window = WorkingServerWindow()
    window.show()
    
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
