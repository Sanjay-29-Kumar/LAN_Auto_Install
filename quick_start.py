#!/usr/bin/env python3
"""
Quick Start Script for LAN Software Automation System
This script helps users get started with the system.
"""

import os
import sys
import subprocess
import platform
import time

def print_banner():
    """Print welcome banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                LAN Software Automation System                ║
║                        Quick Start Guide                     ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"   Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    else:
        print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
        return True

def check_dependencies():
    """Check if required dependencies are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = ['cryptography', 'tkinter']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        return False

def check_files():
    """Check if all required files are present"""
    print("\n📁 Checking required files...")
    
    required_files = [
        'config.py',
        'security.py',
        'network_manager.py',
        'installer.py',
        'gui_components.py',
        'admin_app.py',
        'client_agent.py'
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} - Missing")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n❌ Missing files: {', '.join(missing_files)}")
        return False
    
    return True

def show_menu():
    """Show main menu"""
    menu = """
╔══════════════════════════════════════════════════════════════╗
║                        Main Menu                             ║
╠══════════════════════════════════════════════════════════════╣
║ 1. Start Admin Application                                   ║
║ 2. Start Client Agent                                        ║
║ 3. Install Dependencies                                      ║
║ 4. Run System Check                                          ║
║ 5. View Documentation                                        ║
║ 6. Exit                                                      ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(menu)

def start_admin():
    """Start admin application"""
    print("\n🚀 Starting Admin Application...")
    try:
        from admin_app import main
        main()
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("   Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Error starting admin application: {e}")

def start_client():
    """Start client agent"""
    print("\n🚀 Starting Client Agent...")
    try:
        from client_agent import main
        main()
    except ImportError as e:
        print(f"❌ Error: {e}")
        print("   Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Error starting client agent: {e}")

def run_system_check():
    """Run comprehensive system check"""
    print("\n🔍 Running System Check...")
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Files", check_files),
        ("Dependencies", check_dependencies)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n--- {check_name} ---")
        if not check_func():
            all_passed = False
    
    if all_passed:
        print("\n✅ All checks passed! System is ready to use.")
    else:
        print("\n❌ Some checks failed. Please resolve issues before proceeding.")
    
    return all_passed

def show_documentation():
    """Show documentation links"""
    docs = """
╔══════════════════════════════════════════════════════════════╗
║                        Documentation                         ║
╠══════════════════════════════════════════════════════════════╣
║ 📖 README.md              - Main documentation               ║
║ 📋 INSTALLATION_GUIDE.md  - Detailed installation guide     ║
║ 📁 examples/              - Sample installers and examples   ║
║                                                              ║
║ Quick Start:                                                ║
║ 1. Install dependencies: pip install -r requirements.txt    ║
║ 2. Run client agents on target machines                     ║
║ 3. Run admin application on control machine                 ║
║ 4. Select software and target clients                       ║
║ 5. Start installation                                       ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(docs)

def main():
    """Main function"""
    print_banner()
    
    # Check if running as admin (Windows)
    if platform.system() == "Windows":
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                print("⚠️  Warning: Not running as Administrator")
                print("   Some features may require admin privileges")
        except:
            pass
    
    while True:
        show_menu()
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            start_admin()
        elif choice == '2':
            start_client()
        elif choice == '3':
            install_dependencies()
        elif choice == '4':
            run_system_check()
        elif choice == '5':
            show_documentation()
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-6.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("Press Enter to exit...") 