from ui.server_ui import ServerWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QFileDialog, QListWidgetItem
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from network.server import NetworkServer
from ui.custom_widgets import FileTransferWidget
import os
import time
from network import protocol

class ServerController:
    def __init__(self, network_server, ui):
        self.network_server = network_server
        self.ui = ui
        self.transfer_widgets = {}
        self.pending_transfers = set()
        self.connect_signals()
        self.network_server.start_server() # Start the server network operations

    def connect_signals(self):
        # Connect network signals to UI slots
        self.network_server.client_connected.connect(self.update_client_list)
        self.network_server.client_disconnected.connect(self.update_client_list)

        # Connect UI signals to controller slots
        self.ui.select_files_button.clicked.connect(self.select_files)
        self.ui.send_files_button.clicked.connect(self.send_files)
        self.ui.global_back_home_button.clicked.connect(self.ui.show_home)
        self.ui.refresh_clients_button.clicked.connect(self.update_client_list)
        self.ui.add_more_files_button.clicked.connect(self.select_files)
        self.ui.remove_selected_files_button.clicked.connect(self.remove_selected_files)
        self.ui.select_all_files_button.clicked.connect(self.select_all_files)
        self.ui.send_to_all_button.clicked.connect(self.send_to_all_clients)
        self.network_server.file_progress.connect(self.update_transfer_progress)
        self.network_server.status_update_received.connect(self.update_transfer_status)
        self.ui.client_list_widget.itemClicked.connect(self.show_client_profile)
        self.ui.manual_ip_connect_button.clicked.connect(self.connect_to_manual_ip)
        self.ui.show_server_details_button.clicked.connect(self.show_server_details)
        self.network_server.server_ip_updated.connect(self.update_server_ip_display)
        self.ui.cancel_all_button.clicked.connect(self.cancel_all_transfers)
        self.ui.cancel_selected_button.clicked.connect(self.cancel_selected_transfers)
        self.ui.global_back_home_button.clicked.connect(self.ui.show_home) # Connect global back/home button
        self.network_server.status_update.connect(self.update_status_bar) # Connect status update signal
        self.ui.global_back_home_button.clicked.connect(self.ui.show_home) # Connect global back/home button
        self.network_server.status_update.connect(self.update_status_bar) # Connect status update signal
        # New UI actions
        if hasattr(self.ui, 'select_all_clients_button'):
            self.ui.select_all_clients_button.clicked.connect(self.select_all_clients)
        if hasattr(self.ui, 'share_more_button'):
            self.ui.share_more_button.clicked.connect(self.share_more)

    def update_server_ip_display(self, ip_address):
        self.ui.server_ip_label.setText(f"Server IP: {ip_address}")

    def connect_to_manual_ip(self):
        ip_address = self.ui.manual_ip_input.text()
        if ip_address:
            self.network_server.connect_to_client_manual(ip_address)
            self.ui.manual_ip_input.clear()
            self.ui.status_bar.setText(f"Attempting to connect to {ip_address}...")
        else:
            QMessageBox.warning(self.ui, "Invalid IP", "Please enter a valid IP address.")

    def show_server_details(self):
        server_ip = self.network_server.get_server_ip()
        hostname = os.uname().nodename if hasattr(os, 'uname') else 'N/A'
        system_info = f"""
        <b>Server Details</b><br>
        --------------------<br>
        <b>Hostname:</b> {hostname}<br>
        <b>IP Address:</b> {server_ip}<br>
        <b>Operating System:</b> {os.sys.platform}<br>
        """
        QMessageBox.information(self.ui, "Server Details", system_info)

    def show_client_profile(self, item):
        ip = item.text().split('(')[1].replace(')', '')
        if ip in self.network_server.clients:
            client_info = self.network_server.clients[ip]
            profile_text = f"""
            <b>Client Profile</b><br>
            --------------------<br>
            <b>Hostname:</b> {client_info.get('hostname', 'N/A')}<br>
            <b>IP Address:</b> {client_info.get('ip', 'N/A')}<br>
            <b>Last Seen:</b> {time.ctime(client_info.get('last_seen', 0))}<br>
            <b>Files Sent:</b> {client_info.get('files_sent', 0)}
            """
            QMessageBox.information(self.ui, "Client Profile", profile_text)

    def update_client_list(self, *args):
        self.ui.client_list_widget.clear()
        connected_clients = self.network_server.get_connected_clients()
        for client in connected_clients:
            item = QListWidgetItem(f"{client['hostname']} ({client['ip']})")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.ui.client_list_widget.addItem(item)
        self.ui.connected_clients_label.setText(str(len(connected_clients)))
        self.ui.connection_status_label.setText("Connected" if connected_clients else "Not Connected")

    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self.ui, "Select Files to Share")
        if file_paths:
            self.network_server.add_files_for_distribution(file_paths)
            self.update_selected_files_list()
            self.ui.show_after_selection()

    def update_selected_files_list(self):
        self.ui.selected_files_list_widget.clear()
        for file_info in self.network_server.files_to_distribute:
            item = QListWidgetItem(f"{file_info['name']} ({file_info['size'] / 1024 / 1024:.2f} MB)")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.ui.selected_files_list_widget.addItem(item)

    def remove_selected_files(self):
        items_to_remove = []
        for i in range(self.ui.selected_files_list_widget.count()):
            item = self.ui.selected_files_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                items_to_remove.append(i)

        # Remove in reverse order to avoid index shifting issues
        for i in sorted(items_to_remove, reverse=True):
            self.network_server.files_to_distribute.pop(i)
            self.ui.selected_files_list_widget.takeItem(i)

    def select_all_files(self):
        for i in range(self.ui.selected_files_list_widget.count()):
            item = self.ui.selected_files_list_widget.item(i)
            item.setCheckState(Qt.Checked)

    def send_files(self):
        selected_clients = []
        for i in range(self.ui.client_list_widget.count()):
            item = self.ui.client_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                # Assuming the text is "hostname (ip)"
                ip = item.text().split('(')[1].replace(')', '')
                selected_clients.append(ip)
        
        if not selected_clients:
            QMessageBox.warning(self.ui, "No Clients Selected", "Please select at least one client to send files to.")
            return

        if not self.network_server.files_to_distribute:
            QMessageBox.warning(self.ui, "No Files Selected", "Please select files to distribute.")
            return

        self.ui.transfer_list_widget.clear()
        self.transfer_widgets = {}
        self.pending_transfers = set()
        if hasattr(self.ui, 'share_more_button'):
            self.ui.share_more_button.setVisible(False)

        # Populate transfer list with all selected files for all selected clients
        for file_info in self.network_server.files_to_distribute:
            for client_ip in selected_clients:
                widget = FileTransferWidget(file_info['name'], file_info['size'], client_ip) # Pass client_ip to widget
                item = QListWidgetItem(self.ui.transfer_list_widget)
                item.setSizeHint(widget.sizeHint())
                self.ui.transfer_list_widget.addItem(item)
                self.ui.transfer_list_widget.setItemWidget(item, widget)
                self.transfer_widgets[(file_info['name'], client_ip)] = widget
                self.pending_transfers.add((file_info['name'], client_ip))
                # Connect cancel button for each transfer widget
                widget.cancel_button.clicked.connect(lambda checked, fn=file_info['name'], cip=client_ip: self.cancel_single_transfer(fn, cip))
                # Add a checkbox to the widget for selection
                widget.add_checkbox()

        self.network_server.distribute_files_to_clients(selected_clients)
        self.ui.show_while_sharing()

    def update_transfer_progress(self, file_name, client_ip, percentage):
        if (file_name, client_ip) in self.transfer_widgets:
            widget = self.transfer_widgets[(file_name, client_ip)]
            widget.set_progress(percentage)
            widget.set_status(f"Sending to {client_ip}...", "orange")
            if percentage >= 100:
                widget.set_status("Sent", "lightgreen")

    def update_transfer_status(self, file_name, client_ip, status):
        if (file_name, client_ip) in self.transfer_widgets:
            widget = self.transfer_widgets[(file_name, client_ip)]
            widget.set_status(status, "lightblue")
        if self._is_terminal_status(status):
            self.pending_transfers.discard((file_name, client_ip))
            self._check_all_transfers_done()

    def send_to_all_clients(self):
        connected_clients = self.network_server.get_connected_clients()
        selected_clients_ips = [client['ip'] for client in connected_clients]
        
        if not selected_clients_ips:
            QMessageBox.warning(self.ui, "No Clients Connected", "No clients are connected to send files to.")
            return

        if not self.network_server.files_to_distribute:
            QMessageBox.warning(self.ui, "No Files Selected", "Please select files to distribute.")
            return

        self.ui.transfer_list_widget.clear()
        self.transfer_widgets = {}
        self.pending_transfers = set()
        if hasattr(self.ui, 'share_more_button'):
            self.ui.share_more_button.setVisible(False)

        for file_info in self.network_server.files_to_distribute:
            for client_ip in selected_clients_ips:
                widget = FileTransferWidget(file_info['name'], file_info['size'], client_ip)
                item = QListWidgetItem(self.ui.transfer_list_widget)
                item.setSizeHint(widget.sizeHint())
                self.ui.transfer_list_widget.addItem(item)
                self.ui.transfer_list_widget.setItemWidget(item, widget)
                self.transfer_widgets[(file_info['name'], client_ip)] = widget
                self.pending_transfers.add((file_info['name'], client_ip))
                widget.cancel_button.clicked.connect(lambda checked, fn=file_info['name'], cip=client_ip: self.cancel_single_transfer(fn, cip))
                # Add a checkbox to the widget for selection
                widget.add_checkbox()

        self.network_server.distribute_files_to_clients(selected_clients_ips)
        self.ui.show_while_sharing()

    def cancel_single_transfer(self, file_name, client_ip):
        self.network_server.cancel_file_transfer(client_ip, file_name)
        # Remove the widget row from UI on cancel
        for i in range(self.ui.transfer_list_widget.count()):
            item = self.ui.transfer_list_widget.item(i)
            widget = self.ui.transfer_list_widget.itemWidget(item)
            if widget and widget.file_name == file_name and widget.client_ip == client_ip:
                self.ui.transfer_list_widget.takeItem(i)
                break
        self.transfer_widgets.pop((file_name, client_ip), None)

    def cancel_all_transfers(self):
        self.network_server.cancel_all_transfers()
        # Clear the UI transfer list entirely
        self.ui.transfer_list_widget.clear()
        self.transfer_widgets.clear()

    def update_status_bar(self, message, color):
        """Updates the status bar with a message and color."""
        self.ui.statusBar.setStyleSheet(f"QStatusBar {{ color: {color}; }}")
        self.ui.statusBar.showMessage(message)

    def cancel_selected_transfers(self):
        transfers_to_cancel = []
        for i in range(self.ui.transfer_list_widget.count()):
            item = self.ui.transfer_list_widget.item(i)
            widget = self.ui.transfer_list_widget.itemWidget(item)
            if widget and widget.is_checked(): # Assuming FileTransferWidget has an is_checked method
                transfers_to_cancel.append((widget.file_name, widget.client_ip))
        
        if not transfers_to_cancel:
            QMessageBox.warning(self.ui, "No Transfers Selected", "Please select transfers to cancel.")
            return

        self.network_server.cancel_selected_transfers(transfers_to_cancel)
        for file_name, client_ip in transfers_to_cancel:
            if (file_name, client_ip) in self.transfer_widgets:
                widget = self.transfer_widgets[(file_name, client_ip)]
                widget.set_status("Cancelled by Server", "red")
                widget.set_progress(0)

    def select_all_clients(self):
        for i in range(self.ui.client_list_widget.count()):
            item = self.ui.client_list_widget.item(i)
            item.setCheckState(Qt.Checked)

    def _is_terminal_status(self, status: str) -> bool:
        if not status:
            return False
        s = status.lower()
        terminal_keywords = [
            "received successfully",
            "received",
            "installed",
            "manual setup required",
            "cancelled",
            "not sent",
            "not received",
        ]
        return any(k in s for k in terminal_keywords)

    def _check_all_transfers_done(self):
        if not self.pending_transfers:
            self.network_server.files_to_distribute.clear()
            self.update_selected_files_list()
            if hasattr(self.ui, 'share_more_button'):
                self.ui.share_more_button.setVisible(True)
            self.update_status_bar("All transfers completed. Share more files?", "green")

    def share_more(self):
        if hasattr(self.ui, 'share_more_button'):
            self.ui.share_more_button.setVisible(False)
        self.select_files()

if __name__ == "__main__":
    app = QApplication([])
    
    # Initialize UI
    server_window = ServerWindow()
    
    # Initialize Network Server
    network_server = NetworkServer()
    
    # Initialize Controller
    controller = ServerController(network_server, server_window)
    
    server_window.show()
    app.exec_()
    
    # Ensure server stops gracefully on exit
    network_server.stop_server()
