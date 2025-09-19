LAN AUTO INSTALLATION SYSTEM – PROJECT REPORT

ABSTRACT
The LAN Auto Installation System automates device discovery, secure artifact transfer, and silent installation across a local network. It reduces manual effort, improves consistency, and provides progress visibility with acknowledgments and telemetry. The platform comprises discovery, client/server networking, transfer, installation automation, and a desktop UI for operators. This report documents requirements, architecture, protocol design, algorithms, implementation details, testing, performance, and operational guidance. It also captures lessons learned and troubleshooting for rapid, reliable deployments on typical enterprise LANs.

LIST OF ABBREVIATIONS
- LAN: Local Area Network
- DHCP: Dynamic Host Configuration Protocol
- DNS: Domain Name System
- ARP: Address Resolution Protocol
- ICMP: Internet Control Message Protocol
- TCP: Transmission Control Protocol
- UDP: User Datagram Protocol
- SSH: Secure Shell
- SMB: Server Message Block
- WinRM: Windows Remote Management
- API: Application Programming Interface
- GUI: Graphical User Interface
- CLI: Command-Line Interface
- DBMS: Database Management System
- DFD: Data Flow Diagram
- TLS: Transport Layer Security
- JSON: JavaScript Object Notation
- KPI: Key Performance Indicator

1 INTRODUCTION
The LAN Auto Installation System addresses the operational need to provision and validate many endpoints consistently and quickly. Manual deployment is slow, error-prone, and difficult to audit. By automating discovery, transfer, execution, and verification with an operator UI, the system shortens rollout time while increasing reliability and visibility.

1.1 SIGNIFICANCE OF THE PROJECT
- Reduces manual labor and minimizes human error.
- Enables standardized, repeatable installations across heterogeneous devices.
- Scales to larger environments via broadcast discovery and concurrent transfers.
- Improves visibility with progress events, acknowledgments, and logs.
- Integrates with OS tooling for silent/sandboxed installs and supports future API integrations.

1.2 OVERVIEW OF LAN AUTO INSTALLATION SYSTEM
Core capabilities:
- Network Discovery: Broadcast-based discovery with targeted unicast to likely hosts on the same subnet.
- Configuration & Execution: Silent installer execution and post-install validation via a client agent.
- File Distribution: Reliable, chunked TCP transfers with metadata, acknowledgments, and adaptive timeouts.
- Monitoring & Telemetry: Real-time UI, per-file progress, final status, and local logs for auditing.
- Operator Interface: Desktop GUI for orchestration (server and client views).

1.3 TOOLS AND TECHNOLOGIES USED
- Language: Python 3.x
- Networking: socket (UDP discovery, TCP command/transfer)
- Concurrency: threading for discovery, IO, and background tasks
- Packaging: optional executable builds (scripted)
- Data Formats: JSON for protocol messages and configuration
- GUI: PyQt-based desktop UI
- Security/Integrity: hash verification hooks, AV scan integration on server side
- OS Integration: Windows shell/PowerShell, scheduler for elevated silent installs

1.4 IMPORTANCE OF AUTOMATION IN NETWORK MANAGEMENT
Automation reduces repetitive effort, enforces standards, and provides predictable outcomes at scale.

1.4.1 AUTOMATED NETWORK DISCOVERY
- UDP broadcast discovery with multiple strategies to reach servers on common LAN topologies.
- JSON advertisements returned by servers describe availability and connection port.

1.4.2 REDUCED INSTALLATION TIME
- Parallel discovery and concurrent transfers reduce end-to-end rollout time.
- Silent installers with standardized flags avoid manual prompts.

1.4.3 MINIMIZED HUMAN ERROR
- Deterministic workflows and standardized configurations limit manual variation.
- Built-in validations and post-install checks surface issues early.

1.4.4 SCALABLE NETWORK DEPLOYMENT
- Broadcast discovery and multi-client distribution support multiple endpoints per batch.
- Resumable, idempotent operations reduce repetition under transient failures.

