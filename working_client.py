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


class WorkingNetworkClient(QObject):
    """Working network client with real server connections"""
    server_found = pyqtSignal(dict)
    connection_status = pyqtSignal(str, bool)  # server_ip, connected
    file_received = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.servers = {}
        self.connected_servers = {}
        self.file_receiver_socket = None
        self.local_ip = self._get_local_ip()
        
    def start_discovery(self):
        """Start server discovery and file receiver"""
        self.running = True
        
        # Start file receiver server
        threading.Thread(target=self._start_file_receiver, daemon=True).start()
        
        # Start server discovery
        threading.Thread(target=self._discover_servers, daemon=True).start()
        
        print(f"Client started on {self.local_ip}")
    
    def _start_file_receiver(self):
        """Start file receiver server on port 5002"""
        try:
            self.file_receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.file_receiver_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.file_receiver_socket.bind(('0.0.0.0', 5002))
            self.file_receiver_socket.listen(5)
            
            print("File receiver listening on port 5002")
            
            while self.running:
                try:
                    self.file_receiver_socket.settimeout(1.0)
                    client_sock, addr = self.file_receiver_socket.accept()
                    threading.Thread(target=self._handle_file_transfer, 
                                   args=(client_sock, addr), daemon=True).start()
                except socket.timeout:
                    continue
                except:
                    break
                    
        except Exception as e:
            print(f"File receiver error: {e}")
    
    def _handle_file_transfer(self, sock, addr):
        """Handle incoming file transfer"""
        try:
            # Receive file metadata
            metadata_line = sock.recv(1024).decode('utf-8').strip()
            metadata = json.loads(metadata_line)
            
            file_name = metadata['file_name']
            file_size = metadata['file_size']
            file_category = metadata.get('category', 'other')
            
            print(f"Receiving file: {file_name} ({file_size} bytes)")
            
            # Create storage directory
            base_dir = Path("received_files")
            if file_category == 'installer':
                storage_dir = base_dir / "installers"
            elif file_category == 'document':
                storage_dir = base_dir / "files" / "documents"
            elif file_category == 'media':
                storage_dir = base_dir / "files" / "media"
            elif file_category == 'archive':
                storage_dir = base_dir / "files" / "archives"
            else:
                storage_dir = base_dir / "files" / "others"
            
            storage_dir.mkdir(parents=True, exist_ok=True)
            file_path = storage_dir / file_name
            
            # Receive file data
            bytes_received = 0
            with open(file_path, 'wb') as f:
                while bytes_received < file_size:
                    chunk = sock.recv(min(2048576, file_size - bytes_received))  # 2MB chunks
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_received += len(chunk)
            
            sock.close()
            
            # Emit file received signal
            file_info = {
                'name': file_name,
                'path': str(file_path),
                'size': file_size,
                'category': file_category,
                'sender': addr[0],
                'received_time': time.time()
            }
            
            self.file_received.emit(file_info)
            
            # Auto-install if installer
            if file_category == 'installer':
                self._silent_install(str(file_path))
            
            print(f"File received successfully: {file_name}")
            
        except Exception as e:
            print(f"File transfer error: {e}")
            try:
                sock.close()
            except:
                pass
    
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
                    'client_port': 5002,
                    'timestamp': time.time()
                }).encode('utf-8')
                
                base_ip = '.'.join(self.local_ip.split('.')[:-1])
                sock.sendto(message, (f"{base_ip}.255", 5001))
                
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
                                'port': response.get('port', 5000),
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
                'client_port': 5002,
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
        try:
            while self.running and server_ip in self.connected_servers:
                # Send heartbeat
                heartbeat = json.dumps({
                    'type': 'heartbeat',
                    'client_ip': self.local_ip,
                    'timestamp': time.time()
                }).encode('utf-8')
                
                try:
                    sock.send(heartbeat + b'\n')
                    time.sleep(10)  # Heartbeat every 10 seconds
                except:
                    break
                    
        except Exception as e:
            print(f"Connection to {server_ip} lost: {e}")
        finally:
            if server_ip in self.connected_servers:
                del self.connected_servers[server_ip]
            self.connection_status.emit(server_ip, False)
            try:
                sock.close()
            except:
                pass
    
    def _silent_install(self, installer_path):
        """Execute silent installation"""
        try:
            ext = Path(installer_path).suffix.lower()
            
            if ext == '.exe':
                for flag in ['/S', '/SILENT', '/VERYSILENT', '/quiet', '/q']:
                    try:
                        subprocess.Popen([installer_path, flag], 
                                       creationflags=subprocess.CREATE_NO_WINDOW)
                        print(f"Silent install started: {installer_path} {flag}")
                        break
                    except:
                        continue
            elif ext == '.msi':
                subprocess.Popen(['msiexec', '/i', installer_path, '/quiet', '/norestart'],
                               creationflags=subprocess.CREATE_NO_WINDOW)
                print(f"MSI silent install started: {installer_path}")
                
        except Exception as e:
            print(f"Silent install error: {e}")
    
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


