import os
import subprocess
import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional

class DynamicInstaller:
    def __init__(self, received_files_path: str = None):
        """Initialize dynamic installer with received files monitoring"""
        if received_files_path is None:
            # Determine correct path based on execution context
            if getattr(sys, 'frozen', False):
                # Running as compiled executable - use executable directory
                current_dir = Path(sys.executable).parent
            else:
                # Running as script - use script directory
                current_dir = Path(__file__).parent.parent
            self.received_files_path = current_dir / "received_files"
        else:
            self.received_files_path = Path(received_files_path)
        
        self.installers_path = self.received_files_path / "installers"
        self.installed_apps_file = self.received_files_path / "installed_apps.json"
        
        # Create directories if they don't exist
        self.installers_path.mkdir(parents=True, exist_ok=True)
        self.received_files_path.mkdir(parents=True, exist_ok=True)
        
        # Track installed files
        self.installed_apps = self._load_installed_apps()
        
        # Monitoring thread control
        self._monitoring = False
        self._monitor_thread = None
    
    def _load_installed_apps(self) -> Dict:
        """Load the list of already installed applications"""
        try:
            if self.installed_apps_file.exists():
                with open(self.installed_apps_file, 'r') as f:
                    return json.load(f)
            return {"installed_files": [], "last_check": 0}
        except Exception as e:
            print(f"Error loading installed apps: {e}")
            return {"installed_files": [], "last_check": 0}
    
    def _save_installed_apps(self):
        """Save the list of installed applications"""
        try:
            with open(self.installed_apps_file, 'w') as f:
                json.dump(self.installed_apps, f, indent=2)
        except Exception as e:
            print(f"Error saving installed apps: {e}")
    
    def get_installer_files(self) -> List[Path]:
        """Get all installer files in the received files directory"""
        installer_extensions = ['.exe', '.msi', '.msix']
        installer_files = []
        
        if self.installers_path.exists():
            for file_path in self.installers_path.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in installer_extensions:
                    installer_files.append(file_path)
        
        return installer_files
    
    def is_file_already_processed(self, file_path: Path) -> bool:
        """Check if a file has already been processed/installed"""
        file_info = {
            "name": file_path.name,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime
        }
        
        for installed_file in self.installed_apps.get("installed_files", []):
            if (installed_file.get("name") == file_info["name"] and 
                installed_file.get("size") == file_info["size"] and
                installed_file.get("modified") == file_info["modified"]):
                return True
        
        return False
    
    def mark_file_as_processed(self, file_path: Path, status: str = "installed"):
        """Mark a file as processed/installed"""
        file_info = {
            "name": file_path.name,
            "path": str(file_path),
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime,
            "processed_time": time.time(),
            "status": status
        }
        
        # Remove any existing entry for this file
        self.installed_apps["installed_files"] = [
            f for f in self.installed_apps.get("installed_files", [])
            if f.get("name") != file_path.name
        ]
        
        # Add new entry
        self.installed_apps["installed_files"].append(file_info)
        self.installed_apps["last_check"] = time.time()
        
        self._save_installed_apps()
    
    def install_file_silently(self, installer_path: Path) -> str:
        """Install a file using ONE silent installation attempt only
        Returns: 'success', 'manual_setup_needed', or 'check_manually'
        """
        try:
            # Silent install command
            cmd = f'"{str(installer_path)}" /SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART'

            print("Starting silent installation...")
            try:
                subprocess.run(cmd, shell=True, check=True)
                print("Installation completed successfully.")
                return 'success'
            except subprocess.CalledProcessError as e:
                print(f"Installation failed: {e}")
                return 'check_manually'
        except Exception as e:
            # Critical error - check manually
            print(f"An unexpected error occurred: {e}")
            return 'check_manually'
    
    def process_new_installers(self) -> Dict[str, str]:
        """Process only truly new installer files with immediate automatic installation"""
        results = {}
        installer_files = self.get_installer_files()
        
        if not installer_files:
            return results  # Silent return for empty directory
        
        # Only process files that haven't been processed yet
        new_files = [f for f in installer_files if not self.is_file_already_processed(f)]
        
        if not new_files:
            return results  # Silent return if no new files
        
        # Process new files with ONE ATTEMPT ONLY - no console output during normal operation
        for installer_file in new_files:
            # CRITICAL: Mark file as being processed BEFORE attempting installation
            # This prevents any possibility of multiple attempts
            self.mark_file_as_processed(installer_file, "processing")
            
            # Install the file with single attempt only
            install_result = self.install_file_silently(installer_file)
            
            if install_result == 'success':
                self.mark_file_as_processed(installer_file, "installed")
                results[installer_file.name] = "installed_successfully"
            elif install_result == 'manual_setup_needed':
                self.mark_file_as_processed(installer_file, "manual_setup_needed")
                results[installer_file.name] = "manual_setup_needed"
                # Show clear message once - manual setup needed
                print(f"🔧 {installer_file.name} - Manual setup needed")
            elif install_result == 'check_manually':
                self.mark_file_as_processed(installer_file, "check_manually")
                results[installer_file.name] = "check_manually"
                # Show clear message once - check and set up manually
                print(f"⚠️ {installer_file.name} - Check and set up manually")
            else:
                self.mark_file_as_processed(installer_file, "failed")
                results[installer_file.name] = "installation_failed"
        
        # Update last check time
        self.installed_apps["last_check"] = time.time()
        self._save_installed_apps()
        
        return results
    
    def start_monitoring(self, check_interval: int = 30):
        """Start monitoring the received files directory for new installers"""
        if self._monitoring:
            print("Monitoring is already running")
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            args=(check_interval,),
            daemon=True
        )
        self._monitor_thread.start()
        print(f"Started monitoring received files directory every {check_interval} seconds")
    
    def stop_monitoring(self):
        """Stop monitoring the received files directory"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print("Stopped monitoring received files directory")
    
    def _monitor_loop(self, check_interval: int):
        """Main monitoring loop - only processes truly new files"""
        last_check_time = time.time()
        
        while self._monitoring:
            try:
                # Only check for files modified after last check to avoid repeated processing
                current_time = time.time()
                new_files_found = False
                
                installer_files = self.get_installer_files()
                for installer_file in installer_files:
                    file_modified_time = installer_file.stat().st_mtime
                    
                    # Only process files modified after last check and not already processed
                    if (file_modified_time > last_check_time and 
                        not self.is_file_already_processed(installer_file)):
                        new_files_found = True
                        break
                
                if new_files_found:
                    # Process new files silently - no console output during normal operation
                    results = self.process_new_installers()
                    # Silent processing - results are handled internally
                # No logging during normal monitoring to prevent interruptions
                
                last_check_time = current_time
                
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
            
            # Wait for next check
            for _ in range(check_interval):
                if not self._monitoring:
                    break
                time.sleep(1)
    
    def get_installation_status(self) -> Dict:
        """Get the current installation status"""
        return {
            "total_processed": len(self.installed_apps.get("installed_files", [])),
            "last_check": self.installed_apps.get("last_check", 0),
            "monitoring_active": self._monitoring,
            "installers_path": str(self.installers_path),
            "files": self.installed_apps.get("installed_files", [])
        }
    
    def manual_install_check(self):
        """Manually trigger a check for new installers"""
        print("Manual installation check triggered")
        return self.process_new_installers()


# Convenience function for quick usage
def setup_auto_installer(received_files_path: str = None, start_monitoring: bool = True) -> DynamicInstaller:
    """Set up and optionally start the automatic installer"""
    installer = DynamicInstaller(received_files_path)
    
    # Process any existing files first
    print("Processing existing installer files...")
    results = installer.process_new_installers()
    
    if results:
        print("Initial processing results:")
        for filename, status in results.items():
            print(f"  {filename}: {status}")
    
    # Start monitoring if requested
    if start_monitoring:
        installer.start_monitoring()
    
    return installer


# Example usage
if __name__ == "__main__":
    # Set up the auto installer
    auto_installer = setup_auto_installer()
    
    try:
        # Keep the script running
        print("Auto installer is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(10)
            status = auto_installer.get_installation_status()
            print(f"Status: {status['total_processed']} files processed, monitoring: {status['monitoring_active']}")
    
    except KeyboardInterrupt:
        print("\nStopping auto installer...")
        auto_installer.stop_monitoring()
        print("Auto installer stopped.")
