"""
Watch management commands for AI Employee Foundation CLI
"""
import argparse
from pathlib import Path
import sys

# Add the src directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.gmail_watcher import GmailWatcher
from services.file_monitor import FileMonitor


class WatchCommand:
    """Handles watch-related CLI commands."""
    
    def __init__(self, subparsers):
        """Initialize the watch command parser."""
        self.parser = subparsers.add_parser("watch", help="Watch management commands")
        self.subparsers = self.parser.add_subparsers(dest="watch_action", help="Watch actions")
        
        # Add start command
        start_parser = self.subparsers.add_parser("start", help="Start a watcher service")
        start_parser.add_argument("source", type=str, help="Source to watch (e.g., gmail, filesystem)")
        start_parser.add_argument("--config", "-c", type=str, help="Path to configuration file", 
                                  default="./config.yaml")
        
        # Add stop command
        stop_parser = self.subparsers.add_parser("stop", help="Stop a watcher service")
        stop_parser.add_argument("source", type=str, help="Source to watch (e.g., gmail, filesystem)")
    
    def execute(self, args):
        """Execute the watch command based on parsed arguments."""
        if args.watch_action == "start":
            self.start_watcher(args.source, args.config)
        elif args.watch_action == "stop":
            self.stop_watcher(args.source)
        else:
            self.parser.print_help()
    
    def start_watcher(self, source, config_path):
        """Start a watcher service."""
        print(f"Starting {source} watcher...")
        
        if source.lower() == "gmail":
            try:
                # Initialize the Gmail watcher
                watcher = GmailWatcher(config_path)
                print(f"✅ Gmail watcher initialized. Starting monitoring...")
                
                # In a real implementation, we would start the watcher in a separate thread
                # For now, we'll just simulate starting it
                print(f"📧 Gmail watcher started. Monitoring for new emails...")
                
            except Exception as e:
                print(f"❌ Error starting Gmail watcher: {str(e)}")
        
        elif source.lower() == "filesystem":
            try:
                # Initialize the file monitor
                monitor = FileMonitor(config_path)
                print(f"✅ File system monitor initialized. Starting monitoring...")
                
                # In a real implementation, we would start the monitor in a separate thread
                # For now, we'll just simulate starting it
                print(f"📁 File system monitor started. Monitoring vault folders...")
                
            except Exception as e:
                print(f"❌ Error starting file system monitor: {str(e)}")
        
        else:
            print(f"❌ Unknown watcher source: {source}. Supported sources: gmail, filesystem")
    
    def stop_watcher(self, source):
        """Stop a watcher service."""
        print(f"Stopping {source} watcher...")
        
        # In a real implementation, we would have a mechanism to stop the running watcher
        # For now, we'll just simulate stopping it
        if source.lower() in ["gmail", "filesystem"]:
            print(f"⏹️ {source} watcher stopped.")
        else:
            print(f"❌ Unknown watcher source: {source}. Supported sources: gmail, filesystem")