# Gold Tier Architecture Documentation

## Overview

The Gold Tier architecture transforms the AI Employee Foundation from a polling-based system to a fully **event-driven architecture** with centralized orchestration, real-time event propagation, and production-ready service management.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           GOLD TIER ORCHESTRATOR                                 │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                            EVENT BUS (Pub/Sub)                           │    │
│  │                                                                          │    │
│  │  Event Types:                                                            │    │
│  │  • file.created, file.modified, file.moved, file.deleted                │    │
│  │  • action.generated, action.processed, action.approved, action.executed │    │
│  │  • plan.created, plan.approved, plan.execution_completed                 │    │
│  │  • email.received, whatsapp.message_received                             │    │
│  │  • health.check, health.status, service.started, service.stopped         │    │
│  │  • approval.required, approval.granted, system.shutdown                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│         ┌────────────────────────────┼────────────────────────────┐              │
│         │                            │                            │              │
│  ┌──────▼──────┐            ┌───────▼───────┐           ┌───────▼──────┐        │
│  │   WATCHERS  │            │   SERVICES    │           │  EXECUTION   │        │
│  │             │            │               │           │              │        │
│  │ ┌─────────┐ │  Events    │ ┌───────────┐ │  Events   │ ┌──────────┐ │        │
│  │ │  Gmail  │ │───────────▶│ │  Claude   │ │──────────▶│ │   MCP    │ │        │
│  │ │ Watcher │ │  action    │ │  Service  │ │  plan     │ │  Service │ │        │
│  │ └─────────┘ │  generated │ └───────────┘ │  created  │ └──────────┘ │        │
│  │             │            │               │           │              │        │
│  │ ┌─────────┐ │  Events    │ ┌───────────┐ │           │ ┌──────────┐ │        │
│  │ │  File   │ │───────────▶│ │  Health   │ │           │ │Approval  │ │        │
│  │ │ Watcher │ │  file      │ │   Check   │ │           │ │ Service  │ │        │
│  │ └─────────┘ │  created   │ └───────────┘ │           │ └──────────┘ │        │
│  │             │            │               │           │              │        │
│  │ ┌─────────┐ │  Events    │ ┌───────────┐ │           │              │        │
│  │ │WhatsApp │ │───────────▶│ │  Logging  │ │           │              │        │
│  │ │ Watcher │ │  system    │ │  Service  │ │           │              │        │
│  │ └─────────┘ │  status    │ └───────────┘ │           │              │        │
│  └─────────────┴────────────┴───────────────┴───────────┴──────────────┘        │
│                                      │                                           │
│                            ┌─────────▼─────────┐                                │
│                            │   VAULT STORAGE   │                                │
│                            │                   │                                │
│                            │ Inbox → Needs_    │                                │
│                            │ Action → Plans →  │                                │
│                            │ Pending_Approval  │                                │
│                            │ → Approved → Done │                                │
│                            └───────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Event Flow: Inbox → Needs_Action → Plans

### Complete Flow

```
1. USER drops file in Inbox/
   └─▶ FileMonitor detects: FILE_CREATED event
       └─▶ Event payload: {path, filename, folder: "Inbox"}

2. FileMonitor handles FILE_CREATED
   └─▶ Creates ActionFile in Needs_Action/
   └─▶ Publishes: ACTION_GENERATED event
       └─▶ Event payload: {action_id, action_type, action_path, source}

3. ClaudeService receives ACTION_GENERATED
   └─▶ Loads ActionFile
   └─▶ Calls Claude API (or uses template)
   └─▶ Generates PlanFile
   └─▶ Saves to Plans/
   └─▶ Publishes: PLAN_CREATED event
       └─▶ Event payload: {plan_id, action_id, plan_path, requires_approval}

4. If Approval Required:
   └─▶ Publishes: APPROVAL_REQUIRED event
   └─▶ User moves plan to Pending_Approval/

5. USER approves by moving to Approved/
   └─▶ FileMonitor detects: FILE_MOVED event
   └─▶ Publishes: ACTION_APPROVED event

6. MCPService receives ACTION_APPROVED
   └─▶ Executes plan steps
   └─▶ Publishes: PLAN_EXECUTION_COMPLETED event
   └─▶ Moves plan to Done/
```

## Module Responsibilities

### Core Infrastructure

| Module | File | Responsibility |
|--------|------|---------------|
| **Orchestrator** | `src/orchestrator.py` | Central lifecycle management, service registration, health monitoring, graceful shutdown |
| **EventBus** | `src/lib/event_bus.py` | Pub/sub event distribution, subscriber management, event history |
| **LoggingService** | `src/services/logging_service.py` | Structured JSON logging, log aggregation, event logging |

