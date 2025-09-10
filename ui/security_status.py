from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QProgressBar, QPushButton
)
from PyQt5.QtCore import Qt

class SecurityStatusWidget(QWidget):
    """Widget to display security scan status for files"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                border-radius: 8px;
                color: #e5e7eb;
            }
        """)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header
        header = QHBoxLayout()
        
        icon = QLabel("🛡️")
        icon.setStyleSheet("font-size: 16px;")
        header.addWidget(icon)
        
        title = QLabel("Security Status")
        title.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #e5e7eb;
        """)
        header.addWidget(title)
        
        # Status pill
        self.status_label = QLabel("Scanning...")
        self.status_label.setStyleSheet("""
            background-color: #eab308;
            color: #0f172a;
            border-radius: 10px;
            padding: 3px 12px;
            font-weight: bold;
            font-size: 12px;
        """)
        header.addStretch()
        header.addWidget(self.status_label)
        
        layout.addLayout(header)
        
        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #374151;
                border-radius: 8px;
                background-color: #111827;
                text-align: center;
                height: 16px;
                color: white;
                font-weight: 600;
            }
            QProgressBar::chunk {
                background-color: #22c55e;
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Details
        self.details_label = QLabel("Checking file security...")
        self.details_label.setWordWrap(True)
        self.details_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(self.details_label)
        
    def update_status(self, progress, status, is_safe=None):
        """Update the security status display"""
        self.progress_bar.setValue(progress)
        self.details_label.setText(status)
        
        if is_safe is not None:
            if is_safe:
                self.status_label.setText("✓ Safe")
                self.status_label.setStyleSheet("""
                    background-color: #22c55e;
                    color: #0f172a;
                    border-radius: 10px;
                    padding: 3px 12px;
                    font-weight: bold;
                    font-size: 12px;
                """)
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #374151;
                        border-radius: 8px;
                        background-color: #111827;
                        text-align: center;
                        height: 16px;
                        color: white;
                        font-weight: 600;
                    }
                    QProgressBar::chunk {
                        background-color: #22c55e;
                        border-radius: 6px;
                    }
                """)
            else:
                self.status_label.setText("⚠️ Unsafe")
                self.status_label.setStyleSheet("""
                    background-color: #dc2626;
                    color: #0f172a;
                    border-radius: 10px;
                    padding: 3px 12px;
                    font-weight: bold;
                    font-size: 12px;
                """)
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #374151;
                        border-radius: 8px;
                        background-color: #111827;
                        text-align: center;
                        height: 16px;
                        color: white;
                        font-weight: 600;
                    }
                    QProgressBar::chunk {
                        background-color: #dc2626;
                        border-radius: 6px;
                    }
                """)
        else:
            self.status_label.setText("Scanning...")
            self.status_label.setStyleSheet("""
                background-color: #eab308;
                color: #0f172a;
                border-radius: 10px;
                padding: 3px 12px;
                font-weight: bold;
                font-size: 12px;
            """)
