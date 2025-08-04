import socket
import threading
import time
import subprocess
import platform
import psutil
from typing import List, Dict, Optional
import re

def get_local_ip() -> str:
    """Get the local IP address of this machine"""
    try:
        # Use socket to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return "127.0.0.1"

class NetworkDevice:
    def __init__(self, ip: str, hostname: str = "", os_type: str = "Unknown", is_windows: bool = False):
        self.ip = ip
        self.hostname = hostname
        self.os_type = os_type
        self.is_windows = is_windows
        self.is_online = True
        self.last_seen = time.time()
        self.ports = []
        
    def __repr__(self):
        return f"NetworkDevice(ip={self.ip}, hostname={self.hostname}, os={self.os_type}, windows={self.is_windows})"

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
    
    def ping_host(self, ip: str) -> bool:
        """Ping a host to check if it's online"""
        try:
            if platform.system().lower() == "windows":
                result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip], 
                                      capture_output=True, text=True, timeout=2)
            else:
                result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], 
                                      capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def get_hostname(self, ip: str) -> str:
        """Get hostname for an IP address"""
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return ""
    
    def detect_os(self, ip: str) -> str:
        """Detect the operating system of a remote host"""
        try:
            # Try to connect to common ports to detect OS
            common_ports = [22, 23, 80, 443, 3389, 135, 139, 445]
            for port in common_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex((ip, port))
                    sock.close()
                    if result == 0:
                        # Port is open, try to get OS info
                        if port in [135, 139, 445]:  # Windows-specific ports
                            return "Windows"
                        elif port == 22:  # SSH port
                            return "Linux/Unix"
                except:
                    continue
            return "Unknown"
        except:
            return "Unknown"
    
    def scan_network(self):
        """Scan the network for devices"""
        network_range = self.get_network_range()
        local_ip = self.get_local_ip()
        
        def scan_ip(ip):
            if ip == local_ip:
                return
                
            if self.ping_host(ip):
                hostname = self.get_hostname(ip)
                os_type = self.detect_os(ip)
                is_windows = os_type == "Windows"
                
                device = NetworkDevice(ip, hostname, os_type, is_windows)
                self.devices[ip] = device
                
                if self.callback:
                    self.callback(device)
        
        # Use threading for faster scanning
        threads = []
        for ip in network_range:
            thread = threading.Thread(target=scan_ip, args=(ip,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            
            # Limit concurrent threads
            if len(threads) >= 50:
                for t in threads:
                    t.join()
                threads = []
        
        # Wait for remaining threads
        for t in threads:
            t.join()
    
    def start_discovery(self, callback=None):
        """Start continuous network discovery"""
        self.callback = callback
        self.discovery_running = True
        self.discovery_thread = threading.Thread(target=self._discovery_loop)
        self.discovery_thread.daemon = True
        self.discovery_thread.start()
    
    def stop_discovery(self):
        """Stop network discovery"""
        self.discovery_running = False
        if self.discovery_thread:
            self.discovery_thread.join()
    
    def _discovery_loop(self):
        """Main discovery loop"""
        while self.discovery_running:
            self.scan_network()
            time.sleep(30)  # Rescan every 30 seconds
    
    def get_windows_devices(self) -> List[NetworkDevice]:
        """Get only Windows devices"""
        return [device for device in self.devices.values() if device.is_windows]
    
    def get_all_devices(self) -> List[NetworkDevice]:
        """Get all discovered devices"""
        return list(self.devices.values())
    
    def get_device_by_ip(self, ip: str) -> Optional[NetworkDevice]:
        """Get a specific device by IP"""
        return self.devices.get(ip) 