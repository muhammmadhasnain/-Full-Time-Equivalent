#!/usr/bin/env python3
"""
Test script for the local monitoring system.
Creates test files in the Inbox to demonstrate the monitoring system.
"""

import os
import time
import tempfile
from pathlib import Path

def test_monitoring_system():
    """Test the monitoring system by creating a test file in Inbox."""

    # Define paths
    inbox_path = "AI_Employee_Vault/Inbox"
    processed_path = "AI_Employee_Vault/Processed"
    log_path = "AI_Employee_Vault/System_Log/events.log"

    # Ensure directories exist
    os.makedirs(inbox_path, exist_ok=True)
    os.makedirs(processed_path, exist_ok=True)

    print("Testing Local Monitoring System")
    print("=" * 40)
    print(f"Inbox Path: {inbox_path}")
    print(f"Processed Path: {processed_path}")
    print(f"Log Path: {log_path}")
    print()

    # Create a test file
    test_filename = f"test_task_{int(time.time())}.txt"
    test_file_path = os.path.join(inbox_path, test_filename)

    print(f"Creating test file: {test_filename}")

    with open(test_file_path, 'w') as f:
        f.write(f"# Test Task\n\nThis is a test task file created at {time.ctime()}\n")

    print("Test file created. Waiting for monitoring system to process...")
    print("(Make sure the monitoring script is running: python src/monitor.py)")
    print()

    # Wait and check if file was moved
    start_time = time.time()
    timeout = 30  # 30 seconds timeout

    while time.time() - start_time < timeout:
        if not os.path.exists(test_file_path) and os.path.exists(os.path.join(processed_path, test_filename)):
            print("✓ SUCCESS: File was processed and moved to Processed folder")

            # Check if log file exists and has content
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    log_content = f.read()
                    if test_filename in log_content:
                        print("✓ SUCCESS: Event was logged")
                    else:
                        print("⚠ WARNING: Event not found in log")
            else:
                print("⚠ WARNING: Log file not found")

            break
        elif not os.path.exists(test_file_path) and not os.path.exists(os.path.join(processed_path, test_filename)):
            print("⚠ WARNING: File disappeared but not moved to Processed folder")
            break

        time.sleep(2)
    else:
        print(f"⚠ TIMEOUT: File was not processed within {timeout} seconds")
        print("Please ensure the monitoring script is running and working correctly.")

    print()
    print("Test completed.")

if __name__ == "__main__":
    test_monitoring_system()