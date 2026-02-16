# Orchestrator Bootstrap Code Structure

## Quick Start

### Method 1: Using the Quickstart Script

```bash
python start_gold_tier.py
```

### Method 2: Using CLI

```bash
python -m src.cli.main start
```

### Method 3: Direct Import

```python
import asyncio
from src.orchestrator import create_orchestrator

async def main():
    orchestrator = create_orchestrator("./config.yaml")
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Bootstrap Code Structure

### Basic Bootstrap

```python
#!/usr/bin/env python3
"""
Basic Orchestrator Bootstrap
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lib.utils import setup_logging
from orchestrator import Orchestrator

# Setup
setup_logging(log_level="INFO")

# Create orchestrator
orchestrator = Orchestrator(config_path="./config.yaml")

# Initialize vault
orchestrator.initialize_vault()

# Register services
from services.file_monitor import create_file_monitor
from services.claude_service import create_claude_service
from services.logging_service import create_logging_service

orchestrator.register_service("logging", create_logging_service())
orchestrator.register_service("file_monitor", create_file_monitor())
orchestrator.register_service("claude_service", create_claude_service())

# Run
asyncio.run(orchestrator.run())
```

### Full Bootstrap with All Services

```python
#!/usr/bin/env python3
"""
Full Gold Tier Bootstrap with All Services
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from lib.utils import setup_logging
from orchestrator import Orchestrator

def create_full_orchestrator(config_path: str = "./config.yaml"):
    """Create orchestrator with all Gold Tier services."""
    
    # Initialize
    setup_logging(log_level="INFO")
    orchestrator = Orchestrator(config_path)
    
    # Initialize vault
    orchestrator.initialize_vault()
    
    # Create services
    from services.logging_service import create_logging_service
    from services.file_monitor import create_file_monitor
    from services.gmail_watcher import create_gmail_watcher
    from services.claude_service import create_claude_service
    from services.mcp_service import create_mcp_service
    from services.whatsapp_watcher import create_whatsapp_watcher
    
    # Register services
    orchestrator.register_service("logging", create_logging_service())
    orchestrator.register_service("file_monitor", create_file_monitor())
    orchestrator.register_service("gmail_watcher", create_gmail_watcher())
    orchestrator.register_service("claude_service", create_claude_service())
    orchestrator.register_service("mcp_service", create_mcp_service(dry_run=True))
    orchestrator.register_service("whatsapp_watcher", create_whatsapp_watcher())
    
    return orchestrator

async def main():
    orchestrator = create_full_orchestrator()
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Bootstrap with Event Handlers

```python
#!/usr/bin/env python3
"""
Custom Bootstrap with Custom Event Handlers
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from lib.utils import setup_logging
from lib.event_bus import get_event_bus, EventType, Event
from orchestrator import Orchestrator

def custom_event_handler(event: Event):
    """Custom handler for specific events."""
    print(f"📧 Event received: {event.event_type.value}")
    print(f"   Payload: {event.payload}")

async def main():
    setup_logging(log_level="DEBUG")
    orchestrator = Orchestrator()
    orchestrator.initialize_vault()
    
    # Register services
    from services.file_monitor import create_file_monitor
    from services.claude_service import create_claude_service
    
    orchestrator.register_service("file_monitor", create_file_monitor())
    orchestrator.register_service("claude_service", create_claude_service())
    
    # Add custom event handlers
    event_bus = get_event_bus()
    event_bus.subscribe(EventType.ACTION_GENERATED, custom_event_handler)
    event_bus.subscribe(EventType.PLAN_CREATED, custom_event_handler)
    
    # Start
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
```

### Production Bootstrap with Error Handling

```python
#!/usr/bin/env python3
"""
Production Bootstrap with Error Handling
"""
import asyncio
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from lib.utils import setup_logging
from orchestrator import Orchestrator

logger = logging.getLogger(__name__)

def create_production_orchestrator():
    """Create orchestrator with production settings."""
    
    # Validate environment
    required_env = ['CLAUDE_API_KEY', 'VAULT_PATH']
    missing = [env for env in required_env if not os.getenv(env)]
    
    if missing:
        logger.warning(f"Missing environment variables: {missing}")
        logger.warning("Some features may be limited")
    
    # Create orchestrator
    orchestrator = Orchestrator(config_path="./config.yaml")
    orchestrator.initialize_vault()
    
    # Register services
    from services.logging_service import create_logging_service
    from services.file_monitor import create_file_monitor
    from services.gmail_watcher import create_gmail_watcher
    from services.claude_service import create_claude_service
    from services.mcp_service import create_mcp_service
    
    orchestrator.register_service("logging", create_logging_service())
    orchestrator.register_service("file_monitor", create_file_monitor())
    orchestrator.register_service("gmail_watcher", create_gmail_watcher())
    orchestrator.register_service("claude_service", create_claude_service())
    orchestrator.register_service("mcp_service", create_mcp_service(dry_run=True))
    
    return orchestrator

async def main():
    try:
        logger.info("Starting Gold Tier Orchestrator...")
        orchestrator = create_production_orchestrator()
        
        # Print status
        print("\n" + "=" * 60)
        print("Gold Tier Orchestrator Starting")
        print("=" * 60)
        print(f"Vault: {orchestrator.config.get('app', {}).get('vault_path')}")
        print(f"Services: {list(orchestrator._services.keys())}")
        print("=" * 60 + "\n")
        
        await orchestrator.run()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

### Minimal Bootstrap (Testing)

```python
#!/usr/bin/env python3
"""
Minimal Bootstrap for Testing
"""
import asyncio
from src.orchestrator import Orchestrator