1.4.5 INTEGRATION WITH NETWORK MANAGEMENT SYSTEMS
- Log and status exports for ingestion by CMDB/monitoring systems (extensible).

1.4.6 REAL-TIME MONITORING AND CONFIGURATION
- Operator UI displays discovery, connection, progress, and results.

2 LITERATURE SURVEY
- Discovery: ARP/ICMP sweep, UDP broadcast, and service probing over TCP are common patterns.
- Configuration & Install: Desired state configuration, template engines, and silent installer conventions.
- Remote Execution: SSH/WinRM/agent architectures; agents simplify firewalling and reliability.
- Deployment Strategies: Staged rollouts with validation checkpoints.
- Best Practices: Secure credential storage, transport security, and tamper-evident logging.

3 PROBLEM DESCRIPTION
Manual LAN-wide deployment is slow, inconsistent, and difficult to audit. A system is needed to discover devices, distribute artifacts reliably, execute installations silently, and verify outcomes with minimal operator intervention.

3.1 PROBLEM STATEMENT
Design and implement an automated system to discover LAN devices, connect to them, transfer and execute installers silently, and report success/failure in real time with audit logs.

3.2 OVERVIEW OF THE PROJECT
The solution uses a client/server architecture: a server orchestrates discovery and distribution; clients auto-connect upon discovery, receive files, run installers, and send acknowledgments and status updates.

3.3 MODULE DESCRIPTION
The system comprises five major modules.

3.3.1 NETWORK DISCOVERY MODULE
Discovers servers via UDP broadcast; clients auto-connect to discovered servers.

3.3.1.1 IP RANGE & BROADCAST STRATEGY
- Broadcasts to 255.255.255.255 and <broadcast>.
- Derives /24 and /16 broadcast addresses from the local IP.
- Sends targeted unicast probes to common gateway/server IPs in the local /24 (e.g., .1, .254, .100-.105).

3.3.1.2 DEVICE IDENTIFICATION AND CLASSIFICATION
- Server advertisements include IP, TCP port, hostname, OS type, and timestamps.
- Client-side maintains last_seen and presents devices in the UI.

3.3.2 CONFIGURATION MANAGEMENT MODULE
Generates and validates per-device settings and installer commands (via AutoInstaller) without editing the installer payloads.

3.3.2.1 AUTOMATED CONFIGURATION GENERATION
- Template-driven command construction for silent installs (e.g., MSI/EXE/ZIP).

3.3.2.2 TEMPLATE-BASED SETUP
- Role-based command templates reuse standardized, tested flags for installers.

3.3.3 INSTALLATION DEPLOYMENT MODULE
Transfers installers, executes them silently, and records results.

3.3.3.1 REMOTE INSTALLATION EXECUTION
- Clients run installers with elevated privileges through a controlled mechanism (e.g., Windows Task Scheduler as SYSTEM) to suppress prompts.
- ZIPs are extracted and inner installers executed with silent flags when present.

3.3.3.2 BATCH PROCESSING CAPABILITIES
- Server queues files per client and streams them sequentially with progress.
- Exponential backoff reconnection attempts for resilience.

3.3.4 USER INTERFACE MODULE
PyQt desktop UI for discovery, connection, distribution, and monitoring. Client UI lists servers, shows per-file progress, and exposes cancel controls.

3.3.5 MONITORING AND VALIDATION MODULE
- Progress: per-file percentage and sent/received markers.
- Status: intermediate messages (Installing, Received) and final outcomes (Installed, Manual Setup Required).
- Logs: human-readable logs on disk for post-mortem analysis.

4 SYSTEM REQUIREMENT

4.1 HARDWARE REQUIREMENTS
4.1.1 PROCESSOR
- Server: Multi-core CPU to drive concurrent IO and UI.
- Clients: Standard workstation/server-grade CPU.

4.1.2 MEMORY
- Server: 8–16 GB recommended; buffers and concurrency.
- Clients: 4 GB+ depending on artifacts.