### Watchers (Event Sources)

| Module | File | Responsibility |
|--------|------|---------------|
| **FileMonitor** | `src/services/file_monitor.py` | Watchdog-based filesystem events, inbox-to-action conversion |
| **GmailWatcher** | `src/services/gmail_watcher.py` | Gmail API polling, OAuth2 auth, email-to-action conversion |
| **WhatsAppWatcher** | `src/services/whatsapp_watcher.py` | WhatsApp Business API stub, message-to-action conversion |

### Services (Event Processors)

| Module | File | Responsibility |
|--------|------|---------------|
| **ClaudeService** | `src/services/claude_service.py` | Claude API integration, plan generation, approval detection |
| **MCPService** | `src/services/mcp_service.py` | Plan execution, dry-run support, execution tracking |

### Models

| Module | File | Responsibility |
|--------|------|---------------|
| **ActionFile** | `src/models/action_file.py` | Action representation, YAML serialization |
| **PlanFile** | `src/models/plan_file.py` | Plan representation, Markdown with frontmatter |
| **Vault** | `src/models/vault.py` | Vault initialization, folder structure |

## Service Lifecycle

### States

```
STOPPED → STARTING → RUNNING → STOPPING → STOPPED
                     ↓
                   ERROR
                     ↓
                UNHEALTHY
```

### Health Checks

The orchestrator performs periodic health checks every 30 seconds:

```python
async def _perform_health_checks(self):
    for name, service_info in self._services.items():
        health_check = getattr(service, 'health_check', None)
        if health_check:
            is_healthy = await health_check()
            # Update service state based on result
```

### Graceful Shutdown

```
1. Signal received (SIGINT/SIGTERM) or SYSTEM_SHUTDOWN event
2. Orchestrator sets _running = False
3. Publish SYSTEM_SHUTDOWN event
4. Cancel health check loop
5. Stop all services in reverse order
6. Flush logs
7. Exit
```

## Production Deployment

### Prerequisites

```bash
# Python 3.13+
python --version

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CLAUDE_API_KEY="your-api-key"
export GMAIL_CLIENT_ID="your-client-id"
export GMAIL_CLIENT_SECRET="your-client-secret"
export GMAIL_REFRESH_TOKEN="your-refresh-token"
export VAULT_PATH="./AI_Employee_Vault"
```

### Starting the System

```bash
# Start via CLI
python -m src.cli.main start

# Or directly
python -m src.orchestrator

# With custom config
python -m src.cli.main start --config ./config.yaml --log-level DEBUG
```

### Configuration (config.yaml)

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
```

### Monitoring

```bash
# Check status
python -m src.cli.main status

# JSON output
python -m src.cli.main status --json

# View logs
tail -f logs/app.log
```

### Event History

The EventBus maintains a history of the last 1000 events:

```python
from lib.event_bus import get_event_bus

event_bus = get_event_bus()
history = event_bus.get_event_history(limit=50)
stats = event_bus.get_stats()
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/ --cov-report=html

# Test specific component
pytest tests/test_orchestrator.py -v
```

## Key Differences: Silver → Gold Tier

| Aspect | Silver Tier | Gold Tier |
|--------|-------------|-----------|
| **Architecture** | Polling-based | Event-driven |
| **Communication** | Direct calls | Pub/Sub EventBus |
| **Service Management** | Manual | Orchestrator |
| **Health Monitoring** | None | Periodic checks |
| **Shutdown** | Abrupt | Graceful |
| **Logging** | Text | Structured JSON |
| **Claude Integration** | Template-only | Real API + fallback |
| **Execution** | Stub | Full MCP Service |
| **CLI** | Basic | Full orchestrator control |

## Troubleshooting

### Service won't start

```bash
# Check logs
tail -f logs/app.log

# Verify config
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"

# Check environment variables
env | grep -E 'CLAUDE|GMAIL|VAULT'
```

### Events not propagating

```python
# Check EventBus stats
from lib.event_bus import get_event_bus
print(get_event_bus().get_stats())

# Check event history
print(get_event_bus().get_event_history(limit=10))
```

### Health check failing

```python
# Check service state
python -m src.cli.main status --json | jq '.services'
```

## Future Enhancements

1. **WhatsApp Integration**: Complete WhatsApp Business API integration
2. **Dashboard**: Real-time web dashboard with WebSocket updates
3. **Alerting**: Slack/Email alerts for failures
4. **Metrics Export**: Prometheus/Grafana integration
5. **Distributed Mode**: Multi-instance support with Redis pub/sub
