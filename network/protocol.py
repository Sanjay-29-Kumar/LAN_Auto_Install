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

# Adaptive buffer sizes based on network topology
CROSS_MACHINE_BUFFER_SIZE = 2 * 1024 * 1024  # 2MB for cross-machine
SAME_MACHINE_BUFFER_SIZE = 1024 * 1024  # 1MB for same-machine

# Standard buffer size for receiving data (fallback)
BUFFER_SIZE = 4096

# Adaptive chunk sizes based on network topology
CROSS_MACHINE_CHUNK_SIZE = 2 * 1024 * 1024  # 2MB for cross-machine
SAME_MACHINE_CHUNK_SIZE = 1024 * 1024  # 1MB for same-machine

# Default chunk size (fallback)
CHUNK_SIZE = 1024 * 1024

# Adaptive timeouts based on network topology
# Cross-machine timeouts (different subnets or slower connections)
CROSS_MACHINE_CONNECTION_TIMEOUT = 60  # seconds
CROSS_MACHINE_OPERATION_TIMEOUT = 300  # seconds
CROSS_MACHINE_INACTIVITY_TIMEOUT = 600  # 10 minutes
CROSS_MACHINE_ACK_TIMEOUT = 30  # seconds
CROSS_MACHINE_HEARTBEAT_INTERVAL = 30  # seconds

# Same-machine timeouts (localhost or same subnet)
SAME_MACHINE_CONNECTION_TIMEOUT = 10  # seconds
SAME_MACHINE_OPERATION_TIMEOUT = 120  # seconds
SAME_MACHINE_INACTIVITY_TIMEOUT = 300  # 5 minutes
SAME_MACHINE_ACK_TIMEOUT = 5  # seconds
SAME_MACHINE_HEARTBEAT_INTERVAL = 10  # seconds

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
    """
    try:
        # Same IP = same machine
        if local_ip == remote_ip:
            return False
            
        # Localhost connections = same machine
        if remote_ip in ["127.0.0.1", "localhost"] or local_ip in ["127.0.0.1", "localhost"]:
            return False
            
        # Check if IPs are in same subnet (assuming /24 subnet)
        local_network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        remote_network = ipaddress.IPv4Network(f"{remote_ip}/24", strict=False)
        
        # Same subnet = likely same machine or very close
        if local_network.network_address == remote_network.network_address:
            return False
            
        return True  # Different subnets = cross-machine
    except Exception:
        # If we can't determine, assume cross-machine for safety
        return True

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
            'buffer_size': CROSS_MACHINE_BUFFER_SIZE
        }
    else:
        return {
            'connection': SAME_MACHINE_CONNECTION_TIMEOUT,
            'operation': SAME_MACHINE_OPERATION_TIMEOUT,
            'inactivity': SAME_MACHINE_INACTIVITY_TIMEOUT,
            'ack': SAME_MACHINE_ACK_TIMEOUT,
            'heartbeat': SAME_MACHINE_HEARTBEAT_INTERVAL,
            'chunk_size': SAME_MACHINE_CHUNK_SIZE,
            'buffer_size': SAME_MACHINE_BUFFER_SIZE
        }