class WorkingClientWindow(QMainWindow):
    """Working client window with real connections"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('🚀 LAN Install Working Client v2.0')
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
        
        # Initialize network client
        self.network_client = WorkingNetworkClient()
        
        # Connect signals
        self.network_client.server_found.connect(self.add_server)
        self.network_client.connection_status.connect(self.update_connection_status)
        self.network_client.file_received.connect(self.add_received_file)
        
        self.init_ui()
        
        # Start network client
        self.network_client.start_discovery()
    
    def init_ui(self):
        """Initialize UI"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        
        # Header
        header = QLabel('🚀 LAN Install Working Client v2.0')
        header.setAlignment(Qt.AlignCenter)
        header.setFont(QFont('Segoe UI', 18, QFont.Bold))
        header.setStyleSheet('color: #4a90e2; margin: 20px;')
        layout.addWidget(header)
        
        # Status
        self.status_label = QLabel('🔄 Starting client - Scanning for servers...')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('color: #FFA500; font-size: 14pt; font-weight: bold;')
        layout.addWidget(self.status_label)
        
        # Main content
        content_layout = QHBoxLayout()
        
        # Left panel - Servers
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        
        servers_title = QLabel('🖥️ Available Servers (Live)')
        servers_title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        servers_title.setStyleSheet('color: #4a90e2; margin: 10px;')
        left_layout.addWidget(servers_title)
        
        self.server_list = QListWidget()
        left_layout.addWidget(self.server_list)
        
        server_buttons = QHBoxLayout()
        self.refresh_btn = QPushButton('🔄 Refresh')
        self.connect_btn = QPushButton('🔗 Connect')
        self.refresh_btn.clicked.connect(self.refresh_servers)
        self.connect_btn.clicked.connect(self.connect_to_server)
        server_buttons.addWidget(self.refresh_btn)
        server_buttons.addWidget(self.connect_btn)
        left_layout.addLayout(server_buttons)
        
        left_panel.setLayout(left_layout)
        content_layout.addWidget(left_panel)
        
        # Right panel - Files
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        files_title = QLabel('📁 Received Files (Live)')
        files_title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        files_title.setStyleSheet('color: #4a90e2; margin: 10px;')
        right_layout.addWidget(files_title)
        
        self.file_list = QListWidget()
        right_layout.addWidget(self.file_list)
        
        file_buttons = QHBoxLayout()
        self.open_folder_btn = QPushButton('📂 Open Folder')
        self.install_btn = QPushButton('⚡ Install Selected')
        self.open_folder_btn.clicked.connect(self.open_received_folder)
        file_buttons.addWidget(self.open_folder_btn)
        file_buttons.addWidget(self.install_btn)
        right_layout.addLayout(file_buttons)
        
        right_panel.setLayout(right_layout)
        content_layout.addWidget(right_panel)
        
        layout.addLayout(content_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('Starting client...')
        layout.addWidget(self.progress_bar)
        
        central.setLayout(layout)
        
        # Status bar
        self.statusbar = QStatusBar()
        self.statusbar.showMessage(f'🔄 Client starting on {self.network_client.local_ip}')
        self.setStatusBar(self.statusbar)
    
    @pyqtSlot(dict)
    def add_server(self, server):
        """Add discovered server"""
        server_text = f"🖥️ {server['hostname']} ({server['ip']}) - LAN Install Server [FOUND]"
        self.server_list.addItem(server_text)
        self.statusbar.showMessage(f"✅ Found server: {server['hostname']} at {server['ip']}")
    
    @pyqtSlot(str, bool)
    def update_connection_status(self, server_ip, connected):
        """Update connection status"""
        # Update server list items
        for i in range(self.server_list.count()):
            item = self.server_list.item(i)
            if server_ip in item.text():
                text = item.text()
                if connected:
                    new_text = text.replace('[FOUND]', '[CONNECTED]').replace('[DISCONNECTED]', '[CONNECTED]')
                    item.setText(new_text)
                    item.setBackground(QColor(76, 175, 80, 50))  # Green background
                else:
                    new_text = text.replace('[CONNECTED]', '[DISCONNECTED]').replace('[FOUND]', '[DISCONNECTED]')
                    item.setText(new_text)
                    item.setBackground(QColor(244, 67, 54, 50))  # Red background
                break
        
        if connected:
            self.status_label.setText('✅ Connected to server - Ready to receive files')
            self.status_label.setStyleSheet('color: #4CAF50; font-size: 14pt; font-weight: bold;')
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat('Connected and ready')
            self.statusbar.showMessage(f'✅ Connected to server: {server_ip}')
        else:
            self.statusbar.showMessage(f'⚠️ Disconnected from server: {server_ip}')
    
    @pyqtSlot(dict)
    def add_received_file(self, file_info):
        """Add received file"""
        category_icons = {
            'installer': '📦',
            'document': '📄', 
            'media': '🎵',
            'archive': '📁',
            'other': '📄'
        }
        
        icon = category_icons.get(file_info['category'], '📄')
        size_mb = file_info['size'] / (1024 * 1024)
        
        file_text = f"{icon} {file_info['name']} ({size_mb:.1f}MB) - {file_info['category']} ✅"
        self.file_list.addItem(file_text)
        
        self.statusbar.showMessage(f"📥 Received: {file_info['name']} from {file_info['sender']}")
        
        if file_info['category'] == 'installer':
            self.statusbar.showMessage(f"🤖 Auto-installing: {file_info['name']}")
    
    def refresh_servers(self):
        """Refresh server list"""
        self.server_list.clear()
        self.network_client.servers.clear()
        self.statusbar.showMessage('🔄 Refreshing server list...')
    
    def connect_to_server(self):
        """Connect to selected server"""
        current_item = self.server_list.currentItem()
        if current_item:
            text = current_item.text()
            # Extract IP from text
            ip_start = text.find('(') + 1
            ip_end = text.find(')')
            if ip_start > 0 and ip_end > ip_start:
                server_ip = text[ip_start:ip_end]
                if server_ip in self.network_client.servers:
                    server_info = self.network_client.servers[server_ip]
                    self.network_client._connect_to_server(server_ip, server_info['port'])
    
    def open_received_folder(self):
        """Open received files folder"""
        try:
            folder_path = Path("received_files")
            if folder_path.exists():
                os.startfile(str(folder_path))
            else:
                folder_path.mkdir(parents=True, exist_ok=True)
                os.startfile(str(folder_path))
        except:
            try:
                subprocess.run(['explorer', str(Path("received_files"))])
            except:
                pass
    
    def closeEvent(self, event):
        """Clean shutdown"""
        self.network_client.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('LAN Install Working Client v2.0')
    
    print('🚀 Starting Working LAN Install Client v2.0...')
    print('✅ Real server connections enabled')
    print('✅ Working file reception enabled')
    print('✅ Silent auto-installation enabled')
    print('✅ Professional UI with real status updates')
    
    window = WorkingClientWindow()
    window.show()
    
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
