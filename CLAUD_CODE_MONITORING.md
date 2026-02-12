# Claude Code Monitoring System

## Overview
This document explains how Claude Code can monitor the local AI Employee Foundation system without using the Claude API. The monitoring system uses local file system monitoring to detect new tasks and files.

## How It Works

### 1. Event Log Monitoring
Claude Code monitors `AI_Employee_Vault/System_Log/events.log` for new entries:
- Each line represents a detected file or action
- Timestamped entries show when files were processed
- Claude Code parses these entries to become aware of new tasks

### 2. Pending Approval Folder Monitoring
Claude Code monitors `AI_Employee_Vault/Pending_Approval/` for files requiring review:
- New files are detected automatically
- File contents are read for context
- Claude Code prepares for Plan.md generation

### 3. Awareness Simulation
Instead of making API calls, Claude Code simulates awareness by:
- Logging awareness events to `AI_Employee_Vault/System_Log/claude_awareness.log`
- Preparing for local processing of tasks
- Generating plans and actions based on detected files

## System Components

### Main Monitoring Script
`src/claude_code_monitor.py` - The core monitoring system that:
- Watches event logs for new entries
- Monitors Pending_Approval folder for new files
- Parses events to extract file information
- Simulates Claude Code awareness without API calls

### Startup Scripts
- `start_claude_monitor.bat` - Windows startup script
- `start_claude_monitor.sh` - Linux/macOS startup script

## Event Log Format

Entries in `events.log` follow this format:
```
YYYY-MM-DD HH:MM:SS - Message
```

Example entries:
```
2026-02-11 10:04:37 - Detected new file: task_001.txt
2026-02-11 10:04:37 - Moved task_001.txt to Processed folder as task_001.txt
```

## Claude Code Awareness Process

When a new event is detected:

1. **Event Detection**: New log entry or file detected
2. **Parsing**: Extract timestamp, filename, and action
3. **Awareness**: Claude Code becomes aware of the new task
4. **Processing Preparation**: System prepares for Plan.md generation
5. **Logging**: Awareness is logged to claude_awareness.log

## Integration Points

### For Plan Generation
When Claude Code becomes aware of a new task:
- Read the file content from Inbox or Pending_Approval
- Generate a Plan.md in the Plans folder
- Place the plan where it can be reviewed and approved

### For Action Processing
When files are moved to Approved folder:
- Claude Code can process approved actions
- Execute the planned tasks
- Move completed actions to Done folder

## Running the System

### Method 1: Using Startup Scripts
```cmd
# Windows
start_claude_monitor.bat

# Linux/macOS
./start_claude_monitor.sh
```

### Method 2: Manual Start
```cmd
# Activate virtual environment
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/macOS

# Run the monitoring script
python src/claude_code_monitor.py
```

## Sample Output

When the system detects new events:
```
🤖 Claude Code Monitoring System Started
==================================================
📁 Monitoring event log: AI_Employee_Vault/System_Log/events.log
📁 Monitoring folder: AI_Employee_Vault/Pending_Approval
⏱️  Check interval: 3 seconds
🛑 Press Ctrl+C to stop monitoring

🤖 Claude Code Awareness: New event detected
   📅 Timestamp: 2026-02-11 10:04:37
   📄 Message: Detected new file: task_001.txt
   📁 File: task_001.txt
   🔧 Preparing for Plan.md generation...
   📝 File 'task_001.txt' registered for processing
```

## Customization

You can modify the monitoring behavior by editing `src/claude_code_monitor.py`:

- Adjust check interval (line 127)
- Modify awareness simulation logic (lines 85-100)
- Change log parsing (lines 100-120)
- Add custom processing logic

## Error Handling

The system includes robust error handling:
- Graceful handling of missing files/directories
- Continued operation despite individual file errors
- Detailed error logging for troubleshooting
- Safe duplicate detection to prevent repeated processing

## Requirements

All requirements are met:
- ✅ Fully local-first operation
- ✅ No Claude API or cloud dependencies
- ✅ Continuous monitoring
- ✅ Safe error handling
- ✅ Duplicate prevention
- ✅ Timestamped event logging