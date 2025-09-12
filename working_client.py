from ui.client_ui import ClientWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QListWidgetItem
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QColor
from network.client import NetworkClient
from ui.custom_widgets import FileTransferWidget, ProfileListItemWidget
import time
import sys
import os
import ctypes
import platform
from network import protocol

class ClientController:
    def __init__(self, network_client, ui):
        self.network_client = network_client
        self.ui = ui
        self.transfer_widgets = {}
        self.load_user_preferences()
        self.network_client.status_update.connect(self.ui.update_status_bar)
        self.network_client.start_client() # Start the client network operations

    def load_user_preferences(self):
        # Load user preferences
        if hasattr(self.ui, 'load_preferences'):
            self.ui.load_preferences()
        # Connect network signals to UI slots
        self.network_client.server_found.connect(self.update_server_list)
        self.network_client.connection_status.connect(self.update_connection_status)
        self.network_client.file_received.connect(self.add_received_file)
        self.network_client.file_progress.connect(self.update_transfer_progress)
        # Update receiving status (e.g., cancelled/disconnected)
        self.network_client.status_update_received.connect(self.update_transfer_status)

        # Connect UI signals to controller slots
        self.ui.refresh_servers_button.clicked.connect(self.refresh_servers)
        # Automatically connect to preferred servers on discovery
        for server_info in self.network_client.servers.values():
            if server_info['ip'] in self.ui.preferred_servers:
                self.network_client._connect_to_server(server_info['ip'], server_info['port'])
        self.ui.connect_to_selected_button.clicked.connect(self.connect_to_selected)
        self.ui.open_folder_button.clicked.connect(self.open_received_folder)
        self.ui.clear_list_button.clicked.connect(self.clear_received_list)
        # self.ui.server_list_widget.itemClicked.connect(self.show_server_profile)
        self.ui.show_profile_button.clicked.connect(self.show_selected_server_profile)

    def show_selected_server_profile(self):
        selected_ip = None
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected_ip = item.text().split('(')[1].split(')')[0]
                break

        if not selected_ip:
            QMessageBox.information(self.ui, "Server Profile", "Select a device (checked) first.")
            return

        server_info = self.network_client.servers.get(selected_ip)
        if not server_info:
            QMessageBox.information(self.ui, "Server Profile", "Details not available.")
            return

        profile_text = f"Server Profile\nHostname: {server_info.get('hostname','N/A')}\nIP: {server_info.get('ip','N/A')}\nLast Seen: {time.ctime(server_info.get('last_seen',0))}"
        QMessageBox.information(self.ui, "Server Profile", profile_text)
        self.ui.manual_connect_button.clicked.connect(self.connect_manual)
        self.ui.global_back_home_button.clicked.connect(self.ui.show_home) # Connect global back/home button
        self.ui.connect_to_all_button.clicked.disconnect()
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
            widget = self.ui.server_list_widget.itemWidget(self.ui.server_list_widget.item(i))
            if widget and hasattr(widget, 'server_info') and widget.server_info.get('ip') == server_info.get('ip'):
                # Update existing entry with latest info
                hostname = server_info.get('hostname', 'Unknown Host')
                ip = server_info.get('ip', 'Unknown IP')
                os_type = server_info.get('os_type', 'Unknown OS')
                
                # Format: "Hostname IP [OS]" - ensure full display
                display_text = f"{hostname} {ip} [{os_type}]"
                
                # Update the widget with new info
                widget.server_info = server_info
                if hasattr(widget, 'label'):
                    widget.label.setText(display_text)
                    widget.label.setToolTip(f"Server: {hostname}\nIP: {ip}\nOS: {os_type}\nPort: {server_info.get('port', 'Unknown')}")
                return

        # Create new entry
        hostname = server_info.get('hostname', 'Unknown Host')
        ip = server_info.get('ip', 'Unknown IP')
        os_type = server_info.get('os_type', 'Unknown OS')
        port = server_info.get('port', 5001)
        
        # Format: "Hostname IP [OS]" - ensure full display
        display_text = f"{hostname} {ip} [{os_type}]"
        
        print(f"Adding server to list: {display_text}")
        
        item = QListWidgetItem()
        item.setSizeHint(QSize(650, 100))  # Increased size to better accommodate content
        
        widget = ProfileListItemWidget(display_text, show_checkbox=True)
        widget.setMinimumWidth(600)  # Ensure widget has enough width
        widget.set_checked(False)  # Don't auto-check
        widget.server_info = server_info
        
        # Add detailed tooltip
        tooltip = f"Server Details:\nHostname: {hostname}\nIP Address: {ip}\nOS: {os_type}\nPort: {port}"
        if hasattr(widget, 'label'):
            widget.label.setToolTip(tooltip)
        
        def show_profile():
            self.show_server_profile_by_info(widget.server_info)
        widget.profile_button.clicked.connect(show_profile)
        
        self.ui.server_list_widget.addItem(item)
        self.ui.server_list_widget.setItemWidget(item, widget)
        
        # Status update
        self.ui.update_status_bar(f"Found server: {hostname} ({ip})", "green")
        
        # Auto-connect to each discovered server
        try:
            self.network_client._connect_to_server(server_info['ip'], server_info['port'])
        except Exception as e:
            print(f"Auto-connect error: {e}")

    def show_server_profile_by_ip(self, ip):
        server_info = self.network_client.servers.get(ip)
        self.show_server_profile_by_info(server_info)

    def show_server_profile_by_info(self, server_info):
        if not server_info:
            QMessageBox.information(self.ui, "Server Profile", "Details not available.")
            return
        profile_text = f"Server Profile\nHostname: {server_info.get('hostname','N/A')}\nIP: {server_info.get('ip','N/A')}\nLast Seen: {time.ctime(server_info.get('last_seen',0))}"
        QMessageBox.information(self.ui, "Server Profile", profile_text)

    def update_connection_status(self, server_ip, connected):
        self.ui.connection_status_label.setText(f"Connected to {server_ip}" if connected else f"Disconnected from {server_ip}")
        # Update color only; avoid appending long status text which causes wrapping
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            if server_ip in item.text():
                item.setForeground(QColor("lightgreen" if connected else "lightcoral"))
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
        # Wire cancel button to request cancel from server for this file
        widget.cancel_button.clicked.connect(lambda checked=False, fn=file_name, sip=server_ip: self.handle_cancel_receive(fn, sip))
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

    def handle_cancel_receive(self, file_name, server_ip):
        # Send cancel request to server and reflect in UI
        try:
            self.network_client.request_cancel_receive(server_ip, file_name)
            if (file_name, server_ip) in self.transfer_widgets:
                self.transfer_widgets[(file_name, server_ip)].set_status("Cancel requested", "red")
        except Exception:
            pass

    def refresh_servers(self):
        self.ui.server_list_widget.clear()
        self.network_client.servers.clear()
        # The discovery thread will find servers again automatically

    def connect_to_selected(self):
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            widget = self.ui.server_list_widget.itemWidget(item)
            if widget and widget.is_checked():
                if hasattr(widget, 'server_info'):
                    server_info = widget.server_info
                    self.network_client._connect_to_server(server_info['ip'], server_info['port'])

    def connect_to_all(self):
        """Connects to all discovered servers."""
        for i in range(self.ui.server_list_widget.count()):
            item = self.ui.server_list_widget.item(i)
            widget = self.ui.server_list_widget.itemWidget(item)
            if widget and widget.is_checked():
                if hasattr(widget, 'server_info'):
                    server_info = widget.server_info
                    self.network_client._connect_to_server(server_info['ip'], server_info['port'])

    def connect_manual(self):
        ip = self.ui.manual_ip_input.text().strip()
        if not ip:
            QMessageBox.warning(self.ui, "Invalid IP", "Please enter a valid IP address.")
            return
        
        ip = self.ui.manual_ip_input.text().strip()
        ip = self.ui.manual_ip_input.text().strip()
        port = protocol.COMMAND_PORT
        self.network_client._connect_to_server(ip, port)

    def open_received_folder(self):
        os.startfile(self.network_client.received_files_path)

    def clear_received_list(self):
        self.ui.receiving_list_widget.clear()

if __name__ == "__main__":
    # Setup log file to capture console output
    logs_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "client.log")

    class Tee:
        def __init__(self, *streams):
            # Filter out None streams (e.g., when __stdout__ is None in GUI apps)
            self.streams = [s for s in streams if s is not None]
        def write(self, data):
            for s in self.streams:
                try:
                    s.write(data)
                    s.flush()
                except Exception:
                    # Ignore any stream write errors to avoid crashing the app
                    pass
        def flush(self):
            for s in self.streams:
                try:
                    s.flush()
                except Exception:
                    pass

    log_file = open(log_path, "a", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)

    app = QApplication([])
    
    # Initialize Network Client first as it's a dependency for ClientWindow
    network_client = NetworkClient()

    # Initialize UI
    client_window = ClientWindow(network_client) # Pass network_client instance
    
    # Initialize Controller
    controller = ClientController(network_client, client_window)
    # Attach controller to window for UI callbacks
    client_window.controller = controller
    client_window.show()
    app.exec_()
    # Ensure client stops gracefully on exit
    network_client.stop_client()
    try:
        log_file.close()
    except Exception:
        pass
