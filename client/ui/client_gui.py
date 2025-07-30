import sys
import subprocess
import os
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel

class ClientApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LANAutoInstall Client")
        self.setGeometry(100, 100, 300, 150)

        self.layout = QVBoxLayout()

        self.status_label = QLabel("Status: Waiting for instruction")
        self.layout.addWidget(self.status_label)

        self.start_button = QPushButton("Start Listener")
        self.start_button.clicked.connect(self.start_listener)
        self.layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop Listener")
        self.stop_button.clicked.connect(self.stop_listener)
        self.stop_button.setEnabled(False)
        self.layout.addWidget(self.stop_button)

        self.setLayout(self.layout)

        self.listener_process = None

    def start_listener(self):
        listener_path = os.path.join(os.getcwd(), "client_app.exe")
        if not os.path.exists(listener_path):
            self.status_label.setText("client_app.exe not found!")
            return

        try:
            self.listener_process = subprocess.Popen([listener_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            self.status_label.setText("Status: Listening for instructions")
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")

    def stop_listener(self):
        if self.listener_process:
            self.listener_process.terminate()
            self.listener_process = None
            self.status_label.setText("Status: Listener stopped")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ClientApp()
    window.show()
    sys.exit(app.exec_())
