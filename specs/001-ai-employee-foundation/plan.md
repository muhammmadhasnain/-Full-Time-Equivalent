# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/sp.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The AI Employee Foundation implements a local-first automation system centered around an Obsidian vault. The system includes a Gmail Watcher to monitor emails and create action files, Claude Code integration to process these actions and generate Plan.md files, and a human-in-the-loop approval system. The implementation follows constitutional principles with local-first architecture, traceable automation logic, and secure credential management.

## Technical Context

**Language/Version**: Python 3.13+ with asyncio support
**Primary Dependencies**: google-auth, google-auth-oauthlib, google-auth-httplib2, google-api-python-client, pyyaml, watchdog, python-dotenv
**Storage**: File system-based (Obsidian vault structure)
**Testing**: pytest with coverage reporting
**Target Platform**: Cross-platform (Windows, macOS, Linux)
**Project Type**: Single executable application with daemon components
**Performance Goals**: Action file processing within 30 seconds, Vault operations under 5 seconds
**Constraints**: Local-first operation, offline capability for vault access, minimal external API calls, secure credential handling
**Scale/Scope**: Single user personal automation, up to 1000 actions per month, 100 concurrent vault operations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Local-First Architecture with Privacy Focus
- Data processing prioritizes local computation over cloud services
- Privacy considerations addressed in all design decisions
- Minimal data transmission to external services with strong encryption

### Multi-Domain Integration
- Cross-domain functionality designed with unified interfaces
- Consistent authentication and data models across Personal/Business/Research domains
- Integration points clearly defined and tested

### Accuracy and Reproducibility
- Comprehensive logging and audit trails for all automated actions
- Deterministic automation logic with verifiable outcomes
- Decision-making processes maintain clear auditability

### Autonomy with Human-in-the-Loop
- Automated systems include clear escalation criteria to human oversight
- Graceful degradation mechanisms when autonomy encounters ambiguity
- Well-defined boundaries for autonomous vs. human-required operations

### Traceable Automation Logic
- Complete traceability from triggers to decisions to outcomes
- Sufficient contextual logging to reproduce event sequences
- Audit trails maintained for all automated processes

### Secure Credential Management
- Encrypted credential storage implemented with secure vault mechanisms
- Minimum privilege access patterns followed throughout
- Zero plaintext credentials in code or configuration files

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── action_file.py     # Action file representation
│   ├── plan_file.py       # Plan file representation
│   ├── approval_file.py   # Approval file representation
│   └── vault.py           # Vault structure and operations
├── services/
│   ├── gmail_watcher.py   # Gmail monitoring service
│   ├── claude_service.py  # Claude Code integration service
│   ├── mcp_stub.py        # MCP stub for dry-run actions
│   ├── file_monitor.py    # File system monitoring
│   └── logging_service.py # Structured logging
├── cli/
│   ├── main.py            # Main CLI entry point
│   ├── commands/
│   │   ├── start_cmd.py   # Start orchestrator command
│   │   ├── vault_cmd.py   # Vault management commands
│   │   └── watch_cmd.py   # Watcher control commands
│   └── config.py          # Configuration management
├── lib/
│   ├── utils.py           # Utility functions
│   ├── constants.py       # Application constants
│   └── exceptions.py      # Custom exceptions
└── orchestrator.py        # Main orchestration logic

tests/
├── unit/
│   ├── test_models/
│   ├── test_services/
│   └── test_cli/
├── integration/
│   ├── test_vault_ops.py  # Vault CRUD operations
│   ├── test_watcher.py    # Watcher functionality
│   └── test_claude_loop.py # Claude Code integration
└── contract/
    └── test_api_contracts.py

.env.example               # Environment variables template
config.yaml               # Application configuration template
requirements.txt          # Python dependencies
README.md                 # Setup and usage documentation
```

**Structure Decision**: Single project structure with clear separation of concerns between models, services, CLI components, and utilities. This enables modular development while maintaining simplicity for the local-first architecture.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| External API Dependency (Gmail) | Required for primary watcher functionality | Core feature requirement per spec - cannot implement Gmail watcher without Gmail API |
| Constitutional Exception | Gmail integration violates Local-First principle but is essential for email monitoring use case | Alternative email protocols (POP3, IMAP) still require external connections; local-only solution would severely limit functionality |

## Constitutional Exception Documentation

**Exception Type**: External API Dependency for Essential Functionality
**Justification**: Email monitoring (Gmail) is a core requirement for the AI employee system to function as intended. The system cannot operate without some form of external email access.
**Mitigation Measures**:
- All email content is processed locally after retrieval
- Sensitive data is encrypted when stored locally
- OAuth2 is used for authentication with minimal required scopes
- All credentials are stored securely using OS keyring or .env files
- No email content is transmitted to external services beyond original destination
- User can disable Gmail watcher and use alternative local-only inputs
