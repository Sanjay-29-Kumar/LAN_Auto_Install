import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QFileDialog, QLabel, QMessageBox, QGroupBox, QListWidgetItem
)
from PyQt5.QtCore import Qt
import json
from sendlan import send_file_to_clients

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "clients.json")
UPLOADS_INSTALLERS = os.path.join(BASE_DIR, "uploads", "installers")
UPLOADS_MEDIA = os.path.join(BASE_DIR, "uploads", "media")

# Helpers
def load_clients():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def is_media_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    return ext in [".png", ".jpg", ".jpeg", ".pdf", ".docx", ".txt", ".mp4", ".mp3"]

def classify_and_copy(file_path):
    os.makedirs(UPLOADS_INSTALLERS, exist_ok=True)
    os.makedirs(UPLOADS_MEDIA, exist_ok=True)
    dest_folder = UPLOADS_MEDIA if is_media_file(file_path) else UPLOADS_INSTALLERS
    filename = os.path.basename(file_path)
    dest_path = os.path.join(dest_folder, filename)
    shutil.copy2(file_path, dest_path)
    return dest_path

class ServerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LANAutoInstall - Server Panel")
        self.setGeometry(100, 100, 600, 450)

        self.clients = load_clients()
        self.selected_file_path = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # File Selector Section
        file_group = QGroupBox("Select a File to Send")
        file_layout = QHBoxLayout()

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: gray; font-style: italic;")

        file_button = QPushButton("Browse File")
        file_button.clicked.connect(self.browse_file)

        file_layout.addWidget(self.file_label)
        file_layout.addWidget(file_button)
        file_group.setLayout(file_layout)

        # Clients List Section
        clients_group = QGroupBox("Select Clients")
        clients_layout = QVBoxLayout()
        self.client_list_widget = QListWidget()
        self.client_list_widget.setSelectionMode(QListWidget.MultiSelection)

        for client_key, client_data in self.clients.items():
            display_name = f"{client_data['name']} ({client_data['ip']})"
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, client_key)
            self.client_list_widget.addItem(item)

        clients_layout.addWidget(self.client_list_widget)
        clients_group.setLayout(clients_layout)

        # Send Button
        send_button = QPushButton("Send File to Selected Clients")
        send_button.setStyleSheet("padding: 10px; font-size: 16px;")
        send_button.clicked.connect(self.send_file)

        # Layout Ordering
        main_layout.addWidget(file_group)
        main_layout.addWidget(clients_group)
        main_layout.addWidget(send_button)

        self.setLayout(main_layout)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.selected_file_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.setText(f"Selected: {filename}")
            self.file_label.setStyleSheet("color: black;")

    def send_file(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "No File", "Please select a file first.")
            return

        selected_items = self.client_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Clients", "Please select at least one client.")
            return

        dest_path = classify_and_copy(self.selected_file_path)
        selected_keys = [item.data(Qt.UserRole) for item in selected_items]

        try:
            send_file_to_clients(dest_path, selected_keys)
            QMessageBox.information(self, "Success", "File sent successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send file:\n{str(e)}")

# Entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ServerGUI()
    window.show()
    sys.exit(app.exec_())
