
import socket
import threading
import time
import subprocess
import platform
import concurrent.futures
from typing import List, Dict, Optional
import re
import json

def get_local_ip() -> str:
    """Get the local IP address of this machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return "127.0.0.1"

class NetworkDevice:
    def __init__(self, ip: str, hostname: str = "", is_server: bool = False, response_time: float = 0.0):
        self.ip = ip
        self.hostname = hostname
        self.is_server = is_server
        self.response_time = response_time
        self.last_seen = time.time()
        
    def __repr__(self):
        return f"NetworkDevice(ip={self.ip}, hostname={self.hostname}, server={self.is_server})"

class NetworkDiscovery:
    def __init__(self, port: int = 5000):
        self.port = port
        self.devices: Dict[str, NetworkDevice] = {}
        self.discovery_running = False
        self.discovery_thread = None
        self.callback = None
        
    def get_local_ip(self) -> str:
        """Get the local IP address of this machine"""
        return get_local_ip()
    
    def get_network_range(self) -> List[str]:
        """Get the list of IP addresses to scan in the local network"""
        local_ip = self.get_local_ip()
        base_ip = '.'.join(local_ip.split('.')[:-1])
        return [f"{base_ip}.{i}" for i in range(1, 255)]
    
    def quick_ping(self, ip: str) -> bool:
        """Fast ping check with very short timeout"""
        try:
            if platform.system().lower() == "windows":
                result = subprocess.run(['ping', '-n', '1', '-w', '100', ip], 
                                      capture_output=True, text=True, timeout=0.2)
            else:
                result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], 
                                      capture_output=True, text=True, timeout=0.2)
            return result.returncode == 0
        except:
            return False
    
    def check_server_port(self, ip: str) -> tuple:
        """Check if device has our server running with proper handshake"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.2)  # Very fast timeout
            start_time = time.time()
            result = sock.connect_ex((ip, self.port))
            
            if result == 0:
                try:
                    # Send a quick discovery message
                    discovery_msg = {
                        "type": "discovery",
                        "data": {"client_ip": self.get_local_ip()},
                        "timestamp": time.time()
                    }
                    
                    msg_bytes = json.dumps(discovery_msg).encode('utf-8')
                    msg_length = len(msg_bytes).to_bytes(4, 'big')
                    sock.send(msg_length + msg_bytes)
                    
                    # Try to receive response
                    sock.settimeout(0.3)
                    resp_length_bytes = sock.recv(4)
                    if len(resp_length_bytes) == 4:
                        resp_length = int.from_bytes(resp_length_bytes, 'big')
                        if resp_length < 1024:  # Reasonable response size
                            resp_data = sock.recv(resp_length)
                            response = json.loads(resp_data.decode('utf-8'))
                            if response.get('type') == 'discovery_response':
                                response_time = time.time() - start_time
                                sock.close()
                                return True, response_time
                except:
                    pass
            
            sock.close()
            return False, 999
        except:
            return False, 999
    
    def get_hostname(self, ip: str) -> str:
        """Get hostname for an IP address with fast timeout"""
        try:
            socket.settimeout(0.1)
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return f"Device-{ip.split('.')[-1]}"
    
    def scan_single_ip(self, ip: str) -> Optional[NetworkDevice]:
        """Scan a single IP address with optimized checks"""
        local_ip = self.get_local_ip()
        # Allow same-machine discovery for testing
        # if ip == local_ip:
        #     return None
            
        # First check if server port is available (fastest way to find our servers)
        is_server, response_time = self.check_server_port(ip)
        
        if is_server:
            hostname = self.get_hostname(ip)
            return NetworkDevice(ip, hostname, True, response_time)
        
        return None  # Skip non-server devices for faster discovery
    
    def fast_network_scan(self):
        """Ultra-fast network scan focusing on servers only"""
        network_range = self.get_network_range()
        found_devices = []
        
        # Use ThreadPoolExecutor with higher concurrency for faster scanning
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            future_to_ip = {executor.submit(self.scan_single_ip, ip): ip for ip in network_range}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_ip, timeout=5):
                try:
                    device = future.result()
                    if device:
                        found_devices.append(device)
                        self.devices[device.ip] = device
                        
                        if self.callback:
                            self.callback(device)
                        
                        print(f"✓ Found server: {device.ip} ({device.hostname}) - {device.response_time:.3f}s")
                except Exception as e:
                    pass
        
        return found_devices
    
    def start_discovery(self, callback=None):
        """Start continuous network discovery"""
        self.callback = callback
        self.discovery_running = True
        self.discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self.discovery_thread.start()
    
    def stop_discovery(self):
        """Stop network discovery"""
        self.discovery_running = False
        if self.discovery_thread:
            self.discovery_thread.join(timeout=1)
    
    def _discovery_loop(self):
        """Main discovery loop with adaptive timing"""
        while self.discovery_running:
            try:
                print(f"🔍 Scanning network for servers...")
                start_time = time.time()
                found_devices = self.fast_network_scan()
                scan_time = time.time() - start_time
                
                print(f"🔍 Network scan completed in {scan_time:.2f}s - Found {len(found_devices)} servers")
                
                # Adaptive sleep - scan more frequently if servers found
                if found_devices:
                    time.sleep(15)  # Scan every 15s when servers are present
                else:
                    time.sleep(30)  # Scan every 30s when no servers found
                    
            except Exception as e:
                print(f"Discovery error: {e}")
                time.sleep(10)
    
    def get_server_devices(self) -> List[NetworkDevice]:
        """Get only devices running our server"""
        return [device for device in self.devices.values() if device.is_server]
    
    def get_all_devices(self) -> List[NetworkDevice]:
        """Get all discovered devices"""
        return list(self.devices.values())
    
    def get_device_by_ip(self, ip: str) -> Optional[NetworkDevice]:
        """Get a specific device by IP"""
        return self.devices.get(ip)
    
    def refresh_device_status(self, ip: str) -> bool:
        """Refresh status of a specific device"""
        device = self.scan_single_ip(ip)
        if device:
            self.devices[ip] = device
            return True
        elif ip in self.devices:
            del self.devices[ip]
        return False
