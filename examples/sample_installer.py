#!/usr/bin/env python3
"""
Sample Installer Script for LAN Software Automation System
This is a demonstration installer that creates a simple application.
"""

import os
import sys
import subprocess
import platform
import time

def create_sample_app():
    """Create a sample application"""
    try:
        # Create a simple Python application
        app_code = '''#!/usr/bin/env python3
"""
Sample Application - Created by LAN Software Automation System
"""

import tkinter as tk
from tkinter import messagebox
import datetime

class SampleApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sample Application")
        self.root.geometry("400x300")
        
        # Create GUI
        title = tk.Label(self.root, text="Sample Application", font=("Arial", 16, "bold"))
        title.pack(pady=20)
        
        info = tk.Label(self.root, text="This application was installed using\\nLAN Software Automation System", 
                       font=("Arial", 10))
        info.pack(pady=10)
        
        time_label = tk.Label(self.root, text="", font=("Arial", 10))
        time_label.pack(pady=10)
        
        def update_time():
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time_label.config(text=f"Current Time: {current_time}")
            self.root.after(1000, update_time)
        
        update_time()
        
        # Button
        def show_info():
            messagebox.showinfo("Info", "This is a sample application created by the LAN Software Automation System!")
        
        button = tk.Button(self.root, text="Click Me!", command=show_info, 
                          font=("Arial", 12), bg="#4CAF50", fg="white", padx=20, pady=10)
        button.pack(pady=20)
        
        self.root.mainloop()

if __name__ == "__main__":
    app = SampleApp()
'''
        
        # Create application directory
        app_dir = os.path.join(os.path.expanduser("~"), "SampleApp")
        os.makedirs(app_dir, exist_ok=True)
        
        # Write application file
        app_file = os.path.join(app_dir, "sample_app.py")
        with open(app_file, 'w') as f:
            f.write(app_code)
        
        # Make executable on Unix systems
        if platform.system() != "Windows":
            os.chmod(app_file, 0o755)
        
        # Create desktop shortcut (Windows)
        if platform.system() == "Windows":
            shortcut_code = f'''@echo off
cd /d "{app_dir}"
python sample_app.py
pause
'''
            shortcut_file = os.path.join(app_dir, "run_sample_app.bat")
            with open(shortcut_file, 'w') as f:
                f.write(shortcut_code)
        
        # Create README
        readme_content = """Sample Application
================

This application was installed using the LAN Software Automation System.

To run the application:
- Windows: Double-click run_sample_app.bat
- Linux/Mac: Run python sample_app.py

Features:
- Simple GUI interface
- Real-time clock display
- Interactive button

Created by LAN Software Automation System
"""
        
        readme_file = os.path.join(app_dir, "README.txt")
        with open(readme_file, 'w') as f:
            f.write(readme_content)
        
        print(f"Sample application created successfully in: {app_dir}")
        return True
        
    except Exception as e:
        print(f"Error creating sample application: {e}")
        return False

def main():
    """Main installation function"""
    print("Starting sample application installation...")
    print("This is a demonstration installer for the LAN Software Automation System")
    
    # Simulate installation process
    print("1. Creating application files...")
    time.sleep(1)
    
    print("2. Setting up application directory...")
    time.sleep(1)
    
    print("3. Installing sample application...")
    success = create_sample_app()
    
    if success:
        print("4. Installation completed successfully!")
        print("Sample application has been installed.")
        return True
    else:
        print("4. Installation failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 