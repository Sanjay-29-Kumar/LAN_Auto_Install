# LAN Software Automation Installation System

A complete desktop application for automated software installation across LAN networks.

## 🚀 Quick Start

### Windows Users
Simply double-click `run_app.bat` to start the application!

### Linux/macOS Users
```bash
./run_app.sh
```

### Manual Start
```bash
python app.py
```

## ✨ Features

- **🔧 Admin Panel**: Control software installations across the network
- **💻 Client Agent**: Join network for silent installations
- **🔐 Security**: Encrypted communication and user consent
- **🌐 Network Discovery**: Automatic client detection
- **📊 Real-time Monitoring**: Live installation progress tracking
- **📋 Audit Logging**: Complete activity history

## 📋 System Requirements

- Python 3.8 or higher
- Network connectivity between machines
- Administrative privileges (for software installation)

## 🛠️ Installation

1. **Install Python Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application:**
   - Windows: Double-click `run_app.bat`
   - Linux/macOS: Run `./run_app.sh`
   - Manual: `python app.py`

## 🎯 How It Works

### 1. Start the Application
Launch the main application which provides a unified interface for both admin and client modes.

### 2. Choose Your Mode
- **Admin Panel**: For controlling software installations
- **Client Agent**: For receiving installations

### 3. Network Discovery
The system automatically discovers clients on the same LAN network.

### 4. Software Installation
- Select software files (.exe, .msi, .deb, .rpm, .zip, .tar.gz)
- Choose target clients
- Monitor installation progress in real-time

## 🔐 Security Features

- **Encrypted Communication**: All network traffic is encrypted
- **User Consent**: Clients must explicitly consent to join the network
- **File Integrity**: SHA256 hash verification for all files
- **Audit Logging**: Complete activity tracking

## 📁 File Structure

```
LAN_MK/
├── app.py                    # Main application launcher
├── run_app.bat              # Windows launcher
├── run_app.sh               # Linux/macOS launcher
├── admin_app.py             # Admin control panel
├── client_agent.py          # Client background service
├── network_manager.py       # Network communication
├── installer.py             # Software installation engine
├── security.py              # Encryption and authentication
├── gui_components.py        # GUI components
├── config.py                # Configuration settings
├── requirements.txt         # Python dependencies
└── examples/                # Sample files
    └── sample_installer.py  # Example installer
```

## 🎮 Usage

### Admin Mode
1. Click "🖥️ Admin Panel" to start the admin interface
2. Wait for clients to appear in the discovery list
3. Select software files to install
4. Choose target clients
5. Monitor installation progress

### Client Mode
1. Click "💻 Client Agent" to start the client service
2. Grant consent when prompted (one-time only)
3. The agent runs in background, waiting for admin commands
4. Installations happen silently without user notification

## 🔧 Supported Platforms

### Operating Systems
- ✅ Windows 10/11
- ✅ Linux (Ubuntu, CentOS, etc.)
- ✅ macOS

### File Types Supported
- ✅ **Installers**: .exe, .msi, .deb, .rpm, .sh, .zip, .tar.gz
- ✅ **Documents**: .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt
- ✅ **Media**: .jpg, .jpeg, .png, .gif, .mp3, .mp4, .avi, .mkv
- ✅ **Code**: .py, .js, .html, .css, .json, .xml
- ✅ **Archives**: .zip, .rar, .7z, .tar.gz
- ✅ **Any File Type**: The system now supports ALL file types!

### File Transfer Features
- ✅ **Large Files**: Up to 100MB per file
- ✅ **Chunked Transfer**: Reliable transfer of large files
- ✅ **Progress Tracking**: Real-time transfer progress
- ✅ **Integrity Check**: SHA256 hash verification
- ✅ **Encrypted Transfer**: All data encrypted in transit

## 🛠️ Troubleshooting

### Common Issues

**Application won't start:**
- Ensure Python 3.8+ is installed
- Run `pip install -r requirements.txt`
- Check if all files are present

**Network issues:**
- Verify all machines are on the same LAN
- Check firewall settings
- Ensure ports 5000 and 5001 are available

**Installation failures:**
- Verify file format is supported
- Check file integrity
- Ensure proper permissions

### Getting Help

1. Check the application log for error details
2. Review the troubleshooting section in `INSTALLATION_GUIDE.md`
3. Verify system requirements are met

## 📖 Documentation

- `INSTALLATION_GUIDE.md` - Detailed setup instructions
- `PROJECT_SUMMARY.md` - Complete project overview
- `examples/` - Sample files and usage examples

## 🔒 Security Notice

This software is designed for educational and development purposes. Use in production environments at your own risk. Always ensure proper network security and user consent.

## 📄 License

MIT License - Free to use and modify

---

**Ready to automate your software deployments?** 🚀

Just run `run_app.bat` (Windows) or `./run_app.sh` (Linux/macOS) to get started! 