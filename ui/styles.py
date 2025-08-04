from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtCore import Qt

class ModernStyle:
    """Modern styling for the LAN Software Installation System"""
    
    @staticmethod
    def get_dark_palette():
        """Get dark color palette"""
        palette = QPalette()
        
        # Set color roles
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        
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
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: bold;
            color: #ffffff;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background-color: #505050;
            border-color: #666666;
        }
        
        QPushButton:pressed {
            background-color: #303030;
            border-color: #444444;
        }
        
        QPushButton:disabled {
            background-color: #2a2a2a;
            border-color: #3a3a3a;
            color: #666666;
        }
        
        QLineEdit {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 6px;
            color: #ffffff;
            selection-background-color: #2a82da;
        }
        
        QLineEdit:focus {
            border-color: #2a82da;
        }
        
        QTextEdit {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 6px;
            color: #ffffff;
            selection-background-color: #2a82da;
        }
        
        QListWidget {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 4px;
            color: #ffffff;
            selection-background-color: #2a82da;
            alternate-background-color: #454545;
        }
        
        QListWidget::item {
            padding: 4px;
            border-radius: 2px;
        }
        
        QListWidget::item:selected {
            background-color: #2a82da;
        }
        
        QListWidget::item:hover {
            background-color: #505050;
        }
        
        QTreeWidget {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 4px;
            color: #ffffff;
            selection-background-color: #2a82da;
            alternate-background-color: #454545;
        }
        
        QTreeWidget::item {
            padding: 4px;
            border-radius: 2px;
        }
        
        QTreeWidget::item:selected {
            background-color: #2a82da;
        }
        
        QTreeWidget::item:hover {
            background-color: #505050;
        }
        
        QTableWidget {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 4px;
            gridline-color: #555555;
            color: #ffffff;
            selection-background-color: #2a82da;
            alternate-background-color: #454545;
        }
        
        QTableWidget::item {
            padding: 4px;
            border-radius: 2px;
        }
        
        QTableWidget::item:selected {
            background-color: #2a82da;
        }
        
        QTableWidget::item:hover {
            background-color: #505050;
        }
        
        QHeaderView::section {
            background-color: #505050;
            border: 1px solid #666666;
            padding: 6px;
            font-weight: bold;
            color: #ffffff;
        }
        
        QHeaderView::section:hover {
            background-color: #606060;
        }
        
        QProgressBar {
            border: 2px solid #555555;
            border-radius: 6px;
            text-align: center;
            background-color: #404040;
            color: #ffffff;
        }
        
        QProgressBar::chunk {
            background-color: #2a82da;
            border-radius: 4px;
        }
        
        QTabWidget::pane {
            border: 2px solid #555555;
            border-radius: 4px;
            background-color: #404040;
        }
        
        QTabBar::tab {
            background-color: #505050;
            border: 2px solid #555555;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 16px;
            margin-right: 2px;
            color: #ffffff;
        }
        
        QTabBar::tab:selected {
            background-color: #404040;
            border-color: #2a82da;
        }
        
        QTabBar::tab:hover {
            background-color: #606060;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 2px solid #555555;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 8px;
            color: #ffffff;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 8px 0 8px;
            color: #ffffff;
        }
        
        QLabel {
            color: #ffffff;
        }
        
        QLabel[class="title"] {
            font-size: 16pt;
            font-weight: bold;
            color: #2a82da;
        }
        
        QLabel[class="subtitle"] {
            font-size: 12pt;
            font-weight: bold;
            color: #cccccc;
        }
        
        QLabel[class="status"] {
            font-size: 9pt;
            color: #aaaaaa;
        }
        
        QLabel[class="success"] {
            color: #4CAF50;
        }
        
        QLabel[class="error"] {
            color: #f44336;
        }
        
        QLabel[class="warning"] {
            color: #ff9800;
        }
        
        QCheckBox {
            color: #ffffff;
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #555555;
            border-radius: 3px;
            background-color: #404040;
        }
        
        QCheckBox::indicator:checked {
            background-color: #2a82da;
            border-color: #2a82da;
        }
        
        QCheckBox::indicator:hover {
            border-color: #666666;
        }
        
        QRadioButton {
            color: #ffffff;
            spacing: 8px;
        }
        
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border: 2px solid #555555;
            border-radius: 8px;
            background-color: #404040;
        }
        
        QRadioButton::indicator:checked {
            background-color: #2a82da;
            border-color: #2a82da;
        }
        
        QRadioButton::indicator:hover {
            border-color: #666666;
        }
        
        QComboBox {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 6px;
            color: #ffffff;
            min-height: 20px;
        }
        
        QComboBox:hover {
            border-color: #666666;
        }
        
        QComboBox:focus {
            border-color: #2a82da;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid #ffffff;
        }
        
        QComboBox QAbstractItemView {
            background-color: #404040;
            border: 2px solid #555555;
            selection-background-color: #2a82da;
            color: #ffffff;
        }
        
        QSpinBox {
            background-color: #404040;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 6px;
            color: #ffffff;
        }
        
        QSpinBox:focus {
            border-color: #2a82da;
        }
        
        QSpinBox::up-button, QSpinBox::down-button {
            background-color: #505050;
            border: 1px solid #666666;
            border-radius: 2px;
            width: 16px;
        }
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {
            background-color: #606060;
        }
        
        QMenuBar {
            background-color: #404040;
            border-bottom: 2px solid #555555;
            color: #ffffff;
        }
        
        QMenuBar::item {
            background-color: transparent;
            padding: 8px 12px;
        }
        
        QMenuBar::item:selected {
            background-color: #505050;
        }
        
        QMenu {
            background-color: #404040;
            border: 2px solid #555555;
            color: #ffffff;
        }
        
        QMenu::item {
            padding: 8px 20px;
        }
        
        QMenu::item:selected {
            background-color: #2a82da;
        }
        
        QToolBar {
            background-color: #404040;
            border: none;
            spacing: 4px;
            padding: 4px;
        }
        
        QToolButton {
            background-color: #505050;
            border: 2px solid #555555;
            border-radius: 4px;
            padding: 6px;
            color: #ffffff;
        }
        
        QToolButton:hover {
            background-color: #606060;
            border-color: #666666;
        }
        
        QToolButton:pressed {
            background-color: #404040;
            border-color: #444444;
        }
        
        QStatusBar {
            background-color: #404040;
            border-top: 2px solid #555555;
            color: #ffffff;
        }
        
        QScrollBar:vertical {
            background-color: #404040;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #666666;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #777777;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QScrollBar:horizontal {
            background-color: #404040;
            height: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:horizontal {
            background-color: #666666;
            border-radius: 6px;
            min-width: 20px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background-color: #777777;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        
        QSplitter::handle {
            background-color: #555555;
        }
        
        QSplitter::handle:horizontal {
            width: 2px;
        }
        
        QSplitter::handle:vertical {
            height: 2px;
        }
        
        QFrame[frameShape="4"] {
            color: #555555;
        }
        
        QFrame[frameShape="5"] {
            color: #555555;
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