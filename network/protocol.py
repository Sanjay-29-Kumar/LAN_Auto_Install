"""
Defines the TCP communication protocol for reliable file transfer.
"""

# Port for the main TCP command channel
COMMAND_PORT = 5001

# Port for the UDP discovery broadcast
DISCOVERY_PORT = 5000

# Port for the client's file transfer listener
FILE_TRANSFER_PORT = 5002

# Protocol Message Types
# Sent by clients to find servers on the network.
MSG_TYPE_DISCOVERY = 'client_discovery'
# Sent by servers in response to discovery broadcasts.
MSG_TYPE_SERVER_RESPONSE = 'server_response'
# Sent by a client to register with a server.
MSG_TYPE_CLIENT_REGISTER = 'client_register'
# Sent by the server to acknowledge client registration.
MSG_TYPE_REGISTRATION_ACK = 'registration_ack'
# Sent periodically to keep the connection alive.
MSG_TYPE_HEARTBEAT = 'heartbeat'
# Sent by the server to initiate a file transfer, contains file metadata.
MSG_TYPE_FILE_HEADER = 'file_header'
# Sent by the client to accept or reject a file transfer.
MSG_TYPE_FILE_HEADER_ACK = 'file_header_ack'
# A chunk of the file being transferred.
MSG_TYPE_FILE_CHUNK = 'file_chunk'
# Sent by the client to acknowledge receipt of a file chunk.
MSG_TYPE_CHUNK_ACK = 'chunk_ack'
# Sent by the server to indicate the file transfer is complete.
MSG_TYPE_FILE_END = 'file_end'
# Sent by the client to confirm the entire file has been received and verified.
MSG_TYPE_FILE_COMPLETE_ACK = 'file_complete_ack'
# Sent by the client to request retransmission of a missing chunk.
MSG_TYPE_RETRANSMIT_REQUEST = 'retransmit_request'
# Sent by the server or client to signal cancellation of a transfer.
MSG_TYPE_CANCEL_TRANSFER = 'cancel_transfer'
# Sent by the client to provide a status update on a received file.
MSG_TYPE_STATUS_UPDATE = 'status_update'

# LAN optimization constants for massive scale
MAX_CONCURRENT_CLIENTS = 0   # 0 means unlimited clients
MAX_CONCURRENT_TRANSFERS = 0  # 0 means unlimited concurrent transfers
QUEUE_SIZE_PER_CLIENT = 1000 # Support large number of queued files

# Network buffer sizes for massive files (optimized for 25GB+)
LAN_BUFFER_SMALL = 32 * 1024 * 1024      # 32MB for files < 1GB
LAN_BUFFER_MEDIUM = 64 * 1024 * 1024     # 64MB for files 1GB-10GB
LAN_BUFFER_LARGE = 128 * 1024 * 1024     # 128MB for files > 10GB
LAN_BUFFER_MASSIVE = 256 * 1024 * 1024   # 256MB for files > 25GB

# Chunk sizes optimized for massive file transfer
CHUNK_SIZE_SMALL = 32 * 1024 * 1024      # 32MB chunks < 1GB files
CHUNK_SIZE_MEDIUM = 64 * 1024 * 1024     # 64MB chunks 1GB-10GB files
CHUNK_SIZE_LARGE = 128 * 1024 * 1024     # 128MB chunks 10GB-25GB files
CHUNK_SIZE_MASSIVE = 256 * 1024 * 1024   # 256MB chunks > 25GB files

# Multicast configuration for efficient distribution
MULTICAST_GROUP = '239.255.0.1'
MULTICAST_PORT = 5005
MULTICAST_TTL = 32  # Hop limit for multicast packets

# Advanced network performance settings
MAX_WINDOW_SIZE = 32       # Increased window size for better throughput
MIN_WINDOW_SIZE = 8        # Higher minimum for better baseline performance
WINDOW_SCALE_FACTOR = 2    # Dynamic window scaling

# Rate limiting with dynamic adjustment
BASE_RATE_LIMIT = 10 * 1024 * 1024 * 1024  # 10GB/s base rate for LAN
MAX_CLIENT_RATE = 1024 * 1024 * 1024       # 1GB/s max per client
MIN_CLIENT_RATE = 50 * 1024 * 1024         # 50MB/s min guaranteed
RATE_ADJUST_INTERVAL = 5                    # Adjust rates every 5 seconds

# Enhanced timeout settings for large files
CHUNK_TIMEOUT = 120        # 2 minutes for large chunks
SESSION_TIMEOUT = 7200     # 2 hours for long sessions
RETRY_ATTEMPTS = 5         # Number of retry attempts
RETRY_DELAY = 5           # Seconds between retries

# Memory management
MAX_MEMORY_BUFFER = 1024 * 1024 * 1024  # 1GB max memory buffer
BUFFER_FLUSH_THRESHOLD = 0.8  # Flush at 80% capacity
STREAM_THRESHOLD = 10 * 1024 * 1024 * 1024  # Stream mode for files > 10GB

# Chunk sizes for different file sizes
CHUNK_SIZE_SMALL = 1024 * 1024  # 1MB for files < 100MB
CHUNK_SIZE_MEDIUM = 4 * 1024 * 1024  # 4MB for files between 100MB and 1GB
CHUNK_SIZE_LARGE = 8 * 1024 * 1024  # 8MB for files > 1GB

