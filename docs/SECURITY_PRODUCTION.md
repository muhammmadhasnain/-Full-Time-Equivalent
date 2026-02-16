# Security & Production Safeguards Documentation

## Overview

The Gold Tier security implementation provides **enterprise-grade security** and **production reliability** through:
- Encrypted credential storage with Fernet
- File integrity monitoring with tamper detection
- Immutable audit trails with cryptographic chaining
- Circuit breaker pattern for fault tolerance
- Retry logic with exponential backoff
- Graceful failure recovery
- Dead-letter queue handling

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY ARCHITECTURE                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CREDENTIAL SECURITY                                    │
│                                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐         │
│  │  Master Password │────▶│  PBKDF2 Key Derivation │  Fernet Encryption │         │
│  │  (env var)       │     │  (100k iterations)     │  (AES-128-CBC)     │         │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘         │
│                              │                        │                          │
│                              ▼                        ▼                          │
│                       ┌─────────────────────────────────────┐                   │
│                       │      Credential Vault (Encrypted)    │                   │
│                       │  - API keys                         │                   │
│                       │  - OAuth tokens                     │                   │
│                       │  - Database passwords               │                   │
│                       └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FILE SECURITY                                          │
│                                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐         │
│  │  Permissions     │     │  Integrity       │     │  Tamper          │         │
│  │  (0o600/0o700)   │────▶│  Monitoring      │────▶│  Detection       │         │
│  │                  │     │  (SHA-256)       │     │  (Hash chain)    │         │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘         │
│                              │                        │                          │
│                              ▼                        ▼                          │
│                       ┌─────────────────────────────────────┐                   │
│                       │      Secure File Handler             │                   │
│                       │  - Atomic writes                    │                   │
│                       │  - Secure deletes                   │                   │
│                       │  - Integrity verification           │                   │
│                       └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AUDIT & COMPLIANCE                                     │
│                                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐         │
│  │  All Events      │────▶│  Immutable Log   │────▶│  Cryptographic   │         │
│  │  (with corr ID)  │     │  (JSONL format)  │     │  Chain Hash      │         │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘         │
│                              │                        │                          │
│                              ▼                        ▼                          │
│                       ┌─────────────────────────────────────┐                   │
│                       │      Audit Trail                     │                   │
│                       │  - Tamper detection                 │                   │
│                       │  - Chain verification               │                   │
│                       │  - Compliance export                │                   │
│                       └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                           RELIABILITY PATTERNS                                   │
│                                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐         │
│  │  Circuit Breaker │     │  Retry Handler   │     │  Bulkhead        │         │
│  │  (fail fast)     │     │  (backoff+jitter)│     │  (concurrency)   │         │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘         │
│         │                       │                        │                       │
│         └───────────────────────┼────────────────────────┘                       │
│                                 ▼                                                 │
│                       ┌──────────────────┐                                       │
│                       │  Graceful        │                                       │
│                       │  Failure Handler │                                       │
│                       │  + Dead Letter   │                                       │
│                       └──────────────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Encrypted Credential Storage

### Key Derivation

```
Master Password
       │
       ▼
┌─────────────────┐
│  PBKDF2-HMAC    │
│  - SHA256       │
│  - 100,000 iterations
│  - 16-byte salt │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  Fernet Key     │
│  (AES-128-CBC)  │
└─────────────────┘
       │
       ▼
┌─────────────────┐
│  Encrypted      │
│  Credentials    │
└─────────────────┘
```

### Usage Example

```python
from lib.security.credential_vault import create_credential_vault, SecureEnv

# Initialize vault
vault = create_credential_vault(
    vault_path="./AI_Employee_Vault",
    password=os.getenv("VAULT_MASTER_PASSWORD")
)

# Store credential
vault.set_credential(
    name="claude_api_key",
    value="sk-ant-...",
    expires_in_days=90,  # Auto-expire
    metadata={"service": "anthropic"}
)

# Retrieve credential (automatically decrypted)
api_key = vault.get_credential("claude_api_key")

# Use SecureEnv for environment variables
SecureEnv.initialize("./AI_Employee_Vault")
api_key = SecureEnv.get("claude_api_key")

# Require credentials (raises if missing)
creds = SecureEnv.require("claude_api_key", "gmail_client_id")
```

### Credential Rotation