async def test():
    orchestrator = Orchestrator()
    orchestrator.initialize_vault()
    
    # Just test file monitor
    from src.services.file_monitor import FileMonitor
    orchestrator.register_service("file_monitor", FileMonitor())
    
    # Run for 10 seconds then stop
    import time
    async def stop_after_delay():
        await asyncio.sleep(10)
        await orchestrator.shutdown()
    
    await asyncio.gather(
        orchestrator.run(),
        stop_after_delay()
    )

if __name__ == "__main__":
    asyncio.run(test())
```

## Service Registration Patterns

### Pattern 1: Factory Functions (Recommended)

```python
from services.claude_service import create_claude_service

orchestrator.register_service("claude_service", create_claude_service())
```

### Pattern 2: Direct Instantiation

```python
from services.claude_service import ClaudeService

service = ClaudeService(config_path="./config.yaml")
orchestrator.register_service("claude_service", service)
```

### Pattern 3: Lazy Initialization

```python
def get_claude_service():
    from services.claude_service import ClaudeService
    return ClaudeService()

orchestrator.register_service("claude_service", get_claude_service())
```

## Event Subscription Examples

### Subscribe to File Events

```python
from lib.event_bus import get_event_bus, EventType

event_bus = get_event_bus()

def on_file_created(event):
    print(f"File created: {event.payload['path']}")

event_bus.subscribe(EventType.FILE_CREATED, on_file_created)
```

### Subscribe to Action Events

```python
def on_action_generated(event):
    action_id = event.payload['action_id']
    print(f"Action generated: {action_id}")

event_bus.subscribe(EventType.ACTION_GENERATED, on_action_generated)
```

### Subscribe with Async Handler

```python
async def on_plan_created(event):
    print(f"Plan created: {event.payload['plan_id']}")

event_bus.subscribe(EventType.PLAN_CREATED, on_plan_created, async_callback=True)
```

## Health Check Examples

### Get System Health

```python
from orchestrator import Orchestrator

orchestrator = Orchestrator()
health = orchestrator.get_system_health()

print(f"Orchestrator state: {health['orchestrator_state']}")
print(f"Uptime: {health['uptime_since']}")

for service_name, service_health in health['services'].items():
    print(f"{service_name}: {service_health['state']}")
```

### Manual Health Check

```python
from services.claude_service import ClaudeService

service = ClaudeService()
is_healthy = service.health_check()
metrics = service.get_metrics()

print(f"Healthy: {is_healthy}")
print(f"Metrics: {metrics}")
```

## Configuration Examples

### Minimal config.yaml

```yaml
app:
  vault_path: "./AI_Employee_Vault"

claude:
  api_key: "${CLAUDE_API_KEY}"

logging:
  level: "INFO"
  file: "logs/app.log"
```

### Full config.yaml

```yaml
app:
  name: "AI Employee Foundation"
  env: "production"
  vault_path: "./AI_Employee_Vault"

gmail:
  client_id: "${GMAIL_CLIENT_ID}"
  client_secret: "${GMAIL_CLIENT_SECRET}"
  refresh_token: "${GMAIL_REFRESH_TOKEN}"

claude:
  api_key: "${CLAUDE_API_KEY}"

logging:
  level: "INFO"
  format: "json"
  file: "logs/app.log"

watcher:
  poll_interval: 30
  max_retries: 3

approval:
  dry_run: true
```

## Docker Deployment (Future)

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV VAULT_PATH=/data/vault
ENV LOG_LEVEL=INFO

CMD ["python", "-m", "src.orchestrator"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  orchestrator:
    build: .
    volumes:
      - ./AI_Employee_Vault:/data/vault
      - ./logs:/app/logs
    environment:
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - VAULT_PATH=/data/vault
    restart: unless-stopped
```
