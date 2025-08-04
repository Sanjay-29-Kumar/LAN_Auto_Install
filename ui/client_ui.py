from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QPushButton, QLabel, QListWidget, 
                             QListWidgetItem, QProgressBar, QTextEdit, QGroupBox,
                             QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QStatusBar, QMenuBar, 
                             QMenu, QAction, QToolBar, QFrame, QCheckBox,
                             QComboBox, QSpinBox, QLineEdit, QTreeWidget, 
                             QTreeWidgetItem, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QFont, QIcon, QPixmap
from typing import List, Dict, Any, Optional
import os
import time
from datetime import datetime

from .styles import ModernStyle

class ServerListWidget(QWidget):
    """Widget for displaying available servers"""
    
    server_selected = pyqtSignal(str)  # server_ip
    server_connected = pyqtSignal(str)  # server_ip
    
    def __init__(self):
        super().__init__()
        self.servers: Dict[str, Dict[str, Any]] = {}
        self.selected_server: Optional[str] = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Available Servers")
        self.title_label.setProperty("class", "title")
        self.count_label = QLabel("0 servers found")
        self.count_label.setProperty("class", "status")
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)
        
        layout.addLayout(header_layout)
        
        # Server list
        self.server_list = QListWidget()
        self.server_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.server_list.itemSelectionChanged.connect(self.on_selection_changed)
        self.server_list.itemDoubleClicked.connect(self.on_server_double_clicked)
        
        layout.addWidget(self.server_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_servers)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.connect_btn.setEnabled(False)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.connect_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def update_servers(self, servers: List[Dict[str, Any]]):
        """Update the server list"""
        self.servers.clear()
        self.server_list.clear()
        
        for server in servers:
            server_ip = server.get("ip", "")
            self.servers[server_ip] = server
            
            item = QListWidgetItem()
            item.setText(f"{server.get('hostname', 'Unknown')} ({server_ip})")
            item.setData(Qt.ItemDataRole.UserRole, server_ip)
            
            # Set status icon
            if server.get("connected", False):
                item.setIcon(self.get_status_icon("connected"))
            else:
                item.setIcon(self.get_status_icon("available"))
            
            self.server_list.addItem(item)
        
        self.count_label.setText(f"{len(servers)} servers found")
    
    def get_status_icon(self, status: str):
        """Get status icon (placeholder for now)"""
        # In a real implementation, you would load actual icons
        return QIcon()
    
    def on_selection_changed(self):
        """Handle server selection changes"""
        selected_items = self.server_list.selectedItems()
        if selected_items:
            server_ip = selected_items[0].data(Qt.ItemDataRole.UserRole)
            self.selected_server = server_ip
            self.connect_btn.setEnabled(True)
        else:
            self.selected_server = None
            self.connect_btn.setEnabled(False)
    
    def on_server_double_clicked(self, item):
        """Handle server double-click"""
        server_ip = item.data(Qt.ItemDataRole.UserRole)
        self.server_connected.emit(server_ip)
    
    def connect_to_server(self):
        """Connect to selected server"""
        if self.selected_server:
            self.server_connected.emit(self.selected_server)
    
    def refresh_servers(self):
        """Refresh server list"""
        # This would trigger a server discovery
        pass

