from PyQt5.QtWidgets import QWidget
class ProfileListItemWidget(QWidget):
    """
    Custom widget for device list items with a label, checkbox, and a profile button.
    Enhanced to properly display server information without truncation.
    """
    def __init__(self, label_text, show_checkbox=True, parent=None):
        super().__init__(parent)
        
        # Set minimum and preferred height for better display
        self.setMinimumHeight(80)
        self.setMaximumHeight(100)
        
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(15)
        
        # Checkbox with better sizing
        self.checkbox = QCheckBox()
        self.checkbox.setVisible(show_checkbox)
        self.checkbox.setFixedSize(24, 24)
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 3px;
                border: 2px solid #374151;
                background-color: #111827;
            }
            QCheckBox::indicator:checked {
                background-color: #3b82f6;
                border-color: #3b82f6;
            }
        """)
        
        # Main content area with better layout
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)
        
        # Parse the label text to extract components
        hostname, ip, os_info = self._parse_server_info(label_text)
        
        # Primary label (hostname + IP) with better text handling
        self.label = QLabel()
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.label.setMinimumWidth(200)  # Ensure minimum width for text
        
        # Format as "Hostname IP" with proper styling and ensure no truncation
        primary_text = f'<b style="font-size:14pt; color:#e5e7eb;">{hostname}</b> <span style="font-size:13pt; color:#22c55e;">{ip}</span>'
        self.label.setText(primary_text)
        self.label.setWordWrap(False)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Secondary label (OS info)
        self.secondary_label = QLabel()
        self.secondary_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.secondary_label.setText(f'<span style="font-size:11pt; color:#9ca3af;">{os_info}</span>')
        self.secondary_label.setWordWrap(False)
        self.secondary_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        content_layout.addWidget(self.label)
        content_layout.addWidget(self.secondary_label)
        
        # Profile button with proper sizing and text
        self.profile_button = QPushButton("Detail")
        self.profile_button.setToolTip("Show Details")
        self.profile_button.setFixedSize(70, 36)  # Increased width to fit text
        self.profile_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 12pt;
                font-weight: 600;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        
        # Layout assembly with proper stretch factors
        layout.addWidget(self.checkbox, 0)  # Fixed size
        layout.addWidget(content_widget, 1)  # Expandable
        layout.addWidget(self.profile_button, 0)  # Fixed size
        
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
        # Increase widget height to accommodate longer text
        self.setMinimumHeight(85)
        self.setMaximumHeight(110)
        
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(8)

        # Top row: left (name + status), right (checkbox + cancel)
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # Left column for file info with better sizing
        left_col = QVBoxLayout()
        left_col.setSpacing(3)
        
        # File name label with better text handling
        self.name_label = QLabel(self._full_name_text)
        self.name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.name_label.setMinimumWidth(300)  # Ensure minimum width for file names
        self.name_label.setWordWrap(False)
        self.name_label.setToolTip(self._full_name_text)
        self.name_label.setStyleSheet("""
            QLabel {
                font-size: 13pt;
                font-weight: 600;
                color: #e5e7eb;
                padding: 2px;
            }
        """)
        
        # Status label with better styling
        self.status_label = QLabel(self._status_text)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.status_label.setMinimumWidth(300)
        self.status_label.setWordWrap(False)
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 11pt;
                color: #9ca3af;
                padding: 2px;
            }
        """)
        
        left_col.addWidget(self.name_label)
        left_col.addWidget(self.status_label)

        # Right column for controls
        right_col = QHBoxLayout()
        right_col.setSpacing(8)
        
        self.checkbox = QCheckBox()
        self.checkbox.setVisible(False)
        self.checkbox.setFixedSize(24, 24)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFixedSize(85, 32)  # Slightly larger for better visibility
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:pressed {
                background-color: #991b1b;
            }
        """)
        
        right_col.addWidget(self.checkbox, 0, Qt.AlignRight | Qt.AlignVCenter)
        right_col.addWidget(self.cancel_button, 0, Qt.AlignRight | Qt.AlignVCenter)

        # Add layouts with proper stretch factors
        top_row.addLayout(left_col, 1)  # Expandable
        top_row.addLayout(right_col, 0)  # Fixed size
        outer.addLayout(top_row)

        # Progress bar with better styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setMinimumHeight(20)
        self.progress_bar.setMaximumHeight(24)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #374151;
                border-radius: 8px;
                background-color: #111827;
                text-align: center;
                font-weight: 600;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 6px;
            }
        """)
        
        outer.addWidget(self.progress_bar)

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
        # Display full status text without eliding
        self.status_label.setText(self._status_text)
        self.status_label.setToolTip(self._status_text)  # Add tooltip for very long status
        
        # Apply color with existing styling
        base_style = """
            QLabel {
                font-size: 11pt;
                padding: 2px;
            }
        """
        if color:
            self.status_label.setStyleSheet(base_style + f"QLabel {{ color: {color}; }}")
        else:
            self.status_label.setStyleSheet(base_style + "QLabel { color: #9ca3af; }")

    def add_checkbox(self):
        self.checkbox.setVisible(True)

    def is_checked(self):
        return self.checkbox.isChecked()
