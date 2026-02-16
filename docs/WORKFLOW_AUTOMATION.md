# Vault Workflow Automation Documentation

## Overview

The Gold Tier workflow automation system provides **fully automated vault transitions** with state machine enforcement, file locking, retry mechanisms, and dead-letter queue handling.

## State Machine Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VAULT WORKFLOW STATE MACHINE                             │
└─────────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────┐
                                    │  INBOX   │
                                    └────┬─────┘
                                         │
                                         │ file.created
                                         ▼
                              ┌──────────────────┐
                              │  NEEDS_ACTION    │◄──────┐
                              └────────┬─────────┘       │
                                       │                 │ retry
                                       │ action.generated│
                                       ▼                 │
                              ┌──────────────────┐       │
                              │ ACTION_PROCESSING│───────┘
                              └────────┬─────────┘
                                       │
                                       │ plan.created
                                       ▼
                                    ┌──────────┐
                                    │  PLANS   │
                                    └────┬─────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    │ approval.required  │ auto_execute       │
                    │                    │                    │
                    ▼                    ▼                    ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐
         │PENDING_APPROVAL  │  │EXECUTION_PENDING │  │   FAILED     │
         └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘
                  │                     │                   │
         ┌────────┼────────┐            │         ┌─────────┼────────┐
         │                 │            │         │                   │
         ▼                 ▼            ▼         ▼                   ▼
┌──────────────┐  ┌──────────────┐ ┌──────────┐ ┌──────────┐  ┌──────────────┐
│   APPROVED   │  │   REJECTED   │ │EXECUTING │ │  RETRY   │  │ DEAD_LETTER  │
└──────┬───────┘  └──────┬───────┘ └────┬─────┘ └──────────┘  └──────────────┘
       │                 │              │
       │                 │              │ plan.executed
       │                 │              │
       ▼                 ▼              ▼
┌──────────────┐  ┌──────────────┐ ┌──────────┐
│   ARCHIVED   │  │   ARCHIVED   │ │   DONE   │
└──────────────┘  └──────────────┘ └──────────┘

LEGEND:
┌──────────┐  = State (folder)
─────▼─────  = Valid transition
```

## Folder Structure

```
AI_Employee_Vault/
├── Inbox/              # Entry point for new files
├── Needs_Action/       # Action files awaiting processing
├── Plans/              # Generated plan files
├── Pending_Approval/   # Awaiting human approval
├── Approved/           # Ready for execution
├── Done/               # Completed executions
├── Failed/             # Failed transitions
├── Dead_Letter/        # Unrecoverable failures
├── Archived/           # Historical records
├── .locks/             # File lock metadata (auto-generated)
└── Dashboard.md        # Auto-updated status
```

## State Transitions Matrix

| From State | To States | Trigger |
|------------|-----------|---------|
| `INBOX` | `NEEDS_ACTION`, `FAILED` | File detected |
| `NEEDS_ACTION` | `ACTION_PROCESSING`, `FAILED` | Processing started |
| `ACTION_PROCESSING` | `PLANS`, `FAILED`, `RETRY` | Plan generated |
| `PLANS` | `PENDING_APPROVAL`, `EXECUTION_PENDING`, `FAILED` | Approval check |
| `PENDING_APPROVAL` | `APPROVAL_REVIEW`, `FAILED` | Human review |
| `APPROVAL_REVIEW` | `APPROVED`, `REJECTED`, `FAILED` | Decision made |
| `APPROVED` | `EXECUTING`, `FAILED` | Execution scheduled |
| `EXECUTING` | `EXECUTED`, `FAILED`, `RETRY` | Execution complete |
| `EXECUTED` | `DONE`, `FAILED` | Finalization |
| `DONE` | `ARCHIVED` | Cleanup |
| `REJECTED` | `ARCHIVED`, `DEAD_LETTER` | Cleanup |
| `FAILED` | `RETRY`, `DEAD_LETTER` | Retry decision |
| `RETRY` | Source state, `DEAD_LETTER` | Retry attempt |

## Workflow Engine Pseudocode

```python
class WorkflowEngine:
    """
    Main workflow automation engine.
    """
    
    async def process_file(self, file_path: Path) -> WorkflowResult:
        """
        Process a file through the workflow pipeline.
        """
        # Step 1: Acquire file lock
        lock = await self.file_lock.acquire(file_path.name)
        if not lock:
            return WorkflowResult.failed("Could not acquire lock")
        
        try:
            # Step 2: Determine current state from folder
            current_state = self.get_folder_state(file_path.parent.name)
            
            # Step 3: Determine target state
            target_state = self.determine_next_state(file_path)
            
            # Step 4: Validate transition
            if not self.is_valid_transition(current_state, target_state):
                return WorkflowResult.invalid_transition()
            
            # Step 5: Execute atomic move
            success = await self.atomic_move(file_path, target_state.folder)
            
            if not success:
                # Step 6a: Handle failure with retry
                if self.retry_handler.should_retry():
                    return await self.retry(file_path)
                else:
                    # Move to dead letter queue
                    return await self.dead_letter_queue.add(file_path)
            
            # Step 6b: Success - publish event
            self.publish_transition_event(file_path, current_state, target_state)
            
            return WorkflowResult.success(target_state)
            
        finally:
            # Step 7: Release lock
            await self.file_lock.release(file_path.name)
    
    async def atomic_move(self, source: Path, target_folder: str) -> bool:
        """
        Atomically move a file using copy-rename-delete pattern.
        """
        target = self.vault_path / target_folder / source.name
        temp_target = target.with_suffix('.tmp')
        
        # Copy to temp file
        shutil.copy2(source, temp_target)
        
        # Atomic rename
        temp_target.rename(target)
        
        # Remove source
        source.unlink()
        
        return True
