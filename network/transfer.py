import socket
import os
import hashlib
import threading
import time
from typing import Dict, Any, Optional, Callable
from .protocol import MessageType

class FileTransfer:
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
        self.transfers: Dict[str, Dict[str, Any]] = {}
        self.transfer_callbacks: Dict[str, Callable] = {}
        
    def start_file_transfer(self, file_path: str, target_ip: str, 
                          protocol, transfer_id: str = None) -> bool:
        """Start a file transfer to a specific client"""
        if not os.path.exists(file_path):
            return False
            
        if transfer_id is None:
            transfer_id = f"{int(time.time())}_{os.path.basename(file_path)}"
            
        file_size = os.path.getsize(file_path)
        file_hash = self._calculate_file_hash(file_path)
        
        transfer_info = {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "file_size": file_size,
            "file_hash": file_hash,
            "target_ip": target_ip,
            "status": "initiating",
            "progress": 0,
            "start_time": time.time(),
            "protocol": protocol
        }
        
        self.transfers[transfer_id] = transfer_info
        
        # Send file transfer initiation message
        message_data = {
            "transfer_id": transfer_id,
            "file_name": transfer_info["file_name"],
            "file_size": file_size,
            "file_hash": file_hash,
            "is_installer": self._is_installer_file(file_path)
        }
        
        success = protocol.send_to_client(target_ip, MessageType.FILE_TRANSFER, message_data)
        
        if success:
            # Start transfer thread
            threading.Thread(target=self._transfer_file, 
                           args=(transfer_id,), 
                           daemon=True).start()
            return True
        else:
            del self.transfers[transfer_id]
            return False
    
    def _transfer_file(self, transfer_id: str):
        """Transfer file in chunks"""
        transfer_info = self.transfers.get(transfer_id)
        if not transfer_info:
            return
            
        try:
            file_path = transfer_info["file_path"]
            target_ip = transfer_info["target_ip"]
            protocol = transfer_info["protocol"]
            file_size = transfer_info["file_size"]
            
            transfer_info["status"] = "transferring"
            
            with open(file_path, 'rb') as file:
                bytes_sent = 0
                chunk_number = 0
                
                while bytes_sent < file_size:
                    chunk = file.read(self.chunk_size)
                    if not chunk:
                        break
                        
                    # Send chunk data
                    chunk_data = {
                        "transfer_id": transfer_id,
                        "chunk_number": chunk_number,
                        "chunk_data": chunk.hex(),
                        "is_final": (bytes_sent + len(chunk)) >= file_size
                    }
                    
                    success = protocol.send_to_client(target_ip, MessageType.FILE_TRANSFER, chunk_data)
                    
                    if not success:
                        transfer_info["status"] = "failed"
                        if transfer_id in self.transfer_callbacks:
                            self.transfer_callbacks[transfer_id]("failed", 0)
                        return
                    
                    bytes_sent += len(chunk)
                    chunk_number += 1
                    
                    # Update progress
                    progress = (bytes_sent / file_size) * 100
                    transfer_info["progress"] = progress
                    
                    if transfer_id in self.transfer_callbacks:
                        self.transfer_callbacks[transfer_id]("progress", progress)
                    
                    time.sleep(0.01)  # Small delay to prevent overwhelming
                
                transfer_info["status"] = "completed"
                transfer_info["end_time"] = time.time()
                
                if transfer_id in self.transfer_callbacks:
                    self.transfer_callbacks[transfer_id]("completed", 100)
                    
        except Exception as e:
            print(f"Error transferring file {transfer_id}: {e}")
            transfer_info["status"] = "failed"
            if transfer_id in self.transfer_callbacks:
                self.transfer_callbacks[transfer_id]("failed", 0)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _is_installer_file(self, file_path: str) -> bool:
        """Check if file is an installer"""
        installer_extensions = ['.exe', '.msi', '.msix', '.appx']
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in installer_extensions
    
    def register_transfer_callback(self, transfer_id: str, callback: Callable):
        """Register callback for transfer status updates"""
        self.transfer_callbacks[transfer_id] = callback
    
    def get_transfer_status(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a transfer"""
        return self.transfers.get(transfer_id)
    
    def cancel_transfer(self, transfer_id: str):
        """Cancel an ongoing transfer"""
        if transfer_id in self.transfers:
            self.transfers[transfer_id]["status"] = "cancelled"
            if transfer_id in self.transfer_callbacks:
                self.transfer_callbacks[transfer_id]("cancelled", 0)

class FileReceiver:
    def __init__(self, base_dir: str = "received_files"):
        self.base_dir = base_dir
        self.receiving_files: Dict[str, Dict[str, Any]] = {}
        self.receive_callbacks: Dict[str, Callable] = {}
        
        # Create base directory
        os.makedirs(base_dir, exist_ok=True)
    
    def handle_file_transfer_init(self, data: Dict[str, Any], protocol) -> bool:
        """Handle file transfer initiation from server"""
        transfer_id = data.get("transfer_id")
        file_name = data.get("file_name")
        file_size = data.get("file_size")
        file_hash = data.get("file_hash")
        is_installer = data.get("is_installer", False)
        
        # Create unique filename to avoid conflicts
        timestamp = int(time.time())
        unique_filename = f"{timestamp}_{file_name}"
        
        # Determine storage directory
        if is_installer:
            storage_dir = os.path.join(self.base_dir, "installers")
        else:
            storage_dir = os.path.join(self.base_dir, "files")
        
        os.makedirs(storage_dir, exist_ok=True)
        file_path = os.path.join(storage_dir, unique_filename)
        
        receive_info = {
            "file_path": file_path,
            "file_name": file_name,
            "file_size": file_size,
            "file_hash": file_hash,
            "is_installer": is_installer,
            "status": "receiving",
            "progress": 0,
            "start_time": time.time(),
            "chunks_received": 0,
            "bytes_received": 0
        }
        
        self.receiving_files[transfer_id] = receive_info
        
        # Send acknowledgment
        ack_data = {
            "transfer_id": transfer_id,
            "status": "ready"
        }
        protocol.send_message(MessageType.ACKNOWLEDGMENT, ack_data)
        
        return True
    
    def handle_file_chunk(self, data: Dict[str, Any], protocol) -> bool:
        """Handle incoming file chunk"""
        transfer_id = data.get("transfer_id")
        chunk_number = data.get("chunk_number")
        chunk_data_hex = data.get("chunk_data")
        is_final = data.get("is_final", False)
        
        receive_info = self.receiving_files.get(transfer_id)
        if not receive_info:
            return False
        
        try:
            # Convert hex data back to bytes
            chunk_data = bytes.fromhex(chunk_data_hex)
            
            # Write chunk to file
            mode = "wb" if chunk_number == 0 else "ab"
            with open(receive_info["file_path"], mode) as file:
                file.write(chunk_data)
            
            receive_info["bytes_received"] += len(chunk_data)
            receive_info["chunks_received"] += 1
            
            # Calculate progress
            progress = (receive_info["bytes_received"] / receive_info["file_size"]) * 100
            receive_info["progress"] = progress
            
            # Send chunk acknowledgment
            ack_data = {
                "transfer_id": transfer_id,
                "chunk_number": chunk_number,
                "status": "received"
            }
            protocol.send_message(MessageType.ACKNOWLEDGMENT, ack_data)
            
            if transfer_id in self.receive_callbacks:
                self.receive_callbacks[transfer_id]("progress", progress)
            
            if is_final:
                # Verify file hash
                if self._verify_file_hash(receive_info["file_path"], receive_info["file_hash"]):
                    receive_info["status"] = "completed"
                    receive_info["end_time"] = time.time()
                    
                    if transfer_id in self.receive_callbacks:
                        self.receive_callbacks[transfer_id]("completed", 100)
                else:
                    receive_info["status"] = "hash_mismatch"
                    if transfer_id in self.receive_callbacks:
                        self.receive_callbacks[transfer_id]("hash_mismatch", 0)
            
            return True
            
        except Exception as e:
            print(f"Error handling file chunk: {e}")
            receive_info["status"] = "failed"
            if transfer_id in self.receive_callbacks:
                self.receive_callbacks[transfer_id]("failed", 0)
            return False
    
    def _verify_file_hash(self, file_path: str, expected_hash: str) -> bool:
        """Verify file hash matches expected hash"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            actual_hash = hash_sha256.hexdigest()
            return actual_hash == expected_hash
        except:
            return False
    
    def register_receive_callback(self, transfer_id: str, callback: Callable):
        """Register callback for receive status updates"""
        self.receive_callbacks[transfer_id] = callback
    
    def get_receive_status(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a file receive operation"""
        return self.receiving_files.get(transfer_id)
    
    def get_received_files(self) -> list:
        """Get list of all received files"""
        files = []
        for root, dirs, filenames in os.walk(self.base_dir):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                files.append({
                    "path": file_path,
                    "name": filename,
                    "size": os.path.getsize(file_path),
                    "type": "installer" if "installers" in file_path else "file"
                })
        return files 