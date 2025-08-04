# LAN File Transfer System

A simple and reliable LAN-based file transfer system with automatic installer execution.

## Features

- **Auto-Discovery**: Clients automatically discover servers on the local network
- **Binary-Safe Transfer**: Files transfer without corruption (PNG, EXE, etc.)
- **Silent Installation**: EXE and MSI files automatically install after transfer
- **Progress Tracking**: Real-time transfer progress feedback
- **Multi-Client Support**: Server can handle multiple connected clients

## Quick Start

### 1. Run Server
- Execute: `SimpleServer_BinaryFixed.exe`
- Click "Start Server" button
- Server will start on ports 5000 (TCP) and 5001 (UDP)

### 2. Run Client
- Execute: `SimpleClient_ProtocolFixed.exe`
- Client will automatically discover and show available servers
- Click "Connect" to connect to a server

### 3. Transfer Files
- On server: Select file → Choose connected clients → Send
- Files are saved to `received_files\` folder on client
- EXE/MSI files automatically install silently

## Technical Details

- **Discovery Protocol**: UDP broadcast on port 5001
- **File Transfer**: TCP on port 5000 with binary integrity
- **Supported Installers**: .exe, .msi (with /S silent flag)
- **Chunk Size**: 8192 bytes for optimal performance
- **Timeout**: 30 seconds per operation

## Files Structure

```
lan2/
├── dist/
│   ├── SimpleServer_BinaryFixed.exe    # Final server executable
│   └── SimpleClient_ProtocolFixed.exe  # Final client executable
├── simple_server_fixed.py              # Server source code
├── simple_client.py                    # Client source code
├── requirements.txt                    # Python dependencies
└── README.md                          # This file
```

## Requirements

- Windows 10/11
- Local network connectivity
- No additional dependencies (executables are standalone)

## Troubleshooting

- **No servers found**: Check firewall settings, ensure both devices on same network
- **File corruption**: Use the latest executables with binary-safe protocol
- **Installation fails**: Ensure installer supports /S silent flag

---
Built with Python 3.13 and PyQt5
