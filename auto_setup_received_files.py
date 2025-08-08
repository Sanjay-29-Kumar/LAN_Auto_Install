#!/usr/bin/env python3
"""
Auto Setup Received Files
Automatically installs received installer files using silent installation
"""

import os
import sys
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.dynamic_installer import DynamicInstaller, setup_auto_installer

def main():
    """Main function to run the auto installer"""
    print("=" * 60)
    print("🚀 LAN Auto Install - Received Files Auto Setup")
    print("=" * 60)
    
    try:
        # Initialize the dynamic installer
        print("Initializing dynamic installer...")
        auto_installer = DynamicInstaller()
        
        # Show current status
        status = auto_installer.get_installation_status()
        print(f"📁 Installers path: {status['installers_path']}")
        print(f"📊 Previously processed files: {status['total_processed']}")
        
        # Check for and process any new files
        print("\n🔍 Checking for new installer files...")
        results = auto_installer.manual_install_check()
        
        if results:
            print("\n📋 Processing Results:")
            print("-" * 40)
            for filename, status in results.items():
                status_emoji = {
                    "installed_successfully": "✅",
                    "installation_failed": "❌",
                    "skipped_already_processed": "⏭️"
                }.get(status, "❓")
                
                print(f"{status_emoji} {filename}: {status.replace('_', ' ').title()}")
        else:
            print("✨ No new installer files found.")
        
        # Ask user if they want to start continuous monitoring
        print(f"\n🔄 Would you like to start continuous monitoring?")
        print("This will automatically install new files as they are received.")
        
        choice = input("Start monitoring? (y/n): ").lower().strip()
        
        if choice in ['y', 'yes']:
            print("\n🎯 Starting continuous monitoring...")
            auto_installer.start_monitoring(check_interval=30)
            
            print("✅ Monitoring started! New installer files will be automatically processed.")
            print("📝 Check interval: 30 seconds")
            print("🛑 Press Ctrl+C to stop monitoring")
            
            try:
                while True:
                    time.sleep(60)  # Show status every minute
                    current_status = auto_installer.get_installation_status()
                    print(f"📊 Status: {current_status['total_processed']} files processed | Monitoring: {'Active' if current_status['monitoring_active'] else 'Inactive'}")
            
            except KeyboardInterrupt:
                print("\n\n🛑 Stopping monitoring...")
                auto_installer.stop_monitoring()
                print("✅ Monitoring stopped successfully.")
        
        else:
            print("\n✅ Setup complete. Files processed but monitoring not started.")
            print("💡 You can run this script again to check for new files.")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("🎉 Auto Setup Complete!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())