```python
# Rotate encryption key
vault.rotate_all_credentials(new_password="new_secure_password")

# Rotate individual credential
vault.set_credential("claude_api_key", new_api_key, expires_in_days=90)
```

---

## File Permission Model

### Permission Presets

| Preset | Mode | Use Case |
|--------|------|----------|
| `OWNER_ONLY` | 0o600 | Credential files, keys |
| `OWNER_EXEC` | 0o700 | Directories |
| `GROUP_READ` | 0o640 | Shared config files |
| `WORLD_READ` | 0o644 | Public files (avoid) |

### Folder Structure with Permissions

```
AI_Employee_Vault/
├── .credentials/         # 0o700 - Owner only
│   ├── vault.json        # 0o600 - Encrypted credentials
│   └── access.log        # 0o600 - Access audit log
├── .keys/                # 0o700 - Owner only
│   ├── master.key        # 0o600 - Encryption key
│   └── salt              # 0o600 - Key derivation salt
├── System_Log/
│   ├── Audit/            # 0o700 - Audit logs
│   │   ├── immutable_audit.jsonl  # 0o600
│   │   └── chain_hashes.json      # 0o600
│   └── .integrity/       # 0o700 - Integrity DB
│       └── files.json    # 0o600 - File hashes
├── Inbox/                # 0o755 - Standard
├── Needs_Action/         # 0o755 - Standard
├── Plans/                # 0o755 - Standard
├── Pending_Approval/     # 0o755 - Standard
├── Approved/             # 0o755 - Standard
└── Done/                 # 0o755 - Standard
```

### Setting Secure Permissions

```python
from lib.security.file_security import FilePermissions

# Lock down sensitive folder
FilePermissions.lock_down_folder("./AI_Employee_Vault/.credentials")

# Set specific permissions
FilePermissions.set_secure(
    "./AI_Employee_Vault/.keys/master.key",
    FilePermissions.OWNER_ONLY
)

# Verify permissions
is_secure, mode = FilePermissions.verify(
    "./AI_Employee_Vault/.credentials/vault.json",
    FilePermissions.OWNER_ONLY
)

if not is_secure:
    print(f"Warning: Insecure permissions detected: {oct(mode)}")
```

---

## Tamper Detection

### File Integrity Monitoring

```python
from lib.security.file_security import create_file_integrity_monitor

# Create integrity monitor
monitor = create_file_integrity_monitor("./AI_Employee_Vault")

# Record baseline for critical files
monitor.record_file("./AI_Employee_Vault/System_Log/audit_log.jsonl")
monitor.record_file("./config.yaml")

# Verify file integrity
is_valid, message = monitor.verify_file("./config.yaml")

if not is_valid:
    print(f"TAMPER DETECTED: {message}")

# Verify all recorded files
results = monitor.verify_all()

for path, (is_valid, message) in results.items():
    if not is_valid:
        print(f"ALERT: {path} - {message}")

# Get tampered files
tampered = monitor.get_tampered_files()
if tampered:
    print(f"Tampered files: {tampered}")
```

### Integrity Report

```json
{
  "total_files": 150,
  "tampered_files": 0,
  "verified_files": 148,
  "unverified_files": 2,
  "tamper_rate": 0.0,
  "last_updated": "2026-02-16T10:30:00Z"
}
```

---

## Immutable Audit Trail

### Cryptographic Chaining

```
Entry 1: hash(data1) → chain_hash1 = hash(hash(data1))
Entry 2: hash(data2) → chain_hash2 = hash(hash(data2) + chain_hash1)
Entry 3: hash(data3) → chain_hash3 = hash(hash(data3) + chain_hash2)
...
```

### Logging Events

```python
from lib.security.audit_trail import create_immutable_audit_log, AuditEventTypes

# Create audit log
audit_log = create_immutable_audit_log("./AI_Employee_Vault")

# Log approval event
audit_log.append(
    event_type=AuditEventTypes.APPROVAL_GRANTED,
    actor="john.doe",
    action="approved",
    resource="plan",
    resource_id="plan-123",
    details={"reason": "Business critical"},
    correlation_id="corr-456"
)

# Log execution event
audit_log.append(
    event_type=AuditEventTypes.EXECUTION_COMPLETED,
    actor="mcp_service",
    action="executed",
    resource="plan",
    resource_id="plan-123",
    details={"steps_completed": 5, "duration_ms": 234},
    correlation_id="corr-456"
)
```

