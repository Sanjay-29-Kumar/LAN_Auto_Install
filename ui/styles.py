from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget

class ModernStyle:
    """Modern styling for the LAN Software Installation System"""
    
    @staticmethod
    def get_dark_palette():
        """Get dark color palette"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(43, 43, 43))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(60, 60, 60))
        palette.setColor(QPalette.AlternateBase, QColor(72, 72, 72))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.Button, QColor(72, 72, 72))
        palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.Link, QColor(0, 120, 212))
        palette.setColor(QPalette.Highlight, QColor(0, 120, 212))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        
        return palette
    
    @staticmethod
    def get_light_palette():
        """Get light color palette"""
        palette = QPalette()
        
        # Set color roles
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
        return palette
    
    @staticmethod
    def get_stylesheet():
        """Get modern stylesheet"""
        return """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
        }

        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
        }

        QPushButton {
            background-color: #0078d4;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #106ebe;
        }

        QPushButton:pressed {
            background-color: #005a9e;
        }

        QPushButton:disabled {
            background-color: #404040;
            color: #808080;
        }

        QListWidget {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 4px;
        }

        QListWidget::item {
            padding: 8px;
            border-bottom: 1px solid #555555;
        }

        QListWidget::item:selected {
            background-color: #0078d4;
        }

        QTextEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 8px;
        }

        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 8px;
            margin-top: 1ex;
            padding-top: 10px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }

        QTableWidget {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            gridline-color: #555555;
        }

        QHeaderView::section {
            background-color: #484848;
            color: white;
            padding: 8px;
            border: none;
            font-weight: bold;
        }

        QProgressBar {
            border: 1px solid #555555;
            border-radius: 4px;
            text-align: center;
        }

        QProgressBar::chunk {
            background-color: #0078d4;
            border-radius: 3px;
        }

        QLabel[class="title"] {
            font-size: 14pt;
            font-weight: bold;
            color: #ffffff;
        }

        QLabel[class="status"] {
            color: #cccccc;
        }

        QLabel[class="success"] {
            color: #00ff00;
        }

        QLabel[class="error"] {
            color: #ff4444;
        }

        QStatusBar {
            background-color: #484848;
            border-top: 1px solid #555555;
        }

        QMenuBar {
            background-color: #484848;
            border-bottom: 1px solid #555555;
        }

        QMenuBar::item {
            padding: 8px 12px;
        }

        QMenuBar::item:selected {
            background-color: #0078d4;
        }

        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #3c3c3c;
        }

        QTabBar::tab {
            background-color: #484848;
            padding: 8px 16px;
            margin-right: 2px;
        }

        QTabBar::tab:selected {
            background-color: #0078d4;
        }
        """
    
    @staticmethod
    def get_fonts():
        """Get font configurations"""
        fonts = {
            "default": QFont("Segoe UI", 10),
            "title": QFont("Segoe UI", 16, QFont.Bold),
            "subtitle": QFont("Segoe UI", 12, QFont.Bold),
            "small": QFont("Segoe UI", 8),
            "monospace": QFont("Consolas", 9)
        }
        return fonts
    
    @staticmethod
    def get_colors():
        """Get color definitions"""
        return {
            "primary": "#2a82da",
            "secondary": "#404040",
            "success": "#4CAF50",
            "warning": "#ff9800",
            "error": "#f44336",
            "info": "#2196F3",
            "background": "#2b2b2b",
            "surface": "#404040",
            "text": "#ffffff",
            "text_secondary": "#cccccc",
            "border": "#555555",
            "hover": "#505050",
            "active": "#303030"
        }