class FileReceptionWidget(QWidget):
    """Widget for managing received files"""
    
    def __init__(self):
        super().__init__()
        self.received_files: List[Dict[str, Any]] = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # File list
        files_group = QGroupBox("Received Files")
        files_layout = QVBoxLayout()
        
        # File table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(6)
        self.file_table.setHorizontalHeaderLabels([
            "File Name", "Server", "Type", "Size", "Received", "Status"
        ])
        
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        files_layout.addWidget(self.file_table)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self.open_folder)
        self.export_btn = QPushButton("Export List")
        self.export_btn.clicked.connect(self.export_list)
        self.clear_btn = QPushButton("Clear List")
        self.clear_btn.clicked.connect(self.clear_list)
        
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        
        files_layout.addLayout(btn_layout)
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Storage info
        storage_group = QGroupBox("Storage Information")
        storage_layout = QGridLayout()
        
        storage_layout.addWidget(QLabel("Total Files:"), 0, 0)
        self.total_files_label = QLabel("0")
        storage_layout.addWidget(self.total_files_label, 0, 1)
        
        storage_layout.addWidget(QLabel("Total Size:"), 1, 0)
        self.total_size_label = QLabel("0 B")
        storage_layout.addWidget(self.total_size_label, 1, 1)
        
        storage_layout.addWidget(QLabel("Installers:"), 2, 0)
        self.installer_count_label = QLabel("0")
        storage_layout.addWidget(self.installer_count_label, 2, 1)
        
        storage_layout.addWidget(QLabel("Regular Files:"), 3, 0)
        self.file_count_label = QLabel("0")
        storage_layout.addWidget(self.file_count_label, 3, 1)
        
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        
        self.setLayout(layout)
    
    def add_received_file(self, file_info: Dict[str, Any]):
        """Add a received file to the list"""
        self.received_files.append(file_info)
        
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)
        
        file_name = file_info.get("name", "Unknown")
        server_ip = file_info.get("server_ip", "Unknown")
        file_type = file_info.get("type", "file")
        file_size = self.format_bytes(file_info.get("size", 0))
        received_time = file_info.get("received_time", "")
        status = file_info.get("status", "Received")
        
        self.file_table.setItem(row, 0, QTableWidgetItem(file_name))
        self.file_table.setItem(row, 1, QTableWidgetItem(server_ip))
        self.file_table.setItem(row, 2, QTableWidgetItem(file_type))
        self.file_table.setItem(row, 3, QTableWidgetItem(file_size))
        self.file_table.setItem(row, 4, QTableWidgetItem(received_time))
        
        status_item = QTableWidgetItem(status)
        if status == "Installed":
            status_item.setForeground(Qt.GlobalColor.green)
        elif status == "Failed":
            status_item.setForeground(Qt.GlobalColor.red)
        
        self.file_table.setItem(row, 5, status_item)
        
        self.update_storage_info()
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def update_storage_info(self):
        """Update storage information display"""
        total_files = len(self.received_files)
        total_size = sum(file.get("size", 0) for file in self.received_files)
        installer_count = len([f for f in self.received_files if f.get("type") == "installer"])
        file_count = total_files - installer_count
        
        self.total_files_label.setText(str(total_files))
        self.total_size_label.setText(self.format_bytes(total_size))
        self.installer_count_label.setText(str(installer_count))
        self.file_count_label.setText(str(file_count))
    
    def open_folder(self):
        """Open the received files folder"""
        # Implementation would open the folder in file explorer
        pass
    
    def export_list(self):
        """Export file list to CSV"""
        # Implementation would export the file list
        pass
    
    def clear_list(self):
        """Clear the file list"""
        self.received_files.clear()
        self.file_table.setRowCount(0)
        self.update_storage_info()

