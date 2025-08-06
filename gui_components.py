"""
Reusable GUI components for LAN Software Automation Installation System
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime
import config

class ModernButton(tk.Button):
    """Modern styled button"""
    
    def __init__(self, parent, text, command=None, style="primary", **kwargs):
        super().__init__(parent, text=text, command=command, **kwargs)
        self.style = style
        self._apply_style()
    
    def _apply_style(self):
        """Apply modern styling"""
        if self.style == "primary":
            self.configure(
                bg=config.THEME_COLORS['primary'],
                fg='white',
                font=('Arial', 10, 'bold'),
                relief='flat',
                padx=20,
                pady=10,
                cursor='hand2'
            )
        elif self.style == "secondary":
            self.configure(
                bg=config.THEME_COLORS['secondary'],
                fg='white',
                font=('Arial', 10),
                relief='flat',
                padx=15,
                pady=8,
                cursor='hand2'
            )
        elif self.style == "success":
            self.configure(
                bg=config.THEME_COLORS['success'],
                fg='white',
                font=('Arial', 10, 'bold'),
                relief='flat',
                padx=20,
                pady=10,
                cursor='hand2'
            )
        elif self.style == "warning":
            self.configure(
                bg=config.THEME_COLORS['warning'],
                fg='white',
                font=('Arial', 10, 'bold'),
                relief='flat',
                padx=20,
                pady=10,
                cursor='hand2'
            )
        elif self.style == "error":
            self.configure(
                bg=config.THEME_COLORS['error'],
                fg='white',
                font=('Arial', 10, 'bold'),
                relief='flat',
                padx=20,
                pady=10,
                cursor='hand2'
            )

class StatusLabel(tk.Label):
    """Status display label with color coding"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(
            font=('Arial', 9),
            pady=5
        )
    
    def set_status(self, status, message):
        """Set status with appropriate color"""
        if status == "success":
            self.configure(fg=config.THEME_COLORS['success'], text=message)
        elif status == "error":
            self.configure(fg=config.THEME_COLORS['error'], text=message)
        elif status == "warning":
            self.configure(fg=config.THEME_COLORS['warning'], text=message)
        elif status == "info":
            self.configure(fg=config.THEME_COLORS['secondary'], text=message)
        else:
            self.configure(fg=config.THEME_COLORS['text'], text=message)

