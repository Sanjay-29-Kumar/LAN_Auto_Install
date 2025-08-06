# LAN Software Automation Installation Guide

## Prerequisites

- Python 3.8 or higher
- Network connectivity between admin and client machines
- Administrative privileges (for software installation)

## Installation Steps

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. System Setup

#### For Windows:
- Ensure Windows Firewall allows the application
- Run as Administrator for software installation privileges

#### For Linux:
- Ensure proper permissions for software installation
- May need to configure sudo access for package managers

#### For macOS:
- Ensure Gatekeeper settings allow the application
- May need to grant accessibility permissions

## Usage Instructions

### Starting the Admin Application

1. **Run the admin application:**
   ```bash
   python start_admin.py
   ```
   or
   ```bash
   python admin_app.py
   ```

2. **Admin Interface Features:**
   - **Client Discovery**: Automatically discovers clients on the network
   - **File Selection**: Choose software files to install (.exe, .msi, .deb, .rpm, .zip, .tar.gz)
   - **Client Management**: Select target clients for installation
   - **Real-time Monitoring**: View installation progress and status
   - **Activity Logs**: Track all installation activities

### Starting the Client Agent

1. **Run the client agent on each target machine:**
   ```bash
   python start_client.py
   ```
   or
   ```bash
   python client_agent.py
   ```

2. **Client Agent Features:**
   - **Consent Management**: One-time consent for network participation
   - **Silent Installation**: Installations run without user notification
   - **Status Reporting**: Sends installation status back to admin
   - **Background Operation**: Runs in background after consent

## Step-by-Step Workflow

### 1. Network Setup
- Ensure all machines are on the same LAN network
- Verify network connectivity between admin and clients

### 2. Client Preparation
- Install Python and dependencies on all client machines
- Run the client agent on each target machine
- Grant consent when prompted (one-time only)

### 3. Admin Setup
- Install Python and dependencies on admin machine
- Run the admin application
- Wait for clients to appear in the discovery list

### 4. Software Installation
- Select software file to install
- Choose target clients from the list
- Click "Install Software" to start installation
- Monitor progress in real-time

## Supported File Types

### Windows
- `.exe` - Executable installers
- `.msi` - Microsoft Installer packages
- `.zip` - Compressed archives

### Linux
- `.deb` - Debian/Ubuntu packages
- `.rpm` - Red Hat/CentOS packages
- `.tar.gz` - Compressed archives
- `.sh` - Shell scripts

### Cross-platform
- `.zip` - Compressed archives

## Security Features

### Encryption
- All network communication is encrypted
- File transfers use secure encryption
- Authentication tokens for command verification

### User Consent
- Clients must explicitly consent to join the network
- Consent can be revoked at any time
- No installations without user consent

### Audit Logging
- All installation activities are logged
- Admin can view detailed installation history
- Error tracking and reporting

## Troubleshooting

### Common Issues

#### Client Not Appearing in Admin List
- Check network connectivity
- Verify firewall settings
- Ensure client agent is running
- Check if consent was granted

#### Installation Failures
- Verify file format is supported
- Check file integrity
- Ensure proper permissions
- Review installation logs

#### Network Communication Issues
- Check port availability (5000, 5001)
- Verify network configuration
- Ensure no antivirus blocking communication

### Debug Mode

Enable debug logging by modifying `config.py`:
```python
LOG_LEVEL = "DEBUG"
```

### Log Files

Logs are stored in:
- Windows: `%USERPROFILE%\.lan_automation\lan_automation.log`
- Linux/macOS: `~/.lan_automation/lan_automation.log`

## Advanced Configuration

### Customizing Network Ports

Edit `config.py` to change default ports:
```python
DISCOVERY_PORT = 5000      # UDP broadcast port
COMMUNICATION_PORT = 5001  # TCP communication port
```

### File Size Limits

Modify maximum file size in `config.py`:
```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB default
```

### Security Settings

Change encryption key in `config.py`:
```python
ENCRYPTION_KEY = "YOUR_CUSTOM_KEY_HERE"
```

## Example Usage Scenarios

### Scenario 1: Office Software Deployment
1. Admin selects office software installer
2. Chooses all office computers from client list
3. Initiates installation
4. Monitors progress across all machines

### Scenario 2: Security Update Deployment
1. Admin selects security patch file
2. Targets specific departments or machines
3. Schedules installation during off-hours
4. Tracks completion status

### Scenario 3: Development Environment Setup
1. Admin packages development tools
2. Selects developer workstations
3. Deploys consistent development environment
4. Verifies installation success

## Best Practices

### Security
- Use strong encryption keys in production
- Regularly update the application
- Monitor installation logs for anomalies
- Implement network segmentation if needed

### Performance
- Limit concurrent installations on large networks
- Use appropriate file compression for large packages
- Monitor network bandwidth usage
- Schedule installations during off-peak hours

### Maintenance
- Regularly backup configuration files
- Update client agents when deploying new features
- Monitor system resources during installations
- Keep installation packages updated

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review log files for error details
3. Verify network and system requirements
4. Test with sample installer in examples directory

## License

This software is provided as-is for educational and development purposes.
Use at your own risk in production environments. 