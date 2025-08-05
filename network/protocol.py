
import socket
import json
import struct
import threading
import time
import os
from typing import Dict, Any, Optional, Callable
from enum import Enum
import hashlib

class MessageType(Enum):
    HANDSHAKE = "handshake"
    FILE_TRANSFER = "file_transfer"
    INSTALLATION_REQUEST = "installation_request"
    STATUS_UPDATE = "status_update"
    ACKNOWLEDGMENT = "acknowledgment"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"
    DISCOVERY = "discovery"
    DISCOVERY_RESPONSE = "discovery_response"

class NetworkProtocol:
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.clients: Dict[str, socket.socket] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.connection_callbacks: Dict[str, Callable] = {}

    def start_server(self):
        """Start the server socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(10)
            self.running = True

            # Start listening thread
            threading.Thread(target=self._accept_connections, daemon=True).start()
            print(f"Server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to start server: {e}")
            return False

    def stop_server(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        for client_socket in list(self.clients.values()):
            try:
                client_socket.close()
            except:
                pass
        self.clients.clear()

    def _accept_connections(self):
        """Accept incoming connections"""
        while self.running:
            try:
                if not self.socket:
                    break
                self.socket.settimeout(1.0)
                client_socket, address = self.socket.accept()
                client_ip = address[0]

                # Configure client socket
                client_socket.settimeout(60.0)
                client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                self.clients[client_ip] = client_socket
                print(f"Client connected: {client_ip}")

                # Start client handler thread
                threading.Thread(target=self._handle_client, 
                               args=(client_socket, client_ip), 
                               daemon=True).start()

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
                time.sleep(0.1)

    def _handle_client(self, client_socket: socket.socket, client_ip: str):
        """Handle communication with a client"""
        try:
            while self.running:
                try:
                    message = self._receive_message(client_socket)
                    if message:
                        self._process_message(message, client_ip)
                    else:
                        break
                except socket.timeout:
                    # Send ping to keep connection alive
                    self._send_message(client_socket, MessageType.PING, {})
                    continue
                except Exception as e:
                    print(f"Error handling client {client_ip}: {e}")
                    break
        except Exception as e:
            print(f"Client handler error: {e}")
        finally:
            if client_ip in self.clients:
                del self.clients[client_ip]
            try:
                client_socket.close()
            except:
                pass
            print(f"Client disconnected: {client_ip}")

    def _send_message(self, sock: socket.socket, message_type: MessageType, data: Dict[str, Any]):
        """Send a message to a socket"""
        try:
            message = {
                "type": message_type.value,
                "data": data,
                "timestamp": time.time()
            }
            message_bytes = json.dumps(message).encode('utf-8')
            message_length = struct.pack('!I', len(message_bytes))
            sock.send(message_length + message_bytes)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def _receive_message(self, sock: socket.socket) -> Optional[Dict[str, Any]]:
        """Receive a message from a socket"""
        try:
            # Receive message length
            sock.settimeout(30.0)
            length_data = sock.recv(4)
            if not length_data or len(length_data) != 4:
                return None

            message_length = struct.unpack('!I', length_data)[0]
            if message_length > 10 * 1024 * 1024:  # 10MB limit
                return None

            # Receive message data
            message_data = b""
            while len(message_data) < message_length:
                chunk = sock.recv(min(4096, message_length - len(message_data)))
                if not chunk:
                    return None
                message_data += chunk

            message = json.loads(message_data.decode('utf-8'))
            return message
        except socket.timeout:
            return None
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None

    def _process_message(self, message: Dict[str, Any], client_ip: str):
        """Process received message"""
        try:
            message_type_str = message.get("type")
            if message_type_str:
                try:
                    message_type = MessageType(message_type_str)
                    data = message.get("data", {})

                    if message_type in self.message_handlers:
                        self.message_handlers[message_type](data, client_ip)
                    else:
                        print(f"No handler for message type: {message_type}")
                except ValueError:
                    print(f"Unknown message type: {message_type_str}")

        except Exception as e:
            print(f"Error processing message: {e}")

    def send_to_client(self, client_ip: str, message_type: MessageType, data: Dict[str, Any]):
        """Send message to specific client"""
        if client_ip in self.clients:
            return self._send_message(self.clients[client_ip], message_type, data)
        return False

    def broadcast(self, message_type: MessageType, data: Dict[str, Any]):
        """Send message to all connected clients"""
        results = []
        for client_ip in list(self.clients.keys()):
            result = self.send_to_client(client_ip, message_type, data)
            results.append((client_ip, result))
        return results

    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register a message handler"""
        self.message_handlers[message_type] = handler

    def is_connected(self):
        """Check if server is running"""
        return self.running

