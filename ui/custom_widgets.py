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
    def __init__(self, file_name, file_size, client_ip=None, parent=None):
        super().__init__(parent)
        self.file_name = file_name
        self.file_size = file_size
        # Store the target client IP (if provided) for reference in controllers
        self.client_ip = client_ip
        self._full_name_text = f"{self.file_name} ({self.file_size / 1024 / 1024:.2f} MB)"
        self._status_text = "Waiting..."

        self.init_ui()

    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(6)
        self.setMinimumHeight(64)

        # Top row: left (name + status), right (checkbox + cancel)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        left_col = QVBoxLayout()
        left_col.setSpacing(2)
        self.name_label = QLabel(self._full_name_text)
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.name_label.setToolTip(self._full_name_text)
        self.status_label = QLabel(self._status_text)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        left_col.addWidget(self.name_label)
        left_col.addWidget(self.status_label)

        right_col = QHBoxLayout()
        right_col.setSpacing(6)
        self.checkbox = QCheckBox()
        self.checkbox.setVisible(False)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedSize(80, 28)
        right_col.addWidget(self.checkbox, alignment=Qt.AlignRight | Qt.AlignVCenter)
        right_col.addWidget(self.cancel_button, alignment=Qt.AlignRight | Qt.AlignVCenter)

        top_row.addLayout(left_col, 1)
        top_row.addLayout(right_col, 0)
        outer.addLayout(top_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setMaximumHeight(18)
        outer.addWidget(self.progress_bar)
        # ensure initial elide based on current sizes
        QTimer.singleShot(0, lambda: self.resizeEvent(QResizeEvent(self.size(), self.size())))

    def resizeEvent(self, event):
        # Elide long texts to prevent overlap
        fm_name = QFontMetrics(self.name_label.font())
        fm_status = QFontMetrics(self.status_label.font())
        available_w = max(50, self.name_label.width())
        elided_name = fm_name.elidedText(self._full_name_text, Qt.ElideRight, available_w)
        elided_status = fm_status.elidedText(self._status_text, Qt.ElideRight, max(50, self.status_label.width()))
        self.name_label.setText(elided_name)
        self.status_label.setText(elided_status)
        super().resizeEvent(event)

    def set_progress(self, percentage):
        self.progress_bar.setValue(int(percentage))

    def set_status(self, status, color=None):
        self._status_text = status or ""
        # Update elided text according to current label width
        fm_status = QFontMetrics(self.status_label.font())
        elided_status = fm_status.elidedText(self._status_text, Qt.ElideRight, max(50, self.status_label.width()))
        self.status_label.setText(elided_status)
        if color:
            self.status_label.setStyleSheet(f"color: {color};")

    def add_checkbox(self):
        self.checkbox.setVisible(True)

    def is_checked(self):
        return self.checkbox.isChecked()
