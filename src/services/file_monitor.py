"""
File monitor service for AI Employee Foundation
Monitors vault folders for file changes and triggers appropriate actions
"""
import time
import sys
import threading
from pathlib import Path
from typing import Callable, Dict, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add the src directory to the path so we can import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from models.action_file import ActionFile
from models.approval_file import ApprovalFile
from lib.exceptions import FileMonitorError


class FileMonitor(FileSystemEventHandler):
    """
    Service that monitors vault folders for file changes and triggers appropriate actions.
    Uses watchdog to monitor file system events.
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        """
        Initialize the file monitor with configuration.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.observer = Observer()
        self.watched_paths = {}
        self.event_callbacks = {}
        self.vault_path = None
        self.is_running = False
        
        # Load configuration
        self.load_config()
    
    def load_config(self):
        """Load configuration from the config file."""
        # In a real implementation, we would load the config file and extract the necessary values
        # For now, we'll use a default vault path
        self.vault_path = "./AI_Employee_Vault"
    
    def start_monitoring(self, vault_path: str = None):
        """
        Start monitoring the vault folders.
        
        Args:
            vault_path: Path to the vault to monitor (uses default if not provided)
        """
        if vault_path:
            self.vault_path = vault_path
        
        vault_path_obj = Path(self.vault_path)
        
        # Define the folders to monitor
        folders_to_monitor = [
            "Needs_Action",
            "Pending_Approval",
            "Approved",
            "Inbox"
        ]
        
        # Set up event handlers for each folder
        for folder_name in folders_to_monitor:
            folder_path = vault_path_obj / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Schedule monitoring for this folder
            event_handler = self
            self.observer.schedule(event_handler, str(folder_path), recursive=False)
            
            # Store the path for reference
            self.watched_paths[folder_name] = folder_path
        
        # Start the observer
        self.observer.start()
        self.is_running = True
        
        print(f"File monitoring started for vault: {self.vault_path}")
        print(f"Monitoring folders: {list(self.watched_paths.keys())}")
    
    def stop_monitoring(self):
        """Stop monitoring file system events."""
        self.observer.stop()
        self.observer.join()
        self.is_running = False
        
        print("File monitoring stopped")
    
    def register_callback(self, event_type: str, folder: str, callback: Callable):
        """
        Register a callback function for a specific event type in a specific folder.
        
        Args:
            event_type: Type of event ('created', 'modified', 'moved', 'deleted')
            folder: Folder name to listen for events in
            callback: Function to call when the event occurs
        """
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = {}
        self.event_callbacks[event_type][folder] = callback
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        folder_name = file_path.parent.name
        
        # Check if we have a callback registered for this event type and folder
        if 'created' in self.event_callbacks and folder_name in self.event_callbacks['created']:
            callback = self.event_callbacks['created'][folder_name]
            callback(file_path)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        folder_name = file_path.parent.name
        
        # Check if we have a callback registered for this event type and folder
        if 'modified' in self.event_callbacks and folder_name in self.event_callbacks['modified']:
            callback = self.event_callbacks['modified'][folder_name]
            callback(file_path)
    
    def on_moved(self, event):
        """Handle file move events."""
        if event.is_directory:
            return
        
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        src_folder = src_path.parent.name
        dest_folder = dest_path.parent.name
        
        # Check if we have a callback registered for this event type and source folder
        if 'moved' in self.event_callbacks and src_folder in self.event_callbacks['moved']:
            callback = self.event_callbacks['moved'][src_folder]
            callback(src_path, dest_path)
        
        # Also check for destination folder callbacks
        if 'moved_to' in self.event_callbacks and dest_folder in self.event_callbacks['moved_to']:
            callback = self.event_callbacks['moved_to'][dest_folder]
            callback(src_path, dest_path)
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        folder_name = file_path.parent.name
        
        # Check if we have a callback registered for this event type and folder
        if 'deleted' in self.event_callbacks and folder_name in self.event_callbacks['deleted']:
            callback = self.event_callbacks['deleted'][folder_name]
            callback(file_path)
    
    def handle_needs_action_created(self, file_path: Path):
        """
        Handle when a new action file is created in the Needs_Action folder.
        
        Args:
            file_path: Path to the newly created action file
        """
        print(f"New action file detected: {file_path.name}")
        
        # In a real implementation, we would trigger the Claude service to process this file
        # For now, we'll just log the event
        print(f"  - Would trigger Claude service to process: {file_path.name}")
    
    def handle_pending_approval_created(self, file_path: Path):
        """
        Handle when a new approval file is created in the Pending_Approval folder.
        
        Args:
            file_path: Path to the newly created approval file
        """
        print(f"New approval request detected: {file_path.name}")
        
        # In a real implementation, we would notify the user that approval is needed
        # For now, we'll just log the event
        print(f"  - Would notify user that approval is needed for: {file_path.name}")
    
    def handle_approved_moved(self, src_path: Path, dest_path: Path):
        """
        Handle when an approval file is moved from Pending_Approval to Approved.
        
        Args:
            src_path: Original path of the file
            dest_path: New path of the file
        """
        print(f"Approval granted: {src_path.name} moved to Approved")
        
        # In a real implementation, we would trigger the execution of the approved action
        # For now, we'll just log the event
        print(f"  - Would trigger execution of action: {src_path.name}")
    
    def handle_inbox_created(self, file_path: Path):
        """
        Handle when a new file is created in the Inbox folder.
        
        Args:
            file_path: Path to the newly created file
        """
        print(f"New file in inbox: {file_path.name}")
        
        # In a real implementation, we would process this file based on its type
        # For now, we'll just log the event
        print(f"  - Would process inbox file: {file_path.name}")
    
    def setup_default_callbacks(self):
        """Set up default callbacks for common events."""
        # When a file is created in Needs_Action, trigger Claude processing
        self.register_callback('created', 'Needs_Action', self.handle_needs_action_created)
        
        # When a file is created in Pending_Approval, notify for approval
        self.register_callback('created', 'Pending_Approval', self.handle_pending_approval_created)
        
        # When a file is moved to Approved, trigger execution
        self.register_callback('moved_to', 'Approved', self.handle_approved_moved)
        
        # When a file is created in Inbox, process it
        self.register_callback('created', 'Inbox', self.handle_inbox_created)


class FileMonitorManager:
    """
    Manager class to handle multiple file monitors if needed.
    """
    
    def __init__(self):
        self.monitors = {}
    
    def add_monitor(self, name: str, monitor: FileMonitor):
        """
        Add a file monitor to the manager.
        
        Args:
            name: Name to identify the monitor
            monitor: FileMonitor instance
        """
        self.monitors[name] = monitor
    
    def start_all_monitors(self):
        """Start all registered monitors."""
        for name, monitor in self.monitors.items():
            print(f"Starting monitor: {name}")
            monitor.setup_default_callbacks()
            monitor.start_monitoring()
    
    def stop_all_monitors(self):
        """Stop all registered monitors."""
        for name, monitor in self.monitors.items():
            print(f"Stopping monitor: {name}")
            monitor.stop_monitoring()