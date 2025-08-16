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

# Standard buffer size for receiving data
BUFFER_SIZE = 4096

# Size of each file chunk in bytes (e.g., 1MB)
CHUNK_SIZE = 1024 * 1024

# Timeout for waiting for acknowledgments
ACK_TIMEOUT = 5  # seconds
