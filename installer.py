"""
Software installation engine for LAN Software Automation Installation System
"""

import os
import sys
import subprocess
import platform
import zipfile
import tempfile
import shutil
import time
from pathlib import Path
import config

class SoftwareInstaller:
    """Handles software installation across different platforms"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.install_log = []
        
    def install_software(self, file_path):
        """Install software or copy file based on file type and platform"""
        try:
            file_extension = Path(file_path).suffix.lower()
            filename = os.path.basename(file_path)
            
            # Check if it's an installer file
            installer_extensions = ['.exe', '.msi', '.deb', '.rpm', '.sh']
            if file_extension in installer_extensions:
                # Handle as installer
                if file_extension in ['.exe', '.msi']:
                    return self._install_windows(file_path)
                elif file_extension == '.deb':
                    return self._install_debian(file_path)
                elif file_extension == '.rpm':
                    return self._install_rpm(file_path)
                elif file_extension == '.zip':
                    return self._install_zip(file_path)
                elif file_extension == '.tar.gz':
                    return self._install_targz(file_path)
                else:
                    return self._install_generic(file_path)
            else:
                # Handle as regular file - copy to user's documents folder
                return self._copy_file(file_path, filename)
                
        except Exception as e:
            self._log_error(f"Installation failed: {str(e)}")
            return False
    
    def _install_windows(self, file_path):
        """Install Windows software (.exe, .msi)"""
        try:
            if file_path.endswith('.msi'):
                # Install MSI silently
                cmd = ['msiexec', '/i', file_path, '/quiet', '/norestart']
            else:
                # Install EXE silently (if supported)
                cmd = [file_path, '/S', '/quiet', '/silent']
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self._log_success(f"Windows software installed: {os.path.basename(file_path)}")
                return True
            else:
                self._log_error(f"Windows installation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._log_error("Windows installation timed out")
            return False
        except Exception as e:
            self._log_error(f"Windows installation error: {str(e)}")
            return False
    
    def _install_debian(self, file_path):
        """Install Debian/Ubuntu package (.deb)"""
        try:
            # Install deb package
            cmd = ['sudo', 'dpkg', '-i', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self._log_success(f"Debian package installed: {os.path.basename(file_path)}")
                return True
            else:
                # Try to fix dependencies
                fix_cmd = ['sudo', 'apt-get', 'install', '-f', '-y']
                subprocess.run(fix_cmd, capture_output=True, text=True, timeout=60)
                
                # Try installation again
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    self._log_success(f"Debian package installed with dependency fix: {os.path.basename(file_path)}")
                    return True
                else:
                    self._log_error(f"Debian installation failed: {result.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            self._log_error("Debian installation timed out")
            return False
        except Exception as e:
            self._log_error(f"Debian installation error: {str(e)}")
            return False
    
    def _install_rpm(self, file_path):
        """Install RPM package (.rpm)"""
        try:
            # Install RPM package
            cmd = ['sudo', 'rpm', '-i', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self._log_success(f"RPM package installed: {os.path.basename(file_path)}")
                return True
            else:
                # Try with yum/dnf
                cmd = ['sudo', 'yum', 'install', '-y', file_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    self._log_success(f"RPM package installed via yum: {os.path.basename(file_path)}")
                    return True
                else:
                    self._log_error(f"RPM installation failed: {result.stderr}")
                    return False
                    
        except subprocess.TimeoutExpired:
            self._log_error("RPM installation timed out")
            return False
        except Exception as e:
            self._log_error(f"RPM installation error: {str(e)}")
            return False
    
    def _install_zip(self, file_path):
        """Install software from ZIP archive"""
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract ZIP file
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Look for installer or executable
                extracted_files = os.listdir(temp_dir)
                
                for file in extracted_files:
                    file_path_in_temp = os.path.join(temp_dir, file)
                    
                    if os.path.isfile(file_path_in_temp):
                        if file.endswith('.exe') or file.endswith('.msi'):
                            # Found Windows installer
                            return self._install_windows(file_path_in_temp)
                        elif file.endswith('.deb'):
                            # Found Debian package
                            return self._install_debian(file_path_in_temp)
                        elif file.endswith('.rpm'):
                            # Found RPM package
                            return self._install_rpm(file_path_in_temp)
                        elif file.endswith('.sh'):
                            # Found shell script
                            return self._install_shell_script(file_path_in_temp)
                
                # If no installer found, try to run any executable
                for file in extracted_files:
                    file_path_in_temp = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path_in_temp) and os.access(file_path_in_temp, os.X_OK):
                        return self._install_generic(file_path_in_temp)
                
                self._log_error("No installer found in ZIP archive")
                return False
                
        except Exception as e:
            self._log_error(f"ZIP installation error: {str(e)}")
            return False
    
    def _install_targz(self, file_path):
        """Install software from tar.gz archive"""
        try:
            # Create temporary directory for extraction
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract tar.gz file
                cmd = ['tar', '-xzf', file_path, '-C', temp_dir]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode != 0:
                    self._log_error(f"Failed to extract tar.gz: {result.stderr}")
                    return False
                
                # Look for installer or executable
                extracted_files = os.listdir(temp_dir)
                
                for file in extracted_files:
                    file_path_in_temp = os.path.join(temp_dir, file)
                    
                    if os.path.isfile(file_path_in_temp):
                        if file.endswith('.sh'):
                            # Found shell script
                            return self._install_shell_script(file_path_in_temp)
                        elif os.access(file_path_in_temp, os.X_OK):
                            # Found executable
                            return self._install_generic(file_path_in_temp)
                
                self._log_error("No installer found in tar.gz archive")
                return False
                
        except Exception as e:
            self._log_error(f"tar.gz installation error: {str(e)}")
            return False
    
    def _install_shell_script(self, file_path):
        """Install software using shell script"""
        try:
            # Make script executable
            os.chmod(file_path, 0o755)
            
            # Run shell script
            cmd = ['bash', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self._log_success(f"Shell script executed successfully: {os.path.basename(file_path)}")
                return True
            else:
                self._log_error(f"Shell script failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._log_error("Shell script execution timed out")
            return False
        except Exception as e:
            self._log_error(f"Shell script error: {str(e)}")
            return False
    
    def _install_generic(self, file_path):
        """Install software using generic method"""
        try:
            # Make file executable if it's not already
            if not os.access(file_path, os.X_OK):
                os.chmod(file_path, 0o755)
            
            # Try to run the file
            cmd = [file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self._log_success(f"Generic software installed: {os.path.basename(file_path)}")
                return True
            else:
                self._log_error(f"Generic installation failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self._log_error("Generic installation timed out")
            return False
        except Exception as e:
            self._log_error(f"Generic installation error: {str(e)}")
            return False
    
    def _log_success(self, message):
        """Log successful installation"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[SUCCESS] {timestamp}: {message}"
        self.install_log.append(log_entry)
        print(log_entry)
    
    def _log_error(self, message):
        """Log installation error"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[ERROR] {timestamp}: {message}"
        self.install_log.append(log_entry)
        print(log_entry)
    
    def get_install_log(self):
        """Get installation log"""
        return self.install_log
    
    def clear_log(self):
        """Clear installation log"""
        self.install_log = []
    
    def _copy_file(self, file_path, filename):
        """Copy regular file to user's documents folder"""
        try:
            # Get user's documents folder
            if self.platform == 'windows':
                import winreg
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                        documents_path = winreg.QueryValueEx(key, "Personal")[0]
                except:
                    documents_path = os.path.expanduser("~/Documents")
            else:
                documents_path = os.path.expanduser("~/Documents")
            
            # Create LAN_Automation folder in Documents
            lan_folder = os.path.join(documents_path, "LAN_Automation")
            os.makedirs(lan_folder, exist_ok=True)
            
            # Copy file
            destination = os.path.join(lan_folder, filename)
            shutil.copy2(file_path, destination)
            
            self._log_success(f"File copied to: {destination}")
            return True
            
        except Exception as e:
            self._log_error(f"File copy failed: {str(e)}")
            return False
    
    def validate_file(self, file_path):
        """Validate if file can be installed"""
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        if not os.path.isfile(file_path):
            return False, "Path is not a file"
        
        file_size = os.path.getsize(file_path)
        if file_size > config.MAX_FILE_SIZE:
            return False, f"File too large ({file_size} bytes)"
        
        # Accept all file types now
        return True, "File is valid"

# Global installer instance
installer = SoftwareInstaller() 