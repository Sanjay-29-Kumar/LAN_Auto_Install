"""
Security utilities for LAN Software Automation Installation System
"""

import hashlib
import base64
import json
import os
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import config

class SecurityManager:
    """Handles encryption, decryption, and security operations"""
    
    def __init__(self):
        self.key = self._generate_key()
        self.cipher = Fernet(self.key)
    
    def _generate_key(self):
        """Generate encryption key from the master key"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'lan_automation_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(config.ENCRYPTION_KEY.encode()))
        return key
    
    def encrypt_data(self, data):
        """Encrypt data (supports dict, str, and bytes)"""
        try:
            if isinstance(data, dict):
                data = json.dumps(data)
            if isinstance(data, str):
                data = data.encode('utf-8')
            if isinstance(data, bytes):
                return self.cipher.encrypt(data)
            else:
                raise ValueError("Unsupported data type for encryption")
        except Exception as e:
            print(f"Encryption error: {e}")
            raise
    
    def decrypt_data(self, encrypted_data):
        """Decrypt data (returns dict, str, or bytes)"""
        try:
            if not encrypted_data:
                print("Warning: Empty encrypted data received")
                return None
                
            decrypted = self.cipher.decrypt(encrypted_data)
            
            # First, try to decode as JSON (for dict data)
            try:
                decoded = decrypted.decode('utf-8')
                return json.loads(decoded)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # If JSON fails, try to decode as string
                try:
                    return decrypted.decode('utf-8')
                except UnicodeDecodeError:
                    # If string decode fails, return as bytes (binary data)
                    return decrypted
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    def decrypt_binary_data(self, encrypted_data):
        """Decrypt binary data specifically (returns bytes)"""
        try:
            if not encrypted_data:
                print("Warning: Empty encrypted data received")
                return None
                
            decrypted = self.cipher.decrypt(encrypted_data)
            return decrypted  # Return as bytes directly
        except Exception as e:
            print(f"Binary decryption error: {e}")
            return None
    
    def generate_hash(self, data):
        """Generate SHA256 hash of data"""
        if isinstance(data, str):
            data = data.encode()
        return hashlib.sha256(data).hexdigest()
    
    def verify_hash(self, data, expected_hash):
        """Verify hash of data"""
        actual_hash = self.generate_hash(data)
        return actual_hash == expected_hash

class ConsentManager:
    """Manages user consent for network participation"""
    
    def __init__(self):
        self.consent_file = config.CONSENT_FILE
    
    def has_consent(self):
        """Check if user has given consent"""
        try:
            if os.path.exists(self.consent_file):
                with open(self.consent_file, 'r') as f:
                    consent_data = json.load(f)
                    return consent_data.get('consent_given', False)
            return False
        except Exception:
            return False
    
    def give_consent(self):
        """Record user consent"""
        try:
            consent_data = {
                'consent_given': True,
                'timestamp': time.time(),
                'date': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.consent_file, 'w') as f:
                json.dump(consent_data, f, indent=2)
            return True
        except Exception:
            return False
    
    def revoke_consent(self):
        """Revoke user consent"""
        try:
            if os.path.exists(self.consent_file):
                os.remove(self.consent_file)
            return True
        except Exception:
            return False

class AuthenticationManager:
    """Handles authentication between admin and clients"""
    
    def __init__(self):
        self.security = SecurityManager()
    
    def create_auth_token(self, client_id, timestamp):
        """Create authentication token"""
        data = f"{client_id}:{timestamp}:{config.ENCRYPTION_KEY}"
        return self.security.generate_hash(data)
    
    def verify_auth_token(self, client_id, timestamp, token):
        """Verify authentication token"""
        expected_token = self.create_auth_token(client_id, timestamp)
        return token == expected_token
    
    def create_session_key(self, client_id):
        """Create session key for secure communication"""
        timestamp = str(int(time.time()))
        session_data = f"{client_id}:{timestamp}:{config.ENCRYPTION_KEY}"
        return self.security.generate_hash(session_data)[:32]

class FileSecurity:
    """Handles file security and integrity"""
    
    def __init__(self):
        self.security = SecurityManager()
    
    def calculate_file_hash(self, file_path):
        """Calculate SHA256 hash of a file"""
        try:
            with open(file_path, 'rb') as f:
                return self.security.generate_hash(f.read())
        except Exception:
            return None
    
    def verify_file_integrity(self, file_path, expected_hash):
        """Verify file integrity using hash"""
        actual_hash = self.calculate_file_hash(file_path)
        return actual_hash == expected_hash
    
    def encrypt_file(self, file_path, output_path=None):
        """Encrypt a file"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            encrypted_data = self.security.encrypt_data(data)
            
            if output_path is None:
                output_path = file_path + '.encrypted'
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            return output_path
        except Exception:
            return None
    
    def decrypt_file(self, encrypted_file_path, output_path=None):
        """Decrypt a file"""
        try:
            with open(encrypted_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.security.decrypt_data(encrypted_data)
            
            if output_path is None:
                output_path = encrypted_file_path.replace('.encrypted', '')
            
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            return output_path
        except Exception:
            return None

# Global instances
security_manager = SecurityManager()
consent_manager = ConsentManager()
auth_manager = AuthenticationManager()
file_security = FileSecurity() 