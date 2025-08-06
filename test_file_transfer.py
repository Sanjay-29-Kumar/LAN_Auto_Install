#!/usr/bin/env python3
"""
Test script for LAN Software Automation System - File Transfer
"""

import os
import sys
import time
import threading
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network_manager import NetworkManager
from security import security_manager, file_security
import config

def create_test_file(filename, size_mb=1):
    """Create a test file of specified size"""
    file_path = os.path.join(os.getcwd(), filename)
    size_bytes = size_mb * 1024 * 1024
    
    with open(file_path, 'wb') as f:
        # Write random data
        import random
        chunk_size = 8192
        remaining = size_bytes
        
        while remaining > 0:
            chunk_size = min(chunk_size, remaining)
            data = bytes(random.getrandbits(8) for _ in range(chunk_size))
            f.write(data)
            remaining -= chunk_size
    
    print(f"Created test file: {filename} ({size_mb}MB)")
    return file_path

def test_file_transfer():
    """Test the file transfer functionality"""
    print("=== LAN Software Automation - File Transfer Test ===\n")
    
    # Create test files
    test_files = [
        ("small_file.txt", 0.1),      # 100KB text file
        ("medium_file.pdf", 5),       # 5MB PDF file
        ("large_file.zip", 20),       # 20MB ZIP file
        ("image_file.jpg", 2),        # 2MB image file
        ("document.docx", 1),         # 1MB document
    ]
    
    created_files = []
    for filename, size in test_files:
        file_path = create_test_file(filename, size)
        created_files.append(file_path)
    
    print(f"\nCreated {len(created_files)} test files")
    print("Files ready for transfer testing!")
    
    # Show file information
    print("\n=== File Information ===")
    for file_path in created_files:
        file_size = os.path.getsize(file_path)
        file_hash = file_security.calculate_file_hash(file_path)
        print(f"File: {os.path.basename(file_path)}")
        print(f"  Size: {file_size:,} bytes ({file_size/1024/1024:.1f} MB)")
        print(f"  Hash: {file_hash[:16]}...")
        print()
    
    print("=== Test Instructions ===")
    print("1. Start the main application: python app.py")
    print("2. Start Admin Panel on one machine")
    print("3. Start Client Agent on another machine")
    print("4. Use the test files above to test file transfer")
    print("5. Check the LAN_Automation folder in Documents for received files")
    
    return created_files

if __name__ == "__main__":
    try:
        test_files = test_file_transfer()
        print("\n✅ File transfer test setup completed!")
        print("Ready to test with the main application.")
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        sys.exit(1) 