class ClientListbox(tk.Frame):
    """Client list with checkboxes"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.clients = {}
        self.selected_clients = set()
        self._create_widgets()
    
    def _create_widgets(self):
        """Create listbox widgets"""
        # Header
        header_frame = tk.Frame(self)
        header_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(header_frame, text="Available Clients", font=('Arial', 12, 'bold')).pack(side='left')
        
        # Buttons
        ModernButton(header_frame, "Select All", self.select_all, "secondary").pack(side='right', padx=(5, 0))
        ModernButton(header_frame, "Clear All", self.clear_all, "secondary").pack(side='right')
        
        # Listbox with scrollbar
        list_frame = tk.Frame(self)
        list_frame.pack(fill='both', expand=True)
        
        self.listbox = tk.Listbox(list_frame, selectmode='multiple', font=('Arial', 10))
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        self.listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind selection event
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
    
    def add_client(self, client_id, client_info):
        """Add client to list"""
        self.clients[client_id] = client_info
        display_text = f"{client_info['hostname']} ({client_info['ip']})"
        self.listbox.insert(tk.END, display_text)
    
    def remove_client(self, client_id):
        """Remove client from list"""
        if client_id in self.clients:
            # Find and remove from listbox
            for i in range(self.listbox.size()):
                client_info = self.clients[client_id]
                display_text = f"{client_info['hostname']} ({client_info['ip']})"
                if self.listbox.get(i) == display_text:
                    self.listbox.delete(i)
                    break
            
            del self.clients[client_id]
            self.selected_clients.discard(client_id)
    
    def clear_all(self):
        """Clear all clients"""
        self.listbox.delete(0, tk.END)
        self.clients.clear()
        self.selected_clients.clear()
    
    def select_all(self):
        """Select all clients"""
        self.listbox.selection_set(0, tk.END)
        self.selected_clients = set(self.clients.keys())
    
    def _on_select(self, event):
        """Handle selection change"""
        selection = self.listbox.curselection()
        self.selected_clients.clear()
        
        for index in selection:
            # Find client_id by index
            for i, (client_id, client_info) in enumerate(self.clients.items()):
                if i == index:
                    self.selected_clients.add(client_id)
                    break
    
    def get_selected_clients(self):
        """Get list of selected client IDs"""
        return list(self.selected_clients)
    
    def get_selected_client_info(self):
        """Get info of selected clients"""
        return {client_id: self.clients[client_id] for client_id in self.selected_clients}

class FileSelector(tk.Frame):
    """File selection widget"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.selected_file = None
        self._create_widgets()
    
    def _create_widgets(self):
        """Create file selector widgets"""
        # File path display
        self.file_label = tk.Label(self, text="No file selected", font=('Arial', 10))
        self.file_label.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        # Browse button
        ModernButton(self, "Browse", self._browse_file, "secondary").pack(side='right')
    
    def _browse_file(self):
        """Open file browser"""
        file_types = [
            ("All supported files", "*.exe;*.msi;*.zip;*.tar.gz;*.deb;*.rpm"),
            ("Windows Installers", "*.exe;*.msi"),
            ("Linux Packages", "*.deb;*.rpm"),
            ("Archives", "*.zip;*.tar.gz"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Software File",
            filetypes=file_types
        )
        
        if filename:
            self.selected_file = filename
            self.file_label.configure(text=f"Selected: {filename}")
    
    def get_selected_file(self):
        """Get selected file path"""
        return self.selected_file
    
    def clear_selection(self):
        """Clear file selection"""
        self.selected_file = None
        self.file_label.configure(text="No file selected")

class ProgressBar(tk.Frame):
    """Progress bar with status"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_widgets()
    
    def _create_widgets(self):
        """Create progress bar widgets"""
        # Status label
        self.status_label = tk.Label(self, text="Ready", font=('Arial', 10))
        self.status_label.pack(fill='x')
        
        # Progress bar
        self.progress = ttk.Progressbar(self, mode='determinate')
        self.progress.pack(fill='x', pady=(5, 0))
    
    def start_progress(self, message="Processing..."):
        """Start progress bar"""
        self.status_label.configure(text=message)
        self.progress.configure(value=0)
        self.progress.start()
    
    def update_progress(self, value, message=None):
        """Update progress bar"""
        self.progress.configure(value=value)
        if message:
            self.status_label.configure(text=message)
    
    def complete_progress(self, message="Completed"):
        """Complete progress bar"""
        self.progress.configure(value=100)
        self.progress.stop()
        self.status_label.configure(text=message)
    
    def reset_progress(self):
        """Reset progress bar"""
        self.progress.configure(value=0)
        self.progress.stop()
        self.status_label.configure(text="Ready")

class LogDisplay(tk.Frame):
    """Log display widget"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_widgets()
    
    def _create_widgets(self):
        """Create log display widgets"""
        # Header
        header_frame = tk.Frame(self)
        header_frame.pack(fill='x', pady=(0, 5))
        
        tk.Label(header_frame, text="Activity Log", font=('Arial', 12, 'bold')).pack(side='left')
        
        ModernButton(header_frame, "Clear", self.clear_log, "secondary").pack(side='right')
        
        # Text widget with scrollbar
        text_frame = tk.Frame(self)
        text_frame.pack(fill='both', expand=True)
        
        self.text_widget = tk.Text(text_frame, height=10, font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=self.text_widget.yview)
        self.text_widget.configure(yscrollcommand=scrollbar.set)
        
        self.text_widget.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Configure tags for different log levels
        self.text_widget.tag_configure('success', foreground=config.THEME_COLORS['success'])
        self.text_widget.tag_configure('error', foreground=config.THEME_COLORS['error'])
        self.text_widget.tag_configure('warning', foreground=config.THEME_COLORS['warning'])
        self.text_widget.tag_configure('info', foreground=config.THEME_COLORS['secondary'])
    
    def add_log(self, message, level="info"):
        """Add log message"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        self.text_widget.insert(tk.END, log_entry, level)
        self.text_widget.see(tk.END)
    
    def clear_log(self):
        """Clear log display"""
        self.text_widget.delete(1.0, tk.END)

class ConsentDialog(tk.Toplevel):
    """User consent dialog"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.result = False
        self._create_widgets()
        self._center_window()
    
    def _create_widgets(self):
        """Create consent dialog widgets"""
        self.title("Network Participation Consent")
        self.resizable(False, False)
        
        # Main frame
        main_frame = tk.Frame(self, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Icon and title
        title_frame = tk.Frame(main_frame)
        title_frame.pack(fill='x', pady=(0, 20))
        
        tk.Label(title_frame, text="🔒", font=('Arial', 24)).pack(side='left', padx=(0, 10))
        tk.Label(title_frame, text="Network Participation", font=('Arial', 16, 'bold')).pack(side='left')
        
        # Consent text
        consent_text = """
This application allows remote software installation from an administrator.

By giving consent, you agree to:
• Allow the administrator to install software on this computer
• Receive installation commands without user notification
• Participate in the LAN automation network

Your consent can be revoked at any time.
        """
        
        text_widget = tk.Text(main_frame, height=8, width=50, wrap='word', font=('Arial', 10))
        text_widget.insert('1.0', consent_text)
        text_widget.configure(state='disabled')
        text_widget.pack(fill='both', expand=True, pady=(0, 20))
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill='x')
        
        ModernButton(button_frame, "Decline", self._decline, "error").pack(side='right', padx=(10, 0))
        ModernButton(button_frame, "Give Consent", self._consent, "success").pack(side='right')
    
    def _center_window(self):
        """Center the dialog window"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def _consent(self):
        """User gave consent"""
        self.result = True
        self.destroy()
    
    def _decline(self):
        """User declined consent"""
        self.result = False
        self.destroy()
    
    def show(self):
        """Show dialog and return result"""
        self.grab_set()  # Make dialog modal
        self.wait_window()
        return self.result 