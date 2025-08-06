"""
Admin Application for LAN Software Automation Installation System
"""

import tkinter as tk
from tkinter import messagebox
import threading
import time
import os
from datetime import datetime
import config
from network_manager import NetworkManager
from installer import installer
from gui_components import (
    ModernButton, StatusLabel, ClientListbox, FileSelector, 
    ProgressBar, LogDisplay
)

class AdminApplication:
    """Main admin application window"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.network_manager = NetworkManager(is_admin=True)
        self.installation_running = False
        self._setup_window()
        self._create_widgets()
        self._setup_network()
        self._start_network_discovery()
    
    def _setup_window(self):
        """Setup main window"""
        self.root.title(f"{config.APP_NAME} - Admin Panel v{config.VERSION}")
        self.root.geometry(config.ADMIN_WINDOW_SIZE)
        self.root.configure(bg=config.THEME_COLORS['background'])
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.root.winfo_screenheight() // 2) - (600 // 2)
        self.root.geometry(f'800x600+{x}+{y}')
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
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
            text="🔧 LAN Software Automation - Admin Panel", 
            font=('Arial', 16, 'bold'),
            bg=config.THEME_COLORS['background'],
            fg=config.THEME_COLORS['primary']
        )
        title_label.pack(side='left')
        
        # Status indicator
        self.status_label = StatusLabel(header_frame)
        self.status_label.pack(side='right')
        self.status_label.set_status("info", "Starting...")
        
        # Main content area
        content_frame = tk.Frame(main_frame, bg=config.THEME_COLORS['background'])
        content_frame.pack(fill='both', expand=True)
        
        # Left panel - Client management
        left_panel = tk.Frame(content_frame, bg=config.THEME_COLORS['background'])
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Client list
        self.client_list = ClientListbox(left_panel)
        self.client_list.pack(fill='both', expand=True, pady=(0, 10))
        
        # Client management buttons
        client_buttons_frame = tk.Frame(left_panel, bg=config.THEME_COLORS['background'])
        client_buttons_frame.pack(fill='x')
        
        ModernButton(client_buttons_frame, "Refresh", self._refresh_clients, "secondary").pack(side='left', padx=(0, 5))
        ModernButton(client_buttons_frame, "Ping All", self._ping_all_clients, "secondary").pack(side='left')
        
        # Right panel - Installation control
        right_panel = tk.Frame(content_frame, bg=config.THEME_COLORS['background'])
        right_panel.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        # File selection
        file_frame = tk.Frame(right_panel, bg=config.THEME_COLORS['background'])
        file_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(file_frame, text="Software File:", font=('Arial', 12, 'bold'), 
                bg=config.THEME_COLORS['background']).pack(anchor='w')
        
        self.file_selector = FileSelector(file_frame)
        self.file_selector.pack(fill='x', pady=(5, 0))
        
        # Installation controls
        install_frame = tk.Frame(right_panel, bg=config.THEME_COLORS['background'])
        install_frame.pack(fill='x', pady=(0, 10))
        
        self.install_button = ModernButton(
            install_frame, "Install Software", self._start_installation, "success"
        )
        self.install_button.pack(fill='x', pady=(5, 0))
        
        # Progress bar
        self.progress_bar = ProgressBar(right_panel)
        self.progress_bar.pack(fill='x', pady=(10, 0))
        
        # Log display
        log_frame = tk.Frame(right_panel, bg=config.THEME_COLORS['background'])
        log_frame.pack(fill='both', expand=True, pady=(10, 0))
        
        self.log_display = LogDisplay(log_frame)
        self.log_display.pack(fill='both', expand=True)
        
        # Add initial log message
        self.log_display.add_log("Admin application started", "info")
    
    def _setup_network(self):
        """Setup network manager and callbacks"""
        self.network_manager.register_callback('on_client_discovered', self._on_client_discovered)
    
    def _start_network_discovery(self):
        """Start network discovery service"""
        try:
            self.network_manager.start_discovery()
            self.status_label.set_status("success", "Network discovery active")
            self.log_display.add_log("Network discovery service started", "info")
        except Exception as e:
            self.status_label.set_status("error", f"Network error: {str(e)}")
            self.log_display.add_log(f"Failed to start network discovery: {str(e)}", "error")
    
    def _on_client_discovered(self, client_id, client_info):
        """Handle new client discovery"""
        def update_gui():
            self.client_list.add_client(client_id, client_info)
            self.log_display.add_log(f"Client discovered: {client_info['hostname']} ({client_info['ip']})", "success")
        
        # Update GUI in main thread
        self.root.after(0, update_gui)
    
    def _refresh_clients(self):
        """Refresh client list"""
        self.log_display.add_log("Refreshing client list...", "info")
        
        # Clear current list
        self.client_list.clear_all()
        
        # Get online clients
        online_clients = self.network_manager.get_online_clients()
        for client_id, client_info in online_clients.items():
            self.client_list.add_client(client_id, client_info)
        
        self.log_display.add_log(f"Found {len(online_clients)} online clients", "info")
    
    def _ping_all_clients(self):
        """Ping all discovered clients"""
        def ping_clients():
            self.log_display.add_log("Pinging all clients...", "info")
            
            clients = self.client_list.clients
            total_clients = len(clients)
            online_count = 0
            
            for i, (client_id, client_info) in enumerate(clients.items()):
                progress = (i / total_clients) * 100 if total_clients > 0 else 0
                self.progress_bar.update_progress(progress, f"Pinging {client_info['hostname']}...")
                
                if self.network_manager.ping_client(client_info['ip']):
                    online_count += 1
                    self.log_display.add_log(f"✓ {client_info['hostname']} is online", "success")
                else:
                    self.log_display.add_log(f"✗ {client_info['hostname']} is offline", "error")
                
                time.sleep(0.1)  # Small delay to avoid overwhelming network
            
            self.progress_bar.complete_progress(f"Ping complete: {online_count}/{total_clients} online")
            self.log_display.add_log(f"Ping results: {online_count}/{total_clients} clients online", "info")
        
        threading.Thread(target=ping_clients, daemon=True).start()
    
    def _start_installation(self):
        """Start software installation process"""
        if self.installation_running:
            messagebox.showwarning("Installation in Progress", "Please wait for the current installation to complete.")
            return
        
        # Get selected file
        software_file = self.file_selector.get_selected_file()
        if not software_file:
            messagebox.showerror("No File Selected", "Please select a software file to install.")
            return
        
        # Validate file
        is_valid, message = installer.validate_file(software_file)
        if not is_valid:
            messagebox.showerror("Invalid File", message)
            return
        
        # Get selected clients
        selected_clients = self.client_list.get_selected_clients()
        if not selected_clients:
            messagebox.showerror("No Clients Selected", "Please select at least one client for installation.")
            return
        
        # Confirm installation
        client_names = [self.client_list.clients[client_id]['hostname'] for client_id in selected_clients]
        confirm_message = f"Install {os.path.basename(software_file)} on {len(selected_clients)} client(s)?\n\nClients: {', '.join(client_names)}"
        
        if not messagebox.askyesno("Confirm Installation", confirm_message):
            return
        
        # Start installation in background thread
        self.installation_running = True
        self.install_button.configure(state='disabled')
        
        threading.Thread(target=self._perform_installation, args=(software_file, selected_clients), daemon=True).start()
    
    def _perform_installation(self, software_file, selected_clients):
        """Perform the actual installation"""
        try:
            total_clients = len(selected_clients)
            successful_installations = 0
            failed_installations = 0
            
            self.progress_bar.start_progress("Starting installation...")
            self.log_display.add_log(f"Starting installation on {total_clients} clients", "info")
            
            for i, client_id in enumerate(selected_clients):
                client_info = self.client_list.clients[client_id]
                progress = (i / total_clients) * 100
                
                self.progress_bar.update_progress(progress, f"Installing on {client_info['hostname']}...")
                self.log_display.add_log(f"Installing on {client_info['hostname']} ({client_info['ip']})...", "info")
                
                # Send installation command
                response = self.network_manager.send_install_command(client_info['ip'], software_file)
                
                if response and response.get('success'):
                    successful_installations += 1
                    self.log_display.add_log(f"✓ Installation successful on {client_info['hostname']}", "success")
                else:
                    failed_installations += 1
                    error_msg = response.get('error', 'Unknown error') if response else 'No response'
                    self.log_display.add_log(f"✗ Installation failed on {client_info['hostname']}: {error_msg}", "error")
                
                time.sleep(0.5)  # Small delay between installations
            
            # Complete installation
            self.progress_bar.complete_progress("Installation complete")
            
            # Show results
            result_message = f"Installation complete!\n\nSuccessful: {successful_installations}\nFailed: {failed_installations}"
            if failed_installations == 0:
                self.log_display.add_log(f"All installations completed successfully!", "success")
                messagebox.showinfo("Installation Complete", result_message)
            else:
                self.log_display.add_log(f"Installation completed with {failed_installations} failures", "warning")
                messagebox.showwarning("Installation Complete", result_message)
            
        except Exception as e:
            self.log_display.add_log(f"Installation error: {str(e)}", "error")
            messagebox.showerror("Installation Error", f"An error occurred during installation:\n{str(e)}")
        
        finally:
            # Reset UI state
            self.installation_running = False
            self.root.after(0, lambda: self.install_button.configure(state='normal'))
    
    def _on_closing(self):
        """Handle application closing"""
        try:
            self.network_manager.stop_discovery()
            self.log_display.add_log("Admin application shutting down...", "info")
            time.sleep(0.5)  # Brief delay for cleanup
        except:
            pass
        
        self.root.destroy()
    
    def run(self):
        """Start the admin application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = AdminApplication()
        app.run()
    except Exception as e:
        print(f"Failed to start admin application: {e}")
        messagebox.showerror("Startup Error", f"Failed to start admin application:\n{str(e)}")

if __name__ == "__main__":
    main() 