class InstallationWidget(QWidget):
    """Widget for managing software installations"""
    
    def __init__(self):
        super().__init__()
        self.installations: List[Dict[str, Any]] = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Installation list
        install_group = QGroupBox("Software Installations")
        install_layout = QVBoxLayout()
        
        # Installation table
        self.install_table = QTableWidget()
        self.install_table.setColumnCount(5)
        self.install_table.setHorizontalHeaderLabels([
            "Software", "Version", "Status", "Progress", "Time"
        ])
        
        header = self.install_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        install_layout.addWidget(self.install_table)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        self.auto_install_check = QCheckBox("Auto-install software")
        self.auto_install_check.setChecked(True)
        self.install_btn = QPushButton("Install Selected")
        self.install_btn.clicked.connect(self.install_selected)
        self.uninstall_btn = QPushButton("Uninstall Selected")
        self.uninstall_btn.clicked.connect(self.uninstall_selected)
        
        btn_layout.addWidget(self.auto_install_check)
        btn_layout.addWidget(self.install_btn)
        btn_layout.addWidget(self.uninstall_btn)
        btn_layout.addStretch()
        
        install_layout.addLayout(btn_layout)
        install_group.setLayout(install_layout)
        layout.addWidget(install_group)
        
        # Installed software
        software_group = QGroupBox("Installed Software")
        software_layout = QVBoxLayout()
        
        self.software_tree = QTreeWidget()
        self.software_tree.setHeaderLabels(["Software", "Version", "Install Date"])
        software_layout.addWidget(self.software_tree)
        
        software_group.setLayout(software_layout)
        layout.addWidget(software_group)
        
        self.setLayout(layout)
    
    def add_installation(self, install_info: Dict[str, Any]):
        """Add an installation to the list"""
        self.installations.append(install_info)
        
        row = self.install_table.rowCount()
        self.install_table.insertRow(row)
        
        software_name = install_info.get("name", "Unknown")
        version = install_info.get("version", "")
        status = install_info.get("status", "Pending")
        progress = install_info.get("progress", 0)
        install_time = install_info.get("time", "")
        
        self.install_table.setItem(row, 0, QTableWidgetItem(software_name))
        self.install_table.setItem(row, 1, QTableWidgetItem(version))
        
        status_item = QTableWidgetItem(status)
        if status == "Completed":
            status_item.setForeground(Qt.GlobalColor.green)
        elif status == "Failed":
            status_item.setForeground(Qt.GlobalColor.red)
        elif status == "Installing":
            status_item.setForeground(Qt.GlobalColor.yellow)
        
        self.install_table.setItem(row, 2, status_item)
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(int(progress))
        self.install_table.setCellWidget(row, 3, progress_bar)
        
        self.install_table.setItem(row, 4, QTableWidgetItem(install_time))
    
    def update_installation_progress(self, install_id: str, progress: float, status: str):
        """Update installation progress"""
        # Find the installation in the table and update it
        for row in range(self.install_table.rowCount()):
            # This would match by installation ID
            progress_bar = self.install_table.cellWidget(row, 3)
            if progress_bar:
                progress_bar.setValue(int(progress))
            
            status_item = QTableWidgetItem(status)
            if status == "Completed":
                status_item.setForeground(Qt.GlobalColor.green)
            elif status == "Failed":
                status_item.setForeground(Qt.GlobalColor.red)
            elif status == "Installing":
                status_item.setForeground(Qt.GlobalColor.yellow)
            
            self.install_table.setItem(row, 2, status_item)
            break
    
    def install_selected(self):
        """Install selected software"""
        # Implementation for installing selected software
        pass
    
    def uninstall_selected(self):
        """Uninstall selected software"""
        # Implementation for uninstalling selected software
        pass
    
    def update_installed_software(self, software_list: List[Dict[str, Any]]):
        """Update the installed software tree"""
        self.software_tree.clear()
        
        for software in software_list:
            item = QTreeWidgetItem()
            item.setText(0, software.get("name", "Unknown"))
            item.setText(1, software.get("version", ""))
            item.setText(2, software.get("install_date", ""))
            self.software_tree.addTopLevelItem(item)

