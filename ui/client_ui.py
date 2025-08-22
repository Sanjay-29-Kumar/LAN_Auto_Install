"""
LocalSend-inspired client UI for the LAN Auto Install application.
- Modern dark theme with rounded cards and accent colors
- Device list presented in icon/card mode similar to LocalSend
- Preserves existing widget names used by the controller
"""

import sys
import os
import socket
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .custom_widgets import FileTransferWidget
from string import Template

PRIMARY = "#3b82f6"   # blue-500
ACCENT = "#22c55e"    # green-500
BG0 = "#0b1220"       # near-slate-900
BG1 = "#0f172a"       # slate-900
BG2 = "#111827"       # gray-900
BORDER = "#374151"    # gray-700
FG = "#e5e7eb"        # gray-200
FG_MUTED = "#9ca3af"  # gray-400


class PillLabel(QLabel):
    def __init__(self, text="", color=ACCENT, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"QLabel {{ background-color: {color}; color: #0b1220; border-radius: 10px; padding: 3px 8px; font-weight: 600; }}"
        )


class ClientWindow(QMainWindow):
    # Signal to notify when Details button is clicked
    show_client_details_requested = pyqtSignal()
    def __init__(self, network_client):
        super().__init__()
        self.network_client = network_client
        self.setWindowTitle("LAN Auto Install - Client")
        self.setGeometry(100, 100, 1000, 720)

        # App/window icon
        try:
            base = getattr(sys, '_MEIPASS', os.path.abspath('.'))
            self.setWindowIcon(QIcon(os.path.join(base, 'client.png')))
        except Exception:
            pass

        # Core stacked pages
        self.stacked_widget = QStackedWidget()
        self.home_widget = self.create_home_widget()
        self.receiving_widget = self.create_receiving_widget()
        self.stacked_widget.addWidget(self.home_widget)
        self.stacked_widget.addWidget(self.receiving_widget)

        # Global top app bar (LocalSend-like)
        appbar = QWidget()
        appbar_layout = QHBoxLayout(appbar)
        appbar_layout.setContentsMargins(16, 12, 16, 12)
        appbar_layout.setSpacing(12)

        title_box = QHBoxLayout()
        title_icon = QLabel()
        title_icon.setFixedSize(26, 26)
        # simple circular accent dot as pseudo-logo
        title_icon.setStyleSheet(
            f"background-color: {PRIMARY}; border-radius: 13px;"
        )
        title_label = QLabel("LAN Auto Install")
        title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        title_box.addWidget(title_icon)
        title_box.addSpacing(8)
        title_box.addWidget(title_label)

        appbar_layout.addLayout(title_box)
        appbar_layout.addStretch(1)

        # Device info pill similar to LocalSend header
        self.device_pill = PillLabel(socket.gethostname())
        appbar_layout.addWidget(self.device_pill)

        # Global home/back button preserved for controller wiring
        self.global_back_home_button = QPushButton("Home / Back")
        self.global_back_home_button.setObjectName("secondaryButton")
        self.global_back_home_button.setFixedHeight(34)
        self.global_back_home_button.clicked.connect(self.show_home)
        appbar_layout.addWidget(self.global_back_home_button)

        # Main container: app bar + stacked pages
        main_container_widget = QWidget()
        main_container_layout = QVBoxLayout(main_container_widget)
        main_container_layout.setContentsMargins(12, 8, 12, 8)
        main_container_layout.setSpacing(8)
        main_container_layout.addWidget(appbar)
        main_container_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(main_container_widget)

        self.create_status_bar()
        self.apply_theme()

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

        # Top status row (Client info + Connection status) as compact cards
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        client_info_group = self.create_card_group("Client")
        client_form = QFormLayout()
        client_form.setLabelAlignment(Qt.AlignRight)
        self.client_name_label = QLabel(socket.gethostname())
        self.client_ip_label = QLabel(self.network_client.local_ip)
        self.client_name_label.setObjectName("muted")
        self.client_ip_label.setObjectName("muted")
        client_form.addRow("Name:", self.client_name_label)
        # Add Details button next to IP
        ip_row = QHBoxLayout()
        ip_row.setSpacing(8)
        ip_row.addWidget(self.client_ip_label)
        self.show_client_details_button = QPushButton("Details")
        self.show_client_details_button.setFixedHeight(28)
        self.show_client_details_button.setObjectName("secondaryButton")
        self.show_client_details_button.clicked.connect(self.on_show_client_details_clicked)
        ip_row.addWidget(self.show_client_details_button)
        client_form.addRow("IP:", ip_row)

        client_info_group.layout().addLayout(client_form)
        top_row.addWidget(client_info_group, 1)

        connection_group = self.create_card_group("Connection")
        connection_form = QFormLayout()
        connection_form.setLabelAlignment(Qt.AlignRight)
        self.connection_status_label = QLabel("Not Connected")
        self.connection_status_label.setObjectName("statusLabel")
        connection_form.addRow("Status:", self.connection_status_label)
        connection_group.layout().addLayout(connection_form)
        top_row.addWidget(connection_group, 1)

        layout.addLayout(top_row)

        # Nearby devices (LocalSend-like grid)
        devices_group = self.create_card_group("Nearby Devices")
        devices_vbox = QVBoxLayout()
        devices_vbox.setSpacing(8)

        # QListWidget configured to look like a grid of device cards
        self.server_list_widget = QListWidget()
        self.server_list_widget.setViewMode(QListView.IconMode)
        self.server_list_widget.setIconSize(QSize(72, 72))
        self.server_list_widget.setResizeMode(QListView.Adjust)
        self.server_list_widget.setMovement(QListView.Static)
        self.server_list_widget.setSpacing(18)
        self.server_list_widget.setWordWrap(False)  # prevent multi-line wrap
        self.server_list_widget.setUniformItemSizes(True)
        self.server_list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        # enforce a consistent grid size so text doesn't overlap
        self.server_list_widget.setGridSize(QSize(220, 130))
        devices_vbox.addWidget(self.server_list_widget)

        # Actions row
        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.refresh_servers_button = QPushButton("Refresh")
        self.refresh_servers_button.setObjectName("secondaryButton")
        self.refresh_servers_button.clicked.connect(self._refresh_servers_clicked)
        self.connect_to_selected_button = QPushButton("Connect to Selected")
        self.connect_to_selected_button.clicked.connect(self._connect_to_selected_clicked)
        self.connect_to_all_button = QPushButton("Connect to All")
        self.connect_to_all_button.clicked.connect(self._connect_to_all_clicked)
        self.show_profile_button = QPushButton("Show Profile")
        self.show_profile_button.clicked.connect(self._show_client_profile_clicked)
        actions.addWidget(self.refresh_servers_button)
        actions.addStretch(1)
        actions.addWidget(self.show_profile_button)
        actions.addWidget(self.connect_to_selected_button)
        actions.addWidget(self.connect_to_all_button)
        devices_vbox.addLayout(actions)

        # Manual connect section
        manual_group = self.create_card_group("Manual Connection")
        manual_hbox = QHBoxLayout()
        manual_hbox.setSpacing(8)
        self.manual_ip_input = QLineEdit()
        self.manual_ip_input.setPlaceholderText("Enter server IP")
        self.manual_connect_button = QPushButton("Connect")
        self.manual_connect_button.clicked.connect(self._manual_connect_clicked)
        manual_hbox.addWidget(self.manual_ip_input, 3)
        manual_hbox.addWidget(self.manual_connect_button, 1)
        manual_group.layout().addLayout(manual_hbox)

        devices_group.layout().addLayout(devices_vbox)
        layout.addWidget(devices_group, 5)
        layout.addWidget(manual_group, 1)

        return widget

    def on_show_client_details_clicked(self):
        self.show_client_details_requested.emit()

    def _refresh_servers_clicked(self):
        print("Refresh Servers button clicked!")

    def _connect_to_selected_clicked(self):
        print("Connect to Selected button clicked!")

    def _connect_to_all_clicked(self):
        print("Connect to All button clicked!")

    def _show_client_profile_clicked(self):
        print("Show Client Profile button clicked!")

    def _manual_connect_clicked(self):
        print("Manual Connect button clicked!")

    def create_receiving_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # Transfers list styled as cards
        receiving_group = self.create_card_group("Transfers")
        receiving_vbox = QVBoxLayout()
        receiving_vbox.setSpacing(8)

        self.receiving_list_widget = QListWidget()
        self.receiving_list_widget.setSpacing(10)
        self.receiving_list_widget.setFrameShape(QFrame.NoFrame)
        receiving_vbox.addWidget(self.receiving_list_widget)

        receiving_actions = QHBoxLayout()
        receiving_actions.setSpacing(8)
        self.open_folder_button = QPushButton("Open Folder")
        self.open_folder_button.setObjectName("secondaryButton")
        self.open_folder_button.clicked.connect(self._open_folder_clicked)
        self.clear_list_button = QPushButton("Clear List")
        self.clear_list_button.clicked.connect(self._clear_list_clicked)
        receiving_actions.addWidget(self.open_folder_button)
        receiving_actions.addStretch(1)
        receiving_actions.addWidget(self.clear_list_button)
        receiving_vbox.addLayout(receiving_actions)

        receiving_group.layout().addLayout(receiving_vbox)
        layout.addWidget(receiving_group)

        return widget

    def _open_folder_clicked(self):
        print("Open Folder button clicked!")

    def _clear_list_clicked(self):
        print("Clear List button clicked!")

    def create_status_bar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def update_status_bar(self, message, color):
        self.statusBar.setStyleSheet(f"QStatusBar {{ color: {color}; background: {BG2}; border-top: 1px solid {BORDER}; }}")
        self.statusBar.showMessage(message)

    def show_home(self):
        self.stacked_widget.setCurrentWidget(self.home_widget)

    def show_receiving(self):
        self.stacked_widget.setCurrentWidget(self.receiving_widget)

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


# For ad-hoc testing of the UI only
if __name__ == '__main__':
    class MockNetworkClient:
        def __init__(self):
            self.local_ip = "127.0.0.1"

    app = QApplication(sys.argv)
    client = MockNetworkClient()
    window = ClientWindow(client)
    window.show()
    sys.exit(app.exec_())
