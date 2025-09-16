from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt

class VirusScanWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Title
        self.title_label = QLabel("Security Scan Status")
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: #e5e7eb;
                font-size: 14px;
                font-weight: bold;
                padding: 5px;
            }}
        """)
        
        # File name label
        self.file_label = QLabel()
        self.file_label.setStyleSheet(f"""
            QLabel {{
                color: #9ca3af;
                padding: 2px 5px;
            }}
        """)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #374151;
                border-radius: 5px;
                text-align: center;
                height: 20px;
                background-color: #1f2937;
                color: #e5e7eb;
            }}
            QProgressBar::chunk {{
                background-color: #3b82f6;
                border-radius: 5px;
            }}
        """)
        
        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"""
            QLabel {{
                padding: 5px;
                border-radius: 3px;
                color: #e5e7eb;
            }}
        """)
        self.status_label.setWordWrap(True)
        
        # Results panel
        self.results_label = QLabel()
        self.results_label.setStyleSheet(f"""
            QLabel {{
                color: #9ca3af;
                padding: 5px;
                border: 1px solid #374151;
                border-radius: 5px;
                background-color: #1f2937;
            }}
        """)
        self.results_label.setWordWrap(True)
        self.results_label.setHidden(True)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.file_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.results_label)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def update_scan_status(self, file_name, progress, status, color="#3b82f6"):
        """Update the scan status display"""
        self.file_label.setText(f"File: {file_name}")
        self.progress_bar.hide()  # Hide progress bar
        if "safe" in status.lower():
            status = "✓ Safe"
            color = "#22c55e"
        elif "unsafe" in status.lower():
            status = "⚠️ Unsafe"
            color = "#dc2626"
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                padding: 5px;
                border-radius: 3px;
                background-color: {color}20;
                color: {color};
            }}
        """)
        
    def show_scan_results(self, results, is_safe):
        """Show detailed scan results"""
        self.results_label.setHidden(False)
        self.results_label.setText(results)
        color = "#22c55e" if is_safe else "#ef4444"
        self.results_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                padding: 5px;
                border: 1px solid {color}40;
                border-radius: 5px;
                background-color: {color}10;
            }}
        """)