```

## Retry Mechanism with Exponential Backoff

```python
class RetryHandler:
    """
    Handles retry logic with exponential backoff and jitter.
    """
    
    def __init__(self, base_delay=1.0, max_delay=60.0, max_retries=5):
        self.base_delay = base_delay      # 1 second
        self.max_delay = max_delay        # 60 seconds
        self.max_retries = max_retries    # 5 attempts
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay using exponential backoff with jitter.
        
        Formula: delay = min(base * 2^attempt + jitter, max_delay)
        Where jitter = ±25% of delay
        """
        # Exponential backoff
        delay = self.base_delay * (2 ** attempt)
        
        # Add jitter (±25%)
        jitter = delay * 0.25 * (2 * random() - 1)
        delay += jitter
        
        # Cap at max delay
        return min(delay, self.max_delay)
    
    def should_retry(self, attempt: int, error: str) -> bool:
        """
        Determine if retry should be attempted.
        """
        # Max retries exceeded
        if attempt >= self.max_retries:
            return False
        
        # Non-retryable errors
        non_retryable = [
            "file not found",
            "invalid state",
            "permission denied"
        ]
        
        if any(nr in error.lower() for nr in non_retryable):
            return False
        
        return True
```

## Dead Letter Queue

```python
class DeadLetterQueue:
    """
    Stores failed actions that cannot be automatically recovered.
    """
    
    def add(self, file: Path, error: str, context: WorkflowContext) -> Path:
        """
        Add a failed file to the dead letter queue.
        """
        timestamp = now().strftime("%Y%m%d_%H%M%S")
        dlq_filename = f"{timestamp}_{file.name}"
        
        # Move file to Dead_Letter/
        dlq_path = self.dlq_folder / dlq_filename
        shutil.copy2(file, dlq_path)
        
        # Write metadata
        metadata = {
            "original_filename": file.name,
            "source_folder": file.parent.name,
            "error": error,
            "timestamp": iso_now(),
            "context": context.to_dict()
        }
        
        meta_path = dlq_path.with_suffix(".meta.yaml")
        write_yaml(metadata, meta_path)
        
        return dlq_path
    
    def retry_entry(self, meta_filename: str) -> bool:
        """
        Move a DLQ entry back to the appropriate folder for retry.
        """
        # Load metadata
        metadata = load_yaml(self.dlq_folder / meta_filename)
        
        # Determine target folder
        target_folder = metadata.get('source_folder', 'Needs_Action')
        
        # Move back
        data_file = meta_filename.replace(".meta.yaml", "")
        shutil.copy2(
            self.dlq_folder / data_file,
            self.vault_path / target_folder / data_file
        )
        
        # Remove from DLQ
        (self.dlq_folder / meta_filename).unlink()
        (self.dlq_folder / data_file).unlink()
        
        return True
    
    def purge(self, older_than_days: int = 30) -> int:
        """
        Purge old DLQ entries.
        """
        cutoff = now() - timedelta(days=older_than_days)
        purged = 0
        
        for meta_file in self.dlq_folder.glob("*.meta.yaml"):
            if meta_file.mtime < cutoff:
                # Remove meta and data files
                meta_file.unlink()
                (self.dlq_folder / data_file).unlink()
                purged += 1
        
        return purged
```

## Correlation ID Tracking

```
Action → Plan → Execution Correlation:

┌─────────────────────────────────────────────────────────────────┐
│                     CORRELATION TRACKING                         │
└─────────────────────────────────────────────────────────────────┘

Correlation ID: 550e8400-e29b-41d4-a716-446655440000
│
├─ Action ID:    123e4567-e89b-12d3-a456-426614174000
│  └─ File:      123e4567-e89b-12d3-a456-426614174000.action.yaml
│  └─ State:     Needs_Action → Plans
│
├─ Plan ID:      987fcdeb-51a2-43d1-b890-123456789abc
│  └─ File:      123e4567-e89b-12d3-a456-426614174000.plan.md
│  └─ State:     Plans → Pending_Approval → Approved → Done
│
└─ Approval ID:  abcdef12-3456-7890-abcd-ef1234567890
   └─ File:      approval_123e4567.md
   └─ State:     Pending_Approval → Approved

Query by any ID to get full trace:
  - correlation_tracker.get_context_by_action_id(action_id)
  - correlation_tracker.get_context_by_plan_id(plan_id)
  - correlation_tracker.get_full_trace(correlation_id)
```

## Dashboard Auto-Update

The Dashboard.md is automatically updated every 30 seconds with:

```markdown
# AI Employee Dashboard

## System Status
- **Status**: 🟢 Active
- **Last Updated**: 2026-02-16T10:30:00Z

## Workflow Metrics

| Stage | Count |
|-------|-------|
| 📥 Inbox | 3 |
| ⏳ Needs Action | 5 |
| 📋 Plans | 8 |
| ⏸️ Pending Approval | 2 |
| ✅ Approved | 4 |
| ✔️ Done | 47 |
| ❌ Failed | 1 |
| 📦 Dead Letter | 0 |

**Total Actions**: 55
**Processed Today**: 12
**Errors Today**: 1

## Watchers

- **Gmail Watcher**: 🟢 Running
- **File Monitor**: 🟢 Running
- **WhatsApp Watcher**: 🔴 Stopped
- **Claude Service**: 🟢 Running
- **MCP Service**: 🟢 Running

## Recent Activity

- 2026-02-16T10:29:45: Action Executed - abc123...
- 2026-02-16T10:28:30: Plan Created - def456...
- 2026-02-16T10:27:15: Action Approved - ghi789...

## System Health

| Component | Status |
|-----------|--------|
| Vault | ✅ Operational |
| Workflow Engine | 🟢 Running |
| Storage | ✅ Available |
| Error Rate | ⚠️ 1 errors today |
```

## File Locking Implementation

```python
class FileLock:
    """
    Prevents race conditions during file transitions.
    Uses asyncio.Lock + lock files for dual protection.
    """
    
    async def acquire(self, filename: str, timeout: float = 10.0) -> bool:
        """
        Acquire exclusive lock for a file.
        """
        # Get or create asyncio lock
        async with self._global_lock:
            if filename not in self._locks:
                self._locks[filename] = asyncio.Lock()
        
        lock = self._locks[filename]
        
        # Try to acquire with timeout
        try:
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            
            # Create lock file as secondary mechanism
            lock_file = self.lock_dir / f"{filename}.lock"
            lock_file.write_text(f"{iso_now()}\n{uuid4()}")
            
            return True
        except asyncio.TimeoutError:
            return False
    
    async def release(self, filename: str):
        """
        Release lock for a file.
        """
        async with self._global_lock:
            if filename not in self._locks:
                return
            
            lock = self._locks[filename]
            if lock.locked():
                lock.release()
            
            # Remove lock file
            lock_file = self.lock_dir / f"{filename}.lock"
            if lock_file.exists():
                lock_file.unlink()
    
    def cleanup_stale_locks(self, max_age_seconds: int = 300):
        """
        Clean up stale lock files older than 5 minutes.
        """
        for lock_file in self.lock_dir.glob("*.lock"):
            age = now() - lock_file.mtime
            if age.total_seconds() > max_age_seconds:
                lock_file.unlink()
```

## Production Best Practices

### 1. Atomic Operations

```python
# Always use atomic write pattern
def atomic_write(path: Path, content: str):
    temp_path = path.with_suffix('.tmp')
    temp_path.write_text(content)
    temp_path.rename(path)  # Atomic on most filesystems
```

### 2. Lock Timeout

```python
# Always specify lock timeout to prevent deadlocks
if not await lock.acquire(filename, timeout=10.0):
    logger.warning(f"Lock timeout for {filename}")
    return Result.failed("Lock timeout")
```

### 3. Retry Limits

```python
# Always limit retries to prevent infinite loops
MAX_RETRIES = 5
if attempt >= MAX_RETRIES:
    await dead_letter_queue.add(file, error, context)
    return Result.failed("Max retries exceeded")
```

### 4. Correlation Tracking

```python
# Always track correlation IDs for debugging
correlation_id = await tracker.create_context(action_id)
await tracker.record_transition(correlation_id, from_state, to_state, success)
```

### 5. Event Publishing

```python
# Always publish events for state changes
publish_event(
    EventType.ACTION_PROCESSED,
    {"filename": filename, "success": success},
    source="workflow_engine"
)
```

### 6. Graceful Degradation

```python
# Handle missing files gracefully
if not source_path.exists():
    logger.error(f"File not found: {source_path}")
    return Result.file_not_found()
```

### 7. Metrics Collection

```python
# Track all operations for monitoring
metrics = {
    "transitions_completed": completed,
    "transitions_failed": failed,
    "retries": retries,
    "dlq_size": dlq_count,
    "avg_transition_time": avg_time
}
```

## Usage Examples

### Process Inbox File

```python
from services.workflow_engine import create_workflow_engine

engine = create_workflow_engine("./AI_Employee_Vault")
await engine.start()

# Process a file from Inbox
correlation_id = await engine.process_inbox("meeting_request.txt")

# Trace the workflow
trace = engine.get_workflow_trace(correlation_id)
print(trace['state_history'])
```

### Approve Action

```python
# User moves file to Approved/ folder
# File monitor detects and triggers approval

success = await engine.approve_action(
    filename="plan_123e4567.plan.md",
    plan_id="123e4567-e89b-12d3-a456-426614174000"
)

if success:
    print("Action approved and queued for execution")
```

### Check Dead Letter Queue

```python
dlq = engine.dead_letter_queue

# Get recent entries
entries = dlq.get_entries(limit=10)
for entry in entries:
    print(f"Error: {entry['error']}")
    print(f"Original: {entry['original_filename']}")

# Retry an entry
dlq.retry_entry("20260216_103000_failed_file.meta.yaml")

# Purge old entries
purged = dlq.purge(older_than_days=30)
print(f"Purged {purged} entries")
```

## Error Handling

| Error Type | Handling |
|------------|----------|
| File not found | Log error, return FILE_NOT_FOUND, no retry |
| Lock timeout | Retry up to 3 times, then DLQ |
| Invalid transition | Log error, return INVALID_TRANSITION, no retry |
| Permission denied | Log error, move to DLQ |
| Disk full | Retry with backoff, alert if persists |
| Network error (API) | Retry with exponential backoff |

---

**Implementation Status**: ✅ Complete

All workflow automation features are production-ready.
