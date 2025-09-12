from ui.server_ui import (
    ServerWindow, FG_MUTED, SCAN_PENDING, SCAN_SAFE, SCAN_UNSAFE
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QFileDialog, QListWidgetItem,
    QDialog, QVBoxLayout, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QColor
from network.server import NetworkServer
from ui.custom_widgets import FileTransferWidget, ProfileListItemWidget
import os
import time
from network import protocol

class ServerController:
    def __init__(self, network_server, ui):
        self.network_server = network_server
        self.ui = ui
        self.transfer_widgets = {}
        self.pending_transfers = set()
        self.scanning_files = set()  # Track files being scanned
        self.scan_items = {}  # Track scan items in UI
        self.safe_files = set()  # Track which files are confirmed safe
        self.scanner = None  # Will be initialized when needed
        self.load_user_preferences()
        
        # Connect security-related signals
        if hasattr(ui, 'safety_check'):
            ui.safety_check.toggled.connect(self._update_share_button)
            ui.view_scan_details.clicked.connect(self._show_scan_details)
        
        # Connect scan status updates
        self.network_server.scan_status_update.connect(self.update_scan_status)
        
        # Connect virus scanner signals
        if hasattr(self.network_server, 'virus_scanner'):
            self.network_server.virus_scanner.scan_started.connect(self.on_scan_started)
            self.network_server.virus_scanner.scan_progress.connect(self.on_scan_progress)
            self.network_server.virus_scanner.scan_complete.connect(self.on_scan_complete)
        
        self.network_server.start_server() # Start the server network operations

    def load_user_preferences(self):
        # Load user preferences
        if hasattr(self.ui, 'load_preferences'):
            self.ui.load_preferences()
        # Connect network signals to UI slots
        self.network_server.client_connected.connect(self.update_client_list)
        self.network_server.client_disconnected.connect(self.update_client_list)

        # Connect UI signals to controller slots
        self.ui.select_files_button.clicked.connect(self.select_files)
        # Connect scan files button if it exists
        if hasattr(self.ui, 'scan_files_button'):
            self.ui.scan_files_button.clicked.connect(self.start_security_scan)
        # Automatically connect to previously preferred clients
        for client_info in self.network_server.get_connected_clients():
            if client_info['ip'] in self.ui.preferred_clients:
                self.network_server.connect_to_client_manual(client_info['ip'])
        self.ui.send_files_button.clicked.connect(self.send_files)
        self.ui.global_back_home_button.clicked.connect(self.ui.show_home)
        self.ui.refresh_clients_button.clicked.connect(self.update_client_list)
        self.ui.add_more_files_button.clicked.connect(self.select_files)
        self.ui.remove_selected_files_button.clicked.connect(self.remove_selected_files)
        self.ui.select_all_files_button.clicked.connect(self.select_all_files)
        self.ui.send_to_all_button.clicked.connect(self.send_to_all_clients)
        self.network_server.file_progress.connect(self.update_transfer_progress)
        self.network_server.status_update_received.connect(self.update_transfer_status)
        # self.ui.client_list_widget.itemClicked.connect(self.show_client_profile)
        self.ui.show_profile_button.clicked.connect(self.show_selected_client_profile)
        self.ui.cancel_all_button.clicked.connect(self.cancel_all_transfers)
        self.ui.cancel_selected_button.clicked.connect(self.cancel_selected_transfers)
        if hasattr(self.ui, 'share_more_button'):
            self.ui.share_more_button.clicked.connect(self.share_more)
        # Connect Details button signal
        if hasattr(self.ui, 'show_server_details_requested'):
            self.ui.show_server_details_requested.connect(self.show_server_details)

    def show_selected_client_profile(self):
        selected_ip = None
        for i in range(self.ui.client_list_widget.count()):
            item = self.ui.client_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected_ip = item.text().split('(')[1].replace(')', '')
                break

        if not selected_ip or selected_ip not in self.network_server.clients:
            QMessageBox.information(self.ui, "Client Profile", "Select a client (checked) first.")
            return

        info = self.network_server.clients[selected_ip]["info"]
        profile_text = f"Client Profile\nHostname: {info.get('hostname','N/A')}\nIP: {info.get('ip','N/A')}"
        QMessageBox.information(self.ui, "Client Profile", profile_text)
        self.ui.manual_ip_connect_button.clicked.connect(self.connect_to_manual_ip)
        self.ui.show_server_details_button.clicked.connect(self.show_server_details)
        self.network_server.server_ip_updated.connect(self.update_server_ip_display)
        self.ui.global_back_home_button.clicked.connect(self.ui.show_home) # Connect global back/home button
        self.network_server.status_update.connect(self.update_status_bar) # Connect status update signal
        self.ui.global_back_home_button.clicked.connect(self.ui.show_home) # Connect global back/home button
        self.network_server.status_update.connect(self.update_status_bar) # Connect status update signal
        # New UI actions
        if hasattr(self.ui, 'select_all_clients_button'):
                self.ui.select_all_clients_button.clicked.disconnect()
                self.ui.select_all_clients_button.clicked.connect(self.select_all_clients)

    def update_server_ip_display(self, ip_address):
        self.ui.server_ip_label.setText(f"Server IP: {ip_address}")

    def connect_to_manual_ip(self):
        ip_address = self.ui.manual_ip_input.text()
        if ip_address:
            self.network_server.connect_to_client_manual(ip_address)
            self.ui.manual_ip_input.clear()
            # Show message on themed status bar
            try:
                self.ui.statusBar.showMessage(f"Attempting to connect to {ip_address}...")
            except Exception:
                pass
        else:
            QMessageBox.warning(self.ui, "Invalid IP", "Please enter a valid IP address.")
            
    def update_scan_status(self, file_name, progress, status, color):
        """Update the virus scan status in the UI"""
        # Update the pending scans list
        if progress == 0:  # New scan started
            scan_item = self.ui.pending_scans.add_pending_scan(file_name)
            self.scan_items[file_name] = scan_item
        elif file_name in self.scan_items:
            is_safe = None
            if progress == 100:
                if "safe" in status.lower():
                    is_safe = True
                    self.safe_files.add(file_name)
                elif "unsafe" in status.lower():
                    is_safe = False
                    if file_name in self.safe_files:
                        self.safe_files.remove(file_name)
                
                # Update overall status
                total_files = len(self.scan_items)
                safe_files = len(self.safe_files)
                
                if total_files == 0:
                    self.ui.overall_status.setText("No files selected")
                    self.ui.overall_status.setStyleSheet(f"color: {FG_MUTED}")
                elif safe_files == total_files:
                    self.ui.overall_status.setText("✓ All files scanned and safe")
                    self.ui.overall_status.setStyleSheet(f"color: {SCAN_SAFE}")
                    self.ui.safety_check.setEnabled(True)
                else:
                    unsafe = total_files - safe_files
                    self.ui.overall_status.setText(f"⚠️ {unsafe} files need attention")
                    self.ui.overall_status.setStyleSheet(f"color: {SCAN_UNSAFE}")
                    self.ui.safety_check.setEnabled(False)
                    self.ui.safety_check.setChecked(False)
            
            self.ui.pending_scans.update_scan_status(self.scan_items[file_name], status, is_safe)
        
        # Update detailed scan widget if visible
        if hasattr(self.ui, 'virus_scan_widget'):
            self.ui.virus_scan_widget.update_scan_status(file_name, progress, status, color)
            
            # If scan is complete, show detailed results
            if progress == 100:
                if "safe" in status.lower():
                    self.ui.virus_scan_widget.show_scan_results(
                        f"✓ {file_name} is safe to distribute\n{status}", 
                        True
                    )
                elif "unsafe" in status.lower():
                    self.ui.virus_scan_widget.show_scan_results(
                        f"⚠ {file_name} may be unsafe\n{status}",
                        False
                    )
                else:
                    self.ui.virus_scan_widget.show_scan_results(
                        f"ℹ {status}",
                        True
                    )

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
            
    def _update_share_button(self, checked):
        """Enable/disable share button based on safety check"""
        if hasattr(self.ui, 'share_button'):
            self.ui.share_button.setEnabled(checked)
        
        # Enable/disable send buttons based on safety check
        if hasattr(self.ui, 'send_files_button'):
            self.ui.send_files_button.setEnabled(checked)
        if hasattr(self.ui, 'send_to_all_button'):
            self.ui.send_to_all_button.setEnabled(checked)
            
    def _show_scan_details(self):
        """Show the detailed virus scan results dialog"""
        try:
            if hasattr(self.ui, 'virus_scan_widget') and self.ui.virus_scan_widget:
                dialog = QDialog(self.ui)
                dialog.setWindowTitle("Security Scan Details")
                dialog.setModal(True)
                dialog.resize(600, 400)
                layout = QVBoxLayout()
                
                # Create a new widget to show scan details instead of moving the existing one
                details_text = "Security Scan Details\n\n"
                
                # Add scan results summary
                total_files = len(self.scan_items)
                safe_files = len(self.safe_files)
                scanning_files = len(self.scanning_files)
                
                details_text += f"Total Files: {total_files}\n"
                details_text += f"Safe Files: {safe_files}\n"
                details_text += f"Currently Scanning: {scanning_files}\n\n"
                
                # Add individual file results
                for file_name, scan_item in self.scan_items.items():
                    if file_name in self.safe_files:
                        details_text += f"✓ {file_name}: Safe\n"
                    elif file_name in self.scanning_files:
                        details_text += f"⏳ {file_name}: Scanning...\n"
                    else:
                        details_text += f"⚠️ {file_name}: Needs attention\n"
                
                from PyQt5.QtWidgets import QTextEdit
                text_widget = QTextEdit()
                text_widget.setPlainText(details_text)
                text_widget.setReadOnly(True)
                layout.addWidget(text_widget)
                
                # Add close button
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(dialog.close)
                layout.addWidget(close_btn)
                
                dialog.setLayout(layout)
                dialog.exec_()
        except Exception as e:
            print(f"Error showing scan details: {e}")
            QMessageBox.information(self.ui, "Scan Details", "Scan details are not available at the moment.")
    
    def on_scan_started(self, file_name):
        """Handle virus scan started signal"""
        print(f"Virus scan started for: {file_name}")
        self.scanning_files.add(file_name)
        
        # Add to pending scans UI
        if hasattr(self.ui, 'pending_scans'):
            scan_item = self.ui.pending_scans.add_pending_scan(file_name)
            self.scan_items[file_name] = scan_item
        
        # Update overall status
        self._update_overall_security_status()
        
    def on_scan_progress(self, file_name, progress, status):
        """Handle virus scan progress signal"""
        print(f"Virus scan progress for {file_name}: {progress}% - {status}")
        
        # Update pending scans UI
        if file_name in self.scan_items:
            self.ui.pending_scans.update_scan_status(self.scan_items[file_name], status)
        
        # Update virus scan widget if visible
        if hasattr(self.ui, 'virus_scan_widget') and self.ui.virus_scan_widget:
            try:
                # Show the virus scan widget when scanning starts
                self.ui.virus_scan_widget.setVisible(True)
                
                # Convert progress to color
                if progress < 50:
                    color = SCAN_PENDING
                elif progress < 100:
                    color = "#3b82f6"  # blue for in progress
                else:
                    color = SCAN_SAFE  # will be updated in scan_complete
                
                self.ui.virus_scan_widget.update_scan_status(file_name, progress, status, color)
            except RuntimeError:
                # Widget has been deleted, ignore
                pass
    
    def on_scan_complete(self, file_name, is_safe, details):
        """Handle virus scan complete signal"""
        print(f"Virus scan complete for {file_name}: {'SAFE' if is_safe else 'UNSAFE'}")
        
        # Remove from scanning set
        self.scanning_files.discard(file_name)
        
        # Update safe files tracking
        if is_safe:
            self.safe_files.add(file_name)
        else:
            self.safe_files.discard(file_name)
        
        # Update pending scans UI
        if file_name in self.scan_items:
            status_text = "✓ Safe" if is_safe else "⚠️ Unsafe"
            self.ui.pending_scans.update_scan_status(self.scan_items[file_name], status_text, is_safe)
        
        # Update virus scan widget
        if hasattr(self.ui, 'virus_scan_widget'):
            color = SCAN_SAFE if is_safe else SCAN_UNSAFE
            status_text = f"Scan complete: {'Safe' if is_safe else 'Unsafe'}"
            self.ui.virus_scan_widget.update_scan_status(file_name, 100, status_text, color)
            
            # Show detailed results
            if is_safe:
                result_text = f"✓ {file_name} is safe to distribute"
                if isinstance(details, dict) and 'stats' in details:
                    stats = details['stats']
                    result_text += f"\nScan results: {stats['harmless']} harmless, {stats['undetected']} undetected"
            else:
                result_text = f"⚠ {file_name} may be unsafe"
                if isinstance(details, dict) and 'stats' in details:
                    stats = details['stats']
                    result_text += f"\nDetections: {stats['malicious']} malicious, {stats['suspicious']} suspicious"
                    if 'permalink' in details:
                        result_text += f"\nView details: {details['permalink']}"
            
            self.ui.virus_scan_widget.show_scan_results(result_text, is_safe)
        
        # Update overall security status
        self._update_overall_security_status()
    
    def _update_overall_security_status(self):
        """Update the overall security status display"""
        total_files = len(self.scan_items)
        safe_files = len(self.safe_files)
        scanning_files = len(self.scanning_files)
        
        if total_files == 0:
            self.ui.overall_status.setText("Files not scanned yet")
            self.ui.overall_status.setStyleSheet(f"color: {FG_MUTED}")
            self.ui.safety_check.setEnabled(False)
            self.ui.send_files_button.setEnabled(False)
            self.ui.send_to_all_button.setEnabled(False)
        elif scanning_files > 0:
            self.ui.overall_status.setText(f"⏳ Scanning {scanning_files} files...")
            self.ui.overall_status.setStyleSheet(f"color: {SCAN_PENDING}")
            self.ui.safety_check.setEnabled(False)
            self.ui.send_files_button.setEnabled(False)
            self.ui.send_to_all_button.setEnabled(False)
        elif safe_files == total_files:
            self.ui.overall_status.setText("✓ All files scanned and safe")
            self.ui.overall_status.setStyleSheet(f"color: {SCAN_SAFE}")
            self.ui.safety_check.setEnabled(True)
            # Re-enable scan button
            if hasattr(self.ui, 'scan_files_button'):
                self.ui.scan_files_button.setEnabled(True)
                self.ui.scan_files_button.setText("🔍 Scan Files for Security")
        else:
            unsafe = total_files - safe_files
            self.ui.overall_status.setText(f"⚠️ {unsafe} files need attention")
            self.ui.overall_status.setStyleSheet(f"color: {SCAN_UNSAFE}")
            self.ui.safety_check.setEnabled(False)
            self.ui.safety_check.setChecked(False)
            self.ui.send_files_button.setEnabled(False)
            self.ui.send_to_all_button.setEnabled(False)
            # Re-enable scan button
            if hasattr(self.ui, 'scan_files_button'):
                self.ui.scan_files_button.setEnabled(True)
                self.ui.scan_files_button.setText("🔍 Scan Files for Security")

    def update_client_list(self, *args):
        self.ui.client_list_widget.clear()
        connected_clients = self.network_server.get_connected_clients()
        for client in connected_clients:
            # Get client information with proper fallbacks
            hostname = client.get('hostname', 'Unknown Client')
            ip = client.get('ip', 'Unknown IP')
            os_type = client.get('os_type', 'Unknown OS')
            
            # Format: "Hostname IP [OS]" - same as client display
            display_text = f"{hostname} {ip} [{os_type}]"
            
            print(f"Adding client to server list: {display_text}")
            
            item = QListWidgetItem()
            item.setSizeHint(QSize(650, 100))  # Increased size to better accommodate content
            
            widget = ProfileListItemWidget(display_text, show_checkbox=True)
            widget.setMinimumWidth(600)  # Ensure widget has enough width
            widget.set_checked(False)
            widget.client_info = client
            
            # Add detailed tooltip
            tooltip = f"Client Details:\nHostname: {hostname}\nIP Address: {ip}\nOS: {os_type}"
            if hasattr(widget, 'label'):
                widget.label.setToolTip(tooltip)
            
            def show_profile():
                self.show_client_profile_by_info(widget.client_info)
            widget.profile_button.clicked.connect(show_profile)
            
            self.ui.client_list_widget.addItem(item)
            self.ui.client_list_widget.setItemWidget(item, widget)
            
        # Update status labels
        client_count = len(connected_clients)
        self.ui.connected_clients_label.setText(str(client_count))
        self.ui.connection_status_label.setText("Connected" if connected_clients else "Not Connected")
        
        # Status update
        if client_count > 0:
            self.update_status_bar(f"{client_count} client(s) connected", "green")

    def show_client_profile_by_ip(self, ip):
        client_info = self.network_server.clients.get(ip, {}).get('info')
        self.show_client_profile_by_info(client_info)

    def show_client_profile_by_info(self, client_info):
        if not client_info:
            QMessageBox.information(self.ui, "Client Profile", "Details not available.")
            return
        profile_text = f"Client Profile\nHostname: {client_info.get('hostname','N/A')}\nIP: {client_info.get('ip','N/A')}"
        QMessageBox.information(self.ui, "Client Profile", profile_text)

    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self.ui, "Select Files to Share")
        if file_paths:
            # Add files without scanning first
            for path in file_paths:
                if os.path.exists(path):
                    file_info = {
                        "path": path,
                        "name": os.path.basename(path),
                        "size": os.path.getsize(path),
                        "scan_result": "not_scanned",
                        "scan_details": "Not scanned yet"
                    }
                    self.network_server.files_to_distribute.append(file_info)
            
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
            widget = self.ui.client_list_widget.itemWidget(item)
            if widget and widget.is_checked():
                # Get IP from the client_info stored in the widget
                if hasattr(widget, 'client_info'):
                    ip = widget.client_info.get('ip')
                    if ip:
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
            self.network_server.cancel_file_transfer(client_ip, file_name)
            # Remove the widget row from UI on cancel
            for i in range(self.ui.transfer_list_widget.count()):
                item = self.ui.transfer_list_widget.item(i)
                widget = self.ui.transfer_list_widget.itemWidget(item)
                if widget and widget.file_name == file_name and widget.client_ip == client_ip:
                    self.ui.transfer_list_widget.takeItem(i)
                    break
            self.transfer_widgets.pop((file_name, client_ip), None)

    def select_all_clients(self):
        for i in range(self.ui.client_list_widget.count()):
            item = self.ui.client_list_widget.item(i)
            widget = self.ui.client_list_widget.itemWidget(item)
            if widget:
                widget.set_checked(True)

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
            # self.network_server.files_to_distribute.clear() # Do not clear, allow adding more files
            self.update_selected_files_list()
            if hasattr(self.ui, 'share_more_button'):
                self.ui.share_more_button.setVisible(True)
            self.update_status_bar("All transfers completed. Share more files?", "green")

    def share_more(self):
        if hasattr(self.ui, 'share_more_button'):
            self.ui.share_more_button.setVisible(False)
        self.select_files()
    
    def start_security_scan(self):
        """Start security scanning for all selected files"""
        if not self.network_server.files_to_distribute:
            QMessageBox.warning(self.ui, "No Files", "Please select files first.")
            return
        
        # Clear previous scan results
        self.scanning_files.clear()
        self.scan_items.clear()
        self.safe_files.clear()
        self.ui.pending_scans.clear()
        
        # Disable scan button during scanning
        if hasattr(self.ui, 'scan_files_button'):
            self.ui.scan_files_button.setEnabled(False)
            self.ui.scan_files_button.setText("🔄 Scanning...")
        
        # Start scanning each file
        for file_info in self.network_server.files_to_distribute:
            file_path = file_info['path']
            
            # Start virus scan in background thread
            def scan_file_background(path=file_path):
                try:
                    self.network_server.virus_scanner.scan_file(path)
                except Exception as e:
                    print(f"Error scanning {path}: {e}")
            
            # Start background scan thread
            import threading
            threading.Thread(target=scan_file_background, daemon=True).start()
        
        # Update UI to show scanning in progress
        self._update_overall_security_status()

if __name__ == "__main__":
    app = QApplication([])
    
    # Initialize UI
    server_window = ServerWindow()
    
    # Initialize Network Server
    network_server = NetworkServer()
    
    # Initialize Controller
    controller = ServerController(network_server, server_window)
    # Attach controller to window for UI callbacks
    server_window.controller = controller
    server_window.show()
    app.exec_()
    # Ensure server stops gracefully on exit
    network_server.stop_server()