# Adaptive chunk sizes based on network topology
CROSS_MACHINE_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB for cross-machine
SAME_MACHINE_CHUNK_SIZE = 1024 * 1024  # 1MB for same-machine

# Default chunk size (fallback)
CHUNK_SIZE = 1024 * 1024

# Adaptive timeouts based on network topology
# Cross-machine timeouts (different subnets or slower connections)
CROSS_MACHINE_CONNECTION_TIMEOUT = 300  # 5 minutes - increased for slow networks
CROSS_MACHINE_OPERATION_TIMEOUT = 1800  # 30 minutes - increased for large files
CROSS_MACHINE_INACTIVITY_TIMEOUT = 3600  # 60 minutes - increased for long operations
CROSS_MACHINE_ACK_TIMEOUT = 60  # 1 minute - increased for network latency
CROSS_MACHINE_HEARTBEAT_INTERVAL = 30  # 30 seconds - more frequent heartbeats

# Same-machine timeouts (localhost or same subnet)
SAME_MACHINE_CONNECTION_TIMEOUT = 30  # seconds - increased for network congestion
SAME_MACHINE_OPERATION_TIMEOUT = 600  # 10 minutes - increased for larger files
SAME_MACHINE_INACTIVITY_TIMEOUT = 1800  # 30 minutes - increased for long operations
SAME_MACHINE_ACK_TIMEOUT = 15  # seconds - increased for network congestion
SAME_MACHINE_HEARTBEAT_INTERVAL = 10  # seconds - unchanged

# Default timeout (fallback)
ACK_TIMEOUT = 5  # seconds

# Network topology detection utilities
import socket
import ipaddress

def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def is_cross_machine_connection(local_ip, remote_ip):
    """
    Determine if connection is cross-machine based on IP subnet comparison.
    Returns True if cross-machine, False if same-machine.
    Enhanced for better LAN detection with more permissive subnet matching.
    """
    try:
        # Same IP = same machine
        if local_ip == remote_ip:
            return False
            
        # Localhost connections = same machine
        if remote_ip in ["127.0.0.1", "localhost"] or local_ip in ["127.0.0.1", "localhost"]:
            return False
            
        # Check if IPs are in same subnet with multiple subnet mask possibilities
        local_addr = ipaddress.IPv4Address(local_ip)
        remote_addr = ipaddress.IPv4Address(remote_ip)
        
        # Check with a broader range of subnet masks for better LAN detection
        subnet_masks = [8, 16, 20, 21, 22, 23, 24, 25]  # More inclusive subnet masks
        
        for mask in subnet_masks:
            try:
                local_network = ipaddress.IPv4Network(f"{local_ip}/{mask}", strict=False)
                if remote_addr in local_network:
                    return False  # Same subnet = likely same LAN
            except ValueError:
                continue
        
        # Check for common private network ranges with more permissive matching
        private_ranges = [
            ipaddress.IPv4Network('192.168.0.0/16'),    # 192.168.x.x
            ipaddress.IPv4Network('10.0.0.0/8'),        # 10.x.x.x
            ipaddress.IPv4Network('172.16.0.0/12'),     # 172.16-31.x.x
            ipaddress.IPv4Network('169.254.0.0/16'),    # Link-local addresses
        ]
        
        local_is_private = any(local_addr in network for network in private_ranges)
        remote_is_private = any(remote_addr in network for network in private_ranges)
        
        # If both are in private ranges, consider them same LAN by default
        if local_is_private and remote_is_private:
            return False  # Assume same LAN for private network addresses
            
        return True  # Different networks = cross-machine
    except Exception as e:
        print(f"Error determining network topology: {e}")
        # If we can't determine, assume same machine for better LAN performance
        return False

def get_adaptive_timeouts(local_ip, remote_ip):
    """Get appropriate timeouts based on network topology."""
    if is_cross_machine_connection(local_ip, remote_ip):
        return {
            'connection': CROSS_MACHINE_CONNECTION_TIMEOUT,
            'operation': CROSS_MACHINE_OPERATION_TIMEOUT,
            'inactivity': CROSS_MACHINE_INACTIVITY_TIMEOUT,
            'ack': CROSS_MACHINE_ACK_TIMEOUT,
            'heartbeat': CROSS_MACHINE_HEARTBEAT_INTERVAL,
            'chunk_size': CROSS_MACHINE_CHUNK_SIZE,
            'buffer_size': LAN_BUFFER_MASSIVE  # Use massive buffer for optimal LAN performance
        }
    else:
        return {
            'connection': SAME_MACHINE_CONNECTION_TIMEOUT,
            'operation': SAME_MACHINE_OPERATION_TIMEOUT,
            'inactivity': SAME_MACHINE_INACTIVITY_TIMEOUT,
            'ack': SAME_MACHINE_ACK_TIMEOUT,
            'heartbeat': SAME_MACHINE_HEARTBEAT_INTERVAL,
            'chunk_size': SAME_MACHINE_CHUNK_SIZE,
            'buffer_size': LAN_BUFFER_LARGE  # Use large buffer for local transfers
        }
