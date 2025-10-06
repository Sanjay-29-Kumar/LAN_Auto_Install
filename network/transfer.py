"""
Handles the reliable, chunk-based file transfer over TCP.
"""

import socket
import json
import os
import threading
import time
import hashlib
from . import protocol

class FileSender(threading.Thread):
    """
    Sends a file to a client using a reliable, chunk-based protocol.
    """
    def __init__(self, client_ip, client_port, file_path, file_info, progress_callback=None, completion_callback=None):
        super().__init__()
        self.client_ip = client_ip
        self.client_port = client_port
        self.file_path = file_path
        self.file_info = file_info
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.sock = None
        self.running = True
        self.unacked_chunks = set()

    def run(self):
        try:
            self._connect()
            self._send_file()
        except Exception as e:
            print(f"Error sending file to {self.client_ip}: {e}")
            if self.completion_callback:
                self.completion_callback(self.file_info['name'], 'failed')
        finally:
            self._close()

    def _connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        self.sock.connect((self.client_ip, self.client_port))

    def _send_file(self):
        MAX_RETRIES = 5
        RETRY_DELAY = 5  # seconds
        
        file_size = os.path.getsize(self.file_path)
        
        # Select chunk size based on file size with more conservative sizes
        if file_size < 50 * 1024 * 1024:  # < 50MB
            chunk_size = protocol.CHUNK_SIZE_SMALL // 2  # Smaller chunks for better reliability
        elif file_size < 500 * 1024 * 1024:  # < 500MB
            chunk_size = protocol.CHUNK_SIZE_MEDIUM // 2
        else:  # >= 500MB
            chunk_size = protocol.CHUNK_SIZE_LARGE // 2
            
        total_chunks = (file_size + chunk_size - 1) // chunk_size

        # Prepare header with additional metadata
        header = {
            'type': protocol.MSG_TYPE_FILE_HEADER,
            'file_name': self.file_info['name'],
            'file_size': file_size,
            'total_chunks': total_chunks,
            'chunk_size': chunk_size,
            'category': self.file_info.get('category', 'other'),
            'checksum': self._calculate_file_checksum()
        }

        # Send header with retries
        for retry in range(MAX_RETRIES):
            try:
                self._send_message(header)
                ack = self._receive_message(timeout=30)  # Longer timeout for header ack
                if ack and ack.get('type') == protocol.MSG_TYPE_FILE_HEADER_ACK and ack.get('status') == 'ok':
                    break
            except Exception as e:
                if retry == MAX_RETRIES - 1:
                    raise Exception(f"File transfer initialization failed after {MAX_RETRIES} attempts: {e}")
                time.sleep(RETRY_DELAY)
        else:
            raise Exception("File transfer rejected by client")

        failed_chunks = set()
        with open(self.file_path, 'rb') as f:
            for i in range(total_chunks):
                if not self.running:
                    self._send_message({'type': protocol.MSG_TYPE_CANCEL_TRANSFER})
                    break

                chunk_data = f.read(chunk_size)
                chunk_message = {
                    'type': protocol.MSG_TYPE_FILE_CHUNK,
                    'chunk_index': i,
                    'size': len(chunk_data),
                    'checksum': self._calculate_chunk_checksum(chunk_data)
                }

                # Retry failed chunks
                retry_count = 0
                while retry_count < MAX_RETRIES:
                    try:
                        if i in failed_chunks:
                            f.seek(i * chunk_size)
                            chunk_data = f.read(chunk_size)
                        
                        self._send_message(chunk_message, chunk_data)
                        self.unacked_chunks.add(i)

                        # More conservative window size for better reliability
                        window_size = 2 if file_size < 50 * 1024 * 1024 else (3 if file_size < 500 * 1024 * 1024 else 4)
                        if len(self.unacked_chunks) >= window_size:
                            failed = self._wait_for_acks(timeout=60)  # Longer timeout for acks
                            if failed:
                                failed_chunks.update(failed)
                                continue
                        
                        if i in failed_chunks:
                            failed_chunks.remove(i)
                        break
                        
                    except Exception as e:
                        print(f"Error sending chunk {i}: {e}")
                        retry_count += 1
                        if retry_count < MAX_RETRIES:
                            time.sleep(RETRY_DELAY * (retry_count + 1))  # Exponential backoff
                        else:
                            raise Exception(f"Failed to send chunk {i} after {MAX_RETRIES} attempts")

                if self.progress_callback:
                    self.progress_callback(self.file_info['name'], (i + 1) / total_chunks * 100)

        # Wait for all remaining acks with retries
        retry_count = 0
        while (self.unacked_chunks or failed_chunks) and self.running:
            try:
                failed = self._wait_for_acks(timeout=60)
                if failed:
                    failed_chunks.update(failed)
                if not failed and not self.unacked_chunks:
                    break
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    raise Exception("Failed to get acknowledgment for all chunks")
                time.sleep(RETRY_DELAY * (retry_count + 1))
            except Exception as e:
                if retry_count >= MAX_RETRIES:
                    raise Exception(f"Failed to complete file transfer: {e}")

        if self.running:
            # Send end message with retries
            for retry in range(MAX_RETRIES):
                try:
                    self._send_message({'type': protocol.MSG_TYPE_FILE_END})
                    ack = self._receive_message(timeout=30)
                    if ack and ack.get('type') == protocol.MSG_TYPE_FILE_COMPLETE_ACK:
                        break
                except Exception:
                    if retry == MAX_RETRIES - 1:
                        raise Exception("Failed to confirm file transfer completion")
                    time.sleep(RETRY_DELAY)
                    
    def _calculate_file_checksum(self):
        """Calculate SHA-256 checksum of the file"""
        try:
            import hashlib
            sha256_hash = hashlib.sha256()
            with open(self.file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return None
            
    def _calculate_chunk_checksum(self, chunk_data):
        """Calculate SHA-256 checksum of a chunk"""
        try:
            return hashlib.sha256(chunk_data).hexdigest()
        except Exception:
            return None
            if self.completion_callback:
                self.completion_callback(self.file_info['name'], 'completed')

    def _wait_for_acks(self):
        try:
            self.sock.settimeout(protocol.ACK_TIMEOUT)
            ack = self._receive_message()
            if ack and ack.get('type') == protocol.MSG_TYPE_CHUNK_ACK:
                chunk_index = ack.get('chunk_index')
                if chunk_index in self.unacked_chunks:
                    self.unacked_chunks.remove(chunk_index)
        except socket.timeout:
            # Resend the oldest unacked chunk
            oldest_unacked = min(self.unacked_chunks)
            self._resend_chunk(oldest_unacked)

    def _resend_chunk(self, chunk_index):
        with open(self.file_path, 'rb') as f:
            f.seek(chunk_index * protocol.CHUNK_SIZE)
            chunk_data = f.read(protocol.CHUNK_SIZE)
            chunk_message = {
                'type': protocol.MSG_TYPE_FILE_CHUNK,
                'chunk_index': chunk_index,
                'size': len(chunk_data)
            }
            self._send_message(chunk_message, chunk_data)

    def _send_message(self, message, data=b''):
        json_message = json.dumps(message).encode('utf-8')
        self.sock.sendall(len(json_message).to_bytes(4, 'big') + json_message + data)

    def _receive_message(self):
        try:
            raw_len = self.sock.recv(4)
            if not raw_len:
                return None
            msg_len = int.from_bytes(raw_len, 'big')
            return json.loads(self.sock.recv(msg_len).decode('utf-8'))
        except (socket.timeout, json.JSONDecodeError, ConnectionResetError):
            return None

    def stop(self):
        self.running = False

    def _close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                print(f"Error closing sender socket: {e}")
            finally:
                self.sock = None


class FileReceiver(threading.Thread):
    """
    Receives a file from a server using a reliable, chunk-based protocol.
    """
    def __init__(self, sock, addr, received_files_dir, completion_callback=None, progress_callback=None):
        super().__init__()
        self.sock = sock
        self.addr = addr
        self.received_files_dir = received_files_dir
        self.completion_callback = completion_callback
        self.progress_callback = progress_callback
        self.running = True
        self.file_handle = None
        self.file_path = None
        self.total_chunks = 0
        self.received_chunks = set()

    def run(self):
        try:
            self._handle_transfer()
        except Exception as e:
            print(f"Error receiving file from {self.addr[0]}: {e}")
        finally:
            self._close()

    def _handle_transfer(self):
        # Receive file header
        header_data = self._receive_message_and_data(protocol.BUFFER_SIZE)
        if not header_data:
            return
        
        header, _ = header_data
        if not header or header.get('type') != protocol.MSG_TYPE_FILE_HEADER:
            return

        file_name = header['file_name']
        file_size = header['file_size']
        self.total_chunks = header['total_chunks']
        self.chunk_size = header.get('chunk_size', protocol.CHUNK_SIZE_SMALL)
        category = header.get('category', 'other')
        
        # Set socket buffer size based on chunk size and network type
        if self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF) < self.chunk_size * 2:
            try:
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.chunk_size * 2)
            except Exception as e:
                print(f"Could not set socket buffer size: {e}")

        # Create categorized storage directory
        if category == 'installer':
            storage_dir = os.path.join(self.received_files_dir, "installers")
        elif category == 'document':
            storage_dir = os.path.join(self.received_files_dir, "documents")
        elif category == 'media':
            storage_dir = os.path.join(self.received_files_dir, "media")
        elif category == 'archive':
            storage_dir = os.path.join(self.received_files_dir, "archives")
        else:
            storage_dir = os.path.join(self.received_files_dir, "others")
        
        os.makedirs(storage_dir, exist_ok=True)
        self.file_path = os.path.join(storage_dir, file_name)

        # Send acknowledgment to start transfer
        self._send_message({'type': protocol.MSG_TYPE_FILE_HEADER_ACK, 'status': 'ok'})

        # Open file for writing in binary mode
        self.file_handle = open(self.file_path, 'wb')
        
        while len(self.received_chunks) < self.total_chunks and self.running:
            try:
                # Adjust timeout based on chunk size and network conditions
                base_timeout = protocol.ACK_TIMEOUT * 2
                if self.chunk_size > protocol.CHUNK_SIZE_MEDIUM:
                    base_timeout *= 2  # Double timeout for large chunks
                self.sock.settimeout(base_timeout)
                
                # Use chunk size as the base for receive buffer
                message_data = self._receive_message_and_data(self.chunk_size + 1024)  # Buffer for message + chunk
                if not message_data:
                    print("Connection lost while receiving file.")
                    break
                
                message, data = message_data
                msg_type = message.get('type')

                if msg_type == protocol.MSG_TYPE_FILE_CHUNK:
                    chunk_index = message['chunk_index']
                    
                    # This is a simple implementation. A more robust one would seek and write.
                    # For now, we assume chunks arrive mostly in order.
                    # A better implementation would handle out-of-order chunks by writing to temporary files
                    # or seeking to the correct position in the output file.
                    if chunk_index not in self.received_chunks:
                        self.file_handle.seek(chunk_index * protocol.CHUNK_SIZE)
                        self.file_handle.write(data)
                        self.received_chunks.add(chunk_index)
                    
                    if self.progress_callback:
                        progress = (len(self.received_chunks) / self.total_chunks) * 100
                        self.progress_callback(file_name, self.addr[0], progress)

                    # Acknowledge receipt of the chunk
                    ack_message = {'type': protocol.MSG_TYPE_CHUNK_ACK, 'chunk_index': chunk_index}
                    self._send_message(ack_message)

                elif msg_type == protocol.MSG_TYPE_FILE_END:
                    break # Server signaled end of transfer
                
                elif msg_type == protocol.MSG_TYPE_CANCEL_TRANSFER:
                    self.running = False
                    print(f"Transfer of {file_name} cancelled by server.")
                    break

            except socket.timeout:
                print("Socket timed out waiting for chunk. Requesting retransmit if possible.")
                # A more robust implementation would request missing chunks here.
                continue
            except Exception as e:
                print(f"Error during chunk reception: {e}")
                break
        
        if len(self.received_chunks) == self.total_chunks:
            print(f"File {file_name} received successfully.")
            if self.completion_callback:
                self.completion_callback(file_name, 'completed', self.file_path)
        else:
            print(f"File {file_name} transfer incomplete. Received {len(self.received_chunks)}/{self.total_chunks} chunks.")
            if self.completion_callback:
                self.completion_callback(file_name, 'failed', self.file_path)


    def _send_message(self, message):
        json_message = json.dumps(message).encode('utf-8')
        self.sock.sendall(len(json_message).to_bytes(4, 'big') + json_message)

    def _receive_message_and_data(self, max_data_size):
        try:
            raw_len = self.sock.recv(4)
            if not raw_len:
                return None, None
            msg_len = int.from_bytes(raw_len, 'big')
            json_message = self.sock.recv(msg_len).decode('utf-8')
            message = json.loads(json_message)
            
            data = b''
            if message.get('type') == protocol.MSG_TYPE_FILE_CHUNK:
                data_len = message['size']
                while len(data) < data_len:
                    packet = self.sock.recv(min(data_len - len(data), max_data_size))
                    if not packet:
                        break
                    data += packet
            return message, data
        except (socket.timeout, json.JSONDecodeError, ConnectionResetError, ValueError) as e:
            print(f"Error receiving message and data: {e}")
            return None, None

    def _close(self):
        if self.file_handle:
            self.file_handle.close()
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                print(f"Error closing receiver socket: {e}")
            finally:
                self.sock = None
