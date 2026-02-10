# Usage Guide: AI Employee Foundation

## Getting Started

### Prerequisites
- Python 3.13+ installed
- Gmail account with IMAP enabled
- Claude Code access
- Git for version control

### Initial Setup
1. Clone the repository
2. Create a virtual environment
3. Install dependencies
4. Configure environment variables

### Vault Initialization
Run the following command to create the Obsidian vault structure:
```bash
python -m src.cli.main vault init
```

## Core Workflows

### 1. Email-to-Action Workflow
1. An email arrives in your monitored Gmail account
2. The Gmail Watcher detects the email and creates an action file in `Needs_Action/`
3. The Claude Service processes the action file and creates a Plan.md in `Plans/`
4. If approval is required, an approval file is created in `Pending_Approval/`
5. Move the file to `Approved/` to execute the plan
6. The action is executed (in dry-run mode by default)
7. The file is moved to `Done/` and metrics are updated

### 2. Manual Action Creation
1. Create a YAML action file in `Needs_Action/` with the required fields
2. Follow the same processing flow as email-generated actions

### 3. Plan Review and Approval
1. Review the generated Plan.md file in `Plans/`
2. If manual approval is required, find the approval file in `Pending_Approval/`
3. Move the file to `Approved/` to execute or `Rejected/` to skip
4. Monitor the execution in logs

## Configuration

### Environment Variables
Set these in your `.env` file:
- `GMAIL_CLIENT_ID`: Your Gmail client ID
- `GMAIL_CLIENT_SECRET`: Your Gmail client secret
- `GMAIL_REFRESH_TOKEN`: Your Gmail refresh token
- `VAULT_PATH`: Path to your Obsidian vault (default: ./AI_Employee_Vault)
- `LOG_LEVEL`: Logging level (default: INFO)

### Application Settings
Configure in `config.yaml`:
- Processing intervals
- Approval requirements
- Logging settings
- External service configurations

## Monitoring and Management

### Dashboard
Check `Dashboard.md` in your vault root for:
- Total actions processed
- Pending approvals
- System health status
- Recent activity

### Logs
Monitor system activity in the `logs/` directory:
- `app.log`: Main application logs
- `audit.log`: Security and compliance logs
- `performance.log`: Performance metrics

### CLI Management
Use the CLI for system management:
```bash
# View system stats
python -m src.cli.main vault stats

# Check pending actions
python -m src.cli.main vault pending-actions

# Start the orchestrator
python -m src.cli.main start
```

## Troubleshooting

### Common Issues
1. **Gmail Connection Issues**:
   - Verify OAuth credentials in `.env`
   - Ensure Gmail IMAP is enabled
   - Check internet connectivity

2. **Claude Service Not Responding**:
   - Verify Claude Code is accessible
   - Check Claude configuration
   - Review logs for specific error messages

3. **File Permission Errors**:
   - Ensure the vault directory has proper read/write permissions
   - Check that no other processes are locking vault files

### Debugging Tips
- Enable DEBUG log level for detailed information
- Check the audit logs for security-related issues
- Use the CLI to verify individual components
- Review the Dashboard.md for system health indicators