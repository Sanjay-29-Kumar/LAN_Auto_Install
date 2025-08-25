from PyQt5.QtWidgets import QWidget
class ProfileListItemWidget(QWidget):
    """
    Custom widget for device list items with a label, checkbox, and a profile button.
    Enhanced to properly display server information without truncation.
    """
    def __init__(self, label_text, show_checkbox=True, parent=None):
        super().__init__(parent)
        
        # Set minimum height for better display
        self.setMinimumHeight(70)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setVisible(show_checkbox)
        self.checkbox.setFixedSize(20, 20)
        
        # Main content area
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)
        
        # Parse the label text to extract components
        hostname, ip, os_info = self._parse_server_info(label_text)
        
        # Primary label (hostname + IP)
        self.label = QLabel()
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Format as "Hostname IP" with proper styling
        primary_text = f'<b style="font-size:14pt; color:#e5e7eb;">{hostname}</b> <span style="font-size:13pt; color:#22c55e;">{ip}</span>'
        self.label.setText(primary_text)
        self.label.setWordWrap(False)  # Prevent wrapping
        
        # Secondary label (OS info)
        self.secondary_label = QLabel()
        self.secondary_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.secondary_label.setText(f'<span style="font-size:11pt; color:#9ca3af;">{os_info}</span>')
        self.secondary_label.setWordWrap(False)
        
        content_layout.addWidget(self.label)
        content_layout.addWidget(self.secondary_label)
        
        # Profile button with "Detail" text
        self.profile_button = QPushButton("Detail")
        self.profile_button.setToolTip("Show Server Details")
        self.profile_button.setFixedSize(60, 32)
        self.profile_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        
        # Layout assembly
        layout.addWidget(self.checkbox, 0)
        layout.addLayout(content_layout, 1)
        layout.addWidget(self.profile_button, 0)
        self.setLayout(layout)
    
    def _parse_server_info(self, label_text):
        """Parse server information from label text"""
        try:
            # Handle different formats
            if '[' in label_text and ']' in label_text:
                # Format: "Hostname IP [OS]"
                parts = label_text.split(' [')
                main_part = parts[0].strip()
                os_part = parts[1].rstrip(']').strip() if len(parts) > 1 else 'Unknown OS'
                
                # Split hostname and IP
                main_parts = main_part.split(' ')
                if len(main_parts) >= 2:
                    # Last part should be IP, everything else is hostname
                    ip = main_parts[-1]
                    hostname = ' '.join(main_parts[:-1])
                else:
                    hostname = main_part
                    ip = 'Unknown IP'
                
                return hostname, ip, os_part
            elif '|' in label_text:
                # Legacy format: "Hostname | IP"
                parts = label_text.split('|')
                hostname = parts[0].strip()
                ip = parts[1].strip() if len(parts) > 1 else 'Unknown IP'
                return hostname, ip, 'Unknown OS'
            else:
                # Single text, assume it's hostname
                return label_text.strip(), 'Unknown IP', 'Unknown OS'
        except Exception:
            return label_text.strip(), 'Unknown IP', 'Unknown OS'

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
