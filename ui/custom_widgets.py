"""
Custom widgets for the LAN Auto Install application.
"""

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class FileTransferWidget(QWidget):
    """
    A custom widget to display the progress of a single file transfer.
    """
    def __init__(self, file_name, file_size, parent=None):
        super().__init__(parent)
        self.file_name = file_name
        self.file_size = file_size

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # File name and size
        info_layout = QHBoxLayout()
        self.name_label = QLabel(f"{self.file_name} ({self.file_size / 1024 / 1024:.2f} MB)")
        self.status_label = QLabel("Waiting...")
        info_layout.addWidget(self.name_label)
        info_layout.addStretch()
        info_layout.addWidget(self.status_label)
        layout.addLayout(info_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

    def set_progress(self, percentage):
        self.progress_bar.setValue(int(percentage))

    def set_status(self, status, color=None):
        self.status_label.setText(status)
        if color:
            self.status_label.setStyleSheet(f"color: {color};")
