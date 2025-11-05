# LAN Auto Install Project: Features and Workflow

The LAN Auto Install project is an automated system designed to simplify and streamline software installation across a local area network (LAN). Its primary goal is to allow administrators to silently install applications on multiple client machines without any manual intervention from the end-users.

## How it Works: Core Functionality

### 1. Automatic Discovery (Zero-Configuration Networking)

*   When a client machine starts, it automatically broadcasts a signal (using UDP on Port 5001) on the network to find available servers.
*   Servers on the network listen for these broadcasts and respond, making themselves known to the clients.
*   This means there's no need to manually configure IP addresses or server locations; clients find servers automatically.
*   Once a server is discovered, the client establishes a reliable connection (using TCP on Port 5000) to it.

### 2. Software Distribution

*   The server application provides a graphical interface where an administrator can select software packages (e.g., installers for Nmap, Chrome, LocalSend, or any other application).
*   The administrator can then choose which connected client(s) to send these files to.
*   The server sends the selected software to the client(s) using a robust file transfer protocol (TCP on Port 5002). This transfer happens in chunks (2MB each) and includes metadata like the filename and size.

### 3. Intelligent Silent Installation on Clients

*   Once a client receives a software package, it doesn't just store it; it automatically initiates the installation process.
*   **Intelligent Installer Detection**: The system identifies the type of installer (e.g., MSI, EXE, NSIS) and uses specific, pre-configured commands (silent switches) to run the installation without any pop-ups or user interaction.
*   **Multiple Fallback Methods**: If one silent installation method fails, the system automatically tries several other methods (typically 4-6 different approaches) to ensure the software gets installed successfully. This significantly increases the compatibility with various installers.
*   **Duplicate Prevention**: To avoid unnecessary re-installations, the system uses cryptographic hashing (SHA256) to identify if a file has already been received and installed. It also tracks installation history and prevents immediate retries for failed installations, using a cooldown period to avoid infinite loops.

## Key Features & Innovations

*   **Zero-Click Operation**: From discovery to installation, the entire process is automated, requiring no user interaction on the client side.
*   **Robust File Transfer**: Files are transferred reliably in chunks, with built-in error recovery and progress tracking.
*   **Professional User Interface (UI)**: Both the client and server applications feature a modern, dark-themed graphical interface built with PyQt5. This UI provides real-time status updates, connection statuses, and visual feedback (like progress bars and emojis) to keep administrators informed.
*   **Standalone Executables**: The entire system is packaged into standalone `.exe` files using PyInstaller. This means you don't need Python installed on the client or server machines; you just copy and run the application.
*   **Comprehensive System Information**: The system can gather detailed information about client machines, including hardware, operating system, and installed software.
*   **Scalable Architecture**: Designed to handle multiple clients efficiently and concurrently, making it suitable for enterprise environments.
*   **Detailed Logging**: Provides a full audit trail of all operations, which is crucial for troubleshooting and compliance.

## Virus Scanning Feature

The LAN Auto Install project includes a **Virus Scanning** feature designed to enhance the security of the software distribution process. This feature ensures that files received by client machines are checked for malicious content before they are installed.

Here's how the Virus Scanning feature works:

1.  **Integration with File Reception**: When a client machine receives a software package or any file from the server, the system doesn't immediately proceed with installation. Instead, the received file is first directed to the virus scanning component.

2.  **Scanning Process**:
    *   The `utils/virus_scanner.py` module is responsible for the core logic of the virus scan. It likely integrates with an underlying antivirus engine or uses signature-based detection to identify known threats.
    *   The `ui/virus_scan_widget.py` module provides the user interface elements related to the virus scan, allowing users (or administrators) to see the status of the scan, any detected threats, and the outcome.

3.  **Threat Detection and Action**:
    *   If the virus scanner detects any malicious content or suspicious patterns within the received file, it will flag the file as infected.
    *   Upon detection of a threat, the system is designed to take appropriate action, which could include:
        *   **Quarantining the file**: Moving the suspicious file to a secure, isolated location to prevent it from causing harm.
        *   **Deleting the file**: Removing the malicious file entirely.
        *   **Alerting the user/administrator**: Providing a clear notification through the UI about the detected threat and the action taken.
        *   **Preventing installation**: Crucially, the automatic installation process for that specific file would be halted to prevent the execution of potentially harmful software.

4.  **Security Status Updates**: The `ui/security_status.py` module likely works in conjunction with the virus scanner to display the overall security posture of the client, including the results of recent scans and any pending security alerts.
