
#!/usr/bin/env python3
"""
Connection Tester for LAN File Transfer System
Run this to test network connectivity and diagnose connection issues
"""

import socket
import time
import threading
import os
from network.discovery import get_local_ip, NetworkDiscovery
from network.protocol import NetworkProtocol

def test_network_connectivity():
    """Test basic network connectivity"""
    print("Testing Network Connectivity...")
    
    try:
        local_ip = get_local_ip()
        print(f"✓ Local IP Address: {local_ip}")
        
        # Test internet connectivity
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(3)
        test_socket.connect(("8.8.8.8", 53))
        test_socket.close()
        print("✓ Internet connectivity working")
        
        return True
    except Exception as e:
        print(f"✗ Network connectivity failed: {e}")
        return False

def test_port_availability():
    """Test if required ports are available"""
    print("\nTesting Port Availability...")
    
    test_ports = [5000, 5001]
    all_available = True
    
    for port in test_ports:
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.bind(('0.0.0.0', port))
            test_socket.close()
            print(f"✓ Port {port} is available")
        except Exception as e:
            print(f"✗ Port {port} is not available: {e}")
            all_available = False
    
    return all_available

def test_server_functionality():
    """Test server start/stop functionality"""
    print("\nTesting Server Functionality...")
    
    try:
        protocol = NetworkProtocol(host='0.0.0.0', port=5000)
        
        # Test server start
        if protocol.start_server():
            print("✓ Server started successfully")
            
            # Test client connection
            time.sleep(1)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(3)
            
            try:
                client_socket.connect(('127.0.0.1', 5000))
                print("✓ Client can connect to server")
                client_socket.close()
                connection_test = True
            except Exception as e:
                print(f"✗ Client connection failed: {e}")
                connection_test = False
            
            # Stop server
            protocol.stop_server()
            print("✓ Server stopped successfully")
            
            return connection_test
        else:
            print("✗ Failed to start server")
            return False
            
    except Exception as e:
        print(f"✗ Server functionality test failed: {e}")
        return False

def test_network_discovery():
    """Test network discovery functionality"""
    print("\nTesting Network Discovery...")
    
    try:
        discovery = NetworkDiscovery()
        local_ip = discovery.get_local_ip()
        network_range = discovery.get_network_range()
        
        print(f"✓ Local IP: {local_ip}")
        print(f"✓ Network range: {network_range[0]} - {network_range[-1]}")
        
        # Quick scan test
        print("Performing quick network scan...")
        devices = discovery.fast_network_scan()
        
        print(f"✓ Found {len(devices)} devices on network")
        for device in devices[:5]:  # Show first 5 devices
            status = "SERVER" if device.is_server else "CLIENT"
            print(f"  - {device.ip} ({device.hostname}) [{status}]")
        
        return True
        
    except Exception as e:
        print(f"✗ Network discovery failed: {e}")
        return False

def test_file_operations():
    """Test file operations"""
    print("\nTesting File Operations...")
    
    try:
        # Create test directory
        test_dir = "test_files"
        os.makedirs(test_dir, exist_ok=True)
        
        # Create test file
        test_file = os.path.join(test_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("This is a test file for the LAN transfer system.")
        
        print(f"✓ Created test file: {test_file}")
        
        # Test file size
        file_size = os.path.getsize(test_file)
        print(f"✓ File size: {file_size} bytes")
        
        # Cleanup
        os.remove(test_file)
        os.rmdir(test_dir)
        print("✓ Test file cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"✗ File operations test failed: {e}")
        return False

def main():
    """Run all connection tests"""
    print("=== LAN File Transfer Connection Tester ===\n")
    
    tests = [
        ("Network Connectivity", test_network_connectivity),
        ("Port Availability", test_port_availability),
        ("Server Functionality", test_server_functionality),
        ("Network Discovery", test_network_discovery),
        ("File Operations", test_file_operations)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        if test_func():
            passed += 1
        print(f"{'='*50}")
    
    print(f"\n\nFINAL RESULTS:")
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("✓ All tests passed! Your system is ready for LAN file transfer.")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print("\nTroubleshooting tips:")
        print("- Ensure no firewall is blocking ports 5000-5001")
        print("- Check that no other applications are using these ports")
        print("- Verify network permissions")
        print("- Run as administrator if needed")

if __name__ == "__main__":
    main()
