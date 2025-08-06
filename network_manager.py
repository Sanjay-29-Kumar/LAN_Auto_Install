"""
Network communication layer for LAN Software Automation Installation System
"""

import socket
import json
import threading
import time
import os
from datetime import datetime
import config
from security import security_manager, auth_manager

class NetworkManager:
    """Handles network communication between admin and clients"""
    
    def __init__(self, is_admin=False):
        self.is_admin = is_admin
        self.discovery_socket = None
        self.communication_socket = None
        self.clients = {}  # {client_id: {'ip': ip, 'status': status, 'last_seen': timestamp}}
        self.running = False
        self.callbacks = {}
        
    def start_discovery(self):
        """Start network discovery service"""
        self.running = True
        if self.is_admin:
            threading.Thread(target=self._admin_discovery_listener, daemon=True).start()
        else:
            threading.Thread(target=self._client_discovery_broadcaster, daemon=True).start()
    
    def stop_discovery(self):
        """Stop network discovery service"""
        self.running = False
        if self.discovery_socket:
            self.discovery_socket.close()
        if self.communication_socket:
            self.communication_socket.close()
    
    def _admin_discovery_listener(self):
        """Admin listens for client discovery broadcasts"""
        try:
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.discovery_socket.bind(('', config.DISCOVERY_PORT))
            self.discovery_socket.settimeout(1)  # Add timeout for non-blocking
            
            print(f"Starting discovery listener on port {config.DISCOVERY_PORT}")
            
            while self.running:
                try:
                    data, addr = self.discovery_socket.recvfrom(config.BUFFER_SIZE)
                    message = json.loads(data.decode())
                    
                    if message.get('type') == 'discovery':
                        client_id = message.get('client_id')
                        client_info = {
                            'ip': addr[0],
                            'hostname': message.get('hostname', 'Unknown'),
                            'status': 'online',
                            'last_seen': time.time()
                        }
                        self.clients[client_id] = client_info
                        
                        print(f"Client discovered: {client_id} from {addr[0]}")
                        
                        if 'on_client_discovered' in self.callbacks:
                            self.callbacks['on_client_discovered'](client_id, client_info)
                            
                except socket.timeout:
                    # Timeout is expected, continue listening
                    continue
                except Exception as e:
                    print(f"Discovery error: {e}")
                    continue
                    
        except Exception as e:
            print(f"Failed to start discovery listener: {e}")
    
    def _client_discovery_broadcaster(self):
        """Client broadcasts discovery messages"""
        try:
            self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.discovery_socket.settimeout(1)  # Add timeout
            
            hostname = socket.gethostname()
            client_id = f"{hostname}_{config.LOCAL_IP}"
            
            discovery_message = {
                'type': 'discovery',
                'client_id': client_id,
                'hostname': hostname,
                'timestamp': time.time()
            }
            
            print(f"Starting discovery broadcaster on {config.LOCAL_IP}")
            print(f"Broadcasting to {config.BROADCAST_ADDRESS}:{config.DISCOVERY_PORT}")
            
            while self.running:
                try:
                    message = json.dumps(discovery_message).encode()
                    self.discovery_socket.sendto(message, (config.BROADCAST_ADDRESS, config.DISCOVERY_PORT))
                    print(f"Broadcasted discovery message: {client_id}")
                    time.sleep(config.DISCOVERY_INTERVAL)
                except Exception as e:
                    print(f"Discovery broadcast error: {e}")
                    time.sleep(1)  # Wait before retrying
                    continue
                    
        except Exception as e:
            print(f"Failed to start discovery broadcaster: {e}")
    
    def start_communication_server(self):
        """Start communication server for receiving commands"""
        if not self.is_admin:
            threading.Thread(target=self._communication_server, daemon=True).start()
    
    def _communication_server(self):
        """Client communication server"""
        try:
            self.communication_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.communication_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.communication_socket.bind(('', config.COMMUNICATION_PORT))
            self.communication_socket.listen(5)
            
            while self.running:
                try:
                    client_socket, addr = self.communication_socket.accept()
                    threading.Thread(target=self._handle_admin_command, 
                                  args=(client_socket,), daemon=True).start()
                except Exception as e:
                    print(f"Communication server error: {e}")
                    continue
                    
        except Exception as e:
            print(f"Failed to start communication server: {e}")
    
    def _handle_admin_command(self, client_socket):
        """Handle commands from admin"""
        try:
            data = client_socket.recv(config.BUFFER_SIZE)
            if data:
                encrypted_data = data
                decrypted_data = security_manager.decrypt_data(encrypted_data)
                
                if decrypted_data and isinstance(decrypted_data, dict):
                    command_type = decrypted_data.get('type')
                    
                    if command_type == 'install':
                        self._handle_install_command(decrypted_data, client_socket)
                    elif command_type == 'ping':
                        self._handle_ping_command(client_socket)
                        
        except Exception as e:
            print(f"Command handling error: {e}")
        finally:
            client_socket.close()
    
    def _handle_install_command(self, command_data, client_socket):
        """Handle software installation command with improved file transfer"""
        try:
            filename = command_data.get('filename')
            file_size = command_data.get('file_size')
            file_hash = command_data.get('file_hash')
            
            print(f"Receiving file: {filename} ({file_size} bytes)")
            
            # Send ready signal
            ready_response = {
                'type': 'ready_for_file',
                'timestamp': time.time()
            }
            encrypted_ready = security_manager.encrypt_data(ready_response)
            client_socket.send(encrypted_ready)
            
            # Receive file in chunks
            temp_file = os.path.join(config.TEMP_DIR, f"temp_{filename}")
            received_size = 0
            chunk_number = 0
            
            with open(temp_file, 'wb') as f:
                while received_size < file_size:
                    # Receive chunk header
                    header_data = client_socket.recv(config.BUFFER_SIZE)
                    header = security_manager.decrypt_data(header_data)
                    
                    if header is None or header.get('type') != 'file_chunk':
                        raise Exception("Invalid chunk header received")
                    
                    chunk_size = header.get('chunk_size')
                    is_last = header.get('is_last', False)
                    
                    # Send chunk ready acknowledgment
                    chunk_ready = {
                        'type': 'chunk_ready',
                        'timestamp': time.time()
                    }
                    encrypted_ready = security_manager.encrypt_data(chunk_ready)
                    client_socket.send(encrypted_ready)
                    
                    # Receive chunk data
                    chunk_data = b''
                    while len(chunk_data) < chunk_size:
                        data = client_socket.recv(min(chunk_size - len(chunk_data), config.BUFFER_SIZE))
                        if not data:
                            raise Exception("Connection lost during file transfer")
                        chunk_data += data
                    
                    print(f"Received chunk {chunk_number + 1}: {len(chunk_data)} bytes")
                    
                    # Decrypt and write chunk (use binary decryption for file data)
                    decrypted_chunk = security_manager.decrypt_binary_data(chunk_data)
                    if decrypted_chunk is None:
                        raise Exception("Failed to decrypt chunk data")
                    f.write(decrypted_chunk)
                    received_size += len(decrypted_chunk)
                    chunk_number += 1
                    
                    # Send chunk received acknowledgment
                    chunk_ack = {
                        'type': 'chunk_received',
                        'chunk_number': chunk_number,
                        'timestamp': time.time()
                    }
                    encrypted_ack = security_manager.encrypt_data(chunk_ack)
                    client_socket.send(encrypted_ack)
                    
                    print(f"Received chunk {chunk_number} ({len(decrypted_chunk)} bytes)")
                    
                    if is_last:
                        break
            
            # Wait for completion signal
            completion_data = client_socket.recv(config.BUFFER_SIZE)
            completion = security_manager.decrypt_data(completion_data)
            
            if completion is None or completion.get('type') != 'file_complete':
                raise Exception("File transfer not completed properly")
            
            print(f"File received successfully: {filename}")
            
            # Verify file integrity
            if file_security.verify_file_integrity(temp_file, file_hash):
                # Decrypt and install
                decrypted_file = file_security.decrypt_file(temp_file)
                
                if decrypted_file:
                    # Trigger installation callback
                    if 'on_install_request' in self.callbacks:
                        success = self.callbacks['on_install_request'](decrypted_file)
                        
                        # Send response to admin
                        response = {
                            'type': 'install_response',
                            'success': success,
                            'timestamp': time.time()
                        }
                        
                        encrypted_response = security_manager.encrypt_data(response)
                        try:
                            client_socket.send(encrypted_response)
                        except:
                            pass  # Socket might be closed
                        
                        # Clean up
                        try:
                            os.remove(temp_file)
                            os.remove(decrypted_file)
                        except:
                            pass
                else:
                    # Send failure response
                    response = {
                        'type': 'install_response',
                        'success': False,
                        'error': 'Failed to decrypt file',
                        'timestamp': time.time()
                    }
                    encrypted_response = security_manager.encrypt_data(response)
                    try:
                        client_socket.send(encrypted_response)
                    except:
                        pass
            else:
                # Send failure response
                response = {
                    'type': 'install_response',
                    'success': False,
                    'error': 'File integrity check failed',
                    'timestamp': time.time()
                }
                encrypted_response = security_manager.encrypt_data(response)
                try:
                    client_socket.send(encrypted_response)
                except:
                    pass
                
        except Exception as e:
            print(f"Install command error: {e}")
            # Send error response
            response = {
                'type': 'install_response',
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
            encrypted_response = security_manager.encrypt_data(response)
            try:
                client_socket.send(encrypted_response)
            except:
                pass
    
    def _handle_ping_command(self, client_socket):
        """Handle ping command"""
        try:
            response = {
                'type': 'pong',
                'timestamp': time.time()
            }
            encrypted_response = security_manager.encrypt_data(response)
            try:
                client_socket.send(encrypted_response)
            except:
                pass  # Socket might be closed
        except Exception as e:
            print(f"Ping response error: {e}")
    
    def send_install_command(self, client_ip, software_file_path):
        """Send installation command to a specific client with improved file transfer"""
        try:
            # Get file information
            file_size = os.path.getsize(software_file_path)
            filename = os.path.basename(software_file_path)
            file_hash = file_security.calculate_file_hash(software_file_path)
            
            print(f"Sending file: {filename} ({file_size} bytes) to {client_ip}")
            
            # Create initial command with file metadata
            command = {
                'type': 'install',
                'filename': filename,
                'file_size': file_size,
                'file_hash': file_hash,
                'timestamp': time.time()
            }
            
            # Connect to client
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(config.TIMEOUT)
            client_socket.connect((client_ip, config.COMMUNICATION_PORT))
            
            # Send initial command
            encrypted_command = security_manager.encrypt_data(command)
            client_socket.send(encrypted_command)
            
            # Wait for client to be ready
            ready_response = client_socket.recv(config.BUFFER_SIZE)
            ready_data = security_manager.decrypt_data(ready_response)
            
            if ready_data is None or ready_data.get('type') != 'ready_for_file':
                client_socket.close()
                return {'success': False, 'error': 'Client not ready for file transfer'}
            
            # Send file in chunks
            chunk_size = 8192  # 8KB chunks
            with open(software_file_path, 'rb') as f:
                chunk_number = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Encrypt chunk (use binary encryption for file data)
                    encrypted_chunk = security_manager.encrypt_data(chunk)
                    
                    # Send chunk header
                    chunk_header = {
                        'type': 'file_chunk',
                        'chunk_number': chunk_number,
                        'chunk_size': len(encrypted_chunk),
                        'is_last': len(chunk) < chunk_size
                    }
                    encrypted_header = security_manager.encrypt_data(chunk_header)
                    client_socket.send(encrypted_header)
                    
                    # Wait for header acknowledgment
                    try:
                        ack = client_socket.recv(config.BUFFER_SIZE)
                        ack_data = security_manager.decrypt_data(ack)
                        
                        if ack_data is None or ack_data.get('type') != 'chunk_ready':
                            client_socket.close()
                            return {'success': False, 'error': 'Client not ready for chunk'}
                    except Exception as e:
                        client_socket.close()
                        return {'success': False, 'error': f'Header ack failed: {e}'}
                    
                    # Send chunk data
                    try:
                        client_socket.send(encrypted_chunk)
                    except Exception as e:
                        client_socket.close()
                        return {'success': False, 'error': f'Failed to send chunk: {e}'}
                    
                    # Wait for chunk acknowledgment
                    try:
                        chunk_ack = client_socket.recv(config.BUFFER_SIZE)
                        chunk_ack_data = security_manager.decrypt_data(chunk_ack)
                        
                        if chunk_ack_data is None or chunk_ack_data.get('type') != 'chunk_received':
                            client_socket.close()
                            return {'success': False, 'error': 'Chunk not acknowledged'}
                    except Exception as e:
                        client_socket.close()
                        return {'success': False, 'error': f'Chunk ack failed: {e}'}
                    
                    chunk_number += 1
                    print(f"Sent chunk {chunk_number} ({len(chunk)} bytes, encrypted: {len(encrypted_chunk)} bytes)")
            
            # Send completion signal
            completion = {
                'type': 'file_complete',
                'total_chunks': chunk_number
            }
            encrypted_completion = security_manager.encrypt_data(completion)
            client_socket.send(encrypted_completion)
            
            # Wait for final response
            response_data = client_socket.recv(config.BUFFER_SIZE)
            response = security_manager.decrypt_data(response_data)
            
            if response is None:
                response = {'success': False, 'error': 'Failed to decrypt response'}
            
            client_socket.close()
            print(f"File transfer completed: {response}")
            return response
            
        except Exception as e:
            print(f"Send install command error: {e}")
            return {'success': False, 'error': str(e)}
    
    def ping_client(self, client_ip):
        """Ping a client to check if it's online"""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5)
            client_socket.connect((client_ip, config.COMMUNICATION_PORT))
            
            ping_command = {
                'type': 'ping',
                'timestamp': time.time()
            }
            
            encrypted_ping = security_manager.encrypt_data(ping_command)
            client_socket.send(encrypted_ping)
            
            response_data = client_socket.recv(config.BUFFER_SIZE)
            response = security_manager.decrypt_data(response_data)
            
            client_socket.close()
            return response.get('type') == 'pong'
            
        except Exception as e:
            print(f"Ping error: {e}")
            return False
    
    def register_callback(self, event, callback):
        """Register callback for network events"""
        self.callbacks[event] = callback
    
    def get_online_clients(self):
        """Get list of online clients"""
        online_clients = {}
        current_time = time.time()
        
        for client_id, client_info in self.clients.items():
            if current_time - client_info['last_seen'] < config.HEARTBEAT_INTERVAL * 2:
                online_clients[client_id] = client_info
        
        return online_clients

# Import file_security here to avoid circular import
from security import file_security 