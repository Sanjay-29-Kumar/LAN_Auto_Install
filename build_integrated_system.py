#!/usr/bin/env python3
"""
Integrated LAN Auto Install System Builder v2.1
Builds client with integrated auto setup and server
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    """Build the integrated LAN Auto Install system"""
    print("=" * 80)
    print("🚀 Building Integrated LAN Auto Install System v2.1")
    print("✨ Features: CLIENT WITH INTEGRATED AUTO SETUP")
    print("=" * 80)
    
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist_integrated"
    
    try:
        # Clean previous builds
        if dist_dir.exists():
            print("🧹 Cleaning previous builds...")
            shutil.rmtree(dist_dir)
        
        dist_dir.mkdir(exist_ok=True)
        
        # Build specifications - Only client and server
        builds = [
            {
                "name": "LAN_Install_Integrated_Client_v2.1",
                "script": "working_client.py",
                "description": "Client with Integrated Auto Setup (No Separate Tool Needed)"
            },
            {
                "name": "LAN_Install_Integrated_Server_v2.1", 
                "script": "working_server.py",
                "description": "Server for File Distribution"
            }
        ]
        
        print("\n🔨 Building executables...")
        
        for build in builds:
            print(f"\n📦 Building {build['name']}...")
            print(f"   📋 {build['description']}")
            
            # PyInstaller command with enhanced options
            cmd = [
                "pyinstaller",
                "--onefile",
                "--windowed" if "client" in build["name"].lower() or "server" in build["name"].lower() else "--console",
                "--name", build["name"],
                "--distpath", str(dist_dir),
                "--workpath", str(project_root / "build_temp"),
                "--specpath", str(project_root),
                "--add-data", f"{project_root / 'utils'}:utils",
                "--hidden-import", "PyQt5.QtCore",
                "--hidden-import", "PyQt5.QtWidgets", 
                "--hidden-import", "PyQt5.QtGui",
                "--hidden-import", "utils.dynamic_installer",
                "--hidden-import", "utils.installer",
                build["script"]
            ]
            
            print(f"   🔧 Running: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                exe_path = dist_dir / f"{build['name']}.exe"
                if exe_path.exists():
                    size_mb = exe_path.stat().st_size / (1024 * 1024)
                    print(f"   ✅ Built successfully: {build['name']}.exe ({size_mb:.1f} MB)")
                else:
                    print(f"   ❌ Build completed but executable not found")
            else:
                print(f"   ❌ Build failed:")
                print(f"   Error: {result.stderr}")
                continue
        
        # Create README for the integrated system
        readme_content = """# Integrated LAN Auto Install System v2.1

## 🚀 CLIENT WITH INTEGRATED AUTO SETUP

This integrated version provides **IMMEDIATE AUTOMATIC INSTALLATION** with **NO SEPARATE TOOLS NEEDED**.

## 📦 Components

### 1. LAN_Install_Integrated_Client_v2.1.exe
- **All-in-One Client** with integrated auto setup functionality
- Automatically processes existing installer files on startup
- Starts continuous monitoring automatically (10-second intervals)
- Immediately installs received files using robust silent installation
- Creates `received_files` folder in the same directory as the executable
- Professional modern UI with real-time status updates

### 2. LAN_Install_Integrated_Server_v2.1.exe  
- **Server** for file distribution to multiple clients
- Real-time client connection monitoring
- Professional modern UI

## 🎯 Key Features

### ✅ INTEGRATED AUTO SETUP
- **No separate auto setup tool needed**
- Client automatically processes existing files on startup
- Starts continuous monitoring automatically
- `received_files` folder created wherever the executable is located

### ✅ IMMEDIATE AUTO-INSTALLATION
- Files are installed **IMMEDIATELY** upon receipt
- No user confirmation or manual steps required
- Multiple silent installation methods with fallbacks:
  - `/SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
  - `/S /silent /quiet /norestart`
  - `/quiet /passive /norestart`
  - `-s -q --silent`
  - `msiexec /i [file] /quiet /norestart` (for MSI files)

### ✅ FLEXIBLE DEPLOYMENT
- `received_files` folder created in executable directory
- Works from Downloads, Desktop, or any folder
- No fixed path dependencies

## 🚀 Usage

### Simple Deployment
1. **Server**: Run `LAN_Install_Integrated_Server_v2.1.exe`
2. **Client**: Run `LAN_Install_Integrated_Client_v2.1.exe` 
   - Automatically processes any existing installer files
   - Starts monitoring for new files
   - Creates `received_files` folder in same directory

### File Distribution
1. Server: Click "Add Files" to select installers
2. Server: Click "Send to All" to distribute
3. **Clients automatically install received files immediately**

## 📁 File Organization
Files are organized relative to executable location:
- `[exe_location]/received_files/installers/` - Executable installers (.exe, .msi, .msix)
- `[exe_location]/received_files/files/documents/` - Document files
- `[exe_location]/received_files/files/media/` - Media files  
- `[exe_location]/received_files/files/archives/` - Archive files

## 🎉 Result
**Received executables are automatically installed and ready to use immediately!**

---
Built with Integrated LAN Auto Install System v2.1
"""
        
        readme_path = dist_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"\n📄 Created README.md")
        
        # Clean up build artifacts
        build_temp = project_root / "build_temp"
        if build_temp.exists():
            shutil.rmtree(build_temp)
        
        # Remove .spec files
        for spec_file in project_root.glob("*.spec"):
            if "integrated" in spec_file.name.lower():
                spec_file.unlink()
        
        print("\n" + "=" * 80)
        print("🎉 INTEGRATED BUILD COMPLETE!")
        print("=" * 80)
        print(f"📁 Output directory: {dist_dir}")
        print("\n📦 Built executables:")
        
        for exe_file in dist_dir.glob("*.exe"):
            size_mb = exe_file.stat().st_size / (1024 * 1024)
            print(f"   ✅ {exe_file.name} ({size_mb:.1f} MB)")
        
        print(f"\n📄 Documentation: {readme_path}")
        print("\n🚀 INTEGRATED FEATURES:")
        print("   ✅ Client has integrated auto setup (no separate tool needed)")
        print("   ✅ received_files folder created in executable directory")
        print("   ✅ IMMEDIATE automatic installation upon file receipt")
        print("   ✅ NO manual intervention required")
        print("   ✅ Multiple silent installation fallback methods")
        print("   ✅ Professional modern UI with real-time updates")
        print("   ✅ Ready for production deployment")
        
        print("\n🎯 DEPLOYMENT:")
        print("   📁 Server: LAN_Install_Integrated_Server_v2.1.exe")
        print("   💻 Client: LAN_Install_Integrated_Client_v2.1.exe (with integrated auto setup)")
        print("   🚀 Files install automatically wherever executable is located!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
