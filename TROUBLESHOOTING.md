# Troubleshooting Guide

## Network Discovery Issues

### Problem: Client not discovered by Admin

**Symptoms:**
- Admin panel shows "No clients found"
- Client agent is running but not appearing in admin list

**Solutions:**

1. **Check Network Connectivity:**
   ```bash
   python test_network.py
   ```

2. **Verify Both Machines are on Same Network:**
   - Both machines should have IP addresses in the same subnet
   - Example: 192.168.1.x or 10.0.0.x

3. **Check Windows Firewall:**
   - Open Windows Defender Firewall
   - Allow Python through firewall
   - Or temporarily disable firewall for testing

4. **Run as Administrator:**
   - Right-click on Command Prompt/PowerShell
   - Select "Run as administrator"
   - Navigate to project directory and run the application

5. **Check Antivirus Software:**
   - Some antivirus software blocks network access
   - Add Python to antivirus exceptions

6. **Test Network Discovery:**
   ```bash
   # On Admin machine
   python test_network.py
   
   # On Client machine
   python test_network.py
   ```

## File Transfer Issues

### Problem: File transfer fails with "Chunk not acknowledged"

**Symptoms:**
- File transfer starts but fails during transfer
- Error messages about chunks or decryption

**Solutions:**

1. **Check File Size:**
   - Ensure file is not larger than 100MB
   - Try with a smaller test file first

2. **Test Encryption:**
   ```bash
   python test_binary_encryption.py
   ```

3. **Check Network Stability:**
   - Ensure stable network connection
   - Avoid transferring during network congestion

4. **Verify File Permissions:**
   - Ensure admin has read access to source file
   - Ensure client has write access to destination

## Common Error Messages

### "Failed to start discovery broadcaster"
- **Cause:** Port 5000 already in use
- **Solution:** Restart the application or change port in config.py

### "Client not ready for file transfer"
- **Cause:** Client communication server not running
- **Solution:** Ensure client agent is started and consent is given

### "Decryption error"
- **Cause:** Network data corruption or encryption mismatch
- **Solution:** Restart both admin and client applications

### "Connection refused"
- **Cause:** Firewall blocking connection
- **Solution:** Allow Python through Windows Firewall

## Step-by-Step Debugging

1. **Start with Network Test:**
   ```bash
   python test_network.py
   ```

2. **Test Encryption:**
   ```bash
   python test_binary_encryption.py
   ```

3. **Test File Transfer:**
   ```bash
   python test_file_transfer.py
   ```

4. **Check Application Logs:**
   - Look for error messages in the application window
   - Check console output for detailed errors

## Network Configuration

### Required Ports:
- **Port 5000:** Discovery (UDP)
- **Port 5001:** Communication (TCP)

### Firewall Rules:
```
Allow Python.exe:
- Inbound: Ports 5000-5001
- Outbound: Ports 5000-5001
- Protocol: TCP and UDP
```

## Advanced Troubleshooting

### Enable Debug Mode:
Add debug logging to see detailed network activity:

```python
# In config.py
DEBUG_MODE = True
```

### Test with Different File Types:
- Start with small text files (.txt)
- Then try larger files
- Finally test with executable files

### Network Isolation Test:
- Disconnect from internet
- Use only local network
- Test with direct IP connection

## Getting Help

If issues persist:

1. **Collect Debug Information:**
   - Run `python test_network.py` on both machines
   - Note any error messages
   - Check Windows Event Viewer for network errors

2. **System Information:**
   - Windows version
   - Python version
   - Network adapter type
   - Firewall/antivirus software

3. **Network Configuration:**
   - IP addresses of both machines
   - Subnet mask
   - Gateway address 