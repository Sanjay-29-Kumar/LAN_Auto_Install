from ui.client_ui import ClientWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QListWidgetItem
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from network.client import NetworkClient
from ui.custom_widgets import FileTransferWidget
import time
import os
from network import protocol

class ClientController:
    def __init__(self, network_client, ui):
        self.network_client = network_client
        self.ui = ui
        self.transfer_widgets = {}
        self.connect_signals()
        self.network_client.status_update.connect(self.ui.update_status_bar)
        self.network_client.start_client() # Start the client network operations

    def connect_signals(self):
        # Connect network signals to UI slots
        self.network_client.server_found.connect(self.update_server_list)
        self.network_client.connection_status.connect(self.update_connection_status)
        self.network_client.file_received.connect(self.add_received_file)
        self.network_client.file_progress.connect(self.update_transfer_progress)
        self.network_client.status_update.connect(self.update_transfer_status)

        # Connect UI signals to controller slots
        self.ui.refresh_servers_button.clicked.connect(self.refresh_servers)
        self.ui.connect_to_selected_button.clicked.connect(self.connect_to_selected)
        self.ui.open_folder_button.clicked.connect(self.open_received_folder)
        self.ui.clear_list_button.clicked.connect(self.clear_received_list)
        self.ui.server_list_widget.itemClicked.connect(self.show_server_profile)
        self.ui.manual_connect_button.clicked.connect(self.connect_manual)
        self.ui.global_back_home_button.clicked.connect(self.ui.show_home) # Connect global back/home button
        self.ui.connect_to_all_button.clicked.connect(self.connect_to_all) # Connect connect to all button

    def show_server_profile(self, item):
        ip = item.text().split('(')[1].replace(')', '').split(' ')[0]
        if ip in self.network_client.servers:
            server_info = self.network_client.servers[ip]
            profile_text = f"""
            <b>Server Profile</b><br>
            --------------------<br>
            <b>Hostname:</b> {server_info.get('hostname', 'N/A')}<br>
            <b>IP Address:</b> {server_info.get('ip', 'N/A')}<br>
            <b>Last Seen:</b> {time.ctime(server_info.get('last_seen', 0))}
            """
            QMessageBox.information(self.ui, "Server Profile", profile_text)

    def update_server_list(self, server_info):
        # Avoid duplicates
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if server_info['ip'] in item.text():
                return
        
        item = QListWidgetItem(f"{server_info['hostname']} ({server_info['ip']})")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        if server_info['ip'] == self.network_client.local_ip:
            item.setCheckState(Qt.Checked)
        else:
            item.setCheckState(Qt.Unchecked)
        self.ui.server_list_widget.addItem(item)

    def update_connection_status(self, server_ip, connected):
        self.ui.connection_status_label.setText("Connected" if connected else "Not Connected")
        # You can also update the server list item to show connection status
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if server_ip in item.text():
                if connected:
                    item.setText(f"{item.text().split(' ')[0]} ({server_ip}) [Connected]")
                    item.setForeground(QColor("lightgreen"))
                else:
                    item.setText(f"{item.text().split(' ')[0]} ({server_ip}) [Disconnected]")
                    item.setForeground(QColor("lightcoral"))
                break

    def add_received_file(self, file_info):
        file_name = file_info['name']
        server_ip = file_info['sender']
        
        widget = FileTransferWidget(file_name, file_info['size'])
        item = QListWidgetItem(self.ui.receiving_list_widget)
        item.setSizeHint(widget.sizeHint())
        self.ui.receiving_list_widget.addItem(item)
        self.ui.receiving_list_widget.setItemWidget(item, widget)
        self.transfer_widgets[(file_name, server_ip)] = widget
        self.ui.show_receiving() # Switch to receiving screen when a file starts to be received

    def update_transfer_progress(self, file_name, server_ip, percentage):
        if (file_name, server_ip) in self.transfer_widgets:
            widget = self.transfer_widgets[(file_name, server_ip)]
            widget.set_progress(percentage)
            widget.set_status(f"Receiving from {server_ip}...", "orange")
            if percentage >= 100:
                widget.set_status("Received", "lightgreen")

    def update_transfer_status(self, file_name, server_ip, status):
        if (file_name, server_ip) in self.transfer_widgets:
            widget = self.transfer_widgets[(file_name, server_ip)]
            widget.set_status(status, "lightblue")

    def refresh_servers(self):
        self.ui.server_list_widget.clear()
        self.network_client.servers.clear()
        # The discovery thread will find servers again automatically

    def connect_to_selected(self):
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                ip = item.text().split('(')[1].replace(')', '').split(' ')[0]
                if ip in self.network_client.servers:
                    server_info = self.network_client.servers[ip]
                    self.network_client._connect_to_server(server_info['ip'], server_info['port'])

    def connect_to_all(self):
        """Connects to all discovered servers."""
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if item.checkState() == Qt.Checked: # Only connect to those that are checked
                ip = item.text().split('(')[1].replace(')', '').split(' ')[0]
                if ip in self.network_client.servers:
                    server_info = self.network_client.servers[ip]
                    self.network_client._connect_to_server(server_info['ip'], server_info['port'])

    def connect_manual(self):
        ip = self.ui.manual_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self.ui, "Invalid IP", "Please enter a valid IP address.")
            return
        
        # Use default command port
        port = protocol.COMMAND_PORT
        self.network_client._connect_to_server(ip, port)

    def open_received_folder(self):
        os.startfile(self.network_client.received_files_path)

    def clear_received_list(self):
        self.ui.receiving_list_widget.clear()

if __name__ == "__main__":
    app = QApplication([])
    
    # Initialize Network Client first as it's a dependency for ClientWindow
    network_client = NetworkClient()

    # Initialize UI
    client_window = ClientWindow(network_client) # Pass network_client instance
    
    # Initialize Controller
    controller = ClientController(network_client, client_window)
    
    client_window.show()
    app.exec_()
    
    # Ensure client stops gracefully on exit
    network_client.stop_client()
