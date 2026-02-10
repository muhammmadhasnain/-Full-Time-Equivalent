# Research: AI Employee Foundation

## Decision Points & Rationale

### 1. Watcher Choice: Gmail vs. FileSystem vs. WhatsApp

**Decision**: Gmail Watcher Implementation

**Rationale**:
- Gmail provides structured, rich data ideal for AI processing
- Standardized protocols (IMAP/SMTP) with robust libraries available
- Most commonly used business communication channel
- Supports OAuth2 for secure authentication
- Rich metadata (sender, subject, attachments, timestamps) enhances AI decision-making

**Alternatives Considered**:
- FileSystem Watcher: Less structured data, harder to extract meaningful actions
- WhatsApp Watcher: More complex authentication, restricted by WhatsApp's ToS

### 2. Language and Framework Selection

**Decision**: Python 3.13+ with asyncio for concurrent operations

**Rationale**:
- Excellent ecosystem for file system operations and Gmail integration
- Rich libraries for YAML/Markdown processing
- Strong async support for concurrent watcher and Claude Code operations
- Claude Code integration friendly
- Cross-platform compatibility for local-first architecture

**Alternatives Considered**:
- Node.js: Good for file operations but less ideal for AI interactions
- Go: Excellent concurrency but smaller ecosystem for AI tools

### 3. Plan.md Schema Design

**Decision**: Markdown with structured frontmatter and sections

**Rationale**:
- Integrates seamlessly with Obsidian vault
- Human-readable while maintaining structure
- Supports both markdown formatting and YAML frontmatter
- Easy for Claude Code to generate and parse
- Maintains consistency with constitutional requirement for local-first architecture

**Schema Structure**:
```
---
action_id: [unique identifier]
status: [draft|planned|approved|executed|cancelled]
created_at: [timestamp]
updated_at: [timestamp]
estimated_duration: [minutes]
dependencies: [list of related action IDs]
---

# Objectives
[What needs to be accomplished]

# Steps
[Detailed action steps]

# Resources
[Required tools, files, or information]

# Success Criteria
[How to verify completion]
```

### 4. Logging Strategy and Dashboard.md Updates

**Decision**: Structured logging with rotating log files and aggregated metrics in Dashboard.md

**Rationale**:
- Supports constitutional requirement for traceable automation logic
- Complies with accuracy and reproducibility principles
- Rotating logs prevent storage issues in local-first architecture
- Dashboard metrics provide real-time system visibility
- Aggregated data maintains privacy while showing system health

**Logging Components**:
- Operation logs (timestamp, type, status, details)
- Error logs (exception details, context, remediation suggestions)
- Performance logs (processing times, resource usage)
- Audit logs (user approvals, system actions)

### 5. Dry-run vs. Real Action Handling

**Decision**: MCP stub with "would send" logging pattern

**Rationale**:
- Implements human-in-the-loop safety requirement
- Prevents unintended external communications
- Maintains traceable automation logic
- Supports constitutional requirement for controlled automation
- Allows validation of action execution flow without side effects

**Implementation Pattern**:
- Replace all actual sends/notifications with log entries prefixed "WOULD SEND:"
- Include full action details in log entry for verification
- Separate configuration toggle to enable real actions (production use only)
- Human approval required to transition from dry-run to real actions

### 6. File Operation Safety

**Decision**: Atomic file operations with locking mechanisms

**Rationale**:
- Ensures data integrity during concurrent operations
- Supports constitutional requirement for data reliability
- Prevents race conditions between watcher and Claude Code
- Maintains file system consistency across all vault operations

**Implementation**:
- File locks for critical operations
- Temporary files for atomic moves/replacements
- Retry mechanisms for locked files
- Checksum validation after critical operations