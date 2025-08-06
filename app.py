#!/usr/bin/env python3
"""
LAN Software Automation System - Main Application
A complete desktop application for automated software installation across LAN networks.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
import threading
import subprocess
import platform

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class LANAutomationApp:
    """Main application window for LAN Software Automation System"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.admin_process = None
        self.client_process = None
        self._setup_window()
        self._create_widgets()
        self._check_dependencies()
    
    def _setup_window(self):
        """Setup main application window"""
        self.root.title("LAN Software Automation System v1.0")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.root.winfo_screenheight() // 2) - (600 // 2)
        self.root.geometry(f'800x600+{x}+{y}')
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Set icon (if available)
        try:
            self.root.iconbitmap('icon.ico')
        except:
            pass
    
    def _create_widgets(self):
        """Create main GUI widgets"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg='#f0f0f0')
        header_frame.pack(fill='x', pady=(0, 30))
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="🔧 LAN Software Automation System",
            font=('Arial', 24, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            header_frame,
            text="Automated Software Deployment Across LAN Networks",
            font=('Arial', 12),
            bg='#f0f0f0',
            fg='#7f8c8d'
        )
        subtitle_label.pack(pady=(5, 0))
        
        # System info
        info_frame = tk.Frame(main_frame, bg='#f0f0f0')
        info_frame.pack(fill='x', pady=(0, 20))
        
        hostname = platform.node()
        system_info = f"System: {platform.system()} {platform.release()} | Hostname: {hostname}"
        
        info_label = tk.Label(
            info_frame,
            text=system_info,
            font=('Arial', 10),
            bg='#f0f0f0',
            fg='#34495e'
        )
        info_label.pack()
        
        # Main content area
        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill='both', expand=True)
        
        # Left panel - Application modes
        left_panel = tk.Frame(content_frame, bg='#f0f0f0')
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Mode selection
        mode_frame = tk.LabelFrame(left_panel, text="Application Mode", font=('Arial', 12, 'bold'), bg='#f0f0f0')
        mode_frame.pack(fill='x', pady=(0, 20))
        
        # Admin mode button
        self.admin_button = tk.Button(
            mode_frame,
            text="🖥️ Admin Panel",
            font=('Arial', 14, 'bold'),
            bg='#3498db',
            fg='white',
            relief='flat',
            padx=30,
            pady=15,
            command=self._start_admin
        )
        self.admin_button.pack(fill='x', pady=10, padx=10)
        
        # Client mode button
        self.client_button = tk.Button(
            mode_frame,
            text="💻 Client Agent",
            font=('Arial', 14, 'bold'),
            bg='#27ae60',
            fg='white',
            relief='flat',
            padx=30,
            pady=15,
            command=self._start_client
        )
        self.client_button.pack(fill='x', pady=(0, 10), padx=10)
        
        # Status indicators
        status_frame = tk.LabelFrame(left_panel, text="Status", font=('Arial', 12, 'bold'), bg='#f0f0f0')
        status_frame.pack(fill='x')
        
        self.admin_status = tk.Label(
            status_frame,
            text="Admin Panel: Stopped",
            font=('Arial', 10),
            bg='#f0f0f0',
            fg='#e74c3c'
        )
        self.admin_status.pack(anchor='w', padx=10, pady=5)
        
        self.client_status = tk.Label(
            status_frame,
            text="Client Agent: Stopped",
            font=('Arial', 10),
            bg='#f0f0f0',
            fg='#e74c3c'
        )
        self.client_status.pack(anchor='w', padx=10, pady=(0, 10))
        
        # Right panel - Information and controls
        right_panel = tk.Frame(content_frame, bg='#f0f0f0')
        right_panel.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # Information panel
        info_panel = tk.LabelFrame(right_panel, text="Information", font=('Arial', 12, 'bold'), bg='#f0f0f0')
        info_panel.pack(fill='x', pady=(0, 20))
        
        info_text = """
🔧 Admin Panel:
• Control software installations
• Monitor network clients
• Manage deployment tasks
• View installation logs

💻 Client Agent:
• Join network for installations
• Receive silent installations
• Report status to admin
• Background operation

