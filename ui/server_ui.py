"""
LocalSend-inspired server UI for the LAN Auto Install application.
- Modern dark theme with rounded cards and accent colors
- Connected client list in a grid/card-like presentation similar to LocalSend
- Preserves existing widget names used by the server controller
"""

import sys
import os
import socket

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .custom_widgets import FileTransferWidget
from .virus_scan_widget import VirusScanWidget
from string import Template

def get_local_ip():
    # Returns the best local IP address for display
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"

PRIMARY = "#3b82f6"   # blue-500
ACCENT = "#22c55e"    # green-500
WARNING = "#eab308"   # yellow-500
DANGER = "#ef4444"    # red-500
BG0 = "#0b1220"       # near-slate-900
BG1 = "#0f172a"       # slate-900
BG2 = "#111827"       # gray-900
BORDER = "#374151"    # gray-700
FG = "#e5e7eb"        # gray-200
FG_MUTED = "#9ca3af"  # gray-400

# Virus scan status colors
SCAN_PENDING = "#eab308"  # yellow-500
SCAN_SAFE = "#22c55e"     # green-500
SCAN_UNSAFE = "#ef4444"   # red-500

class PendingScansList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Header
        header = QLabel("Pending Security Scans")
        header.setStyleSheet(f"color: {FG}; font-weight: bold;")
        layout.addWidget(header)
        
        # Scrollable list
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 1px solid {BORDER};
                border-radius: 5px;
                background: {BG2};
            }}
        """)
        
        self.scan_list = QWidget()
        self.scan_list_layout = QVBoxLayout()
        self.scan_list_layout.setAlignment(Qt.AlignTop)
        self.scan_list.setLayout(self.scan_list_layout)
        
        self.scroll_area.setWidget(self.scan_list)
        layout.addWidget(self.scroll_area)
        
        self.setLayout(layout)
        
    def add_pending_scan(self, file_name):
        scan_item = QWidget()
        item_layout = QHBoxLayout()
        
        # Spinner icon (you can replace with an actual spinner)
        spinner = QLabel("⌛")
        item_layout.addWidget(spinner)
        
        # File name
        name_label = QLabel(file_name)
        name_label.setStyleSheet(f"color: {FG_MUTED}")
        item_layout.addWidget(name_label)
        
        # Status
        status = QLabel("Scanning...")
        status.setStyleSheet(f"color: {SCAN_PENDING}")
        item_layout.addWidget(status)
        
        item_layout.addStretch()
        scan_item.setLayout(item_layout)
        
        self.scan_list_layout.addWidget(scan_item)
        return scan_item
        
    def update_scan_status(self, widget, status, is_safe=None):
        if is_safe is not None:
            status_color = SCAN_SAFE if is_safe else SCAN_UNSAFE
            spinner = widget.layout().itemAt(0).widget()
            spinner.setText("✓" if is_safe else "⚠️")
        else:
            status_color = SCAN_PENDING
            
        status_label = widget.layout().itemAt(2).widget()
        status_label.setText(status)
        status_label.setStyleSheet(f"color: {status_color}")
        
    def clear(self):
        while self.scan_list_layout.count():
            item = self.scan_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
SCAN_PENDING = "#6b7280"   # gray-500
SCAN_PROGRESS = "#3b82f6"  # blue-500
SCAN_SAFE = "#22c55e"     # green-500
SCAN_UNSAFE = "#ef4444"    # red-500
SCAN_WARNING = "#eab308"   # yellow-500
SCAN_SCANNING = "#3b82f6"  # blue-500
SCAN_SAFE = "#22c55e"     # green-500
SCAN_UNSAFE = "#ef4444"   # red-500


class PillLabel(QLabel):
    def __init__(self, text="", color=ACCENT, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"QLabel {{ background-color: {color}; color: #0b1220; border-radius: 10px; padding: 3px 8px; font-weight: 600; }}"
        )


class ServerWindow(QMainWindow):
    @staticmethod
    def _get_local_ip():
        # Returns the best local IP address for display
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass
        return "127.0.0.1"
    # Signal to notify when Details button is clicked
    show_server_details_requested = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Auto Install - Server")
        self.setGeometry(100, 100, 1000, 720)

        # App/window icon
        try:
            base = getattr(sys, '_MEIPASS', os.path.abspath('.'))
            self.setWindowIcon(QIcon(os.path.join(base, 'server.png')))
        except Exception:
            pass

        # Core stacked pages
        self.stacked_widget = QStackedWidget()
        self.home_widget = self.create_home_widget()
        self.after_selection_widget = self.create_after_selection_widget()
        self.while_sharing_widget = self.create_while_sharing_widget()
        self.stacked_widget.addWidget(self.home_widget)
        self.stacked_widget.addWidget(self.after_selection_widget)
        self.stacked_widget.addWidget(self.while_sharing_widget)

        # Global top app bar
        appbar = QWidget()
        appbar_layout = QHBoxLayout(appbar)
        appbar_layout.setContentsMargins(16, 12, 16, 12)
        appbar_layout.setSpacing(12)

        title_box = QHBoxLayout()
        title_icon = QLabel()
        title_icon.setFixedSize(26, 26)
        title_icon.setStyleSheet(f"background-color: {PRIMARY}; border-radius: 13px;")
        title_label = QLabel("Server")
        title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        title_box.addWidget(title_icon)
        title_box.addSpacing(8)
        title_box.addWidget(title_label)

        appbar_layout.addLayout(title_box)
        appbar_layout.addStretch(1)

        # Device pill shows hostname
        self.device_pill = PillLabel(socket.gethostname())
        appbar_layout.addWidget(self.device_pill)

        # Global Home/Back button preserved
        self.global_back_home_button = QPushButton("Home / Back")
        self.global_back_home_button.setObjectName("secondaryButton")
        self.global_back_home_button.setFixedHeight(34)
        self.global_back_home_button.clicked.connect(self.show_home)
        appbar_layout.addWidget(self.global_back_home_button)

    # Connect Details button to slot
    # (Details button is created in create_home_widget)
    # Will connect after widget is created

        # Main container: app bar + pages
        main_container_widget = QWidget()
        main_container_layout = QVBoxLayout(main_container_widget)
        main_container_layout.setContentsMargins(12, 8, 12, 8)
        main_container_layout.setSpacing(8)
        main_container_layout.addWidget(appbar)
        main_container_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(main_container_widget)

        self.create_status_bar()
        self.apply_theme()

        # Connect Details button to slot after widget creation
        if hasattr(self, 'show_server_details_button'):
            self.show_server_details_button.clicked.connect(self.on_show_server_details_clicked)
    def on_show_server_details_clicked(self):
        # Emit signal to be handled by controller
        self.show_server_details_requested.emit()

    def create_card_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setFlat(False)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)
        return group

    def create_home_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Add virus scan widget (hidden by default, shown when needed)
        self.virus_scan_widget = VirusScanWidget()
        self.virus_scan_widget.setVisible(False)
        layout.addWidget(self.virus_scan_widget)

        # Top: server info + connection status
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        server_info_group = self.create_card_group("Server")
        server_form = QFormLayout()
        server_form.setLabelAlignment(Qt.AlignRight)
        self.server_name_label = QLabel(socket.gethostname())
        self.server_ip_label = QLabel(get_local_ip())
        self.server_name_label.setObjectName("muted")
        self.server_ip_label.setObjectName("muted")

        ip_row = QHBoxLayout()
        ip_row.setSpacing(8)
        ip_row.addWidget(self.server_ip_label)
        self.show_server_details_button = QPushButton("Details")
        self.show_server_details_button.setFixedHeight(28)
        self.show_server_details_button.setObjectName("secondaryButton")
        ip_row.addWidget(self.show_server_details_button)

        server_form.addRow("Name:", self.server_name_label)
        server_form.addRow("IP:", self._wrap(ip_row))
        server_info_group.layout().addLayout(server_form)
        top_row.addWidget(server_info_group, 1)

        connection_group = self.create_card_group("Connection")
        conn_form = QFormLayout()
        conn_form.setLabelAlignment(Qt.AlignRight)
        self.connection_status_label = QLabel("Not Connected")
        self.connection_status_label.setObjectName("statusLabel")
        self.connected_clients_label = QLabel("0")
        self.connected_clients_label.setObjectName("muted")
        conn_form.addRow("Status:", self.connection_status_label)
        conn_form.addRow("Clients:", self.connected_clients_label)
        connection_group.layout().addLayout(conn_form)
        top_row.addWidget(connection_group, 1)

        layout.addLayout(top_row)

        # Connected Clients list (grid-like)
        clients_group = self.create_card_group("Connected Clients")
        clients_vbox = QVBoxLayout()
        clients_vbox.setSpacing(8)

        self.client_list_widget = QListWidget()
        self.client_list_widget.setViewMode(QListView.ListMode)
        self.client_list_widget.setResizeMode(QListView.Fixed)  # Changed to Fixed mode for more stable sizing
        self.client_list_widget.setMovement(QListView.Static)
        self.client_list_widget.setSpacing(8)
        self.client_list_widget.setWordWrap(False)
        self.client_list_widget.setUniformItemSizes(True)
        self.client_list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.client_list_widget.setMinimumWidth(650)  # Increased minimum width
        self.client_list_widget.setFrameShape(QFrame.NoFrame)  # Remove border
        clients_vbox.addWidget(self.client_list_widget)

        # Manual connect and actions row
        manual_row = QHBoxLayout()
        manual_row.setSpacing(8)
        self.manual_ip_input = QLineEdit()
        self.manual_ip_input.setPlaceholderText("Enter client IP to connect manually")
        self.manual_ip_connect_button = QPushButton("Connect")
        self.manual_ip_connect_button.clicked.connect(self._manual_ip_connect_clicked)
        manual_row.addWidget(self.manual_ip_input, 3)
        manual_row.addWidget(self.manual_ip_connect_button, 1)

        actions_row = QHBoxLayout()
        actions_row.setSpacing(8)
        self.refresh_clients_button = QPushButton("Refresh Client List")
        self.refresh_clients_button.setObjectName("secondaryButton")
        self.select_all_clients_button = QPushButton("Select All Clients")
        self.select_all_clients_button.clicked.connect(self._select_all_clients_clicked)
        self.show_profile_button = QPushButton("Show Profile")
        actions_row.addWidget(self.refresh_clients_button)
        actions_row.addStretch(1)
        actions_row.addWidget(self.show_profile_button)
        actions_row.addWidget(self.select_all_clients_button)

        clients_group.layout().addLayout(clients_vbox)
        clients_group.layout().addLayout(manual_row)
        clients_group.layout().addLayout(actions_row)
        layout.addWidget(clients_group, 5)

        # File Selection and Security
        file_group = self.create_card_group("File Selection & Security")
        
        # File selection row
        file_row = QHBoxLayout()
        self.select_files_button = QPushButton("Select Files to Share")
        
        # Add security scan section
        security_layout = QVBoxLayout()
        
        # Security scan header with status
        scan_header = QHBoxLayout()
        scan_header.setSpacing(10)
        
        security_icon = QLabel("🛡️")
        security_icon.setStyleSheet(f"font-size: 16px;")
        scan_header.addWidget(security_icon)
        
        security_title = QLabel("Security Status")
        security_title.setStyleSheet(f"color: {FG}; font-weight: bold;")
        scan_header.addWidget(security_title)
        
        self.overall_status = QLabel("No files selected")
        self.overall_status.setStyleSheet(f"color: {FG_MUTED}")
        scan_header.addWidget(self.overall_status)
        
        scan_header.addStretch()
        
        # Add a "View Details" button
        self.view_scan_details = QPushButton("View Scan Details")
        self.view_scan_details.setStyleSheet(f"""
            QPushButton {{
                color: {PRIMARY};
                border: 1px solid {PRIMARY};
                padding: 5px 10px;
                border-radius: 5px;
                background: transparent;
            }}
            QPushButton:hover {{
                background: {PRIMARY}20;
            }}
        """)
        scan_header.addWidget(self.view_scan_details)
        
        security_layout.addLayout(scan_header)
        
        # Pending scans list
        self.pending_scans = PendingScansList()
        security_layout.addWidget(self.pending_scans)
        
        # Share controls with safety check
        share_controls = QHBoxLayout()
        self.safety_check = QCheckBox("I confirm all files have been scanned and are safe")
        self.safety_check.setStyleSheet(f"color: {FG}")
        self.safety_check.setEnabled(False)
        share_controls.addWidget(self.safety_check)
        
        self.share_button = QPushButton("Share Files")
        self.share_button.setEnabled(False)
        share_controls.addWidget(self.share_button)
        
        security_layout.addLayout(share_controls)
        self.select_files_button.clicked.connect(self._select_files_clicked)
        file_row.addStretch(1)
        file_row.addWidget(self.select_files_button)
        file_row.addStretch(1)
        file_group.layout().addLayout(file_row)
        file_group.layout().addLayout(security_layout)
        layout.addWidget(file_group, 2)

        return widget

    def _manual_ip_connect_clicked(self):
        print("Manual IP Connect button clicked!")

    def _select_all_clients_clicked(self):
        # Call controller's select_all_clients if available
        if hasattr(self, 'controller') and hasattr(self.controller, 'select_all_clients'):
            self.controller.select_all_clients()

    def _select_files_clicked(self):
        print("Select Files to Share button clicked!")
        self.show_after_selection()

    def create_after_selection_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        selected_group = self.create_card_group("Selected Files")
        selected_vbox = QVBoxLayout()
        self.selected_files_list_widget = QListWidget()
        self.selected_files_list_widget.setSpacing(8)
        self.selected_files_list_widget.setFrameShape(QFrame.NoFrame)
        selected_vbox.addWidget(self.selected_files_list_widget)

        # Actions
        actions = QHBoxLayout()
        self.add_more_files_button = QPushButton("Add More Files")
        self.add_more_files_button.clicked.connect(self._add_more_files_clicked)
        self.remove_selected_files_button = QPushButton("Remove Selected")
        self.remove_selected_files_button.clicked.connect(self._remove_selected_files_clicked)
        self.select_all_files_button = QPushButton("Select All")
        self.select_all_files_button.clicked.connect(self._select_all_files_clicked)
        actions.addWidget(self.add_more_files_button)
        actions.addWidget(self.remove_selected_files_button)
        actions.addStretch(1)
        actions.addWidget(self.select_all_files_button)
        selected_vbox.addLayout(actions)

        selected_group.layout().addLayout(selected_vbox)
        layout.addWidget(selected_group)

        # Security Scanning Section
        security_group = self.create_card_group("Security Scan")
        security_layout = QVBoxLayout()
        
        # Security scan header with status
        scan_header = QHBoxLayout()
        scan_header.setSpacing(10)
        
        security_icon = QLabel("🛡️")
        security_icon.setStyleSheet(f"font-size: 16px;")
        scan_header.addWidget(security_icon)
        
        security_title = QLabel("Security Status")
        security_title.setStyleSheet(f"color: {FG}; font-weight: bold;")
        scan_header.addWidget(security_title)
        
        self.overall_status = QLabel("Files not scanned yet")
        self.overall_status.setStyleSheet(f"color: {FG_MUTED}")
        scan_header.addWidget(self.overall_status)
        
        scan_header.addStretch()
        
        # Scan Files button
        self.scan_files_button = QPushButton("🔍 Scan Files for Security")
        self.scan_files_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {WARNING};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {WARNING}dd;
            }}
        """)
        scan_header.addWidget(self.scan_files_button)
        
        security_layout.addLayout(scan_header)
        
        # Pending scans list
        self.pending_scans = PendingScansList()
        security_layout.addWidget(self.pending_scans)
        
        # Virus scan widget for detailed progress
        self.virus_scan_widget = VirusScanWidget()
        self.virus_scan_widget.setVisible(False)
        security_layout.addWidget(self.virus_scan_widget)
        
        # Share controls with safety check
        share_controls = QHBoxLayout()
        self.safety_check = QCheckBox("I confirm all files have been scanned and are safe")
        self.safety_check.setStyleSheet(f"color: {FG}")
        self.safety_check.setEnabled(False)
        share_controls.addWidget(self.safety_check)
        
        share_controls.addStretch()
        
        # Send buttons
        self.send_files_button = QPushButton("Send to Selected Clients")
        self.send_files_button.clicked.connect(self._send_files_clicked)
        self.send_files_button.setEnabled(False)
        share_controls.addWidget(self.send_files_button)
        
        self.send_to_all_button = QPushButton("Send to All Clients")
        self.send_to_all_button.clicked.connect(self._send_to_all_clicked)
        self.send_to_all_button.setEnabled(False)
        share_controls.addWidget(self.send_to_all_button)
        
        security_layout.addLayout(share_controls)
        
        security_group.layout().addLayout(security_layout)
        layout.addWidget(security_group)

        return widget

    def _add_more_files_clicked(self):
        print("Add More Files button clicked!")

    def _remove_selected_files_clicked(self):
        print("Remove Selected Files button clicked!")

    def _select_all_files_clicked(self):
        print("Select All Files button clicked!")

    def _send_files_clicked(self):
        print("Send to Selected Clients button clicked!")
        self.show_while_sharing()

    def _send_to_all_clicked(self):
        print("Send to All Clients button clicked!")
        self.show_while_sharing()

    def create_while_sharing_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        transfers_group = self.create_card_group("File Transfer Progress")
        transfers_vbox = QVBoxLayout()
        self.transfer_list_widget = QListWidget()
        self.transfer_list_widget.setSpacing(10)
        self.transfer_list_widget.setFrameShape(QFrame.NoFrame)
        transfers_vbox.addWidget(self.transfer_list_widget)

        # Actions
        actions = QHBoxLayout()
        self.cancel_all_button = QPushButton("Cancel All Transfers")
        self.cancel_selected_button = QPushButton("Cancel Selected")
        actions.addWidget(self.cancel_all_button)
        actions.addStretch(1)
        actions.addWidget(self.cancel_selected_button)
        transfers_vbox.addLayout(actions)

        # Share More prompt (hidden until needed)
        self.share_more_button = QPushButton("Share More")
        self.share_more_button.setVisible(False)
        transfers_vbox.addWidget(self.share_more_button, alignment=Qt.AlignHCenter)

        transfers_group.layout().addLayout(transfers_vbox)
        layout.addWidget(transfers_group)

        return widget

    def create_status_bar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def show_home(self):
        self.stacked_widget.setCurrentWidget(self.home_widget)

    def show_after_selection(self):
        self.stacked_widget.setCurrentWidget(self.after_selection_widget)

    def show_while_sharing(self):
        self.stacked_widget.setCurrentWidget(self.while_sharing_widget)

    def update_status_bar(self, message: str, color: str = FG):
        self.statusBar.setStyleSheet(f"QStatusBar {{ color: {color}; background: {BG2}; border-top: 1px solid {BORDER}; }}")
        self.statusBar.showMessage(message)

    def apply_theme(self):
        qss_template = """
        QWidget {
            background-color: $BG1;
            color: $FG;
            font-size: 14px;
        }
        QGroupBox {
            background-color: $BG2;
            border: 1px solid $BORDER;
            border-radius: 12px;
            margin-top: 16px;
            font-weight: 600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            top: 6px;
            padding: 0 6px;
            color: $PRIMARY;
        }
        QLabel#muted {
            color: $FG_MUTED;
        }
        QLabel#statusLabel {
            font-weight: 600;
            color: $FG;
        }
        QLineEdit {
            background: $BG1;
            color: $FG;
            border: 1px solid $BORDER;
            border-radius: 8px;
            padding: 8px 10px;
            selection-background-color: $PRIMARY;
        }
        QPushButton {
            background-color: $PRIMARY;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: 600;
        }
        QPushButton#secondaryButton {
            background-color: #1f2937; /* gray-800 */
            color: $FG;
            border: 1px solid $BORDER;
        }
        QListWidget {
            background: transparent;
            border: none;
        }
        QListWidget::item {
            border-radius: 10px;
            padding: 10px;
            margin: 4px;
        }
        QScrollBar:vertical {
            background: transparent;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: $BORDER;
            border-radius: 5px;
            min-height: 20px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px; width: 0px; background: none; border: none;
        }
        QStatusBar {
            color: $FG;
            background: $BG2;
            border-top: 1px solid $BORDER;
        }
        """
        qss = Template(qss_template).substitute(
            PRIMARY=PRIMARY,
            ACCENT=ACCENT,
            BG0=BG0,
            BG1=BG1,
            BG2=BG2,
            BORDER=BORDER,
            FG=FG,
            FG_MUTED=FG_MUTED,
        )
        self.setStyleSheet(qss)

    @staticmethod
    def _wrap(layout: QLayout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w


# For ad-hoc testing of the UI only
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ServerWindow()
    window.show()
    sys.exit(app.exec_())
