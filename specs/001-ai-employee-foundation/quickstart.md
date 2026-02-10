# Quickstart Guide: AI Employee Foundation

## Overview
This guide will help you set up the AI Employee Foundation system with Obsidian vault, Gmail watcher, Claude Code integration, and approval workflow.

## Prerequisites
- Python 3.13+ installed
- Gmail account with IMAP enabled
- Claude Code access
- Git for version control
- pip (Python package installer)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Set up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
GMAIL_CLIENT_ID=<your_gmail_client_id>
GMAIL_CLIENT_SECRET=<your_gmail_client_secret>
GMAIL_REFRESH_TOKEN=<your_gmail_refresh_token>
VAULT_PATH=./AI_Employee_Vault
LOG_LEVEL=INFO
```

**Security Note**: Store your `.env` file securely and never commit it to version control.

## Initial Setup

### 1. Create Obsidian Vault
```bash
python -m src.cli.main vault init
```

This will create the vault structure:
```
AI_Employee_Vault/
├── Inbox/
├── Needs_Action/
├── Plans/
├── Pending_Approval/
├── Approved/
├── Done/
└── Dashboard.md
```

### 2. Configure Gmail Integration
Follow the Gmail OAuth setup process:
```bash
python -m src.cli.main config gmail
```

This will guide you through:
- Setting up Google Cloud Project
- Enabling Gmail API
- Obtaining credentials
- Granting required permissions

## Running the System

### 1. Start the Orchestrator
```bash
python -m src.cli.main start
```

This starts:
- Gmail watcher (monitors for new emails)
- Claude Code service (processes action files)
- Approval monitor (watches for approved actions)
- Logging service (records all operations)

### 2. Alternative: Start Individual Components
```bash
# Start only the watcher
python -m src.cli.main watch start

# Start only the Claude processor
python -m src.cli.main claude start
```

## Demo Workflow

### 1. Receive an Email
Send an email to your monitored Gmail account with a subject like "Meeting Request: Project Discussion" to trigger the workflow.

### 2. Action File Creation
The Gmail watcher will detect the email and create an action file in `AI_Employee_Vault/Needs_Action/`:
```yaml
id: 123e4567-e89b-12d3-a456-426614174000
type: meeting_request
priority: medium
context:
  sender: sender@example.com
  subject: Meeting Request: Project Discussion
  snippet: Please schedule a meeting for next week...
created_at: "2026-02-06T10:00:00Z"
source: gmail
```

### 3. Claude Processing
The Claude Code service reads the action file and creates a Plan.md file in `AI_Employee_Vault/Plans/`:
```markdown
---
action_id: 123e4567-e89b-12d3-a456-426614174000
status: planned
created_at: "2026-02-06T10:01:00Z"
updated_at: "2026-02-06T10:01:00Z"
estimated_duration: 15
dependencies: []
---

# Objectives
Respond to meeting request with available time slots

# Steps
1. Check calendar for available time slots next week
2. Prepare response email draft with 3 time slot options
3. Send draft for user approval

# Resources
- Calendar integration
- Email templates

# Success Criteria
Meeting scheduled or declined with appropriate response
```

### 4. Approval Process
If the plan requires approval, an approval file is created in `AI_Employee_Vault/Pending_Approval/`. Move the file to `AI_Employee_Vault/Approved/` to execute the plan.

### 5. Action Execution
After approval, the MCP stub executes the plan (in dry-run mode, it logs "WOULD SEND:" actions).

## Monitoring and Management

### 1. Check Dashboard
View `AI_Employee_Vault/Dashboard.md` for system status and metrics.

### 2. View Logs
Check the logs directory for operation details:
```bash
tail -f logs/app.log
```

### 3. Vault Management Commands
```bash
# Check vault integrity
python -m src.cli.main vault check

# View pending actions
python -m src.cli.main vault pending-actions

# View system stats
python -m src.cli.main vault stats
```

## Security Best Practices

### Credential Management
- Store credentials in encrypted form using OS keyring or encrypted .env files
- Use restrictive file permissions (600) for credential files
- Regularly rotate credentials
- Never share credentials between systems

### Vault Security
- Regularly backup your vault directory
- Use file system permissions to restrict access to vault
- Monitor file access logs for unauthorized access attempts

## Troubleshooting

### Gmail Connection Issues
- Verify OAuth credentials in `.env`
- Ensure Gmail IMAP is enabled
- Check internet connectivity
- Verify that the credentials.key and token.pickle files have proper permissions

### Claude Service Not Responding
- Verify Claude Code is accessible
- Check Claude configuration
- Review logs for specific error messages

### File Permission Errors
- Ensure the vault directory has proper read/write permissions
- Check that no other processes are locking vault files
- Verify that credential files have restrictive permissions (600)

### Authentication Failures
- Regenerate credentials if they've expired
- Verify that the encryption key is available
- Check that the token.pickle file hasn't been corrupted

## Next Steps

1. Customize action types and processing rules
2. Add additional watcher sources (filesystem, WhatsApp, etc.)
3. Extend Claude prompts for domain-specific actions
4. Enhance approval workflow for your specific use cases

## Stopping the System
Press `Ctrl+C` to gracefully shut down all services.

## Validation Checklist

Before deploying to production, ensure:

- [ ] Environment variables are properly set and secured
- [ ] Credentials are encrypted and have proper file permissions
- [ ] Vault directory is backed up regularly
- [ ] Logging is configured to capture all required audit information
- [ ] All services start without errors
- [ ] Demo workflow completes successfully
- [ ] Security best practices are implemented