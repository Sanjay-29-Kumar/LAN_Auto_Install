"""
Configuration settings for LAN Software Automation Installation System
"""

import os
import socket

# Network Configuration
DISCOVERY_PORT = 5000
COMMUNICATION_PORT = 5001
BROADCAST_ADDRESS = "255.255.255.255"
BUFFER_SIZE = 8192
TIMEOUT = 30

# Security Configuration
ENCRYPTION_KEY = "LAN_MK_SECURE_KEY_2024"  # In production, use environment variables
HASH_ALGORITHM = "sha256"

# Application Configuration
APP_NAME = "LAN Software Automation"
VERSION = "1.0.0"
ADMIN_WINDOW_SIZE = "800x600"
CLIENT_WINDOW_SIZE = "600x400"

# File Paths
TEMP_DIR = os.path.join(os.path.expanduser("~"), ".lan_automation")
CONFIG_FILE = os.path.join(TEMP_DIR, "config.json")
LOG_FILE = os.path.join(TEMP_DIR, "lan_automation.log")
CONSENT_FILE = os.path.join(TEMP_DIR, "consent.json")

# Installation Configuration
SUPPORTED_EXTENSIONS = ['.exe', '.msi', '.zip', '.tar.gz', '.deb', '.rpm', '.py', '.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif', '.mp3', '.mp4', '.avi', '.mkv']
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# File transfer settings
CHUNK_SIZE = 8192  # 8KB chunks for file transfer

# GUI Configuration
THEME_COLORS = {
    'primary': '#2c3e50',
    'secondary': '#3498db',
    'success': '#27ae60',
    'warning': '#f39c12',
    'error': '#e74c3c',
    'background': '#ecf0f1',
    'text': '#2c3e50'
}

# Status Messages
STATUS_MESSAGES = {
    'discovering': 'Discovering clients on network...',
    'connected': 'Connected to network',
    'installing': 'Installing software...',
    'success': 'Installation completed successfully',
    'failed': 'Installation failed',
    'waiting': 'Waiting for admin commands...',
    'consent_required': 'User consent required to join network'
}

# Network Discovery
DISCOVERY_INTERVAL = 5  # seconds
HEARTBEAT_INTERVAL = 10  # seconds

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Create necessary directories
def ensure_directories():
    """Create necessary directories if they don't exist"""
    os.makedirs(TEMP_DIR, exist_ok=True)

# Get local IP address
def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

# Initialize configuration
ensure_directories()
LOCAL_IP = get_local_ip() 