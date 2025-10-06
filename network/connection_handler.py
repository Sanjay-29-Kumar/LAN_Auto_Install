import socket
import threading
import logging
import time
from typing import Optional, Tuple, Dict
from pathlib import Path

class ConnectionHandler:
    """Handles robust network connections with automatic retry and recovery"""
    
    def __init__(self, port: int = 5000, chunk_size: int = 1048576):
        self.port = port
        self.chunk_size = chunk_size
        self.logger = self._setup_logging()
        self.active_connections: Dict[str, socket.socket] = {}
        self.connection_lock = threading.Lock()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup network logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='network.log'
        )
        return logging.getLogger('network')

    def create_server_socket(self) -> socket.socket:
        """Create and configure server socket with proper options"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Enable keep-alive to detect disconnected clients
        server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Set TCP keep-alive options
        if hasattr(socket, 'TCP_KEEPIDLE'):
            server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        if hasattr(socket, 'TCP_KEEPINTVL'):
            server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 60)
        if hasattr(socket, 'TCP_KEEPCNT'):
            server.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
        # Increase buffer sizes for better performance
        server.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1048576)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1048576)
        return server

    def bind_server(self, server: socket.socket) -> None:
        """Bind server socket with retry mechanism"""
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                server.bind(('0.0.0.0', self.port))
                self.logger.info(f"Server bound successfully to port {self.port}")
                return
            except OSError as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Binding failed, attempt {attempt + 1}/{max_retries}: {e}")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to bind after {max_retries} attempts")
                    raise

    def accept_connection(self, server: socket.socket) -> Tuple[socket.socket, str]:
        """Accept incoming connection with proper configuration"""
        client_socket, addr = server.accept()
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Configure socket for optimal performance
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.chunk_size)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.chunk_size)
        
        with self.connection_lock:
            self.active_connections[addr[0]] = client_socket
            
        self.logger.info(f"Accepted connection from {addr[0]}:{addr[1]}")
        return client_socket, addr[0]

    def create_client_socket(self) -> socket.socket:
        """Create and configure client socket with proper options"""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Set TCP keep-alive options
        if hasattr(socket, 'TCP_KEEPIDLE'):
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
        # Configure socket for optimal performance
        client.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.chunk_size)
        client.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.chunk_size)
        return client

    def connect_to_server(self, server_ip: str, max_retries: int = 5) -> Optional[socket.socket]:
        """Connect to server with retry mechanism"""
        client = self.create_client_socket()
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                client.connect((server_ip, self.port))
                self.logger.info(f"Connected to server at {server_ip}:{self.port}")
                return client
            except (ConnectionRefusedError, TimeoutError) as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Failed to connect after {max_retries} attempts")
                    return None

    def close_connection(self, client_ip: str) -> None:
        """Safely close a connection"""
        with self.connection_lock:
            if client_ip in self.active_connections:
                try:
                    self.active_connections[client_ip].close()
                    del self.active_connections[client_ip]
                    self.logger.info(f"Closed connection with {client_ip}")
                except Exception as e:
                    self.logger.error(f"Error closing connection with {client_ip}: {e}")

    def close_all_connections(self) -> None:
        """Safely close all active connections"""
        with self.connection_lock:
            for client_ip, sock in self.active_connections.items():
                try:
                    sock.close()
                    self.logger.info(f"Closed connection with {client_ip}")
                except Exception as e:
                    self.logger.error(f"Error closing connection with {client_ip}: {e}")
            self.active_connections.clear()