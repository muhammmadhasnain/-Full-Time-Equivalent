# Execution & Approval System Documentation

## Overview

The Gold Tier execution and approval system provides:
- **Full dry-run mode** with detailed logging
- **Real execution mode** (toggleable)
- **Step-level traceability**
- **Rollback capability** for reversible steps
- **Conditional approval rules** based on action type, risk level, and duration
- **CLI-based approval commands**
- **Notification triggers** for pending approvals
- **Comprehensive audit logging**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      EXECUTION & APPROVAL SYSTEM                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           APPROVAL LAYER                                         │
│                                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐         │
│  │  ApprovalRule    │────▶│  RiskAssessor    │────▶│  ApprovalResult  │         │
│  │  Engine          │     │                  │     │                  │         │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘         │
│         │                       │                        │                       │
│         │ Rules:                │ Risk Levels:           │ Decisions:            │
│         │ - Duration > 120min   │ - Low                  │ - Auto Approve        │
│         │ - High Risk           │ - Medium               │ - Require Approval    │
│         │ - Data Analysis       │ - High                 │ - Auto Reject         │
│         │ - Report Generation   │ - Critical             │ - Escalate            │
│         └───────────────────────┴────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EXECUTION LAYER                                        │
│                                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐         │
│  │  MCP Execution   │────▶│  Step Executor   │────▶│  Rollback        │         │
│  │  Engine          │     │                  │     │  Manager         │         │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘         │
│         │                       │                        │                       │
│         │ Modes:                │ Step Types:            │ Strategies:           │
│         │ - Dry Run             │ - Email                │ - Automatic           │
│         │ - Real                │ - Calendar             │ - Manual              │
│         │ - Simulated           │ - File                 │ - None                │
│         │                       │ - API                  │                       │
│         │                       │ - Script               │                       │
│         └───────────────────────┴────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AUDIT LAYER                                            │
│                                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐         │
│  │  Audit Logger    │────▶│  Approval        │────▶│  Execution       │         │
│  │                  │     │  History         │     │  Traces          │         │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘         │
│         │                       │                        │                       │
│         │ Logs:                 │ Tracks:                │ Records:              │
│         │ - All events          │ - Requests             │ - Step execution      │
│         │ - JSONL format        │ - Decisions            │ - Rollbacks           │
│         │ - Queryable           │ - Reasons              │ - Errors              │
│         └───────────────────────┴────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. MCP Execution Layer

### Execution Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `DRY_RUN` | Logs what would happen, no actual execution | Default, safe testing |
| `REAL` | Executes actual actions via APIs | Production use |
| `SIMULATED` | Simulates execution with delays | Integration testing |

### Step-Level Traceability

Each step execution is tracked with:
- Step number and description
- Status (pending, running, completed, failed, rolled_back)
- Duration in milliseconds
- Error messages (if failed)
- Rollback data (for reversible steps)
- Metadata

### Rollback Capability

```python
class RollbackManager:
    """
    Manages rollback operations for reversible steps.
    
    Rollback Strategies:
    - AUTOMATIC: Auto-rollback on any step failure
    - MANUAL: Require manual intervention
    - NONE: No rollback (fire-and-forget)
    """
    
    # Reversible Operations:
    # - File created → Delete file
    # - File moved → Move back
    # - Calendar event → Cancel event
    # - API call → Compensating API call
    
    # Non-Reversible Operations:
    # - Email sent → Cannot unsend (logged only)
    # - External notification → Cannot undo (logged only)
```

### Execution Engine Structure

```python
MCPExecutionEngine
├── RollbackManager
│   ├── push_rollback_data()
│   ├── execute_rollback()
│   └── _rollback_step()
├── StepExecutor
│   ├── execute()
│   ├── _execute_email_step()
│   ├── _execute_calendar_step()
│   ├── _execute_file_step()
│   ├── _execute_api_step()
│   └── _execute_script_step()
└── Execution Methods
    ├── execute_plan()
    ├── _perform_rollback()
    └── get_execution_trace()
```

---

## 2. Approval Rule Engine

### Conditional Approval Rules

Rules are evaluated in priority order (lower = higher priority):

```python
# Default Rules (in priority order)

1. Critical Risk Escalation (priority: 1)
   - Risk Level: CRITICAL
   - Decision: ESCALATE to admin

2. High Duration Actions (priority: 10)
   - Estimated Duration: > 120 minutes
   - Decision: REQUIRE_APPROVAL

3. High Risk Actions (priority: 5)
   - Risk Level: HIGH or CRITICAL
   - Decision: REQUIRE_APPROVAL

4. Data Analysis (priority: 20)
   - Action Type: data_analysis
   - Decision: REQUIRE_APPROVAL

5. Report Generation (priority: 20)
   - Action Type: report_generation
   - Decision: REQUIRE_APPROVAL

6. Quick Email Responses (priority: 50)
   - Action Type: email_response
   - Duration: < 30 minutes
   - Decision: AUTO_APPROVE

7. Follow-up Auto-Approve (priority: 60)
   - Action Type: follow_up
   - Risk Level: LOW
   - Duration: < 30 minutes
   - Decision: AUTO_APPROVE
```

