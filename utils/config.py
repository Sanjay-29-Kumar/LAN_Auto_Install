import os
import base64
from cryptography.fernet import Fernet

def get_encryption_key():
    """Get or generate encryption key from environment"""
    key = os.environ.get('LAN_AUTO_INSTALL_KEY')
    if not key:
        key = Fernet.generate_key()
        with open(os.path.join(os.path.dirname(__file__), '.env_key'), 'wb') as f:
            f.write(key)
    return key

def encrypt_api_key(api_key):
    """Encrypt API key for storage"""
    f = Fernet(get_encryption_key())
    return base64.b64encode(f.encrypt(api_key.encode())).decode()

def decrypt_api_key():
    """Decrypt and return API key"""
    try:
        encrypted_key = os.environ.get('VIRUSTOTAL_API_KEY_ENCRYPTED')
        if not encrypted_key:
            return None
        f = Fernet(get_encryption_key())
        return f.decrypt(base64.b64decode(encrypted_key)).decode()
    except Exception:
        return None

# Store encrypted API key in environment
if not os.environ.get('VIRUSTOTAL_API_KEY_ENCRYPTED'):
    # This is just for development, in production the API key should be set securely
    default_key = "a828b8fdc2b8115bf8b3147dccfcffa28d0ff7aa5c07ea94f1b2ec1c474fc92c"
    os.environ['VIRUSTOTAL_API_KEY_ENCRYPTED'] = encrypt_api_key(default_key)
