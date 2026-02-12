# Local Monitoring System Setup

## Overview
This document explains how to set up and use the local monitoring system for your AI Employee Foundation.

## Prerequisites
- Python 3.8 or higher
- Virtual environment with required packages installed
- AI_Employee_Vault folder structure

## Quick Start

### Method 1: Using the Batch Script (Windows)
Double-click on `start_monitoring.bat` or run from command prompt:
```cmd
start_monitoring.bat
```

### Method 2: Manual Start
1. Activate virtual environment:
   ```cmd
   venv\Scripts\activate
   ```

2. Run the monitoring script:
   ```cmd
   python src/monitor.py
   ```

3. To stop monitoring, press `Ctrl+C`

## System Components

### Folder Structure
```
AI_Employee_Vault/
├── Inbox/              # Files to be monitored (input)
├── Processed/          # Files that have been processed (output)
├── Pending_Approval/   # Files requiring human approval
├── Approved/           # Approved actions for execution
├── Done/               # Completed actions
├── Needs_Action/       # Tasks needing action
├── Plans/              # Generated plans
└── System_Log/         # Event logs
    └── events.log      # Log of detected events
```

### Monitoring Script (`src/monitor.py`)
- Continuously monitors the Inbox folder
- Logs events to System_Log/events.log
- Moves processed files to Processed folder
- Handles errors safely and avoids duplicates

## How It Works

1. **File Detection**: The system watches for new files in the Inbox folder
2. **Event Logging**: Each detected file is logged in System_Log/events.log
3. **File Processing**: Files are moved from Inbox to Processed folder
4. **Claude Code Integration**: Claude Code can monitor:
   - System_Log/events.log for new events
   - Pending_Approval folder for files requiring attention

## Testing the System

Run the setup verification script:
```cmd
python setup_monitoring.py
```

This will:
1. Create a test file in the Inbox
2. Wait for the monitoring system to process it
3. Verify that the event was logged and file moved

## Integration with Claude Code

Claude Code can detect new actions by:

### Method 1: Event Log Monitoring
Periodically check `AI_Employee_Vault/System_Log/events.log` for new entries:
```
2024-01-15 14:30:25 - Detected new file: task_001.txt
2024-01-15 14:30:26 - Moved task_001.txt to Processed folder as task_001.txt
```

### Method 2: Folder Monitoring
Monitor `AI_Employee_Vault/Pending_Approval/` for files that require attention.

## Troubleshooting

### Issue: "No module named watchdog"
**Solution**: Install required packages:
```cmd
pip install -r requirements.txt
```

### Issue: Permission denied errors
**Solution**: Ensure the script has write permissions to AI_Employee_Vault directories.

### Issue: Monitoring system not detecting files
**Solution**:
1. Ensure the monitoring script is running
2. Check that files are being placed directly in Inbox (not subfolders)
3. Verify the System_Log directory exists and is writable

## Customization

You can modify the monitoring behavior by editing `src/monitor.py`:
- Adjust folder paths (lines 15-19)
- Modify logging format (lines 30-35)
- Change file processing logic (lines 43-64)