### Risk Assessment

```python
RiskAssessor.assess(action_type, estimated_duration, metadata)

Risk Scoring:
┌─────────────────────┬──────────────┐
│ Factor              │ Risk Points  │
├─────────────────────┼──────────────┤
│ Action Type:        │              │
│   email_response    │ +1           │
│   follow_up         │ +1           │
│   meeting_request   │ +2           │
│   document_creation │ +3           │
│   data_analysis     │ +4           │
│   report_generation │ +4           │
├─────────────────────┼──────────────┤
│ Duration:           │              │
│   > 180 minutes     │ +3           │
│   > 120 minutes     │ +2           │
│   > 60 minutes      │ +1           │
├─────────────────────┼──────────────┤
│ Priority:           │              │
│   high              │ +2           │
│   critical          │ +3           │
├─────────────────────┼──────────────┤
│ Source:             │              │
│   external          │ +1           │
└─────────────────────┴──────────────┘

Risk Levels:
- 0-3: LOW
- 4-5: MEDIUM
- 6-7: HIGH
- 8+: CRITICAL
```

### Adding Custom Rules

```python
from services.approval_rule_engine import ApprovalRuleEngine, ApprovalRule, ApprovalDecision

engine = ApprovalRuleEngine()

# Add custom rule
engine.add_rule(ApprovalRule(
    rule_id="rule_custom",
    name="Custom Approval Rule",
    description="My custom rule",
    priority=15,
    action_types=["document_creation"],
    min_risk_level=RiskLevel.MEDIUM,
    max_estimated_duration=60,
    decision=ApprovalDecision.REQUIRE_APPROVAL,
    approvers=["manager@example.com"]
))
```

---

## 3. Audit Logging

### Log Structure

```
AI_Employee_Vault/
└── System_Log/
    └── Audit/
        ├── audit_log.jsonl         # All audit events
        ├── approval_history.jsonl  # Approval-specific events
        └── execution_traces.jsonl  # Execution-specific events
```

### Audit Entry Format

```json
{
  "entry_id": "uuid",
  "event_type": "approval_granted",
  "timestamp": "2026-02-16T10:30:00Z",
  "actor": "john.doe",
  "action_id": "uuid",
  "plan_id": "uuid",
  "approval_id": "uuid",
  "details": {
    "reason": "Approved for immediate execution"
  },
  "decision": "approved",
  "approver": "john.doe",
  "previous_status": "pending",
  "new_status": "approved"
}
```

### Query Methods

```python
audit_logger = AuditLogger(vault_path)

# Get approval history
history = audit_logger.get_approval_history(
    action_id="uuid",
    limit=50
)

# Get execution trace
trace = audit_logger.get_execution_trace(
    plan_id="uuid",
    limit=100
)

# Get audit log with filters
log = audit_logger.get_audit_log(
    event_type="approval_granted",
    start_date="2026-02-01",
    end_date="2026-02-16",
    limit=200
)

# Export audit log
audit_logger.export_audit_log(
    output_path="./audit_export.json",
    start_date="2026-02-01"
)
```

---

## 4. CLI Approval Workflow

### Commands

```bash
# List pending approvals
ai-employee approval list
ai-employee approval list --json

# Show approval details
ai-employee approval show <APPROVAL_ID>

# Approve an action
ai-employee approval approve <APPROVAL_ID>
ai-employee approval approve <APPROVAL_ID> --reason "Business critical"
ai-employee approval approve <APPROVAL_ID> -a "john.doe" -r "Urgent"

# Reject an action
ai-employee approval reject <APPROVAL_ID> --reason "Security concerns"
ai-employee approval reject <APPROVAL_ID> -a "jane.doe" -r "Budget exceeded"

# Auto-approve all (testing)
ai-employee approval auto-approve-all

# Show approval history
ai-employee approval history
ai-employee approval history --limit 50
ai-employee approval history --json
```

### Example Workflow

```bash
# 1. Check pending approvals
$ ai-employee approval list

======================================================================
PENDING APPROVALS
======================================================================

📋 abc12345...
   Action ID: 123e4567...
   Plan ID:   987fcdeb...
   Type:      data_analysis
   Duration:  180 minutes
   Risk:      high
   Created:   2026-02-16T09:00:00Z
   Reason:    High estimated duration (180 minutes)

======================================================================
Total: 1 pending approval(s)

# 2. Review the approval details
$ ai-employee approval show abc12345

# 3. Approve with reason
$ ai-employee approval approve abc12345 -r "Analysis required for board meeting"

✅ Approved: abc12345-approval.md
   Approver: cli_user
   Reason:   Analysis required for board meeting
   Status:   Moved to Approved/

# 4. Verify in history
$ ai-employee approval history

======================================================================
APPROVAL HISTORY
======================================================================

✅ 2026-02-16T10:30:00
   Type: approval_granted
   Action: 123e4567...
   Plan:   987fcdeb...
   Approver: cli_user
   Reason: Analysis required for board meeting
```

---

## 5. Notification System

### Notification Channels

