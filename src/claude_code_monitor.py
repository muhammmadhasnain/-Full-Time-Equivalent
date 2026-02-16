#!/usr/bin/env python3
"""
Claude Code Monitoring System
Monitors local folders and event logs for new tasks and generates plans using Claude API.
"""

import os
import time
import json
import re
from datetime import datetime
from pathlib import Path
import sys

# Add the src directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from services.claude_service import ClaudeService
from models.action_file import ActionFile
from models.plan_file import PlanFile

class ClaudeCodeMonitor:
    """Claude Code monitoring system for local-first automation."""

    def __init__(self):
        # Configuration
        self.base_path = "AI_Employee_Vault"
        self.inbox_path = os.path.join(self.base_path, "Inbox")
        self.pending_approval_path = os.path.join(self.base_path, "Pending_Approval")
        self.plans_path = os.path.join(self.base_path, "Plans")
        self.needs_action_path = os.path.join(self.base_path, "Needs_Action")
        self.system_log_path = os.path.join(self.base_path, "System_Log")
        self.events_log_file = os.path.join(self.system_log_path, "events.log")

        # Tracking variables
        self.last_log_position = 0
        self.processed_events = set()
        self.detected_files = {}

        # Initialize Claude Service
        try:
            self.claude_service = ClaudeService()
            print("✅ Claude Service initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing Claude Service: {e}")
            self.claude_service = None

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.base_path,
            self.inbox_path,
            self.pending_approval_path,
            self.plans_path,
            self.needs_action_path,
            self.system_log_path
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def monitor_event_log(self):
        """Monitor the event log for new entries."""
        if not os.path.exists(self.events_log_file):
            return []

        try:
            with open(self.events_log_file, 'r') as f:
                # Move to the last read position
                f.seek(self.last_log_position)

                # Read new content
                new_content = f.read()

                # Update last position
                self.last_log_position = f.tell()

                # Parse new events
                if new_content:
                    events = new_content.strip().split('\n')
                    return [event for event in events if event and event not in self.processed_events]
        except Exception as e:
            print(f"❌ Error reading event log: {e}")

        return []

    def monitor_pending_approval_folder(self):
        """Monitor the Pending_Approval folder for new files."""
        if not os.path.exists(self.pending_approval_path):
            return []

        try:
            current_files = set(os.listdir(self.pending_approval_path))
            new_files = current_files - set(self.detected_files.keys())

            # Update tracked files
            for file in current_files:
                file_path = os.path.join(self.pending_approval_path, file)
                if os.path.isfile(file_path):
                    self.detected_files[file] = os.path.getmtime(file_path)

            return list(new_files)
        except Exception as e:
            print(f"❌ Error reading Pending_Approval folder: {e}")
            return []

    def parse_event(self, event_line):
        """Parse an event log entry to extract file information."""
        try:
            # Extract timestamp and message
            timestamp_str = event_line[:19]  # YYYY-MM-DD HH:MM:SS
            message = event_line[22:]  # Skip timestamp and " - "

            # Parse timestamp
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

            # Extract filename if present
            filename = None
            if "Detected new file:" in message:
                filename = message.replace("Detected new file: ", "").strip()
            elif "Moved" in message and "to Processed folder" in message:
                # Extract original filename from move message
                match = re.search(r"Moved (.+?) to Processed folder", message)
                if match:
                    filename = match.group(1)

            return {
                "timestamp": timestamp,
                "message": message,
                "filename": filename,
                "raw": event_line
            }
        except Exception as e:
            print(f"❌ Error parsing event: {e}")
            return {"raw": event_line}

    def process_new_event(self, event_line):
        """Process a new event from the log."""
        # Mark as processed to avoid duplicates
        self.processed_events.add(event_line)

        # Parse the event
        event_data = self.parse_event(event_line)

        print(f"Claude Code Awareness: New event detected")
        print(f"   Timestamp: {event_data.get('timestamp', 'Unknown')}")
        print(f"   Message: {event_data.get('message', 'Unknown')}")

        if event_data.get('filename'):
            print(f"   File: {event_data['filename']}")

            # Simulate Claude Code awareness (no API call)
            self.simulate_claude_awareness(event_data['filename'], event_data['message'])

        print()

    def process_pending_file(self, filename):
        """Process a new file in Pending_Approval."""
        print(f"Claude Code Awareness: New pending file detected")
        print(f"   File: {filename}")

        file_path = os.path.join(self.pending_approval_path, filename)

        try:
            # Read file content for context
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"   Content preview: {preview}")

            # Simulate Claude Code awareness (no API call)
            self.simulate_claude_awareness(filename, "Pending approval file", content)

        except Exception as e:
            print(f"   Warning: Could not read file content: {e}")
            self.simulate_claude_awareness(filename, "Pending approval file")

        print()

    def simulate_claude_awareness(self, filename, event_type, content=None):
        """
        Simulate Claude Code becoming aware of a new file or event.
        This is where you would normally make an API call or trigger processing.
        """
        print(f"   Preparing for Plan.md generation...")
        print(f"   File '{filename}' registered for processing")

        # In a real implementation, this would:
        # 1. Trigger analysis of the file content
        # 2. Generate a Plan.md based on the task
        # 3. Place the plan in the Plans folder
        # 4. Optionally move to Needs_Action or Pending_Approval

        # For now, we'll just log that Claude Code is aware
        awareness_log = os.path.join(self.system_log_path, "claude_awareness.log")
        with open(awareness_log, 'a') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp} - Claude Code aware of: {filename} ({event_type})\n")

    def monitor(self, interval=3):
        """Continuously monitor for new events and files."""
        print("Claude Code Monitoring System Started")
        print("=" * 50)
        print(f"Monitoring event log: {self.events_log_file}")
        print(f"Monitoring folder: {self.pending_approval_path}")
        print(f"Check interval: {interval} seconds")
        print("Press Ctrl+C to stop monitoring")
        print()

        try:
            while True:
                # Check for new events in log
                new_events = self.monitor_event_log()
                for event in new_events:
                    self.process_new_event(event)

                # Check for new files in Pending_Approval
                new_pending_files = self.monitor_pending_approval_folder()
                for filename in new_pending_files:
                    self.process_pending_file(filename)

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\nClaude Code Monitoring Stopped")
            print("Goodbye!")

def main():
    """Main function to start Claude Code monitoring."""
    monitor = ClaudeCodeMonitor()

    # Show initial status
    print("Claude Code Local Monitoring Setup")
    print("=" * 40)

    # Verify directories
    print("Checking directories...")
    print(f"   Base path: {monitor.base_path}")
    print(f"   Inbox: {monitor.inbox_path}")
    print(f"   Pending Approval: {monitor.pending_approval_path}")
    print(f"   System Log: {monitor.system_log_path}")

    # Check current status
    if os.path.exists(monitor.events_log_file):
        print(f"Event log found: {monitor.events_log_file}")
        with open(monitor.events_log_file, 'r') as f:
            content = f.read()
            if content:
                print(f"   Current entries: {len(content.split(chr(10)))}")
            else:
                print("   Event log is currently empty")
    else:
        print("Event log will be created when first event occurs")

    # Check Pending_Approval folder
    try:
        files = os.listdir(monitor.pending_approval_path)
        print(f"Pending_Approval folder has {len(files)} files")
    except:
        print("Pending_Approval folder is currently empty")

    print()
    print("Starting continuous monitoring...")
    monitor.monitor()

if __name__ == "__main__":
    main()