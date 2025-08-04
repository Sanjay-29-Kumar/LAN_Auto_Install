import os
import shutil
import time
from typing import List, Dict, Any
from datetime import datetime

class FileManager:
    def __init__(self, base_dir: str = "received_files"):
        self.base_dir = base_dir
        self.files_dir = os.path.join(base_dir, "files")
        self.installers_dir = os.path.join(base_dir, "installers")
        self.temp_dir = os.path.join(base_dir, "temp")
        
        # Create directory structure
        self._create_directories()
    
    def _create_directories(self):
        """Create the directory structure"""
        directories = [self.base_dir, self.files_dir, self.installers_dir, self.temp_dir]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def organize_file(self, file_path: str, server_ip: str, file_type: str = "file") -> Dict[str, Any]:
        """Organize a received file into the appropriate directory"""
        if not os.path.exists(file_path):
            return {"success": False, "error": "File does not exist"}
        
        try:
            # Create server-specific directory
            server_dir = os.path.join(
                self.installers_dir if file_type == "installer" else self.files_dir,
                server_ip
            )
            os.makedirs(server_dir, exist_ok=True)
            
            # Generate unique filename
            original_name = os.path.basename(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{timestamp}_{original_name}"
            
            # Move file to organized location
            destination = os.path.join(server_dir, unique_name)
            shutil.move(file_path, destination)
            
            # Create metadata file
            metadata = {
                "original_name": original_name,
                "server_ip": server_ip,
                "received_time": datetime.now().isoformat(),
                "file_type": file_type,
                "file_size": os.path.getsize(destination),
                "file_path": destination
            }
            
            metadata_path = destination + ".meta"
            self._save_metadata(metadata_path, metadata)
            
            return {
                "success": True,
                "file_path": destination,
                "metadata": metadata
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _save_metadata(self, metadata_path: str, metadata: Dict[str, Any]):
        """Save metadata to file"""
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self, metadata_path: str) -> Dict[str, Any]:
        """Load metadata from file"""
        import json
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def get_organized_files(self) -> List[Dict[str, Any]]:
        """Get list of all organized files with metadata"""
        files = []
        
        # Scan files directory
        for root, dirs, filenames in os.walk(self.files_dir):
            for filename in filenames:
                if not filename.endswith('.meta'):
                    file_path = os.path.join(root, filename)
                    metadata_path = file_path + ".meta"
                    
                    metadata = self._load_metadata(metadata_path)
                    if not metadata:
                        # Create basic metadata if missing
                        metadata = {
                            "original_name": filename,
                            "server_ip": os.path.basename(os.path.dirname(file_path)),
                            "received_time": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                            "file_type": "file",
                            "file_size": os.path.getsize(file_path),
                            "file_path": file_path
                        }
                    
                    files.append(metadata)
        
        # Scan installers directory
        for root, dirs, filenames in os.walk(self.installers_dir):
            for filename in filenames:
                if not filename.endswith('.meta'):
                    file_path = os.path.join(root, filename)
                    metadata_path = file_path + ".meta"
                    
                    metadata = self._load_metadata(metadata_path)
                    if not metadata:
                        metadata = {
                            "original_name": filename,
                            "server_ip": os.path.basename(os.path.dirname(file_path)),
                            "received_time": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                            "file_type": "installer",
                            "file_size": os.path.getsize(file_path),
                            "file_path": file_path
                        }
                    
                    files.append(metadata)
        
        return files
    
    def get_files_by_server(self, server_ip: str) -> List[Dict[str, Any]]:
        """Get files received from a specific server"""
        all_files = self.get_organized_files()
        return [file for file in all_files if file.get("server_ip") == server_ip]
    
    def get_files_by_type(self, file_type: str) -> List[Dict[str, Any]]:
        """Get files by type (file or installer)"""
        all_files = self.get_organized_files()
        return [file for file in all_files if file.get("file_type") == file_type]
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file and its metadata"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            
            metadata_path = file_path + ".meta"
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
            
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    def move_file(self, file_path: str, new_location: str) -> bool:
        """Move a file to a new location"""
        try:
            if os.path.exists(file_path):
                shutil.move(file_path, new_location)
                
                # Move metadata file if it exists
                metadata_path = file_path + ".meta"
                if os.path.exists(metadata_path):
                    shutil.move(metadata_path, new_location + ".meta")
                
                return True
        except Exception as e:
            print(f"Error moving file {file_path}: {e}")
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage information"""
        total_size = 0
        file_count = 0
        installer_count = 0
        
        for root, dirs, filenames in os.walk(self.base_dir):
            for filename in filenames:
                if not filename.endswith('.meta'):
                    file_path = os.path.join(root, filename)
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    file_count += 1
                    
                    if "installers" in file_path:
                        installer_count += 1
        
        return {
            "total_size": total_size,
            "total_files": file_count,
            "installer_count": installer_count,
            "file_count": file_count - installer_count,
            "base_directory": self.base_dir
        }
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            if os.path.exists(self.temp_dir):
                for filename in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
        except Exception as e:
            print(f"Error cleaning temp files: {e}")
    
    def export_file_list(self, export_path: str) -> bool:
        """Export list of all files to CSV"""
        try:
            import csv
            files = self.get_organized_files()
            
            with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['original_name', 'server_ip', 'received_time', 'file_type', 'file_size', 'file_path']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for file_info in files:
                    writer.writerow(file_info)
            
            return True
        except Exception as e:
            print(f"Error exporting file list: {e}")
            return False 