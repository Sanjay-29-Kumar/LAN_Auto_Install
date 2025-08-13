"""
Main client window for the LAN Auto Install application.
"""

import sys
import os
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .custom_widgets import FileTransferWidget

class ClientWindow(QMainWindow):
    def __init__(self, network_client):
        super().__init__()
        self.network_client = network_client
        self.setWindowTitle("LAN Auto Install - Client")
        self.setGeometry(100, 100, 900, 700)

        self.main_widget = self.create_main_widget()
        self.setCentralWidget(self.main_widget)

        self.create_status_bar()

    def create_main_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Top section with client info and connection status
        top_layout = QHBoxLayout()
        client_info_group = QGroupBox("Client Information")
        client_info_layout = QFormLayout(client_info_group)
        self.client_name_label = QLabel(self.network_client.local_ip) # Placeholder for now
        self.client_ip_label = QLabel(self.network_client.local_ip)
        client_info_layout.addRow("Client Name:", self.client_name_label)
        client_info_layout.addRow("Client IP:", self.client_ip_label)
        top_layout.addWidget(client_info_group)

        connection_status_group = QGroupBox("Connection Status")
        connection_status_layout = QFormLayout(connection_status_group)
        self.connection_status_label = QLabel("Not Connected")
        connection_status_layout.addRow("Status:", self.connection_status_label)
        top_layout.addWidget(connection_status_group)
        layout.addLayout(top_layout)

        # Server list
        server_list_group = QGroupBox("Available Servers")
        server_list_layout = QVBoxLayout(server_list_group)
        self.server_list_widget = QListWidget()
        server_list_layout.addWidget(self.server_list_widget)
        
        server_buttons_layout = QHBoxLayout()
        self.refresh_servers_button = QPushButton("Refresh")
        self.connect_to_selected_button = QPushButton("Connect to Selected")
        self.connect_to_all_button = QPushButton("Connect to All")
        server_buttons_layout.addWidget(self.refresh_servers_button)
        server_buttons_layout.addWidget(self.connect_to_selected_button)
        server_buttons_layout.addWidget(self.connect_to_all_button)
        server_list_layout.addLayout(server_buttons_layout)

        manual_connect_group = QGroupBox("Manual Connection")
        manual_connect_layout = QHBoxLayout(manual_connect_group)
        self.manual_ip_input = QLineEdit()
        self.manual_ip_input.setPlaceholderText("Enter server IP")
        self.manual_connect_button = QPushButton("Connect")
        manual_connect_layout.addWidget(self.manual_ip_input)
        manual_connect_layout.addWidget(self.manual_connect_button)
        server_list_layout.addWidget(manual_connect_group)

        layout.addWidget(server_list_group)

        # Receiving status
        receiving_status_group = QGroupBox("Receiving Status")
        receiving_status_layout = QVBoxLayout(receiving_status_group)
        self.receiving_list_widget = QListWidget()
        receiving_status_layout.addWidget(self.receiving_list_widget)
        
        receiving_buttons_layout = QHBoxLayout()
        self.open_folder_button = QPushButton("Open Folder")
        self.clear_list_button = QPushButton("Clear List")
        receiving_buttons_layout.addWidget(self.open_folder_button)
        receiving_buttons_layout.addWidget(self.clear_list_button)
        receiving_status_layout.addLayout(receiving_buttons_layout)
        layout.addWidget(receiving_status_group)

        return widget

    def create_status_bar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

# This is a placeholder for testing purposes
if __name__ == '__main__':
    class MockNetworkClient:
        def __init__(self):
            self.local_ip = "127.0.0.1"
    app = QApplication(sys.argv)
    client = MockNetworkClient()
    window = ClientWindow(client)
    window.show()
    sys.exit(app.exec_())
