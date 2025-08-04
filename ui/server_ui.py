from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGridLayout, QPushButton, QLabel, QListWidget, 
                             QListWidgetItem, QProgressBar, QTextEdit, QGroupBox,
                             QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFileDialog, QMessageBox, QStatusBar,
                             QMenuBar, QMenu, QAction, QToolBar, QFrame, QCheckBox,
                             QComboBox, QSpinBox, QLineEdit, QTreeWidget, QTreeWidgetItem)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject
from PyQt5.QtGui import QFont, QIcon, QPixmap
from typing import List, Dict, Any, Optional
import os
import time
from datetime import datetime

from .styles import ModernStyle
from network.discovery import NetworkDevice
from network.transfer import FileTransfer

class DeviceListWidget(QWidget):
    """Widget for displaying discovered network devices"""
    
    device_selected = pyqtSignal(NetworkDevice)
    device_deselected = pyqtSignal(NetworkDevice)
    
    def __init__(self):
        super().__init__()
        self.devices: Dict[str, NetworkDevice] = {}
        self.selected_devices: List[str] = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Network Devices")
        self.title_label.setProperty("class", "title")
        self.count_label = QLabel("0 devices found")
        self.count_label.setProperty("class", "status")
        
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)
        
        layout.addLayout(header_layout)
        
        # Device list
        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.device_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        layout.addWidget(self.device_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_devices)
        self.clear_btn = QPushButton("Clear Selection")
        self.clear_btn.clicked.connect(self.clear_selection)
        
        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def update_devices(self, devices: List[NetworkDevice]):
        """Update the device list"""
        self.devices.clear()
        self.device_list.clear()
        
        self.selected_devices.clear()
        for device in devices:
            self.devices[device.ip] = device
            item = QListWidgetItem()
            item.setText(f"{device.hostname or 'Unknown'} ({device.ip})")
            item.setData(Qt.ItemDataRole.UserRole, device)
            
            # Set icon based on OS type
            if device.is_windows:
                item.setIcon(self.get_os_icon("windows"))
            elif device.os_type == "Linux/Unix":
                item.setIcon(self.get_os_icon("linux"))
            else:
                item.setIcon(self.get_os_icon("unknown"))
            
            self.device_list.addItem(item)
        
        self.count_label.setText(f"{len(devices)} devices found")
    
    def get_os_icon(self, os_type: str):
        """Get OS icon (placeholder for now)"""
        # In a real implementation, you would load actual icons
        return QIcon()
    
    def on_selection_changed(self):
        """Handle device selection changes"""
        selected_items = self.device_list.selectedItems()
        self.selected_devices = []
        
        for item in selected_items:
            device = item.data(Qt.ItemDataRole.UserRole)
            if device and device.ip not in self.selected_devices:
                self.selected_devices.append(device.ip)
                self.device_selected.emit(device)
    
    def get_selected_devices(self) -> List[NetworkDevice]:
        """Get list of selected devices"""
        return [self.devices[ip] for ip in self.selected_devices if ip in self.devices]
    
    def refresh_devices(self):
        """Refresh device list"""
        # This would trigger a network scan
        pass
    
    def select_all_devices(self):
        """Select all devices"""
        for i in range(self.device_list.count()):
            self.device_list.item(i).setSelected(True)
    
    def clear_selection(self):
        """Clear all selections"""
        self.device_list.clearSelection()

