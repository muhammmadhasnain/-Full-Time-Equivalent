# AI Employee Foundation - Gold Tier

<div align="center">

**Enterprise-Grade Local-First Automation System**

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Gold Tier](https://img.shields.io/badge/tier-GOLD-gold.svg)](docs/GOLD_TIER_SUMMARY.md)

**Event-Driven • Secure • Scalable • Production-Ready**

</div>

---

## 🚀 Overview

The AI Employee Foundation is an **enterprise-grade automation system** that transforms your Obsidian vault into an intelligent workflow engine. It automatically processes emails, files, and messages through a secure, auditable pipeline with human-in-the-loop approval controls.

### Gold Tier Features

| Category | Features |
|----------|----------|
| **Architecture** | Event-driven, Async/Await, Pub/Sub EventBus |
| **Security** | Fernet encryption, File integrity, Immutable audit trail |
| **Reliability** | Circuit breaker, Retry with backoff, Dead-letter queue |
| **Observability** | Prometheus metrics, Health endpoints, Structured logging |
| **Scalability** | Redis PubSub, Connection pooling, Horizontal scaling |
| **Compliance** | Correlation IDs, Tamper detection, Audit export |

---

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Core Features](#-core-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Security](#-security)
- [Monitoring](#-monitoring)
- [Documentation](#-documentation)
- [Contributing](#-contributing)

---

## ⚡ Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd FTE-hackathon
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Initialize vault
python -m src.cli.main vault init

# 5. Start the system
python -m src.cli.main start
```

---

## ✨ Core Features

### 🔄 Automated Workflow Pipeline

```
Inbox → Needs_Action → Plans → Pending_Approval → Approved → Done
                              ↓
                         Rejected → Archived
                              ↓
                         Failed → Dead_Letter
```

### 📧 Multi-Channel Input

| Watcher | Description | Status |
|---------|-------------|--------|
| **Gmail** | IMAP/OAuth2 email monitoring | ✅ Production |
| **File System** | Watchdog-based file monitoring | ✅ Production |
| **WhatsApp** | Business API integration | 🔶 Stub |

### 🤖 Intelligent Processing

- **Claude API Integration** with template fallback
- **Automatic plan generation** from action files
- **Risk-based approval routing** (auto-approve low-risk, require approval for high-risk)
- **Step-level execution traceability**

### 🔐 Enterprise Security

```python
# Encrypted credential storage
vault.set_credential("claude_api_key", "sk-ant-...", expires_in_days=90)

# File integrity monitoring
monitor = create_file_integrity_monitor("./AI_Employee_Vault")
monitor.verify_file("./config.yaml")  # Tamper detection

# Immutable audit trail
audit.append(
    event_type=AuditEventTypes.APPROVAL_GRANTED,
    actor="john.doe",
    correlation_id="corr-123"
)
```

### 🛡️ Reliability Patterns

| Pattern | Purpose | Configuration |
|---------|---------|---------------|
| **Circuit Breaker** | Fail fast on service errors | 5 failures → open, 60s timeout |
| **Retry Handler** | Exponential backoff with jitter | 3 retries, 1s-60s delay |
| **Bulkhead** | Concurrency limiting | Max 10 concurrent operations |
| **Dead-Letter Queue** | Failed message handling | Auto-retry or manual review |

---

## 🏗️ Architecture

### Gold Tier Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GOLD TIER ORCHESTRATOR                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    EVENT BUS (Pub/Sub)                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐        │
│  │  WATCHERS   │     │  SERVICES   │     │  EXECUTION  │        │
│  │  (Async)    │     │  (Async)    │     │  (Async)    │        │
│  │ • Gmail     │────▶│ • Claude    │────▶│ • MCP       │        │
│  │ • File      │     │ • Logging   │     │ • Approval  │        │
│  │ • WhatsApp  │     │ • Health    │     │             │        │
│  └─────────────┘     └─────────────┘     └─────────────┘        │
│         │                    │                    │              │
│         └────────────────────┼────────────────────┘              │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │  VAULT STORAGE  │                          │
│                    │  Inbox→Done     │                          │
│                    └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### Component Overview

| Component | File | Responsibility |
|-----------|------|----------------|
| **Orchestrator** | `src/orchestrator.py` | Service lifecycle, health monitoring |
| **EventBus** | `src/lib/event_bus.py` | Pub/sub event distribution |
| **Workflow Engine** | `src/services/workflow_engine.py` | State machine transitions |
| **Claude Service** | `src/services/claude_service.py` | Plan generation |
| **MCP Engine** | `src/services/mcp_execution_engine.py` | Execution with rollback |
| **Approval Engine** | `src/services/approval_rule_engine.py` | Conditional approval rules |
| **Audit Logger** | `src/services/audit_logger.py` | Immutable audit trail |
| **Health Check** | `src/services/health_check.py` | Health endpoints |
| **Metrics** | `src/lib/metrics.py` | Prometheus-style metrics |

---

## 📦 Installation

### Prerequisites

- **Python 3.13+** ([Download](https://www.python.org/downloads/))
- **Git** for version control
- **Gmail OAuth2 credentials** (optional, for email monitoring)
- **Claude API key** (optional, for AI plan generation)
- **Redis** (optional, for distributed deployments)

### Step-by-Step

#### 1. Clone Repository

```bash
git clone https://github.com/your-org/FTE-hackathon.git
cd FTE-hackathon
```

#### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
# Required for full functionality:
# - CLAUDE_API_KEY (Claude plan generation)
# - GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN (Email monitoring)
# - VAULT_MASTER_PASSWORD (Credential encryption)
```

#### 5. Initialize Vault

```bash
python -m src.cli.main vault init
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```env
# Application
VAULT_PATH=./AI_Employee_Vault
LOG_LEVEL=INFO
CONFIG_PATH=./config.yaml

# Claude API (Optional)
CLAUDE_API_KEY=sk-ant-...

# Gmail OAuth2 (Optional)
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret
GMAIL_REFRESH_TOKEN=your-refresh-token

# Security
VAULT_MASTER_PASSWORD=your-master-password

# Redis (Optional for distributed)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

### Configuration File (config.yaml)

```yaml
app:
  name: "AI Employee Foundation"
  vault_path: "./AI_Employee_Vault"

gmail:
  client_id: ${GMAIL_CLIENT_ID}
  client_secret: ${GMAIL_CLIENT_SECRET}
  refresh_token: ${GMAIL_REFRESH_TOKEN}

claude:
  api_key: ${CLAUDE_API_KEY}

logging:
  level: "INFO"
  format: "json"
  file: "logs/app.log"

watcher:
  poll_interval: 30

approval:
  dry_run: true
  rules:
    - rule_id: "high_duration"
      max_estimated_duration: 120
      decision: "require_approval"

performance:
  max_concurrent_actions: 10
  queue_max_size: 10000

security:
  secure_permissions: true
  integrity_monitoring: true
```

---

## 🎯 Usage

### Start the System

```bash
# Start with orchestrator (recommended)
python -m src.cli.main start

# Start with custom config
python -m src.cli.main start --config ./config.yaml --log-level DEBUG

# Quickstart script
python start_gold_tier.py
```

### CLI Commands

```bash
# Vault management
python -m src.cli.main vault init      # Initialize vault
python -m src.cli.main vault check     # Check integrity
python -m src.cli.main vault stats     # View statistics

# Approval management
python -m src.cli.main approval list           # List pending approvals
python -m src.cli.main approval show <ID>      # Show approval details
python -m src.cli.main approval approve <ID>   # Approve action
python -m src.cli.main approval reject <ID> -r "reason"  # Reject

# System control
python -m src.cli.main status          # Check system status
python -m src.cli.main stop            # Stop all services
python -m src.cli.main restart         # Restart services
```

### Approval Workflow

```bash
# 1. List pending approvals
$ python -m src.cli.main approval list

======================================================================
PENDING APPROVALS
======================================================================
📋 abc12345...
   Type: data_analysis
   Duration: 180 minutes
   Risk: high

# 2. Review and approve
$ python -m src.cli.main approval approve abc12345 -r "Business critical"

✅ Approved: abc12345-approval.md
   Status: Moved to Approved/
```

### Monitoring Dashboard

The system auto-updates `Dashboard.md` every 30 seconds:

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
| ✅ Done | 47 |

## Watchers
- **Gmail Watcher**: 🟢 Running
- **File Monitor**: 🟢 Running
- **Claude Service**: 🟢 Running
```

---

## 🔐 Security

### Credential Management

```python
from lib.security import create_credential_vault, SecureEnv

# Initialize encrypted vault
vault = create_credential_vault("./AI_Employee_Vault")

# Store credential (encrypted with Fernet)
vault.set_credential("claude_api_key", "sk-ant-...", expires_in_days=90)

# Retrieve (auto-decrypted)
api_key = vault.get_credential("claude_api_key")

# Or use SecureEnv
SecureEnv.initialize("./AI_Employee_Vault")
api_key = SecureEnv.get("claude_api_key")
```

### File Integrity

```python
from lib.security import create_file_integrity_monitor

monitor = create_file_integrity_monitor("./AI_Employee_Vault")

# Record baseline
monitor.record_file("./config.yaml")

# Verify (detects tampering)
is_valid, message = monitor.verify_file("./config.yaml")
```

### Audit Trail

```python
from lib.security import create_immutable_audit_log, AuditEventTypes

audit = create_immutable_audit_log("./AI_Employee_Vault")

# Log event with correlation ID
audit.append(
    event_type=AuditEventTypes.APPROVAL_GRANTED,
    actor="john.doe",
    action="approved",
    resource="plan",
    resource_id="plan-123",
    correlation_id="corr-456"
)

# Verify chain integrity (detects tampering)
result = audit.verify_chain()
```

---

## 📊 Monitoring

### Health Endpoints

```bash
# Basic health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed

# Prometheus metrics
curl http://localhost:8000/metrics
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `actions_total` | Counter | Total actions processed |
| `action_processing_duration_seconds` | Histogram | Processing latency |
| `approvals_pending` | Gauge | Pending approvals |
| `errors_total` | Counter | Error count |
| `circuit_breaker_state` | Gauge | Circuit breaker status |

### Logs

```bash
# View application logs
tail -f logs/app.log

# View audit logs
cat AI_Employee_Vault/System_Log/Audit/immutable_audit.jsonl

# Export audit log for compliance
python -c "from lib.security import create_immutable_audit_log; \
  audit = create_immutable_audit_log('./AI_Employee_Vault'); \
  audit.export_log('./audit_export.json', start_date='2026-02-01')"
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Gold Tier Summary](GOLD_TIER_SUMMARY.md) | Implementation overview |
| [Workflow Automation](docs/WORKFLOW_AUTOMATION.md) | State machine & transitions |
| [Execution & Approval](docs/EXECUTION_APPROVAL.md) | Execution layer & approvals |
| [Scalability](docs/SCALABILITY_PERFORMANCE.md) | Performance & scaling |
| [Security](docs/SECURITY_PRODUCTION.md) | Security & compliance |
| [Architecture](docs/GOLD_TIER_ARCHITECTURE.md) | System architecture |

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/ --cov-report=html

# Specific test category
pytest tests/test_security.py -v
pytest tests/test_workflow.py -v
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation
- Use async/await for I/O operations
- Include correlation IDs for traceability

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Anthropic** for Claude API
- **Google** for Gmail API
- **Obsidian** for the vault concept
- All contributors and supporters

---

<div align="center">

**AI Employee Foundation - Gold Tier**

*Enterprise-Grade Local-First Automation*

[Report Bug](../../issues) • [Request Feature](../../issues) • [Documentation](docs/)

</div>
