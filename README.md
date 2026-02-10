# AI Employee Foundation

The AI Employee Foundation implements a local-first automation system centered around an Obsidian vault. The system includes a Gmail Watcher to monitor emails and create action file, Claude Code integration to process these actions and generate Plan.md files, and a human-in-the-loop approval system.

## Features

- Local-first automation system with Obsidian vault integration
- Gmail Watcher to monitor emails and create action files
- Claude Code integration to process actions and generate plans
- Human-in-the-loop approval system for safe automation
- Comprehensive logging and audit trails

## Prerequisites

- Python 3.13+ installed
- Gmail account with IMAP enabled
- Claude Code access
- Git for version control

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

## Setup and Usage Instructions

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

### 3. Start the Orchestrator
```bash
python -m src.cli.main start
```

This starts:
- Gmail watcher (monitors for new emails)
- Claude Code service (processes action files)
- Approval monitor (watches for approved actions)
- Logging service (records all operations)

### 4. Using the System
- The Gmail watcher will automatically detect relevant emails and create action files in the `Needs_Action/` folder
- Claude Code will process these action files and create Plan.md files in the `Plans/` folder
- If an action requires approval, an approval file will be created in `Pending_Approval/`
- Move files to the `Approved/` folder to execute them (dry-run mode by default)
- Completed actions are moved to the `Done/` folder
- Check `Dashboard.md` for system metrics and status

### 5. Management Commands
```bash
# Check vault integrity
python -m src.cli.main vault check

# View pending actions
python -m src.cli.main vault pending-actions

# View system stats
python -m src.cli.main vault stats

# Stop/start individual components
python -m src.cli.main watch start
python -m src.cli.main watch stop
```

For more detailed instructions, see the [Quickstart Guide](specs/001-ai-employee-foundation/quickstart.md) and our [documentation](docs/).

## Documentation

- [Architecture](docs/architecture.md) - System architecture and components
- [API Documentation](docs/api.md) - API endpoints and CLI commands
- [Usage Guide](docs/usage.md) - Detailed usage instructions
- [Quickstart Guide](specs/001-ai-employee-foundation/quickstart.md) - Getting started guide

## Architecture

The system follows constitutional principles with:
- Local-first architecture with privacy focus
- Multi-domain integration
- Accuracy and reproducibility
- Autonomy with human-in-the-loop
- Traceable automation logic
- Secure credential management

## Contributing

See the specification documents in the `specs/` directory for detailed information about the architecture and implementation.