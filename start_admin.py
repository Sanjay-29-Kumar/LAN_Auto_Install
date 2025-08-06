#!/usr/bin/env python3
"""
Startup script for LAN Software Automation Admin Application
"""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from admin_app import main
    main()
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please make sure all required files are present and dependencies are installed.")
    print("Run: pip install -r requirements.txt")
    input("Press Enter to exit...")
except Exception as e:
    print(f"Error starting admin application: {e}")
    input("Press Enter to exit...") 