class ClientMainWindow(QMainWindow):
    """Main client application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Software Installation System - Client")
        self.setGeometry(100, 100, 1000, 700)
        
        # Apply modern styling
        self.setStyleSheet(ModernStyle.get_stylesheet())
        self.setPalette(ModernStyle.get_dark_palette())
        
        self.init_ui()
        self.init_menu()
        self.init_status_bar()
    
    def init_ui(self):
        """Initialize the main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Server discovery
        self.server_widget = ServerListWidget()
        splitter.addWidget(self.server_widget)
        
        # Right panel - File reception and installations
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Tab widget for different functions
        self.tab_widget = QTabWidget()
        
        # File reception tab
        self.reception_widget = FileReceptionWidget()
        self.tab_widget.addTab(self.reception_widget, "Received Files")
        
        # Installation tab
        self.installation_widget = InstallationWidget()
        self.tab_widget.addTab(self.installation_widget, "Software Installations")
        
        # Status tab
        self.status_widget = self.create_status_widget()
        self.tab_widget.addTab(self.status_widget, "Status")
        
        right_layout.addWidget(self.tab_widget)
        right_panel.setLayout(right_layout)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([300, 700])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
    
    def create_status_widget(self) -> QWidget:
        """Create status widget"""
        self.status_widget = QWidget()
        layout = QVBoxLayout()
        
        # Connection status
        connection_group = QGroupBox("Connection Status")
        connection_layout = QGridLayout()
        
        connection_layout.addWidget(QLabel("Server:"), 0, 0)
        self.server_label = QLabel("Not connected")
        self.server_label.setProperty("class", "error")
        connection_layout.addWidget(self.server_label, 0, 1)
        
        connection_layout.addWidget(QLabel("Status:"), 1, 0)
        self.connection_status_label = QLabel("Disconnected")
        self.connection_status_label.setProperty("class", "error")
        connection_layout.addWidget(self.connection_status_label, 1, 1)
        
        connection_layout.addWidget(QLabel("Last Activity:"), 2, 0)
        self.last_activity_label = QLabel("Never")
        connection_layout.addWidget(self.last_activity_label, 2, 1)
        
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        # System info
        system_group = QGroupBox("System Information")
        system_layout = QVBoxLayout()
        
        self.system_info_text = QTextEdit()
        self.system_info_text.setReadOnly(True)
        self.system_info_text.setMaximumHeight(200)
        
        system_layout.addWidget(self.system_info_text)
        system_group.setLayout(system_layout)
        layout.addWidget(system_group)
        
        # Activity log
        activity_group = QGroupBox("Activity Log")
        activity_layout = QVBoxLayout()
        
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels([
            "Time", "Event", "Details", "Status"
        ])
        
        header = self.activity_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        activity_layout.addWidget(self.activity_table)
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)
        
        self.status_widget.setLayout(layout)
        return self.status_widget
    
    def init_menu(self):
        """Initialize menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        refresh_action = QAction("Refresh Servers", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_servers)
        tools_menu.addAction(refresh_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_status_bar(self):
        """Initialize status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Status indicators
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setProperty("class", "error")
        self.status_bar.addWidget(self.connection_status)
        
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        self.server_status = QLabel("No server")
        self.status_bar.addPermanentWidget(self.server_status)
        
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        self.file_count = QLabel("0 files")
        self.status_bar.addPermanentWidget(self.file_count)
        
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        self.install_count = QLabel("0 installations")
        self.status_bar.addPermanentWidget(self.install_count)
    
    def refresh_servers(self):
        """Refresh server discovery"""
        # This would trigger a server scan
        pass
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", 
                         "LAN Software Installation System - Client\n"
                         "Version 1.0\n\n"
                         "Client application for receiving software and files "
                         "from LAN servers.")
    
    def update_connection_status(self, connected: bool, server_ip: str = ""):
        """Update connection status"""
        if connected:
            self.connection_status.setText("Connected")
            self.connection_status.setProperty("class", "success")
            self.server_status.setText(f"Server: {server_ip}")
        else:
            self.connection_status.setText("Disconnected")
            self.connection_status.setProperty("class", "error")
            self.server_status.setText("No server")
        
        # Reapply styles
        self.connection_status.style().unpolish(self.connection_status)
        self.connection_status.style().polish(self.connection_status)
    
    def add_activity_event(self, event: str, details: str, status: str = "Info"):
        """Add activity event to log"""
        row = self.activity_table.rowCount()
        self.activity_table.insertRow(row)
        
        time_str = datetime.now().strftime("%H:%M:%S")
        
        self.activity_table.setItem(row, 0, QTableWidgetItem(time_str))
        self.activity_table.setItem(row, 1, QTableWidgetItem(event))
        self.activity_table.setItem(row, 2, QTableWidgetItem(details))
        
        status_item = QTableWidgetItem(status)
        if status == "Success":
            status_item.setForeground(Qt.GlobalColor.green)
        elif status == "Error":
            status_item.setForeground(Qt.GlobalColor.red)
        elif status == "Warning":
            status_item.setForeground(Qt.GlobalColor.yellow)
        
        self.activity_table.setItem(row, 3, status_item)
        
        # Auto-scroll to bottom
        self.activity_table.scrollToBottom()
    
    def update_file_count(self, count: int):
        """Update file count in status bar"""
        self.file_count.setText(f"{count} files")
    
    def update_install_count(self, count: int):
        """Update installation count in status bar"""
        self.install_count.setText(f"{count} installations") 