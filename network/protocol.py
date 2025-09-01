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
CROSS_MACHINE_CONNECTION_TIMEOUT = 120  # seconds
CROSS_MACHINE_OPERATION_TIMEOUT = 600  # seconds
CROSS_MACHINE_INACTIVITY_TIMEOUT = 1200  # 20 minutes
CROSS_MACHINE_ACK_TIMEOUT = 30  # seconds
CROSS_MACHINE_HEARTBEAT_INTERVAL = 60  # seconds

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
    Enhanced for better LAN detection.
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
        
        # Check common subnet masks for LAN networks
        subnet_masks = [24, 16, 20, 22]  # /24, /16, /20, /22 are common
        
        for mask in subnet_masks:
            local_network = ipaddress.IPv4Network(f"{local_ip}/{mask}", strict=False)
            if remote_addr in local_network:
                return False  # Same subnet = likely same LAN
        
        # Check for common private network ranges
        private_ranges = [
            ipaddress.IPv4Network('192.168.0.0/16'),    # 192.168.x.x
            ipaddress.IPv4Network('10.0.0.0/8'),        # 10.x.x.x
            ipaddress.IPv4Network('172.16.0.0/12'),     # 172.16-31.x.x
        ]
        
        local_is_private = any(local_addr in network for network in private_ranges)
        remote_is_private = any(remote_addr in network for network in private_ranges)
        
        # If both are in the same private range, consider them same LAN
        if local_is_private and remote_is_private:
            for network in private_ranges:
                if local_addr in network and remote_addr in network:
                    return False  # Same private network = same LAN
            
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
