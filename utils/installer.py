import os
import subprocess
import threading
import time
import platform
from typing import Dict, Any, Optional, Callable
import winreg
import psutil

class SoftwareInstaller:
    def __init__(self):
        self.installations: Dict[str, Dict[str, Any]] = {}
        self.install_callbacks: Dict[str, Callable] = {}
        
    def install_software(self, installer_path: str, installation_id: str = None) -> bool:
        """Install software silently"""
        if not os.path.exists(installer_path):
            return False
            
        if installation_id is None:
            installation_id = f"install_{int(time.time())}"
            
        file_ext = os.path.splitext(installer_path)[1].lower()
        
        installation_info = {
            "installer_path": installer_path,
            "file_name": os.path.basename(installer_path),
            "status": "initiating",
            "progress": 0,
            "start_time": time.time(),
            "file_ext": file_ext
        }
        
        self.installations[installation_id] = installation_info
        
        # Start installation thread
        threading.Thread(target=self._run_installation, 
                       args=(installation_id,), 
                       daemon=True).start()
        
        return True
    
    def _run_installation(self, installation_id: str):
        """Run the installation process"""
        installation_info = self.installations.get(installation_id)
        if not installation_info:
            return
            
        try:
            installer_path = installation_info["installer_path"]
            file_ext = installation_info["file_ext"]
            
            installation_info["status"] = "installing"
            
            # Determine installation command based on file type
            if file_ext == '.exe':
                cmd = self._get_exe_install_command(installer_path)
            elif file_ext == '.msi':
                cmd = self._get_msi_install_command(installer_path)
            elif file_ext == '.msix':
                cmd = self._get_msix_install_command(installer_path)
            else:
                installation_info["status"] = "unsupported_format"
                if installation_id in self.install_callbacks:
                    self.install_callbacks[installation_id]("unsupported_format", 0)
                return
            
            # Run installation
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Monitor installation progress
            start_time = time.time()
            while process.poll() is None:
                # Simulate progress (actual progress monitoring would require specific installer support)
                elapsed = time.time() - start_time
                if elapsed > 30:  # Assume installation takes at least 30 seconds
                    progress = min(90, (elapsed - 30) * 2)  # Progress from 0 to 90%
                else:
                    progress = min(30, elapsed * 1)  # Initial progress
                
                installation_info["progress"] = progress
                
                if installation_id in self.install_callbacks:
                    self.install_callbacks[installation_id]("progress", progress)
                
                time.sleep(1)
            
            # Check installation result
            return_code = process.returncode
            if return_code == 0:
                installation_info["status"] = "completed"
                installation_info["progress"] = 100
                installation_info["end_time"] = time.time()
                
                if installation_id in self.install_callbacks:
                    self.install_callbacks[installation_id]("completed", 100)
            else:
                installation_info["status"] = "failed"
                installation_info["error_code"] = return_code
                
                if installation_id in self.install_callbacks:
                    self.install_callbacks[installation_id]("failed", 0)
                    
        except Exception as e:
            print(f"Error during installation {installation_id}: {e}")
            installation_info["status"] = "failed"
            installation_info["error"] = str(e)
            
            if installation_id in self.install_callbacks:
                self.install_callbacks[installation_id]("failed", 0)
    
    def _get_exe_install_command(self, installer_path: str) -> str:
        """Get command for EXE installer"""
        # Common silent installation switches for different installers
        silent_switches = [
            "/S", "/silent", "/quiet", "/VERYSILENT", "/sp-", "/suppressmsgboxes",
            "-q", "-s", "--silent", "--quiet", "/passive", "/norestart"
        ]
        
        # Try different silent switches
        for switch in silent_switches:
            cmd = f'"{installer_path}" {switch}'
            if self._test_installer_support(installer_path, switch):
                return cmd
        
        # Fallback to basic silent installation
        return f'"{installer_path}" /S'
    
    def _get_msi_install_command(self, installer_path: str) -> str:
        """Get command for MSI installer"""
        return f'msiexec /i "{installer_path}" /quiet /norestart /log "{installer_path}.log"'
    
    def _get_msix_install_command(self, installer_path: str) -> str:
        """Get command for MSIX installer"""
        return f'powershell -Command "Add-AppxPackage -Path \'{installer_path}\' -ErrorAction Stop"'
    
    def _test_installer_support(self, installer_path: str, switch: str) -> bool:
        """Test if installer supports a specific silent switch"""
        try:
            # Quick test to see if installer accepts the switch
            cmd = f'"{installer_path}" {switch} /?'
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return result.returncode != 1  # Most installers return 1 for invalid switches
        except:
            return False
    
    def register_install_callback(self, installation_id: str, callback: Callable):
        """Register callback for installation status updates"""
        self.install_callbacks[installation_id] = callback
    
    def get_installation_status(self, installation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an installation"""
        return self.installations.get(installation_id)
    
    def cancel_installation(self, installation_id: str):
        """Cancel an ongoing installation"""
        if installation_id in self.installations:
            self.installations[installation_id]["status"] = "cancelled"
            if installation_id in self.install_callbacks:
                self.install_callbacks[installation_id]("cancelled", 0)
    
    def get_installed_software(self) -> list:
        """Get list of installed software"""
        installed_software = []
        
        try:
            # Check Windows registry for installed software
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
                                        installed_software.append({
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
                    
        except Exception as e:
            print(f"Error getting installed software: {e}")
        
        return installed_software
    
    def is_software_installed(self, software_name: str) -> bool:
        """Check if specific software is installed"""
        installed_software = self.get_installed_software()
        return any(software["name"].lower() == software_name.lower() 
                  for software in installed_software)
    
    def uninstall_software(self, software_name: str) -> bool:
        """Uninstall software silently"""
        try:
            # Find uninstall string in registry
            uninstall_string = self._get_uninstall_string(software_name)
            if uninstall_string:
                cmd = f'{uninstall_string} /S'
                subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                return True
        except Exception as e:
            print(f"Error uninstalling software: {e}")
        return False
    
    def _get_uninstall_string(self, software_name: str) -> Optional[str]:
        """Get uninstall string for software from registry"""
        try:
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
                                        if display_name.lower() == software_name.lower():
                                            uninstall_string = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                            return uninstall_string
                                    except:
                                        continue
                            except:
                                continue
                except:
                    continue
        except Exception as e:
            print(f"Error getting uninstall string: {e}")
        
        return None 