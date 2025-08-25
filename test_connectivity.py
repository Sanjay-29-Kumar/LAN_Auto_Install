#!/usr/bin/env python3
"""
Test script to verify LAN connectivity fixes for the Auto Install system.
This script tests both client and server discovery and connection functionality.
"""

import socket
import json
import time
import threading
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network import protocol
from network.client import NetworkClient
from network.server import NetworkServer

def test_ip_detection():
    """Test IP detection methods"""
    print("=== Testing IP Detection ===")
    
    # Test client IP detection
    client = NetworkClient()
    client_ip = client._get_local_ip()
    print(f"Client detected IP: {client_ip}")
    
    # Test server IP detection
    server = NetworkServer()
    server_ip = server._get_local_ip()
    print(f"Server detected IP: {server_ip}")
    
    if client_ip == server_ip and not client_ip.startswith("127."):
        print("✅ IP detection working correctly")
        return True
    else:
        print("❌ IP detection may have issues")
        return False

def test_discovery_protocol():
    """Test UDP discovery protocol"""
    print("\n=== Testing Discovery Protocol ===")
    
    # Start server
    server = NetworkServer()
    server.start_server()
    time.sleep(2)  # Give server time to start
    
    # Start client discovery
    client = NetworkClient()
    client.start_discovery_client()
    
    # Wait for discovery
    servers_found = []
    def on_server_found(server_info):
        servers_found.append(server_info)
        print(f"✅ Server discovered: {server_info['ip']}:{server_info['port']}")
    
    client.server_found.connect(on_server_found)
    
    # Wait up to 10 seconds for discovery
    for i in range(20):  # 20 * 0.5 = 10 seconds
        if servers_found:
            break
        time.sleep(0.5)
    
    # Cleanup
    client.stop_discovery_client()
    server.stop_server()
    
    if servers_found:
        print("✅ Discovery protocol working correctly")
        return True
    else:
        print("❌ Discovery protocol failed")
        return False

def test_tcp_connection():
    """Test TCP connection between client and server"""
    print("\n=== Testing TCP Connection ===")
    
    # Start server
    server = NetworkServer()
    server.start_server()
    time.sleep(2)  # Give server time to start
    
    server_ip = server._get_local_ip()
    
    # Start client and connect
    client = NetworkClient()
    client.start_client()
    time.sleep(1)
    
    # Track connection status
    connection_successful = []
    def on_connection_status(ip, connected):
        if connected:
            connection_successful.append(ip)
            print(f"✅ Connected to server: {ip}")
        else:
            print(f"❌ Disconnected from server: {ip}")
    
    client.connection_status.connect(on_connection_status)
    
    # Attempt connection
    client._connect_to_server(server_ip, protocol.COMMAND_PORT)
    
    # Wait for connection
    for i in range(20):  # 20 * 0.5 = 10 seconds
        if connection_successful:
            break
        time.sleep(0.5)
    
    # Cleanup
    client.stop_client()
    server.stop_server()
    
    if connection_successful:
        print("✅ TCP connection working correctly")
        return True
    else:
        print("❌ TCP connection failed")
        return False

def test_network_interfaces():
    """Test network interface detection"""
    print("\n=== Testing Network Interfaces ===")
    
    try:
        # Get all network interfaces
        hostname = socket.gethostname()
        ip_list = socket.gethostbyname_ex(hostname)[2]
        
        print(f"Hostname: {hostname}")
        print("Available IP addresses:")
        
        valid_ips = []
        for ip in ip_list:
            if not ip.startswith("127.") and not ip.startswith("169.254."):
                valid_ips.append(ip)
                print(f"  ✅ {ip} (valid for LAN)")
            else:
                print(f"  ❌ {ip} (localhost/link-local)")
        
        if valid_ips:
            print(f"✅ Found {len(valid_ips)} valid network interface(s)")
            return True
        else:
            print("❌ No valid network interfaces found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing network interfaces: {e}")
        return False

def main():
    """Run all connectivity tests"""
    print("LAN Auto Install - Connectivity Test Suite")
    print("=" * 50)
    
    tests = [
        ("IP Detection", test_ip_detection),
        ("Network Interfaces", test_network_interfaces),
        ("Discovery Protocol", test_discovery_protocol),
        ("TCP Connection", test_tcp_connection),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All connectivity tests passed! LAN connectivity should work properly.")
    else:
        print("⚠️  Some tests failed. Check network configuration and firewall settings.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