4.1.3 STORAGE
- Server: Space for installers, logs, and artifacts (20–100+ GB typical).
- Clients: Space for payloads and temp files.

4.1.4 NETWORK INTERFACE
- 1 Gbps recommended; Wi-Fi works but reduces throughput and increases jitter.

4.2 SOFTWARE REQUIREMENTS
4.2.1 OPERATING SYSTEM
- Server/Client: Windows or Linux supported by Python 3.x.

4.2.2 PROGRAMMING LANGUAGES
- Python 3.x primary; shell/PowerShell scripts for integration.

4.2.3 NETWORK PROTOCOLS AND LIBRARIES
- UDP for discovery; TCP for command/data.
- Python socket library and threading for concurrency.

4.2.4 DATABASE MANAGEMENT SYSTEM
- Not required; JSON- or file-based persistence suffices. SQLite is optional.

4.2.5 WEB TECHNOLOGIES
- Not required; desktop UI is primary. A web dashboard can be added later.

5 DESIGN AND IMPLEMENTATION

5.1 SYSTEM ARCHITECTURE
- Pattern: Client/Server with agent-based client.
  - Server: Accepts TCP connections, queues and streams files, displays progress, and receives ACK/status.
  - Client: Discovers/auto-connects, receives metadata and bytes, validates size, categorizes file, executes installers, and reports status.
- Modules (repository):
  - network/: client.py, server.py, protocol.py, transfer helpers
  - ui/: widgets and windows for both sides (server_ui.py, client_ui.py, etc.)
  - utils/: dynamic_installer, virus_scanner, config
  - working_server.py, working_client.py: entry points that wire UI and networking

5.2 NETWORK TOPOLOGY & PROTOCOL
- Ports:
  - UDP 5000 (discovery)
  - TCP 5001 (command + data)
- Discovery Flow:
  - Client periodically broadcasts "DISCOVER_SERVER" to 255.255.255.255, <broadcast>, and derived /24, /16 broadcast addresses.
  - The server listens on UDP 5000 and replies with a JSON advertisement: {"type":"SERVER_ADVERTISEMENT","ip","port","hostname","os_type","timestamp"}.
  - The client updates server info and immediately attempts a TCP connect to the advertised port.
- Connection & Framing:
  - TCP socket carries newline-delimited JSON control messages and raw file bytes.
  - Control messages are sent as a single line terminated with \n.
  - File transfer is strictly: FILE_METADATA JSON line announcing file_name and file_size, followed by exactly file_size bytes with no interleaved text.
- Heartbeats & Reconnect:
  - Client sends periodic HEARTBEAT JSON to keep the connection alive.
  - On disconnect, an exponential backoff (3s doubling to max 30s) attempts reconnect.
- Adaptive Timeouts & Buffers:
  - Same-subnet vs cross-machine timeouts and buffer sizes are chosen dynamically.
  - Typical socket buffers are set near 1MB+; client receive chunk default is 128KB with adaptive adjustments.

5.3 DATA FLOW DIAGRAMS
- Level 0: Operator -> Server -> Clients -> Operator
- Level 1: Discover -> Connect -> Distribute -> Execute -> Validate -> Report
- Deploy Sub-flow: Send FILE_METADATA -> Stream bytes -> Client ACK -> Client post-process -> Client STATUS_UPDATE

5.4 DATABASE DESIGN (OPTIONAL)
Suggested entities if persistence is required later:
- devices(id, ip, hostname, os_hint, last_seen, tags)
- templates(id, name, version, role, path, checksum)
- jobs(id, name, created_at, created_by, status)
- job_targets(job_id, device_id, status, times)
- artifacts(id, name, version, path, size, checksum)
- logs(id, entity_id, timestamp, level, message)

5.5 FRONTEND DESIGN
- Server UI: shows server IP, connected clients, distribution queue, progress, and statuses.
- Client UI: lists discovered servers, connection status, receiving list with progress and cancel.
- Status bar provides short, color-coded updates without excessive wrapping.

