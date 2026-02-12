# Claude Code Integration Guide

This document explains how Claude Code can integrate with the local monitoring system without using the Claude API.

## Integration Methods

### 1. Event Log Monitoring

Claude Code can periodically check the event log at `AI_Employee_Vault/System_Log/events.log` to detect new activities.

**Example log entry:**
```
2024-01-15 14:30:25 - Detected new file: task_001.txt
2024-01-15 14:30:26 - Moved task_001.txt to Processed folder as task_001.txt
```

**Implementation approach:**
1. Read the log file
2. Track the last position you read from
3. Process new entries when detected
4. Take appropriate action based on the event type

### 2. Pending Approval Folder Monitoring

Claude Code can monitor the `AI_Employee_Vault/Pending_Approval/` folder for files that require attention.

**Workflow:**
1. Monitor the folder for new files
2. When a file is detected, process it according to its type
3. Move the file to an appropriate folder after processing (Approved, Done, etc.)

## Implementation Example

See `src/claude_code_detector.py` for an example implementation of how Claude Code can detect and process events.

## Benefits of This Approach

1. **Fully Local-First**: No external APIs or cloud dependencies
2. **Privacy Focused**: All data stays on the local machine
3. **Reliable**: No network connectivity issues
4. **Secure**: No exposure of sensitive data to external services
5. **Efficient**: Direct file system monitoring

## Running the System

1. Start the monitoring script:
   ```bash
   python src/monitor.py
   ```

2. Claude Code can then monitor either:
   - The event log file: `AI_Employee_Vault/System_Log/events.log`
   - The Pending Approval folder: `AI_Employee_Vault/Pending_Approval/`

3. Process events as they occur without needing the Claude API