"""
Build script for LAN File Transfer System
Creates standalone executables for both client and server applications
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def clean_build_artifacts():
    """Clean previous build artifacts"""
    print("Cleaning previous build artifacts...")
    
    # Remove build directories
    build_dirs = ['build', 'dist', '__pycache__']
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Removed {dir_name}")
    
    # Remove spec files
    spec_files = [f for f in os.listdir('.') if f.endswith('.spec')]
    for spec_file in spec_files:
        os.remove(spec_file)
        print(f"Removed {spec_file}")

def build_executable(script_name, exe_name, hidden_imports=None):
    """Build executable using PyInstaller"""
    print(f"\nBuilding {exe_name}...")
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',  # No console window
        f'--name={exe_name}',
        '--clean',
        '--noconfirm'
    ]
    
    # Add hidden imports
    if hidden_imports:
        for import_name in hidden_imports:
            cmd.extend(['--hidden-import', import_name])
    
    # Add data files if needed
    if os.path.exists('ui'):
        cmd.extend(['--add-data', 'ui;ui'])
    if os.path.exists('network'):
        cmd.extend(['--add-data', 'network;network'])
    if os.path.exists('utils'):
        cmd.extend(['--add-data', 'utils;utils'])
    
    cmd.append(script_name)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ {exe_name} built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to build {exe_name}")
        print(f"Error: {e.stderr}")
        return False

def build_simple_executable(script_name, exe_name):
    """Build simple executable with minimal dependencies"""
    print(f"\nBuilding {exe_name} (simple version)...")
    
    cmd = [
        'pyinstaller',
        '--onefile',
        f'--name={exe_name}',
        '--clean',
        '--noconfirm',
        '--hidden-import=PyQt5.QtCore',
        '--hidden-import=PyQt5.QtWidgets',
        '--hidden-import=PyQt5.QtGui',
        script_name
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ {exe_name} built successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to build {exe_name}")
        print(f"Error: {e.stderr}")
        return False

def verify_dependencies():
    """Verify required dependencies are installed"""
    print("Verifying dependencies...")
    
    required_packages = ['PyQt5', 'pyinstaller']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} found")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} missing")
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install " + " ".join(missing_packages))
        return False
    
    return True

def create_distribution_structure():
    """Create clean distribution structure"""
    print("\nCreating distribution structure...")
    
    # Create dist directory if it doesn't exist
    dist_dir = Path('dist')
    dist_dir.mkdir(exist_ok=True)
    
    # Create received_files directory for client
    received_files_dir = dist_dir / 'received_files'
    received_files_dir.mkdir(exist_ok=True)
    
    print("✓ Distribution structure created")

def main():
    """Main build process"""
    print("=" * 60)
    print("LAN File Transfer System - Build Script")
    print("=" * 60)
    
    # Change to script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Verify dependencies
    if not verify_dependencies():
        sys.exit(1)
    
    # Clean previous builds
    clean_build_artifacts()
    
    # Create distribution structure
    create_distribution_structure()
    
    # Build executables
    builds_successful = []
    
    # Build main applications (if source files exist)
    if os.path.exists('client_app.py'):
        hidden_imports = [
            'PyQt5.QtCore',
            'PyQt5.QtWidgets', 
            'PyQt5.QtGui',
            'network.discovery',
            'network.protocol',
            'ui.client_ui'
        ]
        success = build_executable('client_app.py', 'LAN_Client', hidden_imports)
        builds_successful.append(('LAN_Client', success))
    
    if os.path.exists('server_app.py'):
        hidden_imports = [
            'PyQt5.QtCore',
            'PyQt5.QtWidgets',
            'PyQt5.QtGui', 
            'network.discovery',
            'network.protocol',
            'ui.server_ui'
        ]
        success = build_executable('server_app.py', 'LAN_Server', hidden_imports)
        builds_successful.append(('LAN_Server', success))
    
    # Build simple versions (if source files exist)
    if os.path.exists('simple_client.py'):
        success = build_simple_executable('simple_client.py', 'SimpleClient')
        builds_successful.append(('SimpleClient', success))
    
    if os.path.exists('simple_server_fixed.py'):
        success = build_simple_executable('simple_server_fixed.py', 'SimpleServer')
        builds_successful.append(('SimpleServer', success))
    
    # Summary
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)
    
    successful_builds = []
    failed_builds = []
    
    for name, success in builds_successful:
        if success:
            successful_builds.append(name)
            print(f"✓ {name}.exe")
        else:
            failed_builds.append(name)
            print(f"✗ {name}.exe")
    
    if successful_builds:
        print(f"\n✓ Successfully built {len(successful_builds)} executable(s)")
        print("Executables are available in the 'dist' folder")
    
    if failed_builds:
        print(f"\n✗ Failed to build {len(failed_builds)} executable(s)")
        print("Check the error messages above for details")
    
    # List final files
    if os.path.exists('dist'):
        print(f"\nFinal files in dist folder:")
        for file in os.listdir('dist'):
            if file.endswith('.exe'):
                file_path = Path('dist') / file
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"  {file} ({size_mb:.1f} MB)")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
