# Using the Local Monitoring System

This guide explains how to use the local monitoring system we've created.

## Prerequisites

- Python 3.8 or higher
- Virtual environment activated
- Required packages installed (`pip install -r requirements.txt`)

## Starting the Monitoring System

1. Open a terminal/command prompt
2. Navigate to the project directory
3. Activate the virtual environment:
   ```bash
   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

4. Run the monitoring script:
   ```bash
   python src/monitor.py
   ```

5. The system will output:
   ```
   Starting local-first monitoring system...
   Monitoring: AI_Employee_Vault/Inbox
   Logging to: AI_Employee_Vault/System_Log/events.log
   Press Ctrl+C to stop monitoring
   ```

## Testing the System

To test that the system is working correctly:

1. Run the test script in another terminal:
   ```bash
   python tests/test_monitoring_system.py
   ```

2. This will create a test file in the Inbox folder and verify that:
   - The monitoring system detects the file
   - The file is moved to the Processed folder
   - The event is logged in the events.log file

## How It Works

### File Detection
The system uses the `watchdog` library to monitor the Inbox folder for new files. When a new file is created:

1. The event is logged in `AI_Employee_Vault/System_Log/events.log`
2. The file is moved to `AI_Employee_Vault/Processed/`
3. If there's a naming conflict, a number is appended (e.g., `file_1.txt`, `file_2.txt`)

### Event Logging
Each event is timestamped and logged with details about what happened:
```
2024-01-15 14:30:25 - Detected new file: task_001.txt
2024-01-15 14:30:26 - Moved task_001.txt to Processed folder as task_001.txt
```

### Claude Code Integration
Claude Code can monitor for changes in two ways:

1. **Event Log Monitoring**: Check `AI_Employee_Vault/System_Log/events.log` for new entries
2. **Folder Monitoring**: Watch `AI_Employee_Vault/Pending_Approval/` for new files

## Stopping the System

To stop the monitoring system, press `Ctrl+C` in the terminal where it's running. The system will gracefully shut down:

```
^C
Stopping monitoring system...
```

## Troubleshooting

### Issue: "No module named watchdog"
**Solution**: Install the required packages:
```bash
pip install -r requirements.txt
```

### Issue: Permission denied when moving files
**Solution**: Ensure the script has write permissions to the AI_Employee_Vault directories.

### Issue: Events not appearing in log
**Solution**: Check that:
1. The monitoring system is running
2. Files are being created in the Inbox folder (not a subfolder)
3. The System_Log directory exists and is writable

## Customization

You can modify the monitoring behavior by editing `src/monitor.py`:

- Change folder paths (lines 12-16)
- Adjust logging format (lines 25-30)
- Modify file processing logic (lines 40-55)

## Integration with Existing Systems

The monitoring system is designed to work alongside your existing AI Employee Foundation setup:

1. Files can still be placed in Inbox by other processes (like the Gmail watcher)
2. Claude Code can monitor for events without using the Claude API
3. The system maintains the same folder structure and conventions