class FileTransferWidget(QWidget):
    """Widget for managing file transfers"""
    
    transfer_started = pyqtSignal(str, str)  # file_path, target_ip
    transfer_progress = pyqtSignal(str, float)  # transfer_id, progress
    transfer_completed = pyqtSignal(str)  # transfer_id
    transfer_failed = pyqtSignal(str, str)  # transfer_id, error
    
    def __init__(self):
        super().__init__()
        self.transfers: Dict[str, Dict[str, Any]] = {}
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        
        file_btn_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select file to transfer...")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_btn_layout.addWidget(self.file_path_edit)
        file_btn_layout.addWidget(self.browse_btn)
        
        file_layout.addLayout(file_btn_layout)
        
        # File info
        self.file_info_label = QLabel("No file selected")
        self.file_info_label.setProperty("class", "status")
        file_layout.addWidget(self.file_info_label)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Transfer controls
        transfer_group = QGroupBox("Transfer Controls")
        transfer_layout = QVBoxLayout()
        
        # Target selection
        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target:"))
        self.target_combo = QComboBox()
        self.target_combo.addItem("All Windows Devices")
        target_layout.addWidget(self.target_combo)
        
        transfer_layout.addLayout(target_layout)
        
        # Transfer buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Transfer")
        self.start_btn.clicked.connect(self.start_transfer)
        self.stop_btn = QPushButton("Stop Transfer")
        self.stop_btn.clicked.connect(self.stop_transfer)
        self.stop_btn.setEnabled(False)
        
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addStretch()
        
        transfer_layout.addLayout(btn_layout)
        transfer_group.setLayout(transfer_layout)
        layout.addWidget(transfer_group)
        
        # Transfer progress
        progress_group = QGroupBox("Transfer Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_table = QTableWidget()
        self.progress_table.setColumnCount(5)
        self.progress_table.setHorizontalHeaderLabels([
            "File", "Target", "Status", "Progress", "Speed"
        ])
        
        header = self.progress_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        progress_layout.addWidget(self.progress_table)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        self.setLayout(layout)
    
    def browse_file(self):
        """Browse for file to transfer"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File to Transfer", "", "All Files (*.*)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            self.update_file_info(file_path)
    
    def update_file_info(self, file_path: str):
        """Update file information display"""
        try:
            file_size = os.path.getsize(file_path)
            file_name = os.path.basename(file_path)
            
            # Format file size
            size_str = self.format_bytes(file_size)
            
            self.file_info_label.setText(
                f"File: {file_name} | Size: {size_str}"
            )
        except Exception as e:
            self.file_info_label.setText(f"Error: {str(e)}")
    
    def format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
    
    def start_transfer(self):
        """Start file transfer"""
        file_path = self.file_path_edit.text()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Error", "Please select a valid file.")
            return
        
        # Get target devices (this would come from the device list)
        target_devices = []  # This would be populated from device selection
        
        if not target_devices:
            QMessageBox.warning(self, "Error", "Please select target devices.")
            return
        
        # Start transfers
        for device in target_devices:
            transfer_id = f"{int(time.time())}_{device.ip}"
            self.transfers[transfer_id] = {
                "file_path": file_path,
                "target_ip": device.ip,
                "status": "starting",
                "progress": 0
            }
            
            # Add to progress table
            self.add_transfer_row(transfer_id)
            
            # Emit signal
            self.transfer_started.emit(file_path, device.ip)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_transfer(self):
        """Stop current transfer"""
        # Implementation would stop ongoing transfers
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def add_transfer_row(self, transfer_id: str):
        """Add transfer to progress table"""
        transfer_info = self.transfers[transfer_id]
        row = self.progress_table.rowCount()
        self.progress_table.insertRow(row)
        
        file_name = os.path.basename(transfer_info["file_path"])
        target_ip = transfer_info["target_ip"]
        
        self.progress_table.setItem(row, 0, QTableWidgetItem(file_name))
        self.progress_table.setItem(row, 1, QTableWidgetItem(target_ip))
        self.progress_table.setItem(row, 2, QTableWidgetItem("Starting"))
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        self.progress_table.setCellWidget(row, 3, progress_bar)
        
        self.progress_table.setItem(row, 4, QTableWidgetItem("0 KB/s"))
    
    def update_transfer_progress(self, transfer_id: str, progress: float):
        """Update transfer progress"""
        if transfer_id in self.transfers:
            self.transfers[transfer_id]["progress"] = progress
            
            # Find row in table
            for row in range(self.progress_table.rowCount()):
                if self.progress_table.item(row, 1).text() == self.transfers[transfer_id]["target_ip"]:
                    # Update progress bar
                    progress_bar = self.progress_table.cellWidget(row, 3)
                    if progress_bar:
                        progress_bar.setValue(int(progress))
                    
                    # Update status
                    if progress == 100:
                        self.progress_table.setItem(row, 2, QTableWidgetItem("Completed"))
                    elif progress > 0:
                        self.progress_table.setItem(row, 2, QTableWidgetItem("Transferring"))
                    
                    break

class ServerMainWindow(QMainWindow):
    """Main server application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Software Installation System - Server")
        self.setGeometry(100, 100, 1200, 800)
        
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
        
        # Left panel - Device discovery
        self.device_widget = DeviceListWidget()
        splitter.addWidget(self.device_widget)
        
        # Right panel - File transfer and monitoring
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # Tab widget for different functions
        self.tab_widget = QTabWidget()
        
        # File transfer tab
        self.transfer_widget = FileTransferWidget()
        self.tab_widget.addTab(self.transfer_widget, "File Transfer")
        
        # Monitoring tab
        self.monitoring_widget = self.create_monitoring_widget()
        self.tab_widget.addTab(self.monitoring_widget, "Monitoring")
        
        # Settings tab
        self.settings_widget = self.create_settings_widget()
        self.tab_widget.addTab(self.settings_widget, "Settings")
        
        right_layout.addWidget(self.tab_widget)
        right_panel.setLayout(right_layout)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
    
    def create_monitoring_widget(self) -> QWidget:
        """Create monitoring widget"""
        self.monitoring_widget = QWidget()
        layout = QVBoxLayout()
        
        # System info
        info_group = QGroupBox("System Information")
        info_layout = QVBoxLayout()
        
        self.system_info_text = QTextEdit()
        self.system_info_text.setReadOnly(True)
        self.system_info_text.setMaximumHeight(200)
        
        info_layout.addWidget(self.system_info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Network activity
        network_group = QGroupBox("Network Activity")
        network_layout = QVBoxLayout()
        
        self.network_table = QTableWidget()
        self.network_table.setColumnCount(4)
        self.network_table.setHorizontalHeaderLabels([
            "Time", "Event", "Details", "Status"
        ])
        
        header = self.network_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        network_layout.addWidget(self.network_table)
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        self.monitoring_widget.setLayout(layout)
        return self.monitoring_widget
    
    def create_settings_widget(self) -> QWidget:
        """Create settings widget"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Network settings
        network_group = QGroupBox("Network Settings")
        network_layout = QGridLayout()
        
        network_layout.addWidget(QLabel("Port:"), 0, 0)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(5000)
        network_layout.addWidget(self.port_spin, 0, 1)
        
        network_layout.addWidget(QLabel("Discovery Interval (seconds):"), 1, 0)
        self.discovery_interval_spin = QSpinBox()
        self.discovery_interval_spin.setRange(10, 300)
        self.discovery_interval_spin.setValue(30)
        network_layout.addWidget(self.discovery_interval_spin, 1, 1)
        
        network_group.setLayout(network_layout)
        layout.addWidget(network_group)
        
        # Transfer settings
        transfer_group = QGroupBox("Transfer Settings")
        transfer_layout = QGridLayout()
        
        transfer_layout.addWidget(QLabel("Chunk Size (bytes):"), 0, 0)
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(1024, 65536)
        self.chunk_size_spin.setValue(8192)
        self.chunk_size_spin.setSuffix(" B")
        transfer_layout.addWidget(self.chunk_size_spin, 0, 1)
        
        transfer_layout.addWidget(QLabel("Auto-install software:"), 1, 0)
        self.auto_install_check = QCheckBox()
        self.auto_install_check.setChecked(True)
        transfer_layout.addWidget(self.auto_install_check, 1, 1)
        
        transfer_group.setLayout(transfer_layout)
        layout.addWidget(transfer_group)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
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
        
        refresh_action = QAction("Refresh Devices", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_devices)
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
        
        self.device_count = QLabel("0 devices")
        self.status_bar.addPermanentWidget(self.device_count)
        
        self.status_bar.addPermanentWidget(QLabel("|"))
        
        self.transfer_count = QLabel("0 transfers")
        self.status_bar.addPermanentWidget(self.transfer_count)
    
    def refresh_devices(self):
        """Refresh device discovery"""
        # This would trigger a network scan
        pass
    
    def save_settings(self):
        """Save application settings"""
        # Implementation for saving settings
        QMessageBox.information(self, "Settings", "Settings saved successfully!")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", 
                         "LAN Software Installation System\n"
                         "Version 1.0\n\n"
                         "A professional tool for distributing software and files "
                         "across local networks.")
    
    def update_status(self, connected: bool, device_count: int = 0, transfer_count: int = 0):
        """Update status bar"""
        if connected:
            self.connection_status.setText("Connected")
            self.connection_status.setProperty("class", "success")
        else:
            self.connection_status.setText("Disconnected")
            self.connection_status.setProperty("class", "error")
        
        self.device_count.setText(f"{device_count} devices")
        self.transfer_count.setText(f"{transfer_count} transfers")
        
        # Reapply styles
        self.connection_status.style().unpolish(self.connection_status)
        self.connection_status.style().polish(self.connection_status)
    
    def add_network_event(self, event: str, details: str, status: str = "Info"):
        """Add network event to monitoring table"""
        row = self.network_table.rowCount()
        self.network_table.insertRow(row)
        
        time_str = datetime.now().strftime("%H:%M:%S")
        
        self.network_table.setItem(row, 0, QTableWidgetItem(time_str))
        self.network_table.setItem(row, 1, QTableWidgetItem(event))
        self.network_table.setItem(row, 2, QTableWidgetItem(details))
        
        status_item = QTableWidgetItem(status)
        if status == "Success":
            status_item.setForeground(Qt.GlobalColor.green)
        elif status == "Error":
            status_item.setForeground(Qt.GlobalColor.red)
        elif status == "Warning":
            status_item.setForeground(Qt.GlobalColor.yellow)
        
        self.network_table.setItem(row, 3, status_item)
        
        # Auto-scroll to bottom
        self.network_table.scrollToBottom() 