#!/usr/bin/env python3
"""
Local-first monitoring system for AI Employee Foundation.
Monitors Inbox folder for new files and logs events.
"""

import os
import time
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
BASE_PATH = "AI_Employee_Vault"
INBOX_PATH = os.path.join(BASE_PATH, "Inbox")
PROCESSED_PATH = os.path.join(BASE_PATH, "Processed")
LOG_PATH = os.path.join(BASE_PATH, "System_Log")
EVENT_LOG_FILE = os.path.join(LOG_PATH, "events.log")

class InboxHandler(FileSystemEventHandler):
    """Handler for file system events in Inbox folder."""

    def __init__(self):
        # Ensure directories exist
        os.makedirs(PROCESSED_PATH, exist_ok=True)
        os.makedirs(LOG_PATH, exist_ok=True)

        # Setup logging
        logging.basicConfig(
            filename=EVENT_LOG_FILE,
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self.process_new_file(event.src_path)

    def process_new_file(self, file_path):
        """Process a newly detected file."""
        try:
            file_name = os.path.basename(file_path)
            self.logger.info(f"Detected new file: {file_name}")

            # Move file to Processed folder
            processed_file_path = os.path.join(PROCESSED_PATH, file_name)

            # Handle potential name conflicts
            counter = 1
            base_name, ext = os.path.splitext(file_name)
            while os.path.exists(processed_file_path):
                new_name = f"{base_name}_{counter}{ext}"
                processed_file_path = os.path.join(PROCESSED_PATH, new_name)
                counter += 1

            os.rename(file_path, processed_file_path)
            self.logger.info(f"Moved {file_name} to Processed folder as {os.path.basename(processed_file_path)}")

        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")

def main():
    """Main monitoring function."""
    print("Starting local-first monitoring system...")
    print(f"Monitoring: {INBOX_PATH}")
    print(f"Logging to: {EVENT_LOG_FILE}")
    print("Press Ctrl+C to stop monitoring")

    # Create handler and observer
    event_handler = InboxHandler()
    observer = Observer()
    observer.schedule(event_handler, INBOX_PATH, recursive=False)

    # Start monitoring
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitoring system...")
        observer.stop()
    finally:
        observer.join()

if __name__ == "__main__":
    main()