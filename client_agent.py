"""
Client Agent for LAN Software Automation Installation System
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
import sys
from datetime import datetime
import config
from network_manager import NetworkManager
from installer import installer
from security import consent_manager
from gui_components import (
    ModernButton, StatusLabel, ProgressBar, LogDisplay, ConsentDialog
)

class ClientAgent:
    """Client agent application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.network_manager = NetworkManager(is_admin=False)
        self.installation_running = False
        self._setup_window()
        self._create_widgets()
        self._check_consent()
    
    def _setup_window(self):
        """Setup main window"""
        self.root.title(f"{config.APP_NAME} - Client Agent v{config.VERSION}")
        self.root.geometry(config.CLIENT_WINDOW_SIZE)
        self.root.configure(bg=config.THEME_COLORS['background'])
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (400 // 2)
        self.root.geometry(f'600x400+{x}+{y}')
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Minimize to system tray (optional)
        self.root.iconify()
    
    def _create_widgets(self):
        """Create main GUI widgets"""
        # Main container
        main_frame = tk.Frame(self.root, bg=config.THEME_COLORS['background'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header
        header_frame = tk.Frame(main_frame, bg=config.THEME_COLORS['background'])
        header_frame.pack(fill='x', pady=(0, 20))
        
        title_label = tk.Label(
            header_frame, 
            text="🖥️ LAN Software Automation - Client Agent", 
            font=('Arial', 14, 'bold'),
            bg=config.THEME_COLORS['background'],
            fg=config.THEME_COLORS['primary']
        )
        title_label.pack(side='left')
        
        # Status indicator
        self.status_label = StatusLabel(header_frame)
        self.status_label.pack(side='right')
        self.status_label.set_status("info", "Initializing...")
        
        # System info
        info_frame = tk.Frame(main_frame, bg=config.THEME_COLORS['background'])
        info_frame.pack(fill='x', pady=(0, 20))
        
        # Hostname and IP
        hostname = os.environ.get('COMPUTERNAME', os.environ.get('HOSTNAME', 'Unknown'))
        ip_info = f"Hostname: {hostname} | IP: {config.LOCAL_IP}"
        
        info_label = tk.Label(
            info_frame, 
            text=ip_info,
            font=('Arial', 10),
            bg=config.THEME_COLORS['background'],
            fg=config.THEME_COLORS['text']
        )
        info_label.pack(anchor='w')
        
        # Consent status
        self.consent_label = tk.Label(
            info_frame,
            text="Consent: Checking...",
            font=('Arial', 10),
            bg=config.THEME_COLORS['background'],
            fg=config.THEME_COLORS['warning']
        )
        self.consent_label.pack(anchor='w', pady=(5, 0))
        
        # Control buttons
        control_frame = tk.Frame(main_frame, bg=config.THEME_COLORS['background'])
        control_frame.pack(fill='x', pady=(0, 20))
        
        self.consent_button = ModernButton(
            control_frame, "Give Consent", self._show_consent_dialog, "success"
        )
        self.consent_button.pack(side='left', padx=(0, 10))
        
        self.revoke_button = ModernButton(
            control_frame, "Revoke Consent", self._revoke_consent, "error"
        )
        self.revoke_button.pack(side='left')
        
        # Progress bar
        self.progress_bar = ProgressBar(main_frame)
        self.progress_bar.pack(fill='x', pady=(0, 20))
        
        # Log display
        log_frame = tk.Frame(main_frame, bg=config.THEME_COLORS['background'])
        log_frame.pack(fill='both', expand=True)
        
        self.log_display = LogDisplay(log_frame)
        self.log_display.pack(fill='both', expand=True)
        
        # Add initial log message
        self.log_display.add_log("Client agent started", "info")
    
    def _check_consent(self):
        """Check user consent status"""
        if consent_manager.has_consent():
            self._consent_granted()
        else:
            self._consent_required()
    
    def _consent_required(self):
        """Handle consent required state"""
        self.consent_label.configure(text="Consent: Required", fg=config.THEME_COLORS['warning'])
        self.status_label.set_status("warning", "Consent required")
        self.log_display.add_log("User consent required to join network", "warning")
        
        # Show consent dialog automatically
        self.root.after(1000, self._show_consent_dialog)
    
    def _consent_granted(self):
        """Handle consent granted state"""
        self.consent_label.configure(text="Consent: Granted", fg=config.THEME_COLORS['success'])
        self.status_label.set_status("success", "Connected to network")
        self.log_display.add_log("User consent granted - joining network", "success")
        
        # Start network services
        self._start_network_services()
    
    def _show_consent_dialog(self):
        """Show consent dialog"""
        dialog = ConsentDialog(self.root)
        if dialog.show():
            self._grant_consent()
        else:
            self._consent_denied()
    
    def _grant_consent(self):
        """Grant user consent"""
        if consent_manager.give_consent():
            self._consent_granted()
        else:
            self.log_display.add_log("Failed to save consent", "error")
            messagebox.showerror("Error", "Failed to save consent. Please try again.")
    
    def _revoke_consent(self):
        """Revoke user consent"""
        if messagebox.askyesno("Revoke Consent", "Are you sure you want to revoke consent? This will disconnect you from the network."):
            if consent_manager.revoke_consent():
                self._consent_required()
                self.log_display.add_log("Consent revoked - disconnected from network", "warning")
            else:
                self.log_display.add_log("Failed to revoke consent", "error")
    
    def _consent_denied(self):
        """Handle consent denied"""
        self.consent_label.configure(text="Consent: Denied", fg=config.THEME_COLORS['error'])
        self.status_label.set_status("error", "Consent denied")
        self.log_display.add_log("User denied consent - cannot join network", "error")
        
        # Show message and exit option
        if messagebox.askyesno("Consent Denied", "Without consent, the client agent cannot function.\n\nWould you like to exit the application?"):
            self._on_closing()
    
    def _start_network_services(self):
        """Start network discovery and communication services"""
        try:
            # Setup installation callback
            self.network_manager.register_callback('on_install_request', self._handle_install_request)
            
            # Start discovery service
            self.network_manager.start_discovery()
            self.log_display.add_log("Network discovery service started", "info")
            
            # Start communication server
            self.network_manager.start_communication_server()
            self.log_display.add_log("Communication server started", "info")
            
            self.status_label.set_status("success", "Ready for installations")
            self.log_display.add_log("Client agent ready - waiting for admin commands", "success")
            
        except Exception as e:
            self.log_display.add_log(f"Failed to start network services: {str(e)}", "error")
            self.status_label.set_status("error", "Network error")
    
    def _handle_install_request(self, file_path):
        """Handle installation request from admin"""
        if self.installation_running:
            self.log_display.add_log("Installation already in progress, ignoring new request", "warning")
            return False
        
        self.installation_running = True
        
        def perform_installation():
            try:
                self.progress_bar.start_progress("Installing software...")
                self.log_display.add_log(f"Starting installation: {os.path.basename(file_path)}", "info")
                
                # Perform installation
                success = installer.install_software(file_path)
                
                if success:
                    self.progress_bar.complete_progress("Installation successful")
                    self.log_display.add_log("Software installation completed successfully", "success")
                else:
                    self.progress_bar.complete_progress("Installation failed")
                    self.log_display.add_log("Software installation failed", "error")
                
                # Show notification (optional)
                if success:
                    self._show_installation_notification("Installation Successful", "Software has been installed successfully.")
                else:
                    self._show_installation_notification("Installation Failed", "Software installation failed. Check logs for details.")
                
                return success
                
            except Exception as e:
                self.log_display.add_log(f"Installation error: {str(e)}", "error")
                self.progress_bar.complete_progress("Installation error")
                return False
            
            finally:
                self.installation_running = False
        
        # Run installation in background thread
        threading.Thread(target=perform_installation, daemon=True).start()
        return True  # Return immediately, actual result will be sent via network
    
    def _show_installation_notification(self, title, message):
        """Show installation notification"""
        try:
            # Try to show system notification
            if sys.platform == "win32":
                # Windows notification
                import win10toast
                toaster = win10toast.ToastNotifier()
                toaster.show_toast(title, message, duration=5, threaded=True)
            else:
                # Fallback to message box
                self.root.after(0, lambda: messagebox.showinfo(title, message))
        except:
            # Fallback to message box
            self.root.after(0, lambda: messagebox.showinfo(title, message))
    
    def _on_closing(self):
        """Handle application closing"""
        try:
            self.network_manager.stop_discovery()
            self.log_display.add_log("Client agent shutting down...", "info")
            time.sleep(0.5)  # Brief delay for cleanup
        except:
            pass
        
        self.root.destroy()
    
    def run(self):
        """Start the client agent"""
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = ClientAgent()
        app.run()
    except Exception as e:
        print(f"Failed to start client agent: {e}")
        messagebox.showerror("Startup Error", f"Failed to start client agent:\n{str(e)}")

if __name__ == "__main__":
    main() 