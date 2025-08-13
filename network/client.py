import socket
import threading
import json
import os
import time
import platform
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from collections import defaultdict

# Define chunk size for file transfers
CHUNK_SIZE = 4096
RECEIVED_FILES_DIR = "received_files"

class NetworkClient(QObject):
    server_found = pyqtSignal(dict) # Emits server info {ip, hostname, os_type, is_windows}
    connection_status = pyqtSignal(str, bool) # Emits (server_ip, connected_status)
    file_received = pyqtSignal(dict) # Emits {name, size, sender, path}
    file_progress = pyqtSignal(str, str, int) # Emits (file_name, server_ip, percentage)
    status_update = pyqtSignal(str, str) # Emits (message, color)

    def __init__(self, host='0.0.0.0', port=0): # Client binds to 0.0.0.0 and an ephemeral port
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket = None
        self.connected_servers = {} # {ip: {socket: ..., thread: ..., info: ...}}
        self.servers = {} # Discovered servers {ip: info}
        self.running = False
        self.discovery_client_running = False
        self.discovery_socket = None
        self.discovery_thread = None
        self.received_files_path = os.path.join(os.getcwd(), RECEIVED_FILES_DIR)
        os.makedirs(self.received_files_path, exist_ok=True)

    def start_client(self):
        if self.running:
            return

        self.running = True
        self.start_discovery_client()
        print("Client started.")

    def stop_client(self):
        if not self.running:
            return

        self.running = False
        self.stop_discovery_client()
        for server_ip in list(self.connected_servers.keys()):
            self._disconnect_from_server(server_ip)
        print("Client stopped.")

    def _connect_to_server(self, server_ip, server_port):
        if server_ip in self.connected_servers:
            print(f"Already connected to {server_ip}")
            return

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5) # Timeout for connection
            client_socket.connect((server_ip, server_port))
            client_socket.settimeout(None) # Remove timeout after connection

            print(f"Connected to server {server_ip}:{server_port}")
            
            # Send client info to server
            client_info = {
                "type": "CLIENT_INFO",
                "ip": client_socket.getsockname()[0],
                "hostname": socket.gethostname(),
                "os_type": platform.system(),
                "is_windows": platform.system() == "Windows"
            }
            client_socket.sendall(json.dumps(client_info).encode('utf-8') + b'\n')

            server_thread = threading.Thread(target=self._handle_server, args=(client_socket, server_ip))
            server_thread.daemon = True
            server_thread.start()

            self.connected_servers[server_ip] = {
                "socket": client_socket,
                "thread": server_thread,
                "info": self.servers.get(server_ip, {"ip": server_ip, "port": server_port, "hostname": "Unknown"})
            }
            self.connection_status.emit(server_ip, True)
            self.status_update.emit(f"Connected to {server_ip}", "green")

        except socket.timeout:
            print(f"Connection to {server_ip} timed out.")
            self.status_update.emit(f"Connection to {server_ip} timed out", "red")
        except ConnectionRefusedError:
            print(f"Connection to {server_ip} refused. Server might not be running or port is wrong.")
            self.status_update.emit(f"Connection to {server_ip} refused", "red")
        except Exception as e:
            print(f"Error connecting to server {server_ip}: {e}")
            self.status_update.emit(f"Error connecting to {server_ip}: {e}", "red")

    def _handle_server(self, server_socket, server_ip):
        buffer = b""
        current_file_transfer = {} # To store state for ongoing file reception

        while self.running:
            try:
                data = server_socket.recv(CHUNK_SIZE)
                if not data:
                    break

                buffer += data

                # Process JSON messages first
                while b'\n' in buffer:
                    line, remaining_buffer = buffer.split(b'\n', 1)
                    try:
                        message = json.loads(line.decode('utf-8'))
                        self._process_server_message(server_ip, message, current_file_transfer)
                        buffer = remaining_buffer # Update buffer after processing JSON
                    except json.JSONDecodeError:
                        # If it's not a complete JSON message, it might be file data
                        # This is a simplified approach; a robust protocol would distinguish
                        # between metadata and file data more explicitly (e.g., length prefixes)
                        if current_file_transfer.get("receiving_file"):
                            self._receive_file_chunk(server_ip, line + remaining_buffer, current_file_transfer)
                            buffer = b"" # All data treated as file chunk
                        else:
                            print(f"Non-JSON data or incomplete JSON from {server_ip}: {line.decode('utf-8', errors='ignore')}")
                            buffer = remaining_buffer # Keep processing if it was just incomplete JSON
                        break # Exit inner loop to process remaining buffer as file data or next message
                
                # If buffer still contains data after JSON processing, and we are receiving a file,
                # treat the rest as file data.
                if buffer and current_file_transfer.get("receiving_file"):
                    self._receive_file_chunk(server_ip, buffer, current_file_transfer)
                    buffer = b"" # Clear buffer after processing as file chunk

            except ConnectionResetError:
                print(f"Server {server_ip} disconnected unexpectedly.")
                break
            except Exception as e:
                if self.running:
                    print(f"Error handling server {server_ip}: {e}")
                break
        self._disconnect_from_server(server_ip)

    def _process_server_message(self, server_ip, message, current_file_transfer):
        msg_type = message.get("type")
        if msg_type == "SERVER_INFO":
            # This is typically received right after connection
            self.servers[server_ip] = message
            self.server_found.emit(message) # Re-emit to update UI with full info
        elif msg_type == "FILE_METADATA":
            file_name = message.get("file_name")
            file_size = message.get("file_size")
            
            current_file_transfer.clear() # Clear any previous transfer state
            current_file_transfer["receiving_file"] = True
            current_file_transfer["file_name"] = file_name
            current_file_transfer["file_size"] = file_size
            current_file_transfer["received_bytes"] = 0
            current_file_transfer["file_path"] = os.path.join(self.received_files_path, file_name)
            current_file_transfer["file_handle"] = open(current_file_transfer["file_path"], 'wb')
            
            print(f"Receiving file metadata: {file_name} ({file_size} bytes) from {server_ip}")
            self.file_received.emit({
                "name": file_name, 
                "size": file_size, 
                "sender": server_ip, 
                "path": current_file_transfer["file_path"]
            })
            self.status_update.emit(f"Receiving {file_name} from {server_ip}", "orange")
        else:
            print(f"Unknown message type from {server_ip}: {message}")

    def _receive_file_chunk(self, server_ip, chunk_data, current_file_transfer):
        if not current_file_transfer.get("receiving_file"):
            print(f"Received unexpected file chunk from {server_ip} without metadata.")
            return

        file_handle = current_file_transfer["file_handle"]
        file_name = current_file_transfer["file_name"]
        file_size = current_file_transfer["file_size"]

        file_handle.write(chunk_data)
        current_file_transfer["received_bytes"] += len(chunk_data)

        percentage = int((current_file_transfer["received_bytes"] / file_size) * 100)
        self.file_progress.emit(file_name, server_ip, percentage)

        if current_file_transfer["received_bytes"] >= file_size:
            file_handle.close()
            print(f"Finished receiving {file_name} from {server_ip}")
            self.status_update.emit(f"Received {file_name} from {server_ip}", "lightgreen")
            self._send_file_ack(server_ip, file_name, "Acknowledged")
            current_file_transfer.clear() # Reset for next file

    def _send_file_ack(self, server_ip, file_name, status):
        if server_ip in self.connected_servers:
            ack_message = {
                "type": "FILE_ACK",
                "file_name": file_name,
                "status": status
            }
            try:
                self.connected_servers[server_ip]["socket"].sendall(json.dumps(ack_message).encode('utf-8') + b'\n')
                print(f"Sent ACK for {file_name} to {server_ip} with status: {status}")
            except Exception as e:
                print(f"Error sending ACK to {server_ip}: {e}")

    def _disconnect_from_server(self, server_ip):
        if server_ip in self.connected_servers:
            server_socket = self.connected_servers[server_ip]["socket"]
            try:
                server_socket.shutdown(socket.SHUT_RDWR)
                server_socket.close()
            except OSError as e:
                print(f"Error closing socket for {server_ip}: {e}")
            del self.connected_servers[server_ip]
            self.connection_status.emit(server_ip, False)
            self.status_update.emit(f"Disconnected from {server_ip}", "red")
            print(f"Disconnected from server {server_ip}.")

    # Discovery Client for finding servers
    def start_discovery_client(self):
        if self.discovery_client_running:
            return

        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.settimeout(1) # Timeout for recvfrom

        discovery_port = 5000 # Must match server's discovery port
        try:
            self.discovery_socket.bind(('', self.port)) # Bind to ephemeral port for sending
            self.discovery_client_running = True
            self.discovery_thread = threading.Thread(target=self._discovery_loop, args=(discovery_port,))
            self.discovery_thread.daemon = True
            self.discovery_thread.start()
            print(f"Discovery client started, listening on port {self.port}")
        except Exception as e:
            print(f"Error starting discovery client: {e}")
            self.discovery_client_running = False

    def stop_discovery_client(self):
        if not self.discovery_client_running:
            return
        self.discovery_client_running = False
        if self.discovery_socket:
            self.discovery_socket.close()
            self.discovery_socket = None
        if self.discovery_thread:
            self.discovery_thread.join()
        print("Discovery client stopped.")

    def _discovery_loop(self, discovery_port):
        while self.discovery_client_running:
            try:
                # Send discovery broadcast
                self.discovery_socket.sendto("DISCOVER_SERVER".encode('utf-8'), ('<broadcast>', discovery_port))
                
                # Listen for server advertisements
                data, addr = self.discovery_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                if message.get("type") == "SERVER_ADVERTISEMENT":
                    server_ip = message.get("ip")
                    if server_ip not in self.servers:
                        self.servers[server_ip] = message
                        self.server_found.emit(message)
                        print(f"Discovered server: {server_ip}")
            except socket.timeout:
                # No server found in this cycle, continue
                pass
            except json.JSONDecodeError:
                print(f"Received non-JSON discovery message from {addr}")
            except Exception as e:
                if self.discovery_client_running:
                    print(f"Error in client discovery loop: {e}")
            time.sleep(5) # Broadcast every 5 seconds