🔐 Security Features:
• Encrypted communication
• User consent required
• File integrity verification
• Audit logging
        """
        
        info_label = tk.Label(
            info_panel,
            text=info_text,
            font=('Consolas', 9),
            bg='#f0f0f0',
            fg='#2c3e50',
            justify='left'
        )
        info_label.pack(padx=10, pady=10)
        
        # Control buttons
        control_frame = tk.LabelFrame(right_panel, text="Controls", font=('Arial', 12, 'bold'), bg='#f0f0f0')
        control_frame.pack(fill='x')
        
        # Stop buttons
        self.stop_admin_button = tk.Button(
            control_frame,
            text="Stop Admin",
            font=('Arial', 10),
            bg='#e74c3c',
            fg='white',
            relief='flat',
            command=self._stop_admin
        )
        self.stop_admin_button.pack(fill='x', pady=5, padx=10)
        
        self.stop_client_button = tk.Button(
            control_frame,
            text="Stop Client",
            font=('Arial', 10),
            bg='#e74c3c',
            fg='white',
            relief='flat',
            command=self._stop_client
        )
        self.stop_client_button.pack(fill='x', pady=(0, 5), padx=10)
        
        # Other controls
        tk.Button(
            control_frame,
            text="Install Dependencies",
            font=('Arial', 10),
            bg='#f39c12',
            fg='white',
            relief='flat',
            command=self._install_dependencies
        ).pack(fill='x', pady=5, padx=10)
        
        tk.Button(
            control_frame,
            text="View Documentation",
            font=('Arial', 10),
            bg='#9b59b6',
            fg='white',
            relief='flat',
            command=self._view_documentation
        ).pack(fill='x', pady=(0, 10), padx=10)
        
        # Log area
        log_frame = tk.LabelFrame(right_panel, text="Application Log", font=('Arial', 12, 'bold'), bg='#f0f0f0')
        log_frame.pack(fill='both', expand=True)
        
        # Text widget with scrollbar
        text_frame = tk.Frame(log_frame, bg='#f0f0f0')
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.log_text = tk.Text(
            text_frame,
            height=8,
            font=('Consolas', 9),
            bg='#2c3e50',
            fg='#ecf0f1',
            wrap='word'
        )
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Add initial log message
        self._log("Application started successfully")
        self._log(f"System: {platform.system()} {platform.release()}")
        self._log(f"Python: {sys.version.split()[0]}")
    
    def _check_dependencies(self):
        """Check if required dependencies are installed"""
        try:
            import cryptography
            import tkinter
            self._log("✅ All dependencies are available")
        except ImportError as e:
            self._log(f"❌ Missing dependency: {e}")
            self._log("Run 'Install Dependencies' to fix this")
    
    def _log(self, message):
        """Add message to log"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
    
    def _start_admin(self):
        """Start admin application"""
        if self.admin_process and self.admin_process.poll() is None:
            messagebox.showinfo("Info", "Admin panel is already running")
            return
        
        try:
            self._log("Starting Admin Panel...")
            self.admin_process = subprocess.Popen([sys.executable, 'admin_app.py'])
            self.admin_status.config(text="Admin Panel: Running", fg='#27ae60')
            self._log("✅ Admin Panel started successfully")
        except Exception as e:
            self._log(f"❌ Failed to start Admin Panel: {e}")
            messagebox.showerror("Error", f"Failed to start Admin Panel:\n{e}")
    
    def _start_client(self):
        """Start client agent"""
        if self.client_process and self.client_process.poll() is None:
            messagebox.showinfo("Info", "Client agent is already running")
            return
        
        try:
            self._log("Starting Client Agent...")
            self.client_process = subprocess.Popen([sys.executable, 'client_agent.py'])
            self.client_status.config(text="Client Agent: Running", fg='#27ae60')
            self._log("✅ Client Agent started successfully")
        except Exception as e:
            self._log(f"❌ Failed to start Client Agent: {e}")
            messagebox.showerror("Error", f"Failed to start Client Agent:\n{e}")
    
    def _stop_admin(self):
        """Stop admin application"""
        if self.admin_process and self.admin_process.poll() is None:
            self.admin_process.terminate()
            self.admin_status.config(text="Admin Panel: Stopped", fg='#e74c3c')
            self._log("Admin Panel stopped")
        else:
            messagebox.showinfo("Info", "Admin Panel is not running")
    
    def _stop_client(self):
        """Stop client agent"""
        if self.client_process and self.client_process.poll() is None:
            self.client_process.terminate()
            self.client_status.config(text="Client Agent: Stopped", fg='#e74c3c')
            self._log("Client Agent stopped")
        else:
            messagebox.showinfo("Info", "Client Agent is not running")
    
    def _install_dependencies(self):
        """Install required dependencies"""
        try:
            self._log("Installing dependencies...")
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self._log("✅ Dependencies installed successfully")
                messagebox.showinfo("Success", "Dependencies installed successfully")
            else:
                self._log(f"❌ Failed to install dependencies: {result.stderr}")
                messagebox.showerror("Error", f"Failed to install dependencies:\n{result.stderr}")
        except Exception as e:
            self._log(f"❌ Error installing dependencies: {e}")
            messagebox.showerror("Error", f"Error installing dependencies:\n{e}")
    
    def _view_documentation(self):
        """Open documentation"""
        try:
            if os.path.exists('README.md'):
                if platform.system() == 'Windows':
                    os.startfile('README.md')
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', 'README.md'])
                else:  # Linux
                    subprocess.run(['xdg-open', 'README.md'])
                self._log("Documentation opened")
            else:
                messagebox.showinfo("Info", "Documentation file not found")
        except Exception as e:
            self._log(f"❌ Error opening documentation: {e}")
            messagebox.showerror("Error", f"Error opening documentation:\n{e}")
    
    def _on_closing(self):
        """Handle application closing"""
        # Stop any running processes
        if self.admin_process and self.admin_process.poll() is None:
            self.admin_process.terminate()
        
        if self.client_process and self.client_process.poll() is None:
            self.client_process.terminate()
        
        self._log("Application shutting down...")
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = LANAutomationApp()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {e}")
        messagebox.showerror("Startup Error", f"Failed to start application:\n{str(e)}")

if __name__ == "__main__":
    main() 