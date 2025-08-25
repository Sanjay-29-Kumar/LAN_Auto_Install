import socket
import threading
import json
import os
import time
import platform
import subprocess
import shutil
import ctypes
import zipfile
import tempfile
from pathlib import Path
from auto_installer import AutoInstaller
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
        # Prepare categorized directories
        self.dirs = {
            "installer": os.path.join(self.received_files_path, "installer"),
            "files": os.path.join(self.received_files_path, "files"),
            "media": os.path.join(self.received_files_path, "media"),
            "tmp": os.path.join(self.received_files_path, "tmp"),
            "manual_setup": os.path.join(self.received_files_path, "manual_setup"),
        }
        for p in self.dirs.values():
            os.makedirs(p, exist_ok=True)
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

                # If currently receiving a file, consume exactly the remaining bytes first
                if current_file_transfer.get("receiving_file"):
                    bytes_needed = current_file_transfer["file_size"] - current_file_transfer["received_bytes"]
                    if bytes_needed > 0:
                        if len(buffer) >= bytes_needed:
                            # Write only the needed bytes to finish the file
                            self._receive_file_chunk(server_ip, buffer[:bytes_needed], current_file_transfer)
                            buffer = buffer[bytes_needed:]
                        else:
                            # Not enough data yet; write all and wait for more
                            self._receive_file_chunk(server_ip, buffer, current_file_transfer)
                            buffer = b""
                            continue  # Wait for more data; skip JSON parsing for now

                # Process JSON messages in buffer after file consumption
                while b'\n' in buffer:
                    line, remaining_buffer = buffer.split(b'\n', 1)
                    try:
                        message = json.loads(line.decode('utf-8'))
                        self._process_server_message(server_ip, message, current_file_transfer)
                        buffer = remaining_buffer # Update buffer after processing JSON
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # If it's not valid JSON and we are (now) receiving a file, treat entire buffer as file data
                        if current_file_transfer.get("receiving_file"):
                            bytes_needed = current_file_transfer["file_size"] - current_file_transfer["received_bytes"]
                            to_write = buffer[:bytes_needed]
                            if to_write:
                                self._receive_file_chunk(server_ip, to_write, current_file_transfer)
                            buffer = buffer[len(to_write):]
                            # If still receiving, wait for more data
                            if current_file_transfer.get("receiving_file"):
                                break
                        else:
                            print(f"Non-JSON data or incomplete JSON from {server_ip}: {line.decode('utf-8', errors='ignore')}")
                            buffer = remaining_buffer
                        break

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

            # Duplicate check before preparing file reception
            try:
                fsize = int(file_size)
            except Exception:
                fsize = file_size
            if self._existing_file(file_name, fsize):
                # Inform server with ACK and skip creating UI row or temp file
                self._send_file_ack(server_ip, file_name, "Received already")
                self._send_status_update(server_ip, file_name, "Received already")
                self.request_cancel_receive(server_ip, file_name)
                return
            
            current_file_transfer.clear() # Clear any previous transfer state
            current_file_transfer["receiving_file"] = True
            current_file_transfer["file_name"] = file_name
            current_file_transfer["file_size"] = file_size
            current_file_transfer["received_bytes"] = 0
            # Save initially into a temp folder; will move to category after completed
            current_file_transfer["file_path"] = os.path.join(self.dirs.get("tmp", self.received_files_path), file_name)
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
            # Inform server that the file was received successfully
            self._send_file_ack(server_ip, file_name, "Received")
            # Also update local UI row
            self.status_update_received.emit(file_name, server_ip, "Received")
            # Offload install to background worker; do not block socket thread
            try:
                file_path = current_file_transfer["file_path"]
            except Exception:
                file_path = None
            if file_path:
                threading.Thread(target=self._post_receive_actions_wrapper, args=(server_ip, file_name, file_path), daemon=True).start()
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

    def _run_process_silent(self, args):
        # Run a process with no visible window (Windows) and a generous timeout
        si = None
        creationflags = 0
        if platform.system() == "Windows":
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            except Exception:
                si = None
                creationflags = 0
        return subprocess.run(args, capture_output=True, timeout=900, startupinfo=si, creationflags=creationflags)

    def _is_admin(self):
        if platform.system() != "Windows":
            return False
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    def _run_via_schtasks(self, args_list):
        if platform.system() != "Windows":
            return (False, "schtasks not supported")
        try:
            task_name = f"LANAutoInstall_{int(time.time())}"
            # Quote args for cmd
            def q(a):
                if not a:
                    return '""'
                return f'"{a}"' if (' ' in a or '\\' in a or '"' in a) else a
            cmd = " ".join(q(a) for a in args_list)
            tr = f"cmd /c {cmd}"
            start_time = time.strftime("%H:%M", time.localtime(time.time() + 10))
            create = [
                "schtasks", "/Create", "/TN", task_name,
                "/TR", tr, "/SC", "ONCE", "/ST", start_time,
                "/RU", "SYSTEM", "/RL", "HIGHEST", "/F"
            ]
            res_create = subprocess.run(create, capture_output=True, text=True)
            if res_create.returncode != 0:
                return (False, f"schtasks create rc={res_create.returncode}: {res_create.stdout or res_create.stderr}")
            subprocess.run(["schtasks", "/Run", "/TN", task_name], capture_output=True)
            # Poll up to 10 minutes
            deadline = time.time() + 600
            last_rc = None
            while time.time() < deadline:
                qres = subprocess.run(["schtasks", "/Query", "/TN", task_name, "/FO", "LIST", "/V"], capture_output=True, text=True)
                out = qres.stdout or ""
                for line in out.splitlines():
                    if line.strip().startswith("Last Run Result:"):
                        last_rc = line.split(":", 1)[1].strip()
                        break
                if last_rc and last_rc.upper().startswith("0X0"):
                    subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True)
                    return (True, "Installed via schtasks")
                time.sleep(5)
            subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], capture_output=True)
            return (False, f"schtasks timeout; last result: {last_rc}")
        except Exception as e:
            return (False, f"schtasks error: {e}")

    def request_cancel_receive(self, server_ip, file_name):
        """Request the server to cancel sending the given file."""
        if server_ip in self.connected_servers:
            try:
                msg = {"type": "CANCEL_TRANSFER", "file_name": file_name}
                self.connected_servers[server_ip]["socket"].sendall(json.dumps(msg).encode('utf-8') + b'\n')
                self.status_update.emit(f"Requested cancel for {file_name}", "orange")
            except Exception as e:
                print(f"Failed to send cancel request for {file_name} to {server_ip}: {e}")

    def _detect_category(self, file_path):
        """Classify file into media or files categories by extension."""
        ext = os.path.splitext(file_path)[1].lower()
        media_exts = {
            # images
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".svg", ".webp", ".heic",
            # audio
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a",
            # video
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm"
        }
        if ext in media_exts:
            return "media"
        return "files"

    def _move_to_category(self, file_path, category):
        try:
            dest_dir = self.dirs.get(category, self.dirs.get("files", self.received_files_path))
            os.makedirs(dest_dir, exist_ok=True)
            dest_path = os.path.join(dest_dir, os.path.basename(file_path))
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(dest_path)
                dest_path = f"{base}_{int(time.time())}{ext}"
            shutil.move(file_path, dest_path)
            return dest_path
        except Exception as e:
            print(f"Failed to move {file_path} to {category}: {e}")
            return file_path

    def _existing_file(self, file_name, file_size):
        """Return True if a file of same name and size already exists in categorized folders."""
        try:
            dirs_to_check = [
                self.dirs.get("installer"),
                self.dirs.get("files"),
                self.dirs.get("media"),
                self.dirs.get("tmp"),
            ]
            for d in dirs_to_check:
                if not d:
                    continue
                p = os.path.join(d, file_name)
                if os.path.exists(p):
                    try:
                        if os.path.getsize(p) == int(file_size):
                            return True
                    except Exception:
                        if os.path.getsize(p) == file_size:
                            return True
        except Exception:
            pass
        return False

    def _move_to_manual_setup(self, file_path, reason):
        try:
            manual_dir = os.path.join(self.received_files_path, "manual_setup")
            os.makedirs(manual_dir, exist_ok=True)
            dest_path = os.path.join(manual_dir, os.path.basename(file_path))
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(dest_path)
                dest_path = f"{base}_{int(time.time())}{ext}"
            shutil.move(file_path, dest_path)
            info_path = dest_path + ".info.txt"
            with open(info_path, "w", encoding="utf-8") as f:
                f.write(f"Reason: {reason}\nTimestamp: {time.ctime()}\n")
            return dest_path
        except Exception:
            return None

    def _post_receive_actions_wrapper(self, server_ip, file_name, file_path):
        try:
            self._post_receive_actions(server_ip, file_name, file_path)
        except Exception as e:
            # Keep errors in status bar; no ACKs here
            self.status_update.emit(f"Post-receive actions failed for {file_name}: {e}", "red")

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
            ".msi", ".exe", ".bat", ".cmd", ".ps1", ".zip",  # Windows (+zip archives)
            ".sh", ".deb", ".rpm",                                # Linux
            ".pkg", ".dmg"                                         # macOS
        ]

    def _attempt_install(self, file_path):
        system = platform.system()
        ext = os.path.splitext(file_path)[1].lower()
        try:
            if system == "Windows":
                if ext == ".msi":
                    # Always run silent via Task Scheduler as SYSTEM to avoid UAC prompts
                    ok, msg = self._run_via_schtasks(["msiexec", "/i", file_path, "/qn", "/norestart", "ALLUSERS=1"])
                    if ok:
                        return (True, "MSI installed silently (SYSTEM)")
                    return (False, f"MSI install failed: {msg}")
                elif ext == ".exe":
                    # Always run via Task Scheduler as SYSTEM to avoid UAC prompts
                    # Only use silent switches; limit attempts to avoid repeated launches
                    candidates = [
                        [file_path, "/S"],  # NSIS, Squirrel
                        [file_path, "/quiet", "/norestart"],  # MSI wrappers, WiX
                        [file_path, "/VERYSILENT", "/SP-", "/SUPPRESSMSGBOXES", "/NORESTART"],  # Inno Setup
                        [file_path, "/s", "/v", "/qn"],  # InstallShield/MSI wrapper
                    ]
                    for args in candidates:
                        ok, msg = self._run_via_schtasks(args)
                        if ok:
                            return (True, "EXE installed silently (SYSTEM)")
                    return (False, f"EXE install failed: {msg}")
                elif ext == ".zip":
                    # Extract ZIP and attempt to install any contained MSI/EXE silently via SYSTEM
                    try:
                        base_name = os.path.splitext(os.path.basename(file_path))[0]
                        extract_dir = os.path.join(self.received_files_path, "extracted", f"{base_name}_{int(time.time())}")
                        os.makedirs(extract_dir, exist_ok=True)
                        with zipfile.ZipFile(file_path, 'r') as zf:
                            zf.extractall(extract_dir)
                        # Find installers inside
                        found_installers = []
                        for root, dirs, files in os.walk(extract_dir):
                            for f in files:
                                fe = os.path.splitext(f)[1].lower()
                                if fe in (".msi", ".exe"):
                                    found_installers.append(os.path.join(root, f))
                        # Try to install first successful one
                        for inst in found_installers:
                            iext = os.path.splitext(inst)[1].lower()
                            if iext == ".msi":
                                ok, msg = self._run_via_schtasks(["msiexec", "/i", inst, "/qn", "/norestart", "ALLUSERS=1"])
                                if ok:
                                    return (True, "ZIP-contained MSI installed (SYSTEM)")
                            else:
                                for args in [
                                    [inst, "/S"],
                                    [inst, "/quiet", "/norestart"],
                                    [inst, "/VERYSILENT", "/SP-", "/SUPPRESSMSGBOXES", "/NORESTART"],
                                    [inst, "/s", "/v", "/qn"],
                                ]:
                                    ok, msg = self._run_via_schtasks(args)
                                    if ok:
                                        return (True, "ZIP-contained EXE installed (SYSTEM)")
                        return (False, "No auto installer found in ZIP or silent install failed")
                    except Exception as e:
                        return (False, f"ZIP processing error: {e}")
                elif ext in (".bat", ".cmd"):
                    # Execute batch silently via Task Scheduler as SYSTEM (hidden session)
                    ok, msg = self._run_via_schtasks(["cmd.exe", "/c", file_path])
                    if ok:
                        return (True, "Batch executed (SYSTEM, hidden)")
                    return (False, f"Batch execution failed: {msg}")
                elif ext == ".ps1":
                    # Execute PowerShell silently via Task Scheduler as SYSTEM (hidden, non-interactive)
                    ok, msg = self._run_via_schtasks(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-NonInteractive", "-File", file_path])
                    if ok:
                        return (True, "PowerShell executed (SYSTEM, hidden)")
                    return (False, f"PowerShell execution failed: {msg}")
                else:
                    return (False, "Unsupported Windows installer type")
            elif system == "Linux":
                if ext == ".sh":
                    return (False, "Shell script requires manual setup")
                elif ext == ".deb":
                    try:
                        result = subprocess.run(["dpkg", "-i", file_path], capture_output=True, timeout=600)
                        return (result.returncode == 0, "dpkg rc=" + str(result.returncode))
                    except Exception as e:
                        return (False, f"dpkg error: {e}")
                elif ext == ".rpm":
                    try:
                        result = subprocess.run(["rpm", "-i", file_path], capture_output=True, timeout=600)
                        return (result.returncode == 0, "rpm rc=" + str(result.returncode))
                    except Exception as e:
                        return (False, f"rpm error: {e}")
                else:
                    return (False, "Unsupported Linux installer type")
            elif system == "Darwin":
                if ext == ".pkg":
                    return (False, "pkg install requires admin privileges (manual setup)")
                elif ext == ".dmg":
                    return (False, "DMG requires manual mount/install")
                else:
                    return (False, "Unsupported macOS installer type")
        except Exception as e:
            return (False, f"Install attempt error: {e}")
        return (False, "No install action taken")

    def _post_receive_actions(self, server_ip, file_name, file_path):
        # Use AutoInstaller for all installer and archive handling
        installer_dir = os.path.dirname(file_path)
        auto_installer = AutoInstaller(installers_dir=installer_dir)
        # Only process the specific file received, not all in the dir
        ext = os.path.splitext(file_path)[1].lower()
        # Only supported installer types will be handled, others will be moved to files/media
        if ext in auto_installer.SILENT_COMMANDS:
            self._send_status_update(server_ip, file_name, "Installing")
            self.status_update_received.emit(file_name, server_ip, "Installing")
            ret = auto_installer.SILENT_COMMANDS[ext](Path(file_path))
            # If any popup or user interaction occurs, the installer will not return 0.
            # In that case, always move to manual setup and notify as such.
            if ret == 0:
                self._move_to_category(file_path, "installer")
                self._send_status_update(server_ip, file_name, "Installed")
                self.status_update_received.emit(file_name, server_ip, "Installed")
            else:
                self._move_to_manual_setup(file_path, "Manual Setup Required (Popup or User Interaction Detected)")
                self._send_status_update(server_ip, file_name, "Manual Setup Required")
                self.status_update_received.emit(file_name, server_ip, "Manual Setup Required")
                self.status_update.emit(f"{file_name}: manual setup required (popup or user interaction detected)", "orange")
        else:
            # Non-installer: categorize as media or files
            category = self._detect_category(file_path)
            dest = self._move_to_category(file_path, category)
            self._send_status_update(server_ip, file_name, "Received successfully")
            self.status_update.emit(f"{file_name}: saved to {category}", "green")

    def _disconnect_from_server(self, server_ip):
        # Safely remove the server from the connected map to avoid KeyError in concurrent paths
        data = self.connected_servers.pop(server_ip, None)
        if not data:
            # Already disconnected elsewhere
            return
        server_socket = data.get("socket")
        try:
            server_socket.shutdown(socket.SHUT_RDWR)
            server_socket.close()
        except Exception as e:
            print(f"Error closing socket for {server_ip}: {e}")
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
