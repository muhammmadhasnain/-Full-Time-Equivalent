# Data Model: AI Employee Foundation

## Entity Definitions

### Action File
- **Type**: YAML document
- **Fields**:
  - `id`: Unique identifier (UUID)
  - `type`: Action type (string, required)
  - `priority`: Priority level (low, medium, high)
  - `context`: Contextual data (dictionary)
  - `created_at`: Timestamp (ISO 8601)
  - `source`: Source identifier (string)
- **Location**: `/Needs_Action/` folder in vault
- **Lifecycle**: Created by Watcher → Processed by Claude → Converted to Plan
- **Validation**: Must have valid UUID, valid priority value, valid timestamp

### Plan File
- **Type**: Markdown with YAML frontmatter
- **Frontmatter Fields**:
  - `action_id`: Reference to originating action (UUID)
  - `status`: draft/planned/approved/executed/cancelled
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp
  - `estimated_duration`: Estimated completion time in minutes
  - `dependencies`: List of related action IDs
- **Body Sections**:
  - `# Objectives`: What needs to be accomplished
  - `# Steps`: Detailed action steps
  - `# Resources`: Required tools, files, or information
  - `# Success Criteria`: How to verify completion
- **Location**: `/Plans/` folder in vault
- **Lifecycle**: Created by Claude → Reviewed → Approved → Executed
- **Validation**: Must reference existing action, valid status value, required sections present

### Approval File
- **Type**: Markdown document with action details and checkboxes for approval
- **Fields**:
  - `action_id`: Reference to action being approved (UUID)
  - `plan_id`: Reference to associated plan (UUID)
  - `description`: Brief description of the action
  - `created_at`: Request timestamp
  - `requested_by`: Requesting system/user
- **Body**: Action details and approval checkboxes
- **Location**: `/Pending_Approval/` folder initially, then `/Approved/` or `/Rejected/`
- **Lifecycle**: Created when action requires approval → Moved by user to approved/rejected
- **Validation**: Must reference existing action and plan, approval must not already exist for same action

### Dashboard Metrics
- **Type**: Markdown document
- **Fields**:
  - `total_actions`: Count of all actions
  - `pending_approvals`: Count of items awaiting approval
  - `recent_activity`: Recent activity log
  - `system_health`: Health indicators
  - `last_updated`: Last update timestamp
- **Location**: Root of vault as `Dashboard.md`
- **Update Frequency**: Updated on each system event

## Relationships

### Action to Plan
- **Relationship**: One-to-One (each action generates one plan)
- **Reference**: Action.id → Plan.action_id

### Plan to Approval
- **Relationship**: One-to-One (each plan may generate one approval request)
- **Reference**: Plan.id → Approval.plan_id

### Approval to Execution Log
- **Relationship**: One-to-Many (one approval may lead to multiple execution steps)
- **Reference**: Approval.id → ExecutionLog.approval_id

## State Transitions

### Action States
- `created` → `processed` → `converted_to_plan` → `archived`

### Plan States
- `draft` → `planned` → `submitted_for_approval` → `approved` → `executed`
- `draft` → `planned` → `submitted_for_approval` → `rejected` → `closed`

### Approval States
- `requested` → `pending` → `approved` → `completed`
- `requested` → `pending` → `rejected` → `completed`

## Validation Rules

### Action File
- Must have a valid UUID for id field
- Type field must be one of allowed action types
- Priority must be low, medium, or high
- Created_at must be a valid ISO 8601 timestamp

### Plan File
- Action_id must reference an existing action
- Status must be one of allowed statuses
- Frontmatter must be valid YAML
- Required sections (# Objectives, # Steps) must be present

### Approval File
- Action_id must reference an existing action
- Plan_id must reference an existing plan
- Approval must not already exist for the same action

## Constraints

### Uniqueness
- Action.id must be unique across all actions
- Plan.action_id must be unique across all plans

### Referential Integrity
- Plan.action_id must reference an existing Action.id
- Approval.plan_id must reference an existing Plan.id

### Access Control
- Only authorized processes can modify files in `/Approved/` folder
- Files in `/Done/` folder are immutable

## File Organization

### Vault Structure
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

### Naming Convention
- Action files: `{uuid}.action.yaml`
- Plan files: `{action_uuid}.plan.md`
- Approval files: `{action_uuid}.approval.md`
- Log files: `log_{timestamp}.txt`