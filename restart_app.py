#!/usr/bin/env python3
"""
Restart script for LAN Auto Install application
This script helps clean up any stuck processes and restart the application
"""

import os
import sys
import subprocess
import time
import signal
import psutil

def kill_python_processes():
    """Kill any Python processes that might be stuck"""
    print("Checking for stuck Python processes...")
    
    current_pid = os.getpid()
    killed_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe':
                # Check if it's related to our application
                cmdline = proc.info['cmdline']
                if cmdline and any('LAN_Auto_Install' in arg or 'working_server.py' in arg for arg in cmdline):
                    if proc.info['pid'] != current_pid:
                        print(f"Killing stuck process: PID {proc.info['pid']}")
                        proc.kill()
                        killed_processes.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_processes:
        print(f"Killed {len(killed_processes)} stuck processes")
        time.sleep(2)  # Wait for processes to terminate
    else:
        print("No stuck processes found")

def restart_application():
    """Restart the LAN Auto Install application"""
    print("Starting LAN Auto Install application...")
    
    # Change to the application directory
    app_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_dir)
    
    # Start the application
    try:
        subprocess.Popen([sys.executable, 'working_server.py'], 
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
        print("Application started successfully!")
    except Exception as e:
        print(f"Error starting application: {e}")

def main():
    print("LAN Auto Install - Restart Utility")
    print("=" * 40)
    
    # Kill any stuck processes
    kill_python_processes()
    
    # Wait a moment
    time.sleep(1)
    
    # Restart the application
    restart_application()
    
    print("Restart complete!")

if __name__ == "__main__":
    main()