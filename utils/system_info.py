import platform
import psutil
import socket
import os
from typing import Dict, Any, List
import time

class SystemInfo:
    def __init__(self):
        pass
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        return {
            "hostname": socket.gethostname(),
            "os": self.get_os_info(),
            "network": self.get_network_info(),
            "hardware": self.get_hardware_info(),
            "storage": self.get_storage_info(),
            "memory": self.get_memory_info(),
            "processes": self.get_process_info()
        }
    
    def get_os_info(self) -> Dict[str, Any]:
        """Get operating system information"""
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.architecture()[0],
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Get network interfaces
            interfaces = {}
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        interfaces[interface] = {
                            "ip": addr.address,
                            "netmask": addr.netmask,
                            "broadcast": addr.broadcast
                        }
            
            return {
                "local_ip": local_ip,
                "hostname": socket.gethostname(),
                "interfaces": interfaces,
                "connections": len(psutil.net_connections())
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information"""
        try:
            return {
                "cpu_count": psutil.cpu_count(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "cpu_stats": psutil.cpu_stats()._asdict(),
                "cpu_times": psutil.cpu_times()._asdict()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        try:
            virtual_memory = psutil.virtual_memory()
            swap_memory = psutil.swap_memory()
            
            return {
                "virtual_memory": {
                    "total": virtual_memory.total,
                    "available": virtual_memory.available,
                    "used": virtual_memory.used,
                    "free": virtual_memory.free,
                    "percent": virtual_memory.percent
                },
                "swap_memory": {
                    "total": swap_memory.total,
                    "used": swap_memory.used,
                    "free": swap_memory.free,
                    "percent": swap_memory.percent
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information"""
        try:
            partitions = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    partitions.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "opts": partition.opts,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    })
                except:
                    continue
            
            return {
                "partitions": partitions,
                "io_counters": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get process information"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except:
                    continue
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return {
                "total_processes": len(processes),
                "top_processes": processes[:10]  # Top 10 by CPU usage
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_network_connections(self) -> List[Dict[str, Any]]:
        """Get active network connections"""
        try:
            connections = []
            for conn in psutil.net_connections():
                try:
                    connections.append({
                        "fd": conn.fd,
                        "family": conn.family,
                        "type": conn.type,
                        "laddr": conn.laddr._asdict() if conn.laddr else None,
                        "raddr": conn.raddr._asdict() if conn.raddr else None,
                        "status": conn.status,
                        "pid": conn.pid
                    })
                except:
                    continue
            return connections
        except Exception as e:
            return []
    
    def get_system_uptime(self) -> Dict[str, Any]:
        """Get system uptime information"""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            
            return {
                "boot_time": boot_time,
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": f"{days}d {hours}h {minutes}m {seconds}s"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_installed_software(self) -> List[Dict[str, Any]]:
        """Get list of installed software (Windows only)"""
        if platform.system() != "Windows":
            return []
        
        try:
            import winreg
            software_list = []
            
            registry_keys = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            
            for key_path in registry_keys:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        display_version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                        software_list.append({
                                            "name": display_name,
                                            "version": display_version,
                                            "registry_key": subkey_name
                                        })
                                    except:
                                        continue
                            except:
                                continue
                except:
                    continue
            
            return software_list
        except Exception as e:
            return []
    
    def get_system_performance(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent if platform.system() != "Windows" else psutil.disk_usage('C:\\').percent,
                "network_io": psutil.net_io_counters()._asdict() if psutil.net_io_counters() else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def get_system_summary(self) -> str:
        """Get a formatted system summary"""
        try:
            info = self.get_system_info()
            
            summary = f"""
System Summary:
==============
Hostname: {info['hostname']}
OS: {info['os']['system']} {info['os']['release']}
Architecture: {info['os']['architecture']}
Local IP: {info['network'].get('local_ip', 'Unknown')}

Hardware:
- CPU Cores: {info['hardware']['cpu_count']} (Logical: {info['hardware']['cpu_count_logical']})
- CPU Usage: {info['hardware']['cpu_percent']:.1f}%
- Memory: {self.format_bytes(info['memory']['virtual_memory']['total'])} 
  (Used: {info['memory']['virtual_memory']['percent']:.1f}%)

Storage:
- Total Disk Space: {self.format_bytes(sum(p['total'] for p in info['storage']['partitions']))}
- Free Disk Space: {self.format_bytes(sum(p['free'] for p in info['storage']['partitions']))}

Network:
- Active Connections: {info['network']['connections']}
- Network Interfaces: {len(info['network']['interfaces'])}

Processes: {info['processes']['total_processes']} running
"""
            return summary
        except Exception as e:
            return f"Error generating system summary: {e}" 