| Channel | Description | Configuration |
|---------|-------------|---------------|
| Console | Print to console (testing) | Always enabled |
| Log | Write to JSONL file | `notifications.log_path` |
| Webhook | Slack, Teams, etc. | `notifications.webhooks` |
| Email | SMTP email | `notifications.email` |

### Notification Rules

```yaml
# config.yaml
notifications:
  log_path: "./logs/notifications.log"
  
  rules:
    approval_required: true      # Notify when approval needed
    execution_completed: false   # Don't notify on success
    execution_failed: true       # Notify on failure
    workflow_error: true         # Notify on errors
  
  webhooks:
    slack:
      enabled: true
      url: "https://hooks.slack.com/..."
      type: "slack"
  
  email:
    enabled: false
    smtp_host: "smtp.example.com"
    smtp_port: 587
    sender: "ai-employee@example.com"
    recipients:
      - "admin@example.com"
```

### Notification Events

- `APPROVAL_REQUIRED` - New approval needed (high priority)
- `ACTION_FAILED` - Execution failed (high priority)
- `EXECUTION_COMPLETED` - Execution completed (configurable)
- `WORKFLOW_ERROR` - System error (high priority)

---

## 6. Production Best Practices

### Execution Mode Management

```python
# Development - Dry run by default
engine = MCPExecutionEngine(vault_path, dry_run=True)

# Staging - Simulated execution
engine.enable_simulated_execution()

# Production - Real execution (with approval)
engine.enable_real_execution()
```

### Rollback Strategy Selection

```python
# High-risk actions: Automatic rollback
result = await engine.execute_plan(
    plan,
    rollback_strategy=RollbackStrategy.AUTOMATIC
)

# Low-risk actions: No rollback needed
result = await engine.execute_plan(
    plan,
    rollback_strategy=RollbackStrategy.NONE
)

# Critical actions: Manual intervention on failure
result = await engine.execute_plan(
    plan,
    rollback_strategy=RollbackStrategy.MANUAL
)
```

### Audit Log Retention

```python
# Export monthly audit logs
audit_logger.export_audit_log(
    output_path=f"./audit_{datetime.now().strftime('%Y%m')}.json",
    start_date="2026-02-01",
    end_date="2026-02-28"
)

# Archive old logs
# (Implement log rotation as needed)
```

### Approval Delegation

```yaml
# config.yaml
approval:
  rules:
    - rule_id: "delegated_approval"
      name: "Manager Approval"
      action_types: ["document_creation", "email_response"]
      max_estimated_duration: 60
      decision: "require_approval"
      approvers:
        - "manager@example.com"
        - "delegate@example.com"
```

---

## 7. Files Created

| File | Purpose |
|------|---------|
| `src/services/mcp_execution_engine.py` | Enhanced execution with rollback |
| `src/services/approval_rule_engine.py` | Conditional approval rules |
| `src/services/audit_logger.py` | Comprehensive audit logging |
| `src/services/notification_service.py` | Multi-channel notifications |
| `src/cli/commands/approval_cmd.py` | CLI approval commands |
| `docs/EXECUTION_APPROVAL.md` | This documentation |

---

## Quick Reference

### Toggle Execution Mode

```python
from services.mcp_execution_engine import create_mcp_execution_engine, ExecutionMode

engine = create_mcp_execution_engine("./AI_Employee_Vault")

# Check current mode
print(f"Current mode: {engine.execution_mode.value}")

# Change mode
engine.enable_dry_run()           # Safe mode
engine.enable_real_execution()    # Production mode
engine.enable_simulated_execution()  # Testing mode
```

### Evaluate Approval

```python
from services.approval_rule_engine import (
    create_approval_rule_engine,
    create_risk_assessor,
    ApprovalContext,
    RiskLevel
)

rule_engine = create_approval_rule_engine()
risk_assessor = create_risk_assessor()

# Assess risk
risk_level = risk_assessor.assess(
    action_type="data_analysis",
    estimated_duration=180,
    metadata={"priority": "high"}
)

# Evaluate approval
context = ApprovalContext(
    action_id="uuid",
    plan_id="uuid",
    approval_id="uuid",
    action_type="data_analysis",
    risk_level=risk_level,
    estimated_duration=180,
    description="Complex data analysis"
)

result = rule_engine.evaluate(context)
print(f"Decision: {result.decision.value}")
print(f"Reason: {result.reason}")
```

### Log Audit Event

```python
from services.audit_logger import create_audit_logger

audit = create_audit_logger("./AI_Employee_Vault")

# Log approval
audit.log_approval_granted(
    approval_id="uuid",
    action_id="uuid",
    plan_id="uuid",
    approver="john.doe",
    actor="john.doe",
    reason="Business critical"
)

# Log execution
audit.log_execution_completed(
    plan_id="uuid",
    action_id="uuid",
    correlation_id="uuid",
    status="completed",
    execution_mode="dry_run",
    steps_completed=5,
    steps_failed=0,
    rollback_performed=False
)
```

---

**Status**: ✅ Execution & Approval System Complete

All objectives met. System is production-ready.