### Querying Audit Log

```python
# Query by correlation ID (full trace)
trace = audit_log.query(correlation_id="corr-456")

# Query by actor
user_actions = audit_log.query(actor="john.doe", limit=100)

# Query by date range
daily_audit = audit_log.query(
    start_date="2026-02-16",
    end_date="2026-02-16",
    limit=1000
)

# Query by event type
approvals = audit_log.query(event_type=AuditEventTypes.APPROVAL_GRANTED)
```

### Verifying Chain Integrity

```python
# Verify entire chain
result = audit_log.verify_chain()

if result["valid"]:
    print(f"Audit chain verified: {result['total_entries']} entries")
else:
    print(f"TAMPER DETECTED: {result['invalid_entries']} invalid entries")
    for issue in result["issues"]:
        print(f"  - Entry {issue['entry_id']}: {issue['reason']}")
```

### Export for Compliance

```python
# Export audit log for compliance review
audit_log.export_log(
    output_path="./compliance_audit_2026_02.json",
    start_date="2026-02-01",
    end_date="2026-02-28"
)
```

---

## Reliability Patterns

### Circuit Breaker

```python
from lib.security.reliability import create_circuit_breaker, CircuitBreakerOpenError

# Create circuit breaker
cb = create_circuit_breaker(
    name="claude_api",
    failure_threshold=5,    # Open after 5 failures
    timeout=60.0            # Try again after 60 seconds
)

# Use circuit breaker
async def call_claude_api():
    return await claude_client.generate_plan(prompt)

async def fallback():
    return generate_plan_template(prompt)

try:
    result = await cb.call(call_claude_api, fallback)
except CircuitBreakerOpenError:
    print("Circuit open - using fallback")
    result = await fallback()

# Check status
stats = cb.get_stats()
print(f"State: {stats['state']}")
print(f"Success rate: {stats['stats']['success_rate']:.2%}")
```

### Retry with Exponential Backoff

```python
from lib.security.reliability import create_retry_handler, RetryConfig

# Create retry handler
retry = create_retry_handler(
    max_retries=3,
    base_delay=1.0,      # Start with 1 second
    max_delay=60.0       # Cap at 60 seconds
)

# Execute with retry
async def send_email():
    return await email_client.send(message)

async def on_retry(attempt, error, delay):
    print(f"Retry {attempt}: {error}. Waiting {delay:.1f}s")

result = await retry.execute(send_email, on_retry=on_retry)
```

### Bulkhead (Concurrency Limiting)

```python
from lib.security.reliability import Bulkhead

# Create bulkhead
bulkhead = Bulkhead(
    name="api_calls",
    max_concurrent=10  # Max 10 concurrent API calls
)

# Execute with concurrency limit
async def make_api_call():
    return await api_client.call()

try:
    result = await bulkhead.execute(make_api_call, timeout=30.0)
except BulkheadFullError:
    print("Bulkhead full - request rejected")
```

### Graceful Failure Recovery

```python
from lib.security.reliability import GracefulFailureHandler

# Create failure handler
fh = GracefulFailureHandler("email_service")

# Register recovery callback
async def recover_email_connection():
    await email_client.reconnect()
    return True

fh.register_recovery("send_email", recover_email_connection)

# Handle failure
async def send_with_recovery():
    try:
        return await email_client.send(message)
    except Exception as e:
        recovered = await fh.handle_failure(
            operation="send_email",
            error=e,
            context={"recipient": recipient},
            auto_recover=True
        )
        
        if recovered:
            return await email_client.send(message)
        raise

# Check DLQ
dlq_entries = fh.get_dlq_entries(limit=100)
for entry in dlq_entries:
    print(f"Failed: {entry['operation']} - {entry['error']}")
```

---

## Production Deployment Checklist

### Pre-Deployment Security

- [ ] **Master Password Set**
  ```bash
  export VAULT_MASTER_PASSWORD="<secure-password>"
  ```

- [ ] **Credential Vault Initialized**
  ```python
  vault = create_credential_vault("./AI_Employee_Vault")
  vault.set_credential("claude_api_key", os.getenv("CLAUDE_API_KEY"))
  ```

- [ ] **File Permissions Verified**
  ```bash
  find ./AI_Employee_Vault/.credentials -type f -exec stat -c "%a %n" {} \;
  # Should show 600 for all files
  ```

