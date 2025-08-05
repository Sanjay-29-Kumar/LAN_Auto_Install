
import os
import json
import threading
import time
import subprocess
import socket
from flask import Flask, render_template, request, jsonify
from pathlib import Path

from network.discovery import NetworkDiscovery, get_local_ip
from network.protocol import ClientProtocol, MessageType
from network.transfer import FileReceiver

app = Flask(__name__)

class WebClientController:
    def __init__(self):
        self.discovery = NetworkDiscovery()
        self.protocol = None
        self.file_receiver = FileReceiver()
        self.connected_server = None
        self.discovered_servers = []
        self.received_files = []
        self.running = False
        self.last_discovery = 0
        self.transfer_progress = {}

    def discover_servers(self):
        """Discover available servers with improved speed and reliability"""
        try:
            print("🔍 Starting fast server discovery...")
            local_ip = get_local_ip()
            print(f"📍 Local IP: {local_ip}")
            
            # Get network range
            base_ip = '.'.join(local_ip.split('.')[:-1])
            network_range = [f"{base_ip}.{i}" for i in range(1, 255)]
            
            servers = []
            scan_start = time.time()
            
            # Use concurrent scanning for speed
            import concurrent.futures
            
            def check_server(ip):
                # Allow same-machine discovery for testing
                # if ip == local_ip:
                #     return None
                    
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.2)  # Very fast timeout
                    result = sock.connect_ex((ip, 5000))
                    
                    if result == 0:
                        try:
                            # Send discovery message
                            discovery_msg = {
                                "type": "discovery",
                                "data": {"client_ip": local_ip},
                                "timestamp": time.time()
                            }
                            
                            msg_bytes = json.dumps(discovery_msg).encode('utf-8')
                            msg_length = len(msg_bytes).to_bytes(4, 'big')
                            sock.send(msg_length + msg_bytes)
                            
                            # Wait for response
                            sock.settimeout(0.3)
                            resp_length_bytes = sock.recv(4)
                            if len(resp_length_bytes) == 4:
                                resp_length = int.from_bytes(resp_length_bytes, 'big')
                                if resp_length < 1024:
                                    resp_data = sock.recv(resp_length)
                                    response = json.loads(resp_data.decode('utf-8'))
                                    
                                    if response.get('type') == 'discovery_response':
                                        server_info = {
                                            'ip': ip,
                                            'hostname': response.get('data', {}).get('server_name', f'LAN-Server-{ip.split(".")[-1]}'),
                                            'port': 5000,
                                            'response_time': time.time() - scan_start
                                        }
                                        sock.close()
                                        return server_info
                        except:
                            pass
                    
                    sock.close()
                except:
                    pass
                return None
            
            # Concurrent scanning with high thread count for speed
            with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
                future_to_ip = {executor.submit(check_server, ip): ip for ip in network_range}
                
                for future in concurrent.futures.as_completed(future_to_ip, timeout=3):
                    try:
                        server_info = future.result()
                        if server_info:
                            servers.append(server_info)
                            print(f"✓ Found server: {server_info['ip']} ({server_info['hostname']}) - {server_info['response_time']:.3f}s")
                    except:
                        pass
            
            scan_time = time.time() - scan_start
            self.discovered_servers = servers
            self.last_discovery = time.time()
            
            print(f"🔍 Discovery complete in {scan_time:.2f}s. Found {len(servers)} servers")
            return servers
            
        except Exception as e:
            print(f"Discovery error: {str(e)}")
            return []

    def connect_to_server(self, server_ip, server_port=5000):
        """Connect to a server with improved error handling"""
        try:
            print(f"🔗 Connecting to server {server_ip}:{server_port}...")
            
            self.protocol = ClientProtocol(server_ip, server_port)
            
            # Register message handlers
            self.protocol.register_message_handler(MessageType.FILE_TRANSFER, self.handle_file_transfer)
            self.protocol.register_message_handler(MessageType.DISCOVERY_RESPONSE, self.handle_discovery_response)
            
            # Register file receive handlers
            self.file_receiver.register_receive_callback("default", self.on_file_progress)
            
            success = self.protocol.connect()
            if success:
                self.connected_server = {'ip': server_ip, 'port': server_port}
                print(f"✅ Connected to server: {server_ip}")
                return True
            else:
                print("❌ Failed to connect to server")
                return False
                
        except Exception as e:
            print(f"Connection error: {str(e)}")
            return False

    def disconnect_from_server(self):
        """Disconnect from current server"""
        if self.protocol:
            self.protocol.disconnect()
            self.protocol = None
        self.connected_server = None
        print("🔌 Disconnected from server")

    def handle_discovery_response(self, data):
        """Handle discovery response from server"""
        pass  # Already handled in discovery

    def handle_file_transfer(self, data):
        """Handle incoming file transfer with progress tracking"""
        try:
            transfer_id = data.get("transfer_id")
            
            if "transfer_id" in data and "chunk_data" not in data:
                # File transfer initiation
                self.file_receiver.handle_file_transfer_init(data, self.protocol)
                file_name = data.get('file_name', 'Unknown')
                file_size = data.get('file_size', 0)
                print(f"📥 Receiving file: {file_name} ({file_size} bytes)")
                
                self.transfer_progress[transfer_id] = {
                    'file_name': file_name,
                    'file_size': file_size,
                    'progress': 0,
                    'status': 'receiving'
                }
                
            elif "chunk_data" in data:
                # File chunk
                self.file_receiver.handle_file_chunk(data, self.protocol)
                
        except Exception as e:
            print(f"File transfer error: {str(e)}")

    def on_file_progress(self, status, progress):
        """Handle file transfer progress with better tracking"""
        print(f"📊 File transfer progress: {status} - {progress:.1f}%")
        
        if status == "completed":
            # Check for received files and handle auto-install
            received_files = self.file_receiver.get_received_files()
            for file_info in received_files:
                if file_info not in self.received_files:  # New file
                    if file_info['type'] == 'installer':
                        self.auto_install_file(file_info['path'])
                    
                    file_entry = {
                        'name': file_info['name'],
                        'path': file_info['path'],
                        'size': file_info['size'],
                        'type': file_info['type'],
                        'received_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'completed'
                    }
                    self.received_files.append(file_entry)
                    print(f"✅ File received: {file_info['name']}")

    def auto_install_file(self, file_path):
        """Auto-install executable files with better error handling"""
        try:
            if file_path.lower().endswith(('.exe', '.msi')):
                print(f"🔧 Auto-installing: {os.path.basename(file_path)}")
                # Run installer silently in background
                if file_path.lower().endswith('.exe'):
                    subprocess.Popen([file_path, '/S'], shell=True, 
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                elif file_path.lower().endswith('.msi'):
                    subprocess.Popen(['msiexec', '/i', file_path, '/quiet'], shell=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                print(f"🚀 Installation started for: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Installation error: {str(e)}")

    def get_status(self):
        """Get comprehensive client status"""
        return {
            'connected': self.connected_server is not None,
            'server': self.connected_server,
            'local_ip': get_local_ip(),
            'received_files': len(self.received_files),
            'discovered_servers': len(self.discovered_servers),
            'last_discovery': self.last_discovery,
            'transfer_progress': self.transfer_progress
        }

# Global client controller
client_controller = WebClientController()

@app.route('/')
def index():
    """Main client dashboard"""
    return render_template('client.html')

@app.route('/api/status')
def get_status():
    """Get client status with more details"""
    return jsonify(client_controller.get_status())

@app.route('/api/discover')
def discover_servers():
    """Discover available servers with faster response"""
    servers = client_controller.discover_servers()
    return jsonify({
        'servers': servers,
        'scan_time': time.time() - client_controller.last_discovery if client_controller.last_discovery else 0,
        'local_ip': get_local_ip()
    })

@app.route('/api/connect', methods=['POST'])
def connect_server():
    """Connect to a server"""
    data = request.get_json()
    server_ip = data.get('ip')
    
    if not server_ip:
        return jsonify({'error': 'No server IP specified'}), 400
    
    success = client_controller.connect_to_server(server_ip)
    
    if success:
        return jsonify({'message': f'Connected to {server_ip}', 'server': {'ip': server_ip, 'port': 5000}})
    else:
        return jsonify({'error': 'Failed to connect to server'}), 500

@app.route('/api/disconnect', methods=['POST'])
def disconnect_server():
    """Disconnect from server"""
    client_controller.disconnect_from_server()
    return jsonify({'message': 'Disconnected from server'})

@app.route('/api/files')
def get_received_files():
    """Get list of received files with more details"""
    return jsonify({
        'files': client_controller.received_files,
        'total_count': len(client_controller.received_files)
    })

@app.route('/api/progress')
def get_transfer_progress():
    """Get current transfer progress"""
    return jsonify(client_controller.transfer_progress)

if __name__ == '__main__':
    print(f"🌐 Client web interface starting on http://0.0.0.0:3001")
    print(f"📍 Local IP: {get_local_ip()}")
    app.run(host='0.0.0.0', port=3001, debug=False, threaded=True)
