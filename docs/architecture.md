# Architecture Documentation: AI Employee Foundation

## Overview

The AI Employee Foundation implements a local-first automation system centered around an Obsidian vault. The system includes a Gmail Watcher to monitor emails and create action files, Claude Code integration to process these actions and generate Plan.md files, and a human-in-the-loop approval system.

## System Components

### 1. Vault System
- **Purpose**: Centralized file-based storage using Obsidian vault structure
- **Folders**:
  - `Inbox/`: Initial input files
  - `Needs_Action/`: Action files awaiting processing
  - `Plans/`: Generated plans from Claude Code
  - `Pending_Approval/`: Items requiring human approval
  - `Approved/`: Approved items ready for execution
  - `Done/`: Completed items
- **Dashboard.md**: Real-time system metrics and status

### 2. Gmail Watcher
- **Purpose**: Monitors Gmail account for new emails
- **Triggers**: Specific email subjects or content patterns
- **Output**: Creates action files in `Needs_Action/` folder
- **Authentication**: OAuth2 with secure credential storage

### 3. Claude Service
- **Purpose**: Processes action files and generates structured Plan.md files
- **Input**: Action files from `Needs_Action/` folder
- **Output**: Plan.md files with objectives, steps, resources, and success criteria
- **Processing**: AI-driven analysis and plan generation

### 4. Approval System
- **Purpose**: Human-in-the-loop validation for sensitive actions
- **Workflow**: Creates approval files in `Pending_Approval/`, moved to `Approved/` by user
- **Safety**: Dry-run execution with "would send" logging before real actions
- **Audit Trail**: Complete logging of all approval decisions

### 5. Orchestrator
- **Purpose**: Coordinates all system components
- **Responsibilities**: Starts/stops services, manages file monitoring, handles state transitions
- **Monitoring**: Tracks system health and performance metrics

## Data Flow

1. **Email Detection**: Gmail Watcher detects relevant emails
2. **Action Creation**: Creates YAML action files in `Needs_Action/`
3. **Plan Generation**: Claude Service processes action files and creates Plan.md
4. **Approval Check**: Determines if plan requires human approval
5. **Execution**: Approved plans are executed (dry-run by default)
6. **Completion**: Moves files to appropriate completion folders
7. **Metrics Update**: Updates Dashboard.md with latest metrics

## Security & Privacy

- Local-first architecture keeps data on user's machine
- Encrypted credential storage using OS keyring or secure .env files
- OAuth2 authentication for external services
- Comprehensive audit logging for all automated actions
- Dry-run mode prevents unintended external communications

## Configuration

- `config.yaml`: Application-wide settings
- `.env`: Sensitive environment variables
- Per-component configuration files in `src/config/`