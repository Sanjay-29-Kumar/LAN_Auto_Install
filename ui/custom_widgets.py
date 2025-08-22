from PyQt5.QtWidgets import QWidget
class ProfileListItemWidget(QWidget):
    """
    Custom widget for device list items with a label, checkbox, and a profile button.
    """
    def __init__(self, label_text, show_checkbox=True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)
        self.checkbox = QCheckBox()
        self.checkbox.setVisible(show_checkbox)
        self.label = QLabel()
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.label.setStyleSheet("font-size: 13pt; padding: 2px 8px 2px 0px;")
        # Use HTML for better formatting: name bold, IP smaller
        if '|' in label_text:
            parts = label_text.split('|')
            name = parts[0].strip()
            ip = parts[1].strip()
            self.label.setText(f'<b style="font-size:14pt;">{name}</b><br><span style="font-size:11pt;color:#aaa;">{ip}</span>')
        else:
            self.label.setText(label_text)
        self.profile_button = QPushButton()
        self.profile_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogInfoView))
        self.profile_button.setToolTip("Show Profile")
        self.profile_button.setFixedSize(36, 36)
        self.profile_button.setStyleSheet("background:#2a2a40; border-radius:18px; padding:2px;")
        layout.addWidget(self.checkbox, 0)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.profile_button, 0)
        self.setLayout(layout)

    def is_checked(self):
        return self.checkbox.isChecked()

    def set_checked(self, checked):
        self.checkbox.setChecked(checked)
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
