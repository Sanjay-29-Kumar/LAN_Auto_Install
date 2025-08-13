"""
Main server window for the LAN Auto Install application.
"""

import sys
import os
import socket
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from .custom_widgets import FileTransferWidget

class ServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Auto Install - Server")
        self.setGeometry(100, 100, 900, 700)

        self.stacked_widget = QStackedWidget()
        
        self.home_widget = self.create_home_widget()
        self.after_selection_widget = self.create_after_selection_widget()
        self.while_sharing_widget = self.create_while_sharing_widget()

        self.stacked_widget.addWidget(self.home_widget)
        self.stacked_widget.addWidget(self.after_selection_widget)
        self.stacked_widget.addWidget(self.while_sharing_widget)

        # Add a global back/home button
        self.global_back_home_button = QPushButton("Home / Back")
        self.global_back_home_button.setFixedSize(100, 30)
        self.global_back_home_button.clicked.connect(self.show_home)

        # Main layout to hold stacked widget and global button
        main_container_widget = QWidget()
        main_container_layout = QVBoxLayout(main_container_widget)
        
        # Top bar for global buttons/status
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch(1) # Push button to the right
        top_bar_layout.addWidget(self.global_back_home_button)
        main_container_layout.addLayout(top_bar_layout)
        
        main_container_layout.addWidget(self.stacked_widget)
        self.setCentralWidget(main_container_widget)

        self.create_status_bar()

    def create_home_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Top section with server info and connection status
        top_layout = QHBoxLayout()
        server_info_group = QGroupBox("Server Information")
        server_info_layout = QFormLayout(server_info_group)
        self.server_name_label = QLabel(socket.gethostname())
        self.server_ip_label = QLabel("Fetching IP...") # Initial text
        self.show_server_details_button = QPushButton("Details")
        self.show_server_details_button.setFixedSize(60, 25) # Smaller button
        
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(self.server_ip_label)
        ip_layout.addWidget(self.show_server_details_button)

        server_info_layout.addRow("Server Name:", self.server_name_label)
        server_info_layout.addRow("Server IP:", ip_layout)
        top_layout.addWidget(server_info_group)

        connection_status_group = QGroupBox("Connection Status")
        connection_status_layout = QFormLayout(connection_status_group)
        self.connection_status_label = QLabel("Not Connected")
        self.connected_clients_label = QLabel("0")
        connection_status_layout.addRow("Status:", self.connection_status_label)
        connection_status_layout.addRow("Connected Clients:", self.connected_clients_label)
        top_layout.addWidget(connection_status_group)
        layout.addLayout(top_layout)

        # Client list
        client_list_group = QGroupBox("Connected Clients")
        client_list_layout = QVBoxLayout(client_list_group)
        self.client_list_widget = QListWidget()
        client_list_layout.addWidget(self.client_list_widget)
        
        # Manual IP connection
        manual_ip_layout = QHBoxLayout()
        self.manual_ip_input = QLineEdit()
        self.manual_ip_input.setPlaceholderText("Enter client IP to connect manually")
        self.manual_ip_connect_button = QPushButton("Connect")
        manual_ip_layout.addWidget(self.manual_ip_input)
        manual_ip_layout.addWidget(self.manual_ip_connect_button)
        client_list_layout.addLayout(manual_ip_layout)

        self.refresh_clients_button = QPushButton("Refresh Client List")
        client_list_layout.addWidget(self.refresh_clients_button)
        layout.addWidget(client_list_group)

        # File selection
        file_selection_group = QGroupBox("File Selection")
        file_selection_layout = QVBoxLayout(file_selection_group)
        self.select_files_button = QPushButton("Select Files to Share")
        file_selection_layout.addWidget(self.select_files_button)
        layout.addWidget(file_selection_group)

        return widget

    def create_after_selection_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Selected files list
        selected_files_group = QGroupBox("Selected Files")
        selected_files_layout = QVBoxLayout(selected_files_group)
        self.selected_files_list_widget = QListWidget()
        selected_files_layout.addWidget(self.selected_files_list_widget)
        layout.addWidget(selected_files_group)

        # Action buttons
        button_layout = QHBoxLayout()
        self.add_more_files_button = QPushButton("Add More Files")
        self.remove_selected_files_button = QPushButton("Remove Selected")
        self.send_files_button = QPushButton("Send to Selected Clients")
        self.select_all_files_button = QPushButton("Select All")
        self.send_to_all_button = QPushButton("Send to All Clients")
        button_layout.addWidget(self.add_more_files_button)
        button_layout.addWidget(self.remove_selected_files_button)
        button_layout.addWidget(self.select_all_files_button)
        button_layout.addWidget(self.send_files_button)
        button_layout.addWidget(self.send_to_all_button)
        layout.addLayout(button_layout)

        return widget

    def create_while_sharing_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Transfer progress list
        transfer_progress_group = QGroupBox("File Transfer Progress")
        transfer_progress_layout = QVBoxLayout(transfer_progress_group)
        self.transfer_list_widget = QListWidget()
        transfer_progress_layout.addWidget(self.transfer_list_widget)
        layout.addWidget(transfer_progress_group)

        # Action buttons
        # Action buttons
        button_layout = QHBoxLayout()
        self.cancel_all_button = QPushButton("Cancel All Transfers")
        self.cancel_selected_button = QPushButton("Cancel Selected")
        # The back to home button is now global, so remove this one
        button_layout.addWidget(self.cancel_all_button)
        button_layout.addWidget(self.cancel_selected_button)
        layout.addLayout(button_layout)

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

# This is a placeholder for testing purposes
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ServerWindow()
    window.show()
    sys.exit(app.exec_())
