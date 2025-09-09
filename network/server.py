from pathlib import Path
from auto_installer import AutoInstaller
import socket
import threading
import json
import os
import time
import platform
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from collections import defaultdict
from utils.virus_scanner import VirusScanner

# Define chunk size for file transfers - increased for better performance
CHUNK_SIZE = 1048576  # 1MB chunks for better throughput
MAX_MEMORY_BUFFER = 104857600  # 100MB max memory buffer
RECEIVED_FILES_DIR = "received_files" # For client, not server

# Constants for connection management
RECONNECT_TIMEOUT = 300  # 5 minutes to allow for reconnection
MAX_RETRIES = 5  # Maximum number of retry attempts
RETRY_DELAY = 2  # Seconds between retries

from . import protocol

class NetworkServer(QObject):
    def _post_receive_actions(self, client_ip, file_name, file_path):
        installer_dir = os.path.dirname(file_path)
        auto_installer = AutoInstaller(installers_dir=installer_dir)
        ext = os.path.splitext(file_path)[1].lower()
        if ext in auto_installer.SILENT_COMMANDS:
            self._send_status_update(client_ip, file_name, "Installing")
            self.status_update_received.emit(file_name, client_ip, "Installing")
            if file_name == "LocalSend.exe":
                cmd = f'"{file_path}" /SILENT /NORESTART'
                ret = auto_installer.run_command(cmd)
            else:
                ret = auto_installer.SILENT_COMMANDS[ext](Path(file_path))
            # If any popup or user interaction occurs, the installer will not return 0.
            # In that case, always move to manual setup and notify as such.
            if ret == 0:
                self._move_to_category(file_path, "installer")
                self._send_status_update(client_ip, file_name, "Installed")
                self.status_update_received.emit(file_name, client_ip, "Installed")
            else:
                self._move_to_manual_setup(file_path, "Manual Setup Required (Popup or User Interaction Detected)")
                self._send_status_update(client_ip, file_name, "Manual Setup Required")
                self.status_update_received.emit(file_name, client_ip, "Manual Setup Required")
                self.status_update.emit(f"{file_name}: manual setup required (popup or user interaction detected)", "orange")
        else:
            # Non-installer: categorize as media or files
            category = self._detect_category(file_path)
            dest = self._move_to_category(file_path, category)
            self._send_status_update(client_ip, file_name, "Received successfully")
            self.status_update.emit(f"{file_name}: saved to {category}", "green")
    client_connected = pyqtSignal(dict) # Emits client info {ip, hostname, os_type, is_windows}
    client_disconnected = pyqtSignal(str) # Emits client IP
    file_progress = pyqtSignal(str, str, int) # Emits (file_name, client_ip, percentage)
    status_update_received = pyqtSignal(str, str, str) # Emits (file_name, client_ip, status_message)
    status_update = pyqtSignal(str, str) # Emits (message, color)
    server_ip_updated = pyqtSignal(str) # Emits the server's IP address
    scan_status_update = pyqtSignal(str, str, str) # Emits (file_name, status, color)

    def __init__(self, host='0.0.0.0', port=protocol.COMMAND_PORT, discovery_port=protocol.DISCOVERY_PORT):
        super().__init__()
        self.port = port
        self.discovery_port = discovery_port
        self.server_socket = None
        self.discovery_socket = None
        self.clients = {} # {ip: {socket: ..., thread: ..., info: ..., files_to_send: []}}
        self.running = False
        self.discovery_server_running = False
        self.discovery_thread = None
        self.file_transfer_states = defaultdict(lambda: defaultdict(dict)) # {client_ip: {file_name: {sent_bytes, total_bytes, chunks_acked}}}
        self.files_to_distribute = [] # List of files selected by the user for distribution
        self.server_ip = None # To store the server's actual IP
        self.host = host
        self.virus_scanner = VirusScanner()
        self.scan_results = {}  # Cache for scan results

    def start_server(self):
        if self.running:
            return

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Enable TCP keepalive
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)  # Increased backlog for better connection handling
            self.running = True
            threading.Thread(target=self._accept_connections, daemon=True).start()
            self.start_discovery_server()
            self.server_ip = self._get_local_ip()
            self.server_ip_updated.emit(self.server_ip)
            print(f"Server listening on {self.host}:{self.port}")
            print(f"Discovery advertising on UDP {self.discovery_port}")
            self.status_update.emit(f"Server started on {self.host}:{self.port}", "green")
        except Exception as e:
            print(f"Error starting server: {e}")
            self.status_update.emit(f"Error starting server: {e}", "red")
            self.running = False

    def stop_server(self):
        """Stop the server and clean up all resources"""
        if not self.running:
            return

        print("Stopping server...")
        self.running = False
        
        # Stop discovery server first
        self.stop_discovery_server()
        
        # Disconnect all clients with proper cleanup
        client_ips = list(self.clients.keys())  # Create a copy since we'll be modifying self.clients
        for client_ip in client_ips:
            try:
                self._disconnect_client(client_ip, is_shutdown=True)
            except Exception as e:
                print(f"Error disconnecting client {client_ip}: {e}")
        
        # Close main server socket
        if self.server_socket:
            try:
                try:
                    self.server_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass  # Socket might already be shutdown
                self.server_socket.close()
            except Exception as e:
                print(f"Error closing server socket: {e}")
        
        # Clear all remaining data
        self.clients.clear()
        self.file_transfer_states.clear()
        
        print("Server stopped")
        try:
            self.status_update.emit("Server stopped", "red")
        except RuntimeError:
            pass  # Qt might already be shut down

    def _accept_connections(self):
        while self.running:
            try:
                self.server_socket.settimeout(1.0)  # Add timeout to prevent blocking
                client_socket, client_address = self.server_socket.accept()
                client_ip = client_address[0]
                print(f"Client connected from {client_ip}")
                
                # Configure client socket with better settings for multiple connections
                client_socket.settimeout(120)  # Longer timeout for file operations
                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Enable TCP keepalive with more aggressive settings
                if hasattr(socket, 'TCP_KEEPIDLE'):  # Linux
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                if hasattr(socket, 'TCP_KEEPINTVL'):
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
                if hasattr(socket, 'TCP_KEEPCNT'):
                    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
                
                # Increase socket buffer sizes for better performance
                try:
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)  # 1MB receive buffer
                    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)  # 1MB send buffer
                except Exception:
                    pass  # Some systems may not support these options
                    
                # Check if this is a reconnecting client
                existing_client = self.clients.get(client_ip)
                if existing_client and existing_client.get("reconnect_pending"):
                    print(f"Client {client_ip} is reconnecting")
                    # Update socket and clear reconnection flag
                    existing_client["socket"] = client_socket
                    existing_client["reconnect_pending"] = False
                    # Resume any pending transfers
                    if existing_client.get("current_file_transfer"):
                        self.status_update.emit(f"Resuming transfers for {client_ip}", "green")
                        threading.Thread(target=self._process_file_queue, args=(client_ip,), daemon=True).start()
                
                # Wait for client information
                try:
                    # Receive client info with timeout
                    client_socket.settimeout(5)  # Short timeout for initial info
                    data = client_socket.recv(4096)
                    client_socket.settimeout(120)  # Restore longer timeout for file operations
                    
                    if data:
                        try:
                            # Parse client information
                            message = json.loads(data.decode('utf-8').strip())
                            if message.get("type") == "CLIENT_INFO":
                                client_info = {
                                    "ip": client_ip,
                                    "hostname": message.get("hostname", "Unknown Client"),
                                    "os_type": message.get("os_type", "Unknown OS"),
                                    "is_windows": message.get("is_windows", False),
                                    "connected_at": time.time()
                                }
                                print(f"Received client info: {client_info['hostname']} ({client_info['os_type']})")
                            else:
                                # Fallback if no proper client info received
                                client_info = {
                                    "ip": client_ip,
                                    "hostname": "Unknown Client",
                                    "os_type": "Unknown OS",
                                    "is_windows": False,
                                    "connected_at": time.time()
                                }
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            # Fallback for invalid JSON
                            client_info = {
                                "ip": client_ip,
                                "hostname": "Unknown Client",
                                "os_type": "Unknown OS",
                                "is_windows": False,
                                "connected_at": time.time()
                            }
                    else:
                        # No data received, use fallback
                        client_info = {
                            "ip": client_ip,
                            "hostname": "Unknown Client",
                            "os_type": "Unknown OS",
                            "is_windows": False,
                            "connected_at": time.time()
                        }
                        
                except socket.timeout:
                    print(f"Timeout waiting for client info from {client_ip}")
                    client_info = {
                        "ip": client_ip,
                        "hostname": "Timeout Client",
                        "os_type": "Unknown OS",
                        "is_windows": False,
                        "connected_at": time.time()
                    }
                
                # Store client information
                self.clients[client_ip] = {
                    "socket": client_socket,
                    "thread": None,
                    "info": client_info,
                    "files_to_send": [],
                    "current_file_transfer": None
                }
                
                # Start a thread to handle this client
                client_thread = threading.Thread(target=self._handle_client, args=(client_socket, client_ip), daemon=True)
                client_thread.start()
                self.clients[client_ip]["thread"] = client_thread
                
                # Emit signal for UI update with complete client info
                self.client_connected.emit(client_info)
                self.status_update.emit(f"Client connected: {client_info['hostname']} ({client_ip})", "green")
                
            except socket.timeout:
                # Timeout is expected, continue the loop
                continue
            except OSError:
                if self.running:
                    print("Error accepting connections")
                break
            except Exception as e:
                if self.running:
                    print(f"Unexpected error in accept_connections: {e}")
                    self.status_update.emit(f"Connection error: {e}", "red")
                    time.sleep(1) # Brief pause before retrying

    def _handle_client(self, client_socket, client_ip):
        buffer = b""
        last_activity = time.time()
        reconnect_attempts = 0
        max_reconnect_attempts = 5
        
        while self.running:
            try:
                # Use non-blocking socket with select for better concurrent handling
                client_socket.settimeout(0.1)  # Short timeout for non-blocking behavior
                try:
                    data = client_socket.recv(CHUNK_SIZE)
                    if data:
                        last_activity = time.time()
                        reconnect_attempts = 0  # Reset attempts on successful data
                    else:
                        # Empty data might mean graceful disconnect or temporary issue
                        # Wait a bit before considering it a disconnect
                        time.sleep(1)
                        try:
                            # Try to send a ping to check connection
                            client_socket.sendall(b'ping\n')
                            continue
                        except:
                            if reconnect_attempts < max_reconnect_attempts:
                                print(f"Connection issue with {client_ip}, attempting to maintain...")
                                reconnect_attempts += 1
                                time.sleep(2)  # Wait before retry
                                continue
                            else:
                                print(f"Client {client_ip} disconnected after {max_reconnect_attempts} attempts")
                                break
                except socket.timeout:
                    # Only timeout after extended period of no activity
                    if time.time() - last_activity > 600:  # 10 minutes timeout
                        print(f"Client {client_ip} timed out due to extended inactivity")
                        break
                    continue  # Continue waiting for data
                except (ConnectionResetError, OSError) as e:
                    # Don't immediately disconnect on connection errors
                    if reconnect_attempts < max_reconnect_attempts:
                        print(f"Connection issue with {client_ip}: {e}, attempting to maintain...")
                        reconnect_attempts += 1
                        time.sleep(2)  # Wait before retry
                        continue
                    else:
                        print(f"Client {client_ip} disconnected after {max_reconnect_attempts} attempts")
                        break

                buffer += data

                # Process complete JSON messages
                while b'\n' in buffer:
                    line, remaining_buffer = buffer.split(b'\n', 1)
                    try:
                        message = json.loads(line.decode('utf-8'))
                        self._process_client_message(client_ip, message)
                        buffer = remaining_buffer
                    except json.JSONDecodeError:
                        print(f"Non-JSON data from client {client_ip}: {line.decode('utf-8', errors='ignore')[:100]}...")
                        buffer = remaining_buffer
                        break

            except Exception as e:
                if self.running:
                    print(f"Unexpected error handling client {client_ip}: {e}")
                break
                
        self._disconnect_client(client_ip)

    def _process_client_message(self, client_ip, message):
        msg_type = message.get("type")
        if msg_type == "FILE_ACK":
            file_name = message.get("file_name")
            status = message.get("status")
            print(f"Received ACK for {file_name} from {client_ip} with status: {status}")
            self.status_update_received.emit(file_name, client_ip, status)
            # Track ack status for this client/file
            st = self.file_transfer_states[client_ip][file_name]
            st["status"] = status
            st["ack_status"] = status
            if status in ("Acknowledged", "Received"):
                st["completed"] = True
        elif msg_type == "STATUS_UPDATE":
            file_name = message.get("file_name")
            status = message.get("status")
            # Normalize client statuses for server UI
            if status == "Saved (No Install)":
                status = "Received successfully"
            print(f"STATUS_UPDATE from {client_ip} for {file_name}: {status}")
            self.status_update_received.emit(file_name, client_ip, status)
        elif msg_type == "CANCEL_TRANSFER":
            file_name = message.get("file_name")
            # If currently sending this file, signal cancel; also remove from queue
            if client_ip in self.clients:
                client_data = self.clients[client_ip]
                current = client_data.get("current_file_transfer")
                if current and current.get("file_name") == file_name:
                    if "cancel_event" in client_data:
                        client_data["cancel_event"].set()
                    self.status_update_received.emit(file_name, client_ip, "Cancelled by Client")
                    self.status_update.emit(f"Client requested cancel for {file_name}", "red")
                # Remove from queued files
                client_data["files_to_send"] = [f for f in client_data["files_to_send"] if f.get("file_name") != file_name]
        else:
            print(f"Unknown message type from client {client_ip}: {message}")

    def _get_local_ip(self):
        """Get the most appropriate local IP address for LAN communication"""
        # Method 1: Connect to a remote address to determine the best local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
        except Exception:
            pass
        
        # Method 2: Get all network interfaces and find the best LAN IP
        try:
            import subprocess
            if platform.system() == "Windows":
                result = subprocess.run(["ipconfig"], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                for line in lines:
                    if "IPv4 Address" in line and ":" in line:
                        ip = line.split(":")[1].strip()
                        if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                            return ip
            else:
                result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
                ips = result.stdout.strip().split()
                for ip in ips:
                    if not ip.startswith("127.") and not ip.startswith("169.254."):
                        return ip
        except Exception:
            pass
        
        # Method 3: Fallback to hostname resolution
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if ip and not ip.startswith("127.") and not ip.startswith("169.254."):
                return ip
        except Exception:
            pass
        
        # Method 4: Get all available IPs and pick the best one
        try:
            hostname = socket.gethostname()
            ip_list = socket.gethostbyname_ex(hostname)[2]
            for ip in ip_list:
                if not ip.startswith("127.") and not ip.startswith("169.254."):
                    return ip
        except Exception:
            pass
        
        return "127.0.0.1"

    def get_server_ip(self):
        return self.server_ip if self.server_ip else "N/A"

    def get_connected_clients(self):
        return [client_data["info"] for client_data in self.clients.values()]

    def add_files_for_distribution(self, file_paths):
        """Add files to distribution queue with virus scanning"""
        try:
            for path in file_paths:
                if not os.path.exists(path):
                    self.status_update.emit(f"File not found: {path}", "red")
                    continue
                    
                try:
                    file_name = os.path.basename(path)
                    self.status_update.emit(f"Processing {file_name}...", "blue")
                    
                    # Add file to distribution queue immediately
                    file_info = {
                        "path": path,
                        "name": file_name,
                        "size": os.path.getsize(path),
                        "scan_result": "pending",
                        "scan_details": "Scan in progress"
                    }
                    self.files_to_distribute.append(file_info)
                    self.status_update.emit(f"Added {file_name} to queue", "blue")
                    
                    # Start virus scan in background thread
                    def scan_file_background():
                        try:
                            def scan_callback(message, color):
                                try:
                                    self.scan_status_update.emit(file_name, message, color)
                                except Exception as e:
                                    print(f"Error in scan callback: {e}")
                            
                            # Start virus scan
                            is_safe, details = self.virus_scanner.scan_file(path, callback=scan_callback)
                            
                            # Update file info with scan results
                            file_info["scan_result"] = "safe" if is_safe else "unsafe"
                            file_info["scan_details"] = details
                            
                            if is_safe:
                                self.scan_status_update.emit(file_name, "Safe - Ready for distribution", "green")
                            else:
                                self.scan_status_update.emit(
                                    file_name,
                                    f"Warning: File may be unsafe - {details if isinstance(details, str) else 'See scan report'}",
                                    "red"
                                )
                                # Remove file from distribution queue if unsafe
                                self.files_to_distribute.remove(file_info)
                                self.status_update.emit(f"Removed unsafe file: {file_name}", "red")
                                
                        except Exception as e:
                            print(f"Error in background scan for {file_name}: {e}")
                            self.status_update.emit(f"Error scanning {file_name}: {str(e)}", "red")
                    
                    # Start background scan thread
                    threading.Thread(target=scan_file_background, daemon=True).start()
                    
                except Exception as e:
                    print(f"Error processing file {path}: {e}")
                    self.status_update.emit(f"Error processing file: {str(e)}", "red")
                    continue
                    
        except Exception as e:
            print(f"Error in add_files_for_distribution: {e}")
            self.status_update.emit(f"Error adding files: {str(e)}", "red")

    def distribute_files_to_clients(self, client_ips=None):
        """
        Distribute files to multiple clients concurrently
        """
        if not self.files_to_distribute:
            self.status_update.emit("No files selected for distribution.", "orange")
            return

        if not self.clients:
            self.status_update.emit("No clients connected to distribute files to.", "orange")
            return

        target_clients = client_ips if client_ips is not None else list(self.clients.keys())
        active_clients = [ip for ip in target_clients if ip in self.clients]

        if not active_clients:
            self.status_update.emit("No active clients to distribute files to.", "orange")
            return

        # Initialize distribution tracking
        for file_info in self.files_to_distribute:
            for client_ip in active_clients:
                if client_ip in self.clients:
                    # Queue file for each client
                    self.send_file(client_ip, file_info["path"])

        # Start a monitoring thread for overall progress
        threading.Thread(target=self._monitor_distribution_progress, 
                       args=(self.files_to_distribute, active_clients),
                       daemon=True).start()
        
        self.status_update.emit(
            f"Started distribution of {len(self.files_to_distribute)} files to {len(active_clients)} clients.", 
            "green"
        )

    def connect_to_client_manual(self, ip_address):
        # This method is a placeholder. In a real scenario, the server doesn't "connect" to a client manually
        # in the same way a client connects to a server. Clients connect to the server.
        # However, if this is meant for the server to initiate a connection to a client that is also running a server,
        # that would require a different architecture (e.g., peer-to-peer).
        # For now, we'll just log it and perhaps add it to a list of "known" clients if it's not already connected.
        # The primary connection mechanism is still clients connecting to this server.
        print(f"Attempting to connect to client manually (server-side): {ip_address}")
        self.status_update.emit(f"Attempting to connect to client manually: {ip_address}", "blue")
        # In a typical client-server model, the server waits for clients.
        # If the intent is for the server to *discover* a client that hasn't broadcasted,
        # or to re-establish a connection, that logic would go here.
        # For now, we assume clients initiate connections.
        # If the client is already connected, we can update its status or info.
        if ip_address in self.clients:
            self.status_update.emit(f"Client {ip_address} is already connected.", "green")
        else:
            self.status_update.emit(f"Client {ip_address} not found. Waiting for client to connect.", "orange")

    def cancel_all_transfers(self):
        for client_ip in self.clients:
            self.clients[client_ip]["files_to_send"].clear()
            # signal cancel for any ongoing transfer
            if "cancel_event" in self.clients[client_ip]:
                self.clients[client_ip]["cancel_event"].set()
            current = self.clients[client_ip]["current_file_transfer"]
            if current:
                file_name = current["file_name"]
                # Inform client to stop receiving this file
                try:
                    cancel_msg = json.dumps({"type": "CANCEL_TRANSFER", "file_name": file_name}).encode("utf-8") + b"\n"
                    self.clients[client_ip]["socket"].sendall(cancel_msg)
                except Exception:
                    pass
                self.status_update_received.emit(file_name, client_ip, "Cancelled")
                self.status_update.emit(f"Cancelled transfer of {file_name} to {client_ip}", "red")
        self.status_update.emit("All transfers cancelled.", "red")

    def cancel_file_transfer(self, client_ip, file_name):
        if client_ip in self.clients:
            # Check if the file is currently being transferred
            current = self.clients[client_ip]["current_file_transfer"]
            if current and current["file_name"] == file_name:
                # signal cancellation to the sending loop
                if "cancel_event" in self.clients[client_ip]:
                    self.clients[client_ip]["cancel_event"].set()
                # Inform client to stop receiving this file
                try:
                    cancel_msg = json.dumps({"type": "CANCEL_TRANSFER", "file_name": file_name}).encode("utf-8") + b"\n"
                    self.clients[client_ip]["socket"].sendall(cancel_msg)
                except Exception:
                    pass
                self.status_update_received.emit(file_name, client_ip, "Cancelled")
                self.status_update.emit(f"Cancelled current transfer of {file_name} to {client_ip}", "red")
            
            # Remove from queue
            self.clients[client_ip]["files_to_send"] = [
                f for f in self.clients[client_ip]["files_to_send"] if f["file_name"] != file_name
            ]
            self.status_update.emit(f"Removed {file_name} from queue for {client_ip}", "red")
        else:
            self.status_update.emit(f"Client {client_ip} not found, cannot cancel transfer.", "orange")

    def cancel_selected_transfers(self, transfers_to_cancel):
        # transfers_to_cancel is a list of (file_name, client_ip) tuples
        for file_name, client_ip in transfers_to_cancel:
            self.cancel_file_transfer(client_ip, file_name)
        self.status_update.emit("Selected transfers cancelled.", "red")

    def _monitor_distribution_progress(self, files_to_distribute, target_clients):
        """Monitor the progress of file distribution to multiple clients"""
        start_time = time.time()
        total_files = len(files_to_distribute)
        total_clients = len(target_clients)
        total_transfers = total_files * total_clients

        while True:
            completed_transfers = 0
            active_transfers = False

            # Check each file for each client
            for file_info in files_to_distribute:
                file_name = file_info["name"]
                for client_ip in target_clients:
                    if client_ip not in self.clients:
                        continue

                    transfer_state = self.file_transfer_states.get(client_ip, {}).get(file_name, {})
                    if transfer_state.get("completed", False):
                        completed_transfers += 1
                    elif transfer_state.get("sent_bytes", 0) > 0:
                        active_transfers = True

            # Calculate overall progress
            progress = (completed_transfers / total_transfers) * 100 if total_transfers > 0 else 0
            elapsed_time = time.time() - start_time

            # Update status
            if completed_transfers == total_transfers:
                self.status_update.emit(
                    f"Distribution completed: {completed_transfers}/{total_transfers} transfers", 
                    "green"
                )
                break
            elif active_transfers:
                self.status_update.emit(
                    f"Distribution in progress: {completed_transfers}/{total_transfers} transfers ({progress:.1f}%)", 
                    "blue"
                )
            else:
                if elapsed_time > RECONNECT_TIMEOUT:
                    self.status_update.emit(
                        f"Distribution timeout: {completed_transfers}/{total_transfers} transfers completed", 
                        "red"
                    )
                    break

            time.sleep(1)  # Update every second

    def _disconnect_client(self, client_ip, is_shutdown=False, is_temporary=False):
        """
        Safely disconnect a client and clean up resources
        :param client_ip: IP of client to disconnect
        :param is_shutdown: True if server is shutting down
        :param is_temporary: True if this is a temporary disconnection
        """
        if client_ip not in self.clients:
            return
            
        client_data = self.clients[client_ip]
        client_socket = client_data.get("socket")
        
        # For temporary disconnections, preserve client data for reconnection
        if is_temporary:
            print(f"Temporary disconnection for client {client_ip}")
            # Just close the socket but keep the client data
            if client_socket:
                try:
                    client_socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    client_socket.close()
                except Exception:
                    pass
            client_data["socket"] = None
            client_data["reconnect_pending"] = True
            self.status_update.emit(f"Client {client_ip} temporarily disconnected", "orange")
            return
        
        # For permanent disconnections or shutdown
        if "cancel_event" in client_data:
            try:
                client_data["cancel_event"].set()
            except Exception:
                pass
        
        # Handle current transfer
        current_transfer = client_data.get("current_file_transfer")
        if current_transfer:
            try:
                file_name = current_transfer.get("file_name", "Unknown")
                if not is_shutdown:
                    self.status_update_received.emit(file_name, client_ip, "Paused")
                    self.status_update.emit(f"Transfer paused: {file_name}", "orange")
            except Exception:
                pass
        
        # Don't clear pending transfers unless it's a shutdown
        if is_shutdown:
            client_data["files_to_send"].clear()
        
        # Close socket safely
        if client_socket:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                client_socket.close()
            except Exception:
                pass
        
        # Clean up client data only on permanent disconnect or shutdown
        if not is_temporary:
            try:
                del self.clients[client_ip]
                if not is_shutdown:
                    self.client_disconnected.emit(client_ip)
                    self.status_update.emit(f"Client {client_ip} disconnected", "red")
            except Exception as e:
                print(f"Error cleaning up client data for {client_ip}: {e}")
            print(f"Disconnected client {client_ip}")

    def send_file(self, client_ip, file_path):
        if client_ip not in self.clients:
            print(f"Client {client_ip} not connected.")
            self.status_update.emit(f"Client {client_ip} not connected", "red")
            return

        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            self.status_update.emit(f"File not found: {file_path}", "red")
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        client_socket = self.clients[client_ip]["socket"]

        # Add to queue for this client
        self.clients[client_ip]["files_to_send"].append({
            "file_path": file_path,
            "file_name": file_name,
            "file_size": file_size,
            "sent_bytes": 0,
            "chunks_acked": set() # For chunk-based retransmission (advanced)
        })
        self.status_update.emit(f"Queued {file_name} for {client_ip}", "blue")
        print(f"Queued {file_name} for {client_ip}")
        
        # Start sending if not already sending
        if not self.clients[client_ip]["current_file_transfer"]:
            threading.Thread(target=self._process_file_queue, args=(client_ip,), daemon=True).start()

    def _process_file_queue(self, client_ip):
        client_data = self.clients[client_ip]
        while self.running and client_data["files_to_send"]:
            if client_data["current_file_transfer"]:
                time.sleep(1) # Wait if a file is already being sent
                continue

            file_info = client_data["files_to_send"].pop(0) # Get next file from queue
            client_data["current_file_transfer"] = file_info
            
            file_path = file_info["file_path"]
            file_name = file_info["file_name"]
            file_size = file_info["file_size"]
            sent_bytes = file_info["sent_bytes"]

            try:
                # Send file metadata
                # ensure cancel_event exists and is cleared before metadata so duplicate ACK can set it later
                if "cancel_event" not in client_data:
                    client_data["cancel_event"] = threading.Event()
                client_data["cancel_event"].clear()
                metadata = {
                    "type": "FILE_METADATA",
                    "file_name": file_name,
                    "file_size": file_size,
                    "scan_result": file_info.get("scan_result", "not_scanned"),
                    "scan_details": file_info.get("scan_details", "File not scanned")
                }
                client_data["socket"].sendall(json.dumps(metadata).encode('utf-8') + b'\n')
                self.status_update.emit(f"Sending metadata for {file_name} to {client_ip}", "orange")
                print(f"Sending metadata for {file_name} to {client_ip}")
                time.sleep(0.05) # Brief pause to let client process metadata
                # Check for cancellation only, allow duplicates
                if client_data["cancel_event"].is_set():
                    self.status_update_received.emit(file_name, client_ip, "Cancelled")
                    self.status_update.emit(f"Cancelled: {file_name} to {client_ip}", "red")
                    client_data["current_file_transfer"] = None
                    continue

                with open(file_path, 'rb') as f:
                    f.seek(sent_bytes) # Resume from where it left off if needed
                    cancelled = False
                    buffer_size = 0
                    last_progress_update = time.time()
                    
                    while sent_bytes < file_size and self.running:
                        if client_data["cancel_event"].is_set():
                            cancelled = True
                            break
                            
                        # Determine chunk size based on remaining buffer space
                        remaining_buffer = MAX_MEMORY_BUFFER - buffer_size
                        current_chunk_size = min(CHUNK_SIZE, remaining_buffer)
                        
                        chunk = f.read(current_chunk_size)
                        if not chunk:
                            break
                            
                        try:
                            client_data["socket"].sendall(chunk)
                            chunk_size = len(chunk)
                            sent_bytes += chunk_size
                            buffer_size += chunk_size
                            
                            # Update progress every 0.5 seconds to reduce UI load
                            current_time = time.time()
                            if current_time - last_progress_update >= 0.5:
                                percentage = int((sent_bytes / file_size) * 100)
                                self.file_progress.emit(file_name, client_ip, percentage)
                                last_progress_update = current_time
                            
                            self.file_transfer_states[client_ip][file_name].update({
                                "sent_bytes": sent_bytes,
                                "total_bytes": file_size,
                                "last_activity": time.time()
                            })
                            
                            # Memory management: if buffer is full, wait for network to catch up
                            if buffer_size >= MAX_MEMORY_BUFFER * 0.8:  # 80% full
                                time.sleep(0.1)  # Brief pause to allow network to catch up
                                buffer_size = 0  # Reset buffer tracking
                        except (ConnectionResetError, OSError, BrokenPipeError, socket.timeout) as e:
                            print(f"Socket error during chunk send to {client_ip}: {e}")
                            cancelled = True
                            break

                if cancelled:
                    print(f"Transfer of {file_name} to {client_ip} cancelled.")
                    self.status_update_received.emit(file_name, client_ip, "Cancelled")
                    self.status_update.emit(f"Cancelled transfer of {file_name} to {client_ip}", "red")
                else:
                    print(f"Finished sending {file_name} to {client_ip}")
                    # Ensure final 100% update is emitted
                    self.file_progress.emit(file_name, client_ip, 100)
                    # File sent successfully, awaiting ACK
                    self.status_update_received.emit(file_name, client_ip, "Sent - Awaiting ACK")
                    self.status_update.emit(f"Sent {file_name} to {client_ip}, awaiting ACK", "lightblue")

            except ConnectionResetError:
                print(f"Client {client_ip} disconnected during transfer of {file_name}.")
                self.status_update_received.emit(file_name, client_ip, "Not Sent (Client Disconnected)")
                self.status_update.emit(f"Client {client_ip} disconnected during {file_name} transfer", "red")
                self._disconnect_client(client_ip)
                break # Exit loop for this client
            except OSError:
                print(f"Socket error sending {file_name} to {client_ip}; disconnecting client.")
                self.status_update_received.emit(file_name, client_ip, "Not Sent (Socket Error)")
                self.status_update.emit(f"Socket error during {file_name} to {client_ip}", "red")
                self._disconnect_client(client_ip)
                break
            except Exception:
                print(f"Unexpected error sending {file_name} to {client_ip}; marking as not sent.")
                self.status_update_received.emit(file_name, client_ip, "Not Sent (Unexpected Error)")
                self.status_update.emit(f"Error sending {file_name} to {client_ip}", "red")
            finally:
                client_data["current_file_transfer"] = None # Reset for next file

    # Discovery Server for advertising presence
    def start_discovery_server(self):
        if self.discovery_server_running:
            return

        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Bind to all interfaces on the discovery port
            self.discovery_socket.bind(('0.0.0.0', self.discovery_port))
            self.discovery_server_running = True
            self.discovery_thread = threading.Thread(target=self._discovery_advertisement_loop, daemon=True)
            self.discovery_thread.start()
            print(f"Discovery server started, advertising on port {self.discovery_port}")
            self.status_update.emit(f"Discovery server started on port {self.discovery_port}", "green")
        except Exception as e:
            print(f"Error starting discovery server: {e}")
            self.status_update.emit(f"Discovery server error: {e}", "red")
            self.discovery_server_running = False

    def stop_discovery_server(self):
        if not self.discovery_server_running:
            return
        self.discovery_server_running = False
        if self.discovery_socket:
            self.discovery_socket.close()
            self.discovery_socket = None
        if self.discovery_thread:
            self.discovery_thread.join()
        print("Discovery server stopped.")

    def _discovery_advertisement_loop(self):
        last_ip_update = 0
        ip_update_interval = 30  # Update IP every 30 seconds (less frequent)
        
        while self.discovery_server_running:
            try:
                # Periodically update server IP in case of network changes
                current_time = time.time()
                if current_time - last_ip_update >= ip_update_interval:
                    old_ip = self.server_ip
                    self.server_ip = self._get_local_ip()
                    if old_ip != self.server_ip:
                        print(f"Server IP updated from {old_ip} to {self.server_ip}")
                        self.server_ip_updated.emit(self.server_ip)
                    last_ip_update = current_time
                
                # Listen for discovery requests with longer timeout for better LAN coverage
                self.discovery_socket.settimeout(2)  # Increased timeout for LAN
                data, addr = self.discovery_socket.recvfrom(1024)
                
                try:
                    message_text = data.decode('utf-8')
                    if message_text == "DISCOVER_SERVER":
                        # Build advertisement with the most accurate IP at send time
                        current_ip = self.server_ip or self._get_local_ip()
                        server_info = {
                            "type": "SERVER_ADVERTISEMENT",
                            "ip": current_ip,
                            "port": self.port,
                            "hostname": socket.gethostname(),
                            "os_type": platform.system(),
                            "is_windows": platform.system() == "Windows",
                            "timestamp": time.time()
                        }
                        response = json.dumps(server_info).encode('utf-8')
                        
                        # Send response back to the requesting client - try multiple times for reliability
                        for attempt in range(3):  # Try 3 times
                            try:
                                self.discovery_socket.sendto(response, addr)
                                print(f"Sent advertisement to {addr[0]} with server IP: {current_ip} (attempt {attempt + 1})")
                                break  # Success, exit retry loop
                            except Exception as e:
                                if attempt == 2:  # Last attempt
                                    print(f"Failed to send advertisement to {addr[0]} after 3 attempts: {e}")
                                else:
                                    time.sleep(0.1)  # Brief delay before retry
                            
                except UnicodeDecodeError:
                    print(f"Received non-UTF8 discovery message from {addr[0]}")
                    
            except socket.timeout:
                # No discovery request received, continue
                pass
            except Exception as e:
                if self.discovery_server_running:
                    print(f"Error in server discovery loop: {e}")
                    self.status_update.emit(f"Discovery error: {e}", "red")
            
            time.sleep(0.1)  # Keep responsive for discovery requests
