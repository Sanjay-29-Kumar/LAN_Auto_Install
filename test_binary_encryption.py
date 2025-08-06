#!/usr/bin/env python3
"""
Test script for binary data encryption/decryption
"""

import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from security import security_manager
import config

def test_binary_encryption():
    """Test binary data encryption and decryption"""
    print("=== Testing Binary Data Encryption/Decryption ===\n")
    
    # Test with binary data similar to file chunks
    test_binary = b"This is binary data with \x00\x01\x02\x90\x91\x92 bytes"
    print(f"Original binary data: {test_binary}")
    print(f"Length: {len(test_binary)} bytes")
    print(f"Contains non-UTF8 bytes: {[b for b in test_binary if b > 127]}")
    
    try:
        # Encrypt using regular method
        print("\n1. Testing regular encryption...")
        encrypted = security_manager.encrypt_data(test_binary)
        print(f"Encrypted length: {len(encrypted)} bytes")
        
        # Decrypt using binary method
        print("\n2. Testing binary decryption...")
        decrypted = security_manager.decrypt_binary_data(encrypted)
        print(f"Decrypted length: {len(decrypted) if decrypted else 0} bytes")
        
        if decrypted == test_binary:
            print("✅ Binary encryption/decryption: PASSED")
        else:
            print("❌ Binary encryption/decryption: FAILED")
            print(f"Expected: {test_binary}")
            print(f"Got: {decrypted}")
        
        # Test with larger binary data
        print("\n3. Testing larger binary data...")
        large_binary = b"Large binary data " * 1000 + b"\x00\x01\x02\x90\x91\x92"
        encrypted_large = security_manager.encrypt_data(large_binary)
        decrypted_large = security_manager.decrypt_binary_data(encrypted_large)
        
        if decrypted_large == large_binary:
            print("✅ Large binary encryption/decryption: PASSED")
        else:
            print("❌ Large binary encryption/decryption: FAILED")
            print(f"Expected size: {len(large_binary)}")
            print(f"Got size: {len(decrypted_large) if decrypted_large else 0}")
        
        # Test with actual file-like data
        print("\n4. Testing file-like binary data...")
        file_like_data = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xFF\xFF"  # PE header-like
        encrypted_file = security_manager.encrypt_data(file_like_data)
        decrypted_file = security_manager.decrypt_binary_data(encrypted_file)
        
        if decrypted_file == file_like_data:
            print("✅ File-like binary encryption/decryption: PASSED")
        else:
            print("❌ File-like binary encryption/decryption: FAILED")
            print(f"Expected: {file_like_data}")
            print(f"Got: {decrypted_file}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Binary Encryption Test Complete ===")

if __name__ == "__main__":
    test_binary_encryption() 