#!/usr/bin/env python3
"""
Setup script for the local monitoring system.
This script demonstrates how to start the monitoring and test its functionality.
"""

import os
import time
import subprocess
import threading
from pathlib import Path

def create_test_file():
    """Create a test file in the Inbox folder."""
    inbox_path = "AI_Employee_Vault/Inbox"
    os.makedirs(inbox_path, exist_ok=True)

    # Create a timestamped test file
    timestamp = int(time.time())
    test_filename = f"test_task_{timestamp}.txt"
    test_file_path = os.path.join(inbox_path, test_filename)

    with open(test_file_path, 'w') as f:
        f.write(f"# Test Task\n\nThis is a test task file created at {time.ctime()}\n")

    print(f"Created test file: {test_filename}")
    return test_filename

def check_log_for_entry(filename):
    """Check if the event log contains an entry for the given filename."""
    log_path = "AI_Employee_Vault/System_Log/events.log"

    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            content = f.read()
            return filename in content
    return False

def check_file_moved(filename):
    """Check if the file has been moved to the Processed folder."""
    processed_path = os.path.join("AI_Employee_Vault", "Processed", filename)
    return os.path.exists(processed_path)

def main():
    """Main function to demonstrate the monitoring system."""
    print("Setting up local monitoring system...")
    print("=" * 50)

    # Create a test file
    print("1. Creating test file in Inbox...")
    test_filename = create_test_file()

    # Wait a moment for the monitoring system to process the file
    print("2. Waiting for monitoring system to process the file...")
    time.sleep(5)

    # Check if the file was processed
    print("3. Checking results...")
    log_entry_found = check_log_for_entry(test_filename)
    file_moved = check_file_moved(test_filename)

    if log_entry_found and file_moved:
        print("✅ SUCCESS: Monitoring system is working correctly!")
        print(f"   - Event logged for {test_filename}")
        print(f"   - File moved to Processed folder")
    elif log_entry_found:
        print("⚠ PARTIAL SUCCESS: Event was logged but file may not be moved yet")
        print(f"   - Event logged for {test_filename}")
    elif file_moved:
        print("⚠ PARTIAL SUCCESS: File was moved but event may not be logged")
        print(f"   - File moved to Processed folder")
    else:
        print("❌ ISSUE: Monitoring system may not be running")
        print("   Please ensure 'python src/monitor.py' is running in another terminal")

    print("\n" + "=" * 50)
    print("Setup monitoring verification complete!")

if __name__ == "__main__":
    main()