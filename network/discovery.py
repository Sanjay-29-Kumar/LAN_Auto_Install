import socket
import json
import time
import threading
from typing import List, Set

class NetworkDiscovery:
    def __init__(self, port: int = 5000):
        self.port = port
        self.running = False
        self.discovered_servers: Set[str] = set()
        self._lock = threading.Lock()

    def _get_local_network_ranges(self) -> List[str]:
        """Get potential network ranges to scan"""
        network_ranges = set()
        
        try:
            # Get the machine's IP addresses
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            
            for ip in local_ips:
                if not ip.startswith('127.'):  # Skip loopback
                    # Convert IP to network address
                    ip_parts = ip.split('.')
                    # Add common subnet ranges
                    network_ranges.add(f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}")
        except Exception as e:
            print(f"Error getting network ranges: {e}")
        
        # Add common LAN ranges if none found
        if not network_ranges:
            network_ranges.update([
                "192.168.0", "192.168.1",
                "10.0.0", "10.0.1",
                "172.16.0", "172.16.1"
            ])
        
        return list(network_ranges)

    def _is_port_open(self, ip: str, timeout: float = 0.5) -> bool:
        """Check if a TCP port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, self.port))
            sock.close()
            return result == 0
        except:
            return False

    def _verify_server(self, ip: str) -> bool:
        """Verify if the IP is a valid LAN Auto Install server"""
        try:
            # Try to establish TCP connection
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect((ip, self.port))
                
                # Send verification request
                verify_msg = json.dumps({
                    "type": "VERIFY_SERVER",
                    "client_info": {
                        "hostname": socket.gethostname()
                    }
                }).encode() + b'\n'
                
                sock.sendall(verify_msg)
                
                # Wait for response
                response = sock.recv(1024).decode().strip()
                try:
                    response_data = json.loads(response)
                    if response_data.get("type") == "SERVER_VERIFY_OK":
                        return True
                except:
                    pass
        except:
            pass
        return False

    def start_discovery_server(self, server_ip: str):
        """Start TCP server to respond to discovery attempts"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind(('', self.port))
            self.server_socket.listen(5)
            
            def handle_verification():
                while self.running:
                    try:
                        client_socket, addr = self.server_socket.accept()
                        client_socket.settimeout(5)
                        
                        try:
                            data = client_socket.recv(1024).decode().strip()
                            request = json.loads(data)
                            
                            if request.get("type") == "VERIFY_SERVER":
                                # Send verification response
                                response = json.dumps({
                                    "type": "SERVER_VERIFY_OK",
                                    "server_ip": server_ip
                                }).encode() + b'\n'
                                client_socket.sendall(response)
                        except:
                            pass
                        finally:
                            client_socket.close()
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self.running:
                            print(f"Discovery server error: {e}")
                            time.sleep(1)
            
            threading.Thread(target=handle_verification, daemon=True).start()
            
        except Exception as e:
            print(f"Could not start discovery server: {e}")
            self.running = False

    def discover_servers(self, timeout: int = 30) -> List[str]:
        """
        Discover servers using TCP connection attempts.
        Uses a more firewall-friendly approach with direct TCP connections.
        """
        self.discovered_servers.clear()
        network_ranges = self._get_local_network_ranges()
        end_time = time.time() + timeout
        
        def scan_ip(ip: str):
            if self._is_port_open(ip):
                if self._verify_server(ip):
                    with self._lock:
                        self.discovered_servers.add(ip)
        
        while time.time() < end_time and not self.discovered_servers:
            threads = []
            
            # Scan each network range
            for network_range in network_ranges:
                for i in range(1, 255):
                    ip = f"{network_range}.{i}"
                    
                    # Limit concurrent threads
                    while len(threads) >= 50:
                        threads = [t for t in threads if t.is_alive()]
                        time.sleep(0.1)
                    
                    thread = threading.Thread(target=scan_ip, args=(ip,), daemon=True)
                    thread.start()
                    threads.append(thread)
            
            # Wait for remaining threads
            for thread in threads:
                thread.join()
            
            if not self.discovered_servers:
                time.sleep(2)  # Wait before retrying
        
        return list(self.discovered_servers)

    def stop(self):
        """Stop discovery server"""
        self.running = False
        if hasattr(self, 'server_socket'):
            try:
                self.server_socket.close()
            except Exception:
                pass
