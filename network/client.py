import socket
import threading
import json
import os
import time
import platform
import subprocess
import shutil
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from . import protocol
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
    status_update_received = pyqtSignal(str, str, str) # Emits (file_name, server_ip, status)

    def __init__(self, host='0.0.0.0', port=0): # Client binds to 0.0.0.0 and an ephemeral port
        super().__init__()
        self.host = host
        self.port = port
        self.client_socket = None
        self.local_ip = self._get_local_ip()  # Determine actual local IP early for UI display
        self.connected_servers = {} # {ip: {socket: ..., thread: ..., info: ...}}
        self.servers = {} # Discovered servers {ip: info}
        self.running = False
        self.discovery_client_running = False
        self.discovery_socket = None
        self.discovery_thread = None
        self.received_files_path = os.path.join(os.getcwd(), RECEIVED_FILES_DIR)
        os.makedirs(self.received_files_path, exist_ok=True)
        # Track reconnect attempts to avoid duplicates
        self._reconnect_in_progress = set()

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass
        return "127.0.0.1"

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

            # Enable TCP keepalive to reduce idle disconnects
            try:
                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            except Exception:
                pass
            try:
                client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except Exception:
                pass

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

            # Start heartbeat thread to keep connection alive
            heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(server_ip,), daemon=True)
            heartbeat_thread.start()

            self.connected_servers[server_ip] = {
                "socket": client_socket,
                "thread": server_thread,
                "info": self.servers.get(server_ip, {"ip": server_ip, "port": server_port, "hostname": "Unknown"})
            }
            # Store heartbeat thread
            self.connected_servers[server_ip]["heartbeat_thread"] = heartbeat_thread
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
                    # Server closed connection. If mid-file, mark as cancelled/incomplete
                    if current_file_transfer.get("receiving_file") and \
                       current_file_transfer.get("received_bytes", 0) < current_file_transfer.get("file_size", 0):
                        try:
                            fh = current_file_transfer.get("file_handle")
                            if fh:
                                fh.close()
                        except Exception:
                            pass
                        file_name = current_file_transfer.get("file_name", "")
                        self.status_update_received.emit(file_name, server_ip, "Not Received (Disconnected)")
                        self.status_update.emit(f"Disconnected during {file_name} from {server_ip}", "red")
                        current_file_transfer.clear()
                    break

                buffer += data

                # Process JSON messages first
                while b'\n' in buffer:
                    line, remaining_buffer = buffer.split(b'\n', 1)
                    try:
                        message = json.loads(line.decode('utf-8'))
                        self._process_server_message(server_ip, message, current_file_transfer)
                        buffer = remaining_buffer # Update buffer after processing JSON
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # If it's not a complete/valid JSON message, it might be file data
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
        elif msg_type == "CANCEL_TRANSFER":
            file_name = message.get("file_name")
            # If we are currently receiving this file, close it and mark cancelled
            if current_file_transfer.get("receiving_file") and current_file_transfer.get("file_name") == file_name:
                try:
                    fh = current_file_transfer.get("file_handle")
                    if fh:
                        fh.close()
                except Exception:
                    pass
                current_file_transfer.clear()
            self.status_update_received.emit(file_name, server_ip, "Cancelled by Server")
            self.status_update.emit(f"Transfer of {file_name} cancelled by server {server_ip}", "red")
        elif msg_type == "HEARTBEAT":
            # No-op heartbeat from server; keeps NAT mappings alive on some paths
            pass
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
            # Inform server that the file was received successfully
            self._send_file_ack(server_ip, file_name, "Received")
            # Attempt to install if applicable and send status update
            try:
                self._post_receive_actions(server_ip, file_name, current_file_transfer["file_path"])
            except Exception as e:
                self.status_update.emit(f"Post-receive actions failed for {file_name}: {e}", "red")
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

    def _send_status_update(self, server_ip, file_name, status):
        if server_ip in self.connected_servers:
            msg = {
                "type": "STATUS_UPDATE",
                "file_name": file_name,
                "status": status
            }
            try:
                self.connected_servers[server_ip]["socket"].sendall(json.dumps(msg).encode('utf-8') + b'\n')
                print(f"Sent STATUS_UPDATE for {file_name} to {server_ip}: {status}")
            except Exception as e:
                print(f"Error sending STATUS_UPDATE to {server_ip}: {e}")

    def _heartbeat_loop(self, server_ip):
        # Periodically send heartbeat to keep the connection alive
        while self.running and server_ip in self.connected_servers:
            try:
                hb = {"type": "HEARTBEAT"}
                self.connected_servers[server_ip]["socket"].sendall(json.dumps(hb).encode('utf-8') + b'\n')
            except Exception:
                pass
            time.sleep(10)

    def _schedule_reconnect(self, server_ip, server_port):
        if not self.running:
            return
        if server_ip in self.connected_servers:
            return
        if server_ip in self._reconnect_in_progress:
            return
        self._reconnect_in_progress.add(server_ip)
        threading.Thread(target=self._reconnect_loop, args=(server_ip, server_port), daemon=True).start()

    def _reconnect_loop(self, server_ip, server_port):
        # Keep trying to reconnect until connected or client stopped
        backoff = 3
        while self.running and server_ip not in self.connected_servers:
            try:
                self.status_update.emit(f"Reconnecting to {server_ip}...", "orange")
                self._connect_to_server(server_ip, server_port)
                break
            except Exception:
                pass
            time.sleep(backoff)
            backoff = min(backoff * 2, 30)
        self._reconnect_in_progress.discard(server_ip)

    def _is_installer(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        # Common installer extensions
        return ext in [
            ".msi", ".exe", ".bat", ".cmd", ".ps1",  # Windows
            ".sh", ".deb", ".rpm",                        # Linux
            ".pkg", ".dmg"                                 # macOS
        ]

    def _attempt_install(self, file_path):
        system = platform.system()
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if system == "Windows":
                if ext == ".msi":
                    # Silent MSI install
                    result = subprocess.run(["msiexec", "/i", file_path, "/qn", "/norestart"], capture_output=True)
                    return (result.returncode == 0, "MSI install rc=" + str(result.returncode))
                elif ext == ".exe":
                    # Try common silent flags
                    silent_flags = [["/S"], ["/silent"], ["/quiet"], ["/VERYSILENT"], ["/s"]]
                    for flags in silent_flags:
                        result = subprocess.run([file_path] + flags, capture_output=True)
                        if result.returncode == 0:
                            return (True, "EXE installed silently")
                    # As a fallback, run normally (may show UI)
                    subprocess.Popen([file_path])
                    return (False, "EXE started (manual setup likely)")
                elif ext in (".bat", ".cmd"):
                    subprocess.Popen([file_path], shell=True)
                    return (False, "Script started (manual setup likely)")
                elif ext == ".ps1":
                    subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", file_path], shell=False)
                    return (False, "PowerShell script started (manual setup likely)")
                else:
                    return (False, "Unsupported Windows installer type")
            elif system == "Linux":
                if ext == ".sh":
                    subprocess.Popen(["bash", file_path])
                    return (False, "Shell script started (manual setup likely)")
                elif ext == ".deb":
                    result = subprocess.run(["sudo", "dpkg", "-i", file_path])
                    return (result.returncode == 0, "dpkg rc=" + str(result.returncode))
                elif ext == ".rpm":
                    result = subprocess.run(["sudo", "rpm", "-i", file_path])
                    return (result.returncode == 0, "rpm rc=" + str(result.returncode))
                else:
                    return (False, "Unsupported Linux installer type")
            elif system == "Darwin":
                if ext == ".pkg":
                    result = subprocess.run(["sudo", "installer", "-pkg", file_path, "-target", "/"])
                    return (result.returncode == 0, "installer rc=" + str(result.returncode))
                elif ext == ".dmg":
                    return (False, "DMG requires manual mount/install")
                else:
                    return (False, "Unsupported macOS installer type")
        except Exception as e:
            return (False, f"Install attempt error: {e}")
        return (False, "No install action taken")

    def _post_receive_actions(self, server_ip, file_name, file_path):
        if self._is_installer(file_path):
            installed, msg = self._attempt_install(file_path)
            if installed:
                self._send_status_update(server_ip, file_name, "Installed")
                self.status_update.emit(f"Installed {file_name}", "lightgreen")
            else:
                # Could not install silently; manual setup likely required
                self._send_status_update(server_ip, file_name, "Need Manual Setup")
                self.status_update.emit(f"{file_name}: {msg}", "orange")
        else:
            # Not an installer; mark as received successfully
            self._send_status_update(server_ip, file_name, "Received Successfully")

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
            # Schedule auto-reconnect unless stopped manually
            server_port = self.servers.get(server_ip, {}).get('port', protocol.COMMAND_PORT)
            self._schedule_reconnect(server_ip, server_port)

    # Discovery Client for finding servers
    def start_discovery_client(self):
        if self.discovery_client_running:
            return

        self.discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.discovery_socket.settimeout(1) # Timeout for recvfrom

        discovery_port = protocol.DISCOVERY_PORT # Must match server's discovery port
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
