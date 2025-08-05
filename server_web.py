
import os
import json
import threading
import time
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import socket
from pathlib import Path

from network.discovery import NetworkDiscovery, get_local_ip
from network.protocol import NetworkProtocol, MessageType
from network.transfer import FileTransfer

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1GB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class WebServerController:
    def __init__(self):
        self.protocol = NetworkProtocol()
        self.discovery = NetworkDiscovery()
        self.file_transfer = FileTransfer()
        self.connected_clients = {}
        self.discovered_devices = []
        self.transfer_status = {}
        self.running = False
        self.server_stats = {
            'start_time': time.time(),
            'total_transfers': 0,
            'total_bytes_sent': 0,
            'active_transfers': 0
        }

    def start_server(self):
        """Start the file transfer server with enhanced logging"""
        try:
            local_ip = get_local_ip()
            print(f"🚀 Starting server on {local_ip}:5000...")
            
            success = self.protocol.start_server()
            if success:
                self.running = True
                
                # Register message handlers
                self.protocol.register_message_handler(MessageType.HANDSHAKE, self.handle_handshake)
                self.protocol.register_message_handler(MessageType.DISCOVERY, self.handle_discovery)
                self.protocol.register_message_handler(MessageType.ACKNOWLEDGMENT, self.handle_acknowledgment)
                
                # Start discovery
                self.discovery.start_discovery(self.on_device_discovered)
                
                print(f"✅ Protocol server started on {local_ip}:5000")
                print(f"🔍 Network discovery started")
                print(f"📊 Server ready to accept connections")
                return True
            else:
                print("❌ Failed to start protocol server on port 5000")
                return False
        except Exception as e:
            print(f"❌ Server start error: {str(e)}")
            return False

    def handle_handshake(self, data, client_ip):
        """Handle client handshake with enhanced client info"""
        client_id = data.get("client_id", client_ip)
        hostname = data.get("hostname", socket.gethostname())
        
        self.connected_clients[client_ip] = {
            "id": client_id,
            "hostname": hostname,
            "connected_time": time.time(),
            "last_seen": time.time(),
            "transfers_received": 0,
            "bytes_received": 0
        }
        print(f"✅ Client connected: {client_ip} ({hostname})")

    def handle_discovery(self, data, client_ip):
        """Handle discovery request with server info"""
        local_ip = get_local_ip()
        response_data = {
            "server_name": f"LAN-Server-{local_ip.split('.')[-1]}",
            "server_ip": local_ip,
            "server_port": 5000,
            "server_version": "2.0",
            "max_file_size": app.config['MAX_CONTENT_LENGTH'],
            "connected_clients": len(self.connected_clients)
        }
        self.protocol.send_to_client(client_ip, MessageType.DISCOVERY_RESPONSE, response_data)

    def handle_acknowledgment(self, data, client_ip):
        """Handle transfer acknowledgments"""
        transfer_id = data.get("transfer_id")
        status = data.get("status")
        
        if transfer_id in self.transfer_status:
            if status == "received":
                print(f"✅ Chunk acknowledged by {client_ip} for transfer {transfer_id}")

    def on_device_discovered(self, device):
        """Handle discovered device"""
        # Update device list without duplicates
        existing_device = next((d for d in self.discovered_devices if d.ip == device.ip), None)
        if existing_device:
            existing_device.last_seen = device.last_seen
        else:
            self.discovered_devices.append(device)
            print(f"🔍 Device discovered: {device.ip} ({device.hostname})")

    def send_file_to_clients(self, file_path, target_clients=None):
        """Send file to specified clients with enhanced tracking"""
        if target_clients is None:
            target_clients = list(self.connected_clients.keys())
        
        if not target_clients:
            print("⚠️ No clients available for file transfer")
            return {}
        
        results = {}
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        
        for client_ip in target_clients:
            if client_ip in self.connected_clients:
                transfer_id = f"transfer_{int(time.time())}_{client_ip}_{file_name}"
                
                # Initialize transfer status
                self.transfer_status[transfer_id] = {
                    "status": "initiating",
                    "progress": 0,
                    "client_ip": client_ip,
                    "file_name": file_name,
                    "file_size": file_size,
                    "start_time": time.time(),
                    "bytes_sent": 0,
                    "speed": 0
                }
                
                # Register transfer callback
                def progress_callback(status, progress, ip=client_ip, tid=transfer_id, size=file_size):
                    if tid in self.transfer_status:
                        self.transfer_status[tid]["status"] = status
                        self.transfer_status[tid]["progress"] = progress
                        self.transfer_status[tid]["bytes_sent"] = int((progress / 100) * size)
                        
                        # Calculate transfer speed
                        elapsed_time = time.time() - self.transfer_status[tid]["start_time"]
                        if elapsed_time > 0:
                            speed = self.transfer_status[tid]["bytes_sent"] / elapsed_time
                            self.transfer_status[tid]["speed"] = speed
                        
                        if status == "completed":
                            self.server_stats["total_transfers"] += 1
                            self.server_stats["total_bytes_sent"] += size
                            self.connected_clients[ip]["transfers_received"] += 1
                            self.connected_clients[ip]["bytes_received"] += size
                            print(f"✅ Transfer completed to {ip}: {file_name}")
                        elif status == "failed":
                            print(f"❌ Transfer failed to {ip}: {file_name}")
                
                self.file_transfer.register_transfer_callback(transfer_id, progress_callback)
                
                # Start transfer
                success = self.file_transfer.start_file_transfer(
                    file_path, client_ip, self.protocol, transfer_id
                )
                results[client_ip] = success
                
                if success:
                    self.server_stats["active_transfers"] += 1
                    print(f"🚀 Started file transfer to {client_ip}: {file_name} ({file_size} bytes)")
                else:
                    print(f"❌ Failed to start transfer to {client_ip}")
                    if transfer_id in self.transfer_status:
                        del self.transfer_status[transfer_id]
        
        return results

    def get_server_stats(self):
        """Get comprehensive server statistics"""
        uptime = time.time() - self.server_stats['start_time']
        return {
            **self.server_stats,
            'uptime': uptime,
            'uptime_formatted': self.format_uptime(uptime),
            'avg_transfer_size': (self.server_stats['total_bytes_sent'] / self.server_stats['total_transfers']) 
                               if self.server_stats['total_transfers'] > 0 else 0
        }

    def format_uptime(self, seconds):
        """Format uptime in human readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Global server controller
server_controller = WebServerController()

@app.route('/')
def index():
    """Main server dashboard"""
    return render_template('server.html')

@app.route('/api/status')
def get_status():
    """Get comprehensive server status"""
    stats = server_controller.get_server_stats()
    return jsonify({
        'running': server_controller.running,
        'local_ip': get_local_ip(),
        'connected_clients': len(server_controller.connected_clients),
        'clients': list(server_controller.connected_clients.keys()),
        'discovered_devices': len(server_controller.discovered_devices),
        'active_transfers': len([t for t in server_controller.transfer_status.values() 
                               if t['status'] in ['initiating', 'transferring']]),
        'stats': stats
    })

@app.route('/api/clients')
def get_clients():
    """Get detailed connected clients info"""
    clients = []
    for ip, info in server_controller.connected_clients.items():
        clients.append({
            'ip': ip,
            'hostname': info.get('hostname', 'Unknown'),
            'connected_time': info['connected_time'],
            'connected_duration': time.time() - info['connected_time'],
            'transfers_received': info.get('transfers_received', 0),
            'bytes_received': info.get('bytes_received', 0),
            'last_seen': info.get('last_seen', info['connected_time'])
        })
    return jsonify(clients)

@app.route('/api/devices')
def get_devices():
    """Get discovered devices"""
    devices = []
    for device in server_controller.discovered_devices:
        devices.append({
            'ip': device.ip,
            'hostname': device.hostname,
            'is_server': device.is_server,
            'response_time': device.response_time,
            'last_seen': device.last_seen
        })
    return jsonify(devices)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload file for transfer with progress tracking"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Save file with progress tracking
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        print(f"📁 File uploaded: {filename} ({file_size} bytes)")
        
        return jsonify({
            'message': 'File uploaded successfully',
            'filename': filename,
            'path': file_path,
            'size': file_size,
            'type': 'installer' if filename.lower().endswith(('.exe', '.msi')) else 'file'
        })

@app.route('/api/send', methods=['POST'])
def send_file():
    """Send file to clients with enhanced options"""
    data = request.get_json()
    filename = data.get('filename')
    target_clients = data.get('clients', [])
    
    if not filename:
        return jsonify({'error': 'No filename specified'}), 400
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    if not target_clients:
        target_clients = list(server_controller.connected_clients.keys())
    
    if not target_clients:
        return jsonify({'error': 'No clients available'}), 400
    
    results = server_controller.send_file_to_clients(file_path, target_clients)
    successful_transfers = sum(1 for success in results.values() if success)
    
    return jsonify({
        'message': f'File transfer initiated to {successful_transfers}/{len(target_clients)} clients',
        'results': results,
        'target_clients': target_clients,
        'file_size': os.path.getsize(file_path)
    })

@app.route('/api/transfers')
def get_transfers():
    """Get detailed transfer status"""
    transfers = {}
    for transfer_id, status in server_controller.transfer_status.items():
        transfers[transfer_id] = {
            **status,
            'duration': time.time() - status['start_time'],
            'speed_formatted': f"{status.get('speed', 0) / 1024:.1f} KB/s" if status.get('speed') else "0 KB/s"
        }
    return jsonify(transfers)

@app.route('/api/start')
def start_server():
    """Start the file transfer server"""
    if server_controller.start_server():
        return jsonify({'message': 'Server started successfully', 'ip': get_local_ip()})
    else:
        return jsonify({'error': 'Failed to start server'}), 500

@app.route('/api/stats')
def get_server_stats():
    """Get detailed server statistics"""
    return jsonify(server_controller.get_server_stats())

if __name__ == '__main__':
    # Auto-start the file transfer server
    if server_controller.start_server():
        print(f"🌐 Web interface starting on http://0.0.0.0:3030")
        app.run(host='0.0.0.0', port=3030, debug=False, threaded=True)
    else:
        print("❌ Failed to start server, exiting...")