class ClientProtocol:
    def __init__(self, server_host: str, server_port: int = 5000):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.connection_callback: Optional[Callable] = None
        self.running = False

    def connect(self) -> bool:
        """Connect to server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.server_host, self.server_port))
            self.socket.settimeout(60.0)
            self.connected = True
            self.running = True

            # Start listening thread
            threading.Thread(target=self._listen_for_messages, daemon=True).start()

            # Send handshake
            self.send_message(MessageType.HANDSHAKE, {
                "client_id": socket.gethostname(),
                "version": "1.0"
            })

            if self.connection_callback:
                self.connection_callback(True)

            return True
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            return False

    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.connection_callback:
            self.connection_callback(False)

    def _listen_for_messages(self):
        """Listen for incoming messages from server"""
        while self.running and self.connected:
            try:
                message = self._receive_message(self.socket)
                if message:
                    self._process_message(message)
                else:
                    break
            except Exception as e:
                if self.running:
                    print(f"Error listening for messages: {e}")
                break

        self.connected = False
        if self.connection_callback:
            self.connection_callback(False)

    def _send_message(self, message_type: MessageType, data: Dict[str, Any]):
        """Send message to server"""
        try:
            if not self.connected:
                return False
                
            message = {
                "type": message_type.value,
                "data": data,
                "timestamp": time.time()
            }
            message_bytes = json.dumps(message).encode('utf-8')
            message_length = struct.pack('!I', len(message_bytes))
            self.socket.send(message_length + message_bytes)
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect()
            return False

    def _receive_message(self, sock: socket.socket) -> Optional[Dict[str, Any]]:
        """Receive message from server"""
        try:
            # Receive message length
            length_data = sock.recv(4)
            if not length_data or len(length_data) != 4:
                return None

            message_length = struct.unpack('!I', length_data)[0]
            if message_length > 10 * 1024 * 1024:  # 10MB limit
                return None

            # Receive message data
            message_data = b""
            while len(message_data) < message_length:
                chunk = sock.recv(min(4096, message_length - len(message_data)))
                if not chunk:
                    return None
                message_data += chunk

            message = json.loads(message_data.decode('utf-8'))
            return message
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None

    def _process_message(self, message: Dict[str, Any]):
        """Process received message"""
        try:
            message_type_str = message.get("type")
            if message_type_str:
                try:
                    message_type = MessageType(message_type_str)
                    data = message.get("data", {})

                    if message_type in self.message_handlers:
                        self.message_handlers[message_type](data)
                    else:
                        print(f"No handler for message type: {message_type}")
                except ValueError:
                    print(f"Unknown message type: {message_type_str}")

        except Exception as e:
            print(f"Error processing message: {e}")

    def send_message(self, message_type: MessageType, data: Dict[str, Any]):
        """Send message to server"""
        if self.connected:
            return self._send_message(message_type, data)
        return False

    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register message handler"""
        self.message_handlers[message_type] = handler

    def register_connection_callback(self, callback: Callable):
        """Register connection status callback"""
        self.connection_callback = callback

    def is_connected(self):
        """Check if connected to server"""
        return self.connected
