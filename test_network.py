#!/usr/bin/env python3
"""
Network test script for LAN Software Automation System
"""

import os
import sys
import socket
import json
import time
import threading

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

def test_network_discovery():
    """Test network discovery functionality"""
    print("=== Network Discovery Test ===\n")
    
    # Test 1: Check local IP
    print("1. Checking local IP address...")
    try:
        local_ip = config.LOCAL_IP
        print(f"Local IP: {local_ip}")
        
        # Test if we can bind to the discovery port
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.bind(('', config.DISCOVERY_PORT))
        test_socket.close()
        print("✅ Discovery port available")
    except Exception as e:
        print(f"❌ Discovery port error: {e}")
    
    # Test 2: Test broadcast capability
    print("\n2. Testing broadcast capability...")
    try:
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        test_message = {
            'type': 'test',
            'message': 'Network test',
            'timestamp': time.time()
        }
        
        broadcast_socket.sendto(
            json.dumps(test_message).encode(),
            (config.BROADCAST_ADDRESS, config.DISCOVERY_PORT)
        )
        print("✅ Broadcast test message sent")
        broadcast_socket.close()
    except Exception as e:
        print(f"❌ Broadcast test failed: {e}")
    
    # Test 3: Test listener
    print("\n3. Testing discovery listener...")
    listener_running = True
    received_messages = []
    
    def test_listener():
        try:
            listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener_socket.bind(('', config.DISCOVERY_PORT))
            listener_socket.settimeout(5)
            
            print("Listening for discovery messages...")
            
            while listener_running:
                try:
                    data, addr = listener_socket.recvfrom(1024)
                    message = json.loads(data.decode())
                    received_messages.append((addr, message))
                    print(f"Received from {addr}: {message}")
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Listener error: {e}")
                    break
            
            listener_socket.close()
        except Exception as e:
            print(f"❌ Listener failed: {e}")
    
    # Start listener in background
    listener_thread = threading.Thread(target=test_listener, daemon=True)
    listener_thread.start()
    
    # Wait a bit and send test broadcast
    time.sleep(2)
    
    try:
        test_broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        test_discovery = {
            'type': 'discovery',
            'client_id': f"test_{config.LOCAL_IP}",
            'hostname': 'test_client',
            'timestamp': time.time()
        }
        
        test_broadcast_socket.sendto(
            json.dumps(test_discovery).encode(),
            (config.BROADCAST_ADDRESS, config.DISCOVERY_PORT)
        )
        print("✅ Test discovery message sent")
        test_broadcast_socket.close()
    except Exception as e:
        print(f"❌ Test broadcast failed: {e}")
    
    # Wait for messages
    time.sleep(3)
    listener_running = False
    
    if received_messages:
        print("✅ Discovery listener working")
        for addr, msg in received_messages:
            print(f"  - From {addr}: {msg.get('type', 'unknown')}")
    else:
        print("❌ No discovery messages received")
    
    # Test 4: Check firewall and network
    print("\n4. Checking network connectivity...")
    try:
        # Test if we can connect to ourselves
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(5)
        test_socket.connect((config.LOCAL_IP, config.COMMUNICATION_PORT))
        test_socket.close()
        print("✅ Local communication port accessible")
    except Exception as e:
        print(f"❌ Local communication port error: {e}")
    
    print("\n=== Network Test Complete ===")
    print("\nTroubleshooting Tips:")
    print("1. Ensure both machines are on the same network")
    print("2. Check Windows Firewall settings")
    print("3. Try running as administrator")
    print("4. Check antivirus software blocking network access")

if __name__ == "__main__":
    test_network_discovery() 