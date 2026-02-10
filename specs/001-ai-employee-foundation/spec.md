# Feature Specification: AI Employee Foundation

**Feature Branch**: `001-ai-employee-foundation`
**Created**: 2026-02-06
**Status**: Draft
**Input**: User description: "Personal AI Employee Hackathon — Bronze Tier (Foundation)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Local Obsidian Vault Setup (Priority: P1)

An intermediate developer wants to set up a local-first AI employee system using Obsidian as a knowledge vault. The user needs a properly structured vault with standardized folder organization that supports AI automation workflows.

**Why this priority**: The vault structure forms the foundation for all subsequent AI automation features. Without this structure, no other functionality can work.

**Independent Test**: The vault can be created with required folder structure (/Inbox, /Needs_Action, /Plans, /Pending_Approval, /Approved, /Done) and can be opened in Obsidian. The Dashboard.md file is initialized and accessible.

**Acceptance Scenarios**:

1. **Given** a fresh installation, **When** the user runs the setup script, **Then** an Obsidian vault with correct folder structure is created
2. **Given** the vault exists with proper structure, **When** the user opens it in Obsidian, **Then** all folders are visible and Dashboard.md displays initial content

---

### User Story 2 - Watcher Implementation (Priority: P2)

A developer wants to monitor external inputs (like Gmail) and automatically create action files in the /Needs_Action folder. The user needs a working watcher that detects relevant events and creates structured action files.

**Why this priority**: This provides the input mechanism for the AI automation system. Without a working input source, the Claude Code loop cannot function.

**Independent Test**: The watcher can be started and listens for the selected input source (Gmail/FileSystem/WhatsApp). When an event occurs, a properly formatted action file appears in /Needs_Action.

**Acceptance Scenarios**:

1. **Given** the watcher is configured and running, **When** a monitored event occurs (email received, file changes), **Then** a corresponding action file is created in /Needs_Action
2. **Given** an action file exists in /Needs_Action, **When** the system processes it, **Then** it contains the necessary context for Claude Code to read and act upon

---

### User Story 3 - Claude Code Read-Write Loop (Priority: P3)

A user wants Claude Code to read action files from /Needs_Action and create Plan.md files that outline how to handle the action. The system should demonstrate basic AI reasoning capabilities.

**Why this priority**: This implements the core AI decision-making component of the system. It demonstrates Claude Code's ability to interpret and plan responses to actions.

**Independent Test**: Claude Code can read an action file from /Needs_Action and produce a structured Plan.md file with appropriate content.

**Acceptance Scenarios**:

1. **Given** an action file exists in /Needs_Action, **When** Claude Code processes it, **Then** a corresponding Plan.md file is created in the appropriate location
2. **Given** Claude Code is prompted with an action, **When** it generates a plan, **Then** the plan contains specific, actionable steps

---

### User Story 4 - Human-in-the-Loop Approval System (Priority: P4)

A user wants to ensure all automated actions require human approval before execution. The system should create approval files in /Pending_Approval and only execute actions after they are moved to /Approved.

**Why this priority**: This provides safety and control for the AI automation system, ensuring humans remain in the loop for important decisions.

**Independent Test**: An approval file can be created in /Pending_Approval, and when moved to /Approved, the corresponding action is executed safely.

**Acceptance Scenarios**:

1. **Given** an action is ready for approval, **When** the system creates an approval file, **Then** it appears in /Pending_Approval folder
2. **Given** an approval file exists in /Pending_Approval, **When** it's moved to /Approved, **Then** the corresponding action is executed

---

### Edge Cases

- What happens when the watcher receives malformed input data?
- How does the system handle corrupted action files in the vault?
- What occurs when multiple action files are created simultaneously?
- How does the system behave when Claude Code cannot generate a suitable plan for an action?
- What happens when an approval file is deleted from /Pending_Approval instead of being approved?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST create a properly structured Obsidian vault with /Inbox, /Needs_Action, /Plans, /Pending_Approval, /Approved, and /Done folders
- **FR-002**: System MUST initialize Dashboard.md with basic statistics and status information
- **FR-003**: User MUST be able to run a Gmail Watcher that monitors external events
- **FR-004**: Watcher MUST write structured action files to the /Needs_Action folder when relevant events occur
- **FR-005**: Claude Code MUST read action files from /Needs_Action and generate corresponding Plan.md files
- **FR-006**: System MUST create approval files in /Pending_Approval for any proposed actions
- **FR-007**: System MUST only execute approved actions after files are moved from /Pending_Approval to /Approved
- **FR-008**: System MUST implement basic MCP stub functionality for dry-run action execution (logging "would send" instead of sending)
- **FR-009**: System MUST maintain basic logging of all operations and events
- **FR-010**: System MUST provide a CLI/start script to launch both the orchestrator and watcher components
- **FR-011**: System MUST include unit tests for watcher and vault CRUD operations
- **FR-012**: System MUST store all secrets outside the vault (using .env or OS keyring)

### Key Entities

- **Action File**: A structured document representing a task that needs to be processed by the AI employee; see data-model.md for complete specification including fields, validation rules, and lifecycle
- **Plan File**: A structured document created by Claude Code outlining how to handle a specific action; see data-model.md for complete specification including frontmatter fields, body sections, and lifecycle
- **Approval File**: A document that represents a proposed action requiring human approval before execution; acts as a gatekeeping mechanism in Markdown format with action details and checkboxes for approval
- **Dashboard**: A central information hub displaying system status, statistics, and current tasks in various states, including task counts by status, recent activity log, and system health indicators

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Obsidian vault with all required folder structure is created within 2 minutes of running setup script on a standard laptop with 8GB+ RAM
- **SC-002**: Watcher successfully detects and writes at least one action file to /Needs_Action within 5 minutes of configuration under normal network conditions
- **SC-003**: Claude Code can read an action file and generate a Plan.md file within 30 seconds under normal system load
- **SC-004**: At least 80% of attempted actions successfully pass through the approval workflow over a 24-hour period
- **SC-005**: Basic logging system records all major operations with timestamps and status
- **SC-006**: CLI/start script successfully launches both orchestrator and watcher components without errors
- **SC-007**: Unit tests achieve at least 70% code coverage for watcher and vault operations
- **SC-008**: System demonstrates safe operation by not executing any unauthorized actions

### Constitutional Compliance

- **CC-001**: Local-First Architecture - All data processing prioritizes local computation with privacy as fundamental requirement
- **CC-002**: Multi-Domain Integration - Cross-domain functionality operates seamlessly across Personal, Business, and Research domains
- **CC-003**: Accuracy and Reproducibility - All automated actions maintain comprehensive logging and traceable audit trails
- **CC-004**: Autonomy with Human-in-the-Loop - Systems escalate to human oversight when encountering ambiguous situations
- **CC-005**: Traceable Automation Logic - Every decision maintains sufficient context to reproduce sequence of events
- **CC-006**: Secure Credential Management - All credentials stored encrypted with secure vault mechanisms and zero plaintext credentials

## Clarifications

### Session 2026-02-06

- Q: Which specific watcher should be implemented as the primary input mechanism for the Bronze Tier? → A: Gmail Watcher
- Q: What should be the format and essential fields of the action files created by the watcher? → A: YAML format with type, priority, and context fields
- Q: What should be the structure and essential components of the Plan.md files generated by Claude Code? → A: Markdown with sections for objectives, steps, resources, and success criteria
- Q: What should be the required content and format of the approval files in the approval workflow? → A: Markdown with action details and checkboxes for approval
- Q: What specific statistics and status information should be displayed on the Dashboard? → A: Task counts by status, recent activity log, and system health indicators