5.6 BACKEND IMPLEMENTATION DETAILS
- Discovery Client (network/client.py):
  - Periodic broadcasts and targeted unicasts every ~2 seconds.
  - On receiving SERVER_ADVERTISEMENT, stores server info and auto-connects immediately.
- Client Connection Handling:
  - Sends CLIENT_INFO JSON upon TCP connect.
  - Reads control lines and raw bytes; uses file_size from metadata to segment the stream.
  - Emits progress events and sends FILE_ACK and STATUS_UPDATE upon completion.
  - Performs post-receive actions: categorize file and attempt silent install for supported types; move to manual_setup with a .info file if interaction detected.
- Server Distribution (network/server.py):
  - Accepts connections; maintains per-client queues and current file transfer.
  - Sends FILE_METADATA followed by byte stream, throttled by buffer thresholds.
  - Tracks sent_bytes and emits per-file progress.
  - Records "Sent - Awaiting ACK" after streaming, then updates on receiving ACK/STATUS_UPDATE.
- Virus Scan (utils/virus_scanner.py):
  - Hook point to scan files before distribution; scan results can be attached to metadata.
- Installer Automation (utils/dynamic_installer.py, auto_installer.py):
  - MSI/EXE/ZIP handling with standard silent switches and Task Scheduler elevation on Windows.

5.7 NETWORK SCANNING & DISCOVERY ALGORITHMS
- Multi-target broadcast strategy to reach diverse LANs.
- Adaptive retry and timeouts to cope with packet loss.
- Duplicate suppression by keying known servers by IP and updating last_seen.

5.8 AUTOMATED INSTALLATION SCRIPTS & POLICIES
- Pre-checks: permissions, disk space, and AV results (when enabled).
- Silent install flags per installer type; ZIP extraction and inner installer execution.
- Post-checks: move to installer/files/media categories; status reporting to server.

5.9 SECURITY IMPLEMENTATION
- Transport: same-host or LAN TCP connections; TLS can be layered later if needed.
- Integrity: hooks for checksum/hash verification; AV scanning option on server side.
- Least Privilege: client runs installers via controlled elevated context (SYSTEM via Task Scheduler) only when required.
- Secrets: no hardcoded credentials in protocol; environment-based configuration recommended.
- Auditing: JSON and human-readable logs; per-target status in UI.

5.10 TESTING STRATEGIES
- Unit tests (protocol parsing, discovery message handling, file categorization).
- Integration tests (client/server connect, file metadata framing, byte-accurate transfers).
- End-to-end tests on a switched 1 Gbps LAN with two or more clients.
- Failure injection: simulate disconnects mid-transfer; verify resume/cancel behavior and UI updates.
- Performance tests: measure throughput and CPU/memory during large transfers.

5.11 DOCUMENTATION AND USER MANUAL (OPERATIONS)
- Startup:
  1) Start the server application on a LAN-connected host.
  2) Start client(s); they broadcast discovery and auto-connect upon advertisement.
- Distribution:
  1) Add files to the server queue (UI) and start distribution.
  2) Observe per-client progress and statuses.
- Logs:
  - Clients: logs/client.log (rolling text log)
  - Server: console and UI status; optional file logs can be enabled in the same pattern.
- File Destinations on Clients:
  - received_files/tmp (staging during transfer)
  - received_files/installer | files | media (categorized)
  - received_files/manual_setup (+ .info.txt) for interactive/manual installs

6 RESULT ANALYSIS

6.1 INSTALLATION ACCURACY AND SUCCESS RATE
- Metrics: per-file success (ACK Received), post-install status (Installed, Manual Setup Required), and error reasons.
- Observations: Deterministic metadata+byte framing and immediate ACKs improve correctness versus ad-hoc copy methods.

