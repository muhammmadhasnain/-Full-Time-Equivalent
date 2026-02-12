# Local-First Monitoring System

This document describes the local-first monitoring system that watches for new files in the Inbox folder and logs events for Claude Code to process.

## System Architecture

```
AI_Employee_Vault/
├── Inbox/           # Files to be monitored
├── Processed/       # Files that have been processed
└── System_Log/      # Event logs
    └── events.log   # Log file for detected events
```

## Monitoring Script

The monitoring script (`src/monitor.py`) continuously watches the `/Inbox` folder for new files and:

1. Logs each detected event in `/System_Log/events.log`
2. Moves processed files to `/Processed`
3. Handles errors safely and avoids duplicate processing

## How to Run

1. **Activate virtual environment:**
   ```bash
   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

2. **Run the monitoring script:**
   ```bash
   python src/monitor.py
   ```

3. **Stop monitoring:**
   Press `Ctrl+C` to stop the monitoring process

## How Claude Code Detects Changes

Claude Code should NOT monitor via API. Instead, it should read from:

1. **Event Log Detection:**
   - Claude Code periodically checks `/System_Log/events.log` for new entries
   - New log entries indicate new files were detected and processed
   - Example log entry:
     ```
     2024-01-15 14:30:25 - Detected new file: task_001.txt
     2024-01-15 14:30:26 - Moved task_001.txt to Processed folder as task_001.txt
     ```

2. **Pending Approval Folder:**
   - Alternatively, Claude Code can monitor `/Pending_Approval` for files that require attention
   - This folder can be populated by the monitoring script or other processes

## Requirements

- Python 3.8+
- watchdog library (included in requirements.txt)
- No external APIs or cloud dependencies
- Fully local-first operation

## Features

- Continuous monitoring (watch mode)
- Automatic file detection
- Safe error handling
- Duplicate processing prevention
- Detailed event logging
- No external dependencies