- [ ] **Integrity Baselines Recorded**
  ```python
  monitor = create_file_integrity_monitor("./AI_Employee_Vault")
  monitor.record_file("./config.yaml")
  ```

### Deployment Configuration

```yaml
# config.yaml - Security Settings
security:
  # Credential vault
  vault_path: "./AI_Employee_Vault"
  master_password_env: "VAULT_MASTER_PASSWORD"
  
  # File security
  secure_permissions: true
  integrity_monitoring: true
  
  # Audit
  audit_enabled: true
  audit_path: "./AI_Employee_Vault/System_Log/Audit"
  
  # Reliability
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    timeout: 60
  
  retry:
    enabled: true
    max_retries: 3
    base_delay: 1.0
```

### Post-Deployment Verification

- [ ] **Verify Credential Access**
  ```python
  from lib.security.credential_vault import SecureEnv
  api_key = SecureEnv.get("claude_api_key")
  assert api_key is not None
  ```

- [ ] **Verify Audit Logging**
  ```python
  audit = create_immutable_audit_log("./AI_Employee_Vault")
  audit.append(
      event_type="system.startup",
      actor="system",
      action="started",
      resource="orchestrator",
      resource_id="main"
  )
  ```

- [ ] **Verify Circuit Breaker**
  ```python
  from lib.security.reliability import create_circuit_breaker
  cb = create_circuit_breaker("test")
  assert cb.is_closed
  ```

- [ ] **Verify File Integrity**
  ```python
  monitor = create_file_integrity_monitor("./AI_Employee_Vault")
  result = monitor.verify_chain()
  assert result["valid"]
  ```

### Monitoring Setup

- [ ] **Alert on Tamper Detection**
  ```python
  tampered = monitor.get_tampered_files()
  if tampered:
      send_alert(f"Tamper detected: {tampered}")
  ```

- [ ] **Alert on Circuit Breaker Open**
  ```python
  if cb.is_open:
      send_alert(f"Circuit breaker open: {cb.name}")
  ```

- [ ] **Alert on High Error Rate**
  ```python
  stats = cb.get_stats()
  if stats["stats"]["success_rate"] < 0.9:
      send_alert(f"High error rate: {stats['stats']['success_rate']:.2%}")
  ```

- [ ] **Daily Audit Export**
  ```python
  yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
  audit.export_log(
      f"./audit_export_{yesterday}.json",
      start_date=yesterday,
      end_date=yesterday
  )
  ```

### Compliance Requirements

| Requirement | Implementation |
|-------------|----------------|
| Access logging | Immutable audit trail |
| Data encryption | Fernet encryption for credentials |
| Integrity verification | SHA-256 file hashing |
| Tamper detection | Cryptographic chain verification |
| Failure recovery | Circuit breaker + retry + DLQ |
| Audit export | JSON export with chain hash |

---

## Files Created

| File | Purpose |
|------|---------|
| `src/lib/security/credential_vault.py` | Encrypted credential storage |
| `src/lib/security/file_security.py` | File permissions & integrity |
| `src/lib/security/reliability.py` | Circuit breaker, retry, bulkhead |
| `src/lib/security/audit_trail.py` | Immutable audit logging |
| `docs/SECURITY_PRODUCTION.md` | This documentation |

---

## Quick Reference

### Initialize Security

```python
from lib.security.credential_vault import initialize_secure_env
from lib.security.file_security import create_file_integrity_monitor
from lib.security.audit_trail import create_immutable_audit_log
from lib.security.reliability import create_reliability_manager

# Initialize all security components
initialize_secure_env("./AI_Employee_Vault")
monitor = create_file_integrity_monitor("./AI_Employee_Vault")
audit = create_immutable_audit_log("./AI_Employee_Vault")
reliability = create_reliability_manager()
```

### Log Security Event

```python
audit.append(
    event_type=AuditEventTypes.SECURITY_EVENT,
    actor="system",
    action="detected",
    resource="file",
    resource_id="/path/to/file",
    details={"type": "tamper_detected"}
)
```

### Execute with Reliability

```python
result = await reliability.execute_with_reliability(
    operation="send_email",
    func=send_email,
    fallback=log_for_manual_send,
    use_circuit_breaker=True,
    use_retry=True,
    use_bulkhead=True
)
```

---

**Status**: ✅ Security & Production Complete

All enterprise-grade security and reliability patterns implemented.