6.2 PERFORMANCE METRICS (TYPICAL ON 1 Gbps LAN)
- Discovery: server found within 2–10 seconds via broadcast.
- Transfer: sustained 50–120 MB/s for large files depends on disk and NIC; smaller files complete near-instantly.
- CPU/Memory: modest; buffers sized ~1MB and adaptive waits prevent excessive memory usage.

6.3 TIME EFFICIENCY ANALYSIS
- Auto-connect reduces operator time to near zero; manual retries rarely needed.
- Concurrent clients receive sequential byte streams independently; UI updates at ~0.5s cadence to reduce overhead.

6.4 USER EXPERIENCE EVALUATION
- Clear statuses (Sending, Awaiting ACK, Received, Installing, Installed).
- Cancel controls for the receiving client; per-client progress visibility on server.

6.5 SCALABILITY TESTING
- Multiple clients attached concurrently; server queues per client.
- Exponential backoff reconnect ensures eventual recovery from transient disconnects.

6.6 SECURITY ASSESSMENT
- No plaintext credentials in transit; minimal attack surface on closed LAN.
- Recommended to add TLS and strong authentication for multi-tenant or untrusted networks.

7 CONCLUSION AND FUTURE WORK
The system demonstrates reliable, automated deployment across a LAN with fast discovery, auto-connect, robust file transfer, and silent installer execution. Operators get immediate feedback, and error cases are explicit and actionable. The architecture is modular and ready for incremental enhancements.

Future work:
- Add authentication and optional TLS for the TCP channel.
- Web dashboard with RBAC and historical reporting.
- Smarter discovery (multicast, mDNS) and segmented network awareness.
- Global rate limiting and QoS-aware throttling.
- Pluggable post-install validations and rollback workflows.

APPENDIX
A. Protocol Summary
- UDP 5000: discovery request "DISCOVER_SERVER"; server replies with JSON advertisement.
- TCP 5001: newline-delimited JSON control messages and raw bytes for file data.
- Message Types (examples):
  - CLIENT_INFO, SERVER_ADVERTISEMENT, FILE_METADATA, FILE_ACK, STATUS_UPDATE, HEARTBEAT, CANCEL_TRANSFER
- Framing Rules:
  - Control messages: JSON + "\n".
  - File data: exactly file_size bytes after FILE_METADATA; no interleaving control text.

B. Port Matrix (Firewall Rules)
- Server: inbound TCP 5001, inbound UDP 5000; outbound UDP 5000 responses.
- Clients: outbound UDP 5000 broadcasts, outbound TCP 5001; inbound UDP 5000 responses for discovery.

C. Operational Troubleshooting
- Auto-connect delay (>10s):
  - Verify UDP 5000 allowed both ways; confirm the client’s network is in a Private/Domain profile on Windows.
  - Ensure multiple NICs aren’t isolating broadcasts; the client sends to /24 and /16 derived broadcasts and common unicast targets.
  - As a fallback, verify that the client can initiate TCP 5001 to the server’s IP.
- Partial/failed file receipts:
  - Ensure no extraneous bytes are injected during byte streaming. Only FILE_METADATA JSON then raw bytes must be sent.
  - Check for timeouts or disconnects; server will re-attempt after backoff.
  - Confirm disk space and AV exclusions for the staging folder on the client.
- Installation prompts:
  - If an installer presents a UI, the client moves the file to manual_setup and emits "Manual Setup Required" with a .info note.

D. Repository Structure (key paths)
- network/: client.py, server.py, protocol.py (ports, timeouts, discovery constants)
- ui/: server_ui.py, client_ui.py, custom_widgets.py, etc.
- utils/: dynamic_installer.py, virus_scanner.py, config.py
- working_server.py, working_client.py: runnable entry points

E. Recent Improvements
- Immediate auto-connect on discovery from the networking layer to reduce UI latency and ensure fast attachment on LANs.
- Adaptive socket timeouts and buffer sizing tuned for same-subnet vs cross-machine connections.
- Strict byte framing guidance documented to prevent interleaving control text with file data.
