#!/usr/bin/env python3
"""
Test script for encryption/decryption functionality
"""

import os
import sys
import tempfile

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from security import security_manager, file_security
import config

def test_encryption():
    """Test encryption and decryption functionality"""
    print("=== Testing Encryption/Decryption ===\n")
    
    # Test 1: Dictionary encryption
    print("1. Testing dictionary encryption...")
    test_dict = {'type': 'test', 'data': 'hello world', 'number': 42}
    encrypted_dict = security_manager.encrypt_data(test_dict)
    decrypted_dict = security_manager.decrypt_data(encrypted_dict)
    
    if decrypted_dict == test_dict:
        print("✅ Dictionary encryption/decryption: PASSED")
    else:
        print("❌ Dictionary encryption/decryption: FAILED")
        print(f"Expected: {test_dict}")
        print(f"Got: {decrypted_dict}")
    
    # Test 2: String encryption
    print("\n2. Testing string encryption...")
    test_string = "Hello, World! This is a test string."
    encrypted_string = security_manager.encrypt_data(test_string)
    decrypted_string = security_manager.decrypt_data(encrypted_string)
    
    if decrypted_string == test_string:
        print("✅ String encryption/decryption: PASSED")
    else:
        print("❌ String encryption/decryption: FAILED")
        print(f"Expected: {test_string}")
        print(f"Got: {decrypted_string}")
    
    # Test 3: Binary data encryption
    print("\n3. Testing binary data encryption...")
    test_binary = b"This is binary data with \x00\x01\x02 bytes"
    encrypted_binary = security_manager.encrypt_data(test_binary)
    decrypted_binary = security_manager.decrypt_data(encrypted_binary)
    
    if decrypted_binary == test_binary:
        print("✅ Binary encryption/decryption: PASSED")
    else:
        print("❌ Binary encryption/decryption: FAILED")
        print(f"Expected: {test_binary}")
        print(f"Got: {decrypted_binary}")
    
    # Test 4: File encryption
    print("\n4. Testing file encryption...")
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        test_content = b"This is test file content with binary data \x00\x01\x02"
        temp_file.write(test_content)
        temp_file_path = temp_file.name
    
    try:
        # Encrypt file
        encrypted_file = file_security.encrypt_file(temp_file_path)
        if encrypted_file and os.path.exists(encrypted_file):
            print("✅ File encryption: PASSED")
            
            # Decrypt file
            decrypted_file = file_security.decrypt_file(encrypted_file)
            if decrypted_file and os.path.exists(decrypted_file):
                with open(decrypted_file, 'rb') as f:
                    decrypted_content = f.read()
                
                if decrypted_content == test_content:
                    print("✅ File decryption: PASSED")
                else:
                    print("❌ File decryption: FAILED")
                    print(f"Expected: {test_content}")
                    print(f"Got: {decrypted_content}")
            else:
                print("❌ File decryption: FAILED - Could not decrypt file")
        else:
            print("❌ File encryption: FAILED - Could not encrypt file")
    
    finally:
        # Clean up
        for file_path in [temp_file_path, encrypted_file, decrypted_file]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
    
    # Test 5: Large binary data (simulating file chunks)
    print("\n5. Testing large binary data...")
    large_binary = b"Large binary data " * 1000  # ~18KB
    encrypted_large = security_manager.encrypt_data(large_binary)
    decrypted_large = security_manager.decrypt_data(encrypted_large)
    
    if decrypted_large == large_binary:
        print("✅ Large binary encryption/decryption: PASSED")
    else:
        print("❌ Large binary encryption/decryption: FAILED")
        print(f"Expected size: {len(large_binary)}")
        print(f"Got size: {len(decrypted_large) if decrypted_large else 0}")
    
    print("\n=== Encryption Test Complete ===")

if __name__ == "__main__":
    try:
        test_encryption()
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc() 