"""
Gold Tier Orchestrator
Central lifecycle management, event routing, health monitoring, and graceful shutdown
"""
import asyncio
import signal
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from lib.event_bus import EventBus, EventType, Event, publish_event, get_event_bus
from lib.utils import setup_logging, get_current_iso_timestamp
from models.vault import Vault


class ServiceState(Enum):
    """Service lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    UNHEALTHY = "unhealthy"


@dataclass
class ServiceHealth:
    """Health status of a service."""
    service_name: str
    state: ServiceState
    last_check: str = field(default_factory=lambda: get_current_iso_timestamp())
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "last_check": self.last_check,
            "last_error": self.last_error,
            "metrics": self.metrics
        }


class Orchestrator:
    """
    Gold Tier Orchestrator - Central system coordinator.
    
    Responsibilities:
    - Service lifecycle management (start, stop, restart)
    - Event-driven communication coordination
    - Health monitoring and alerting
    - Graceful shutdown handling
    - Centralized status logging
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        self.config_path = config_path
        self.config = {}
        
        # Core components
        self.event_bus = get_event_bus()
        self.vault: Optional[Vault] = None
        self.logger = logging.getLogger("Orchestrator")
        
        # Services
        self._services: Dict[str, Any] = {}
        self._service_states: Dict[str, ServiceHealth] = {}
        self._service_tasks: Dict[str, asyncio.Task] = {}
        
        # State
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._start_time: Optional[str] = None
        self._event_count = 0
        
        # Setup
        self._load_config()
        self._setup_signal_handlers()
        
        self.logger.info("Gold Tier Orchestrator initialized")
    
    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            # Extract key config values
            vault_path = self.config.get('app', {}).get('vault_path', './AI_Employee_Vault')
            self._health_check_interval = self.config.get('watcher', {}).get('poll_interval', 30)
            
            self.logger.info(f"Configuration loaded from {self.config_path}")
            self.logger.info(f"Vault path: {vault_path}")
            
        except Exception as e:
            self.logger.warning(f"Could not load config from {self.config_path}: {e}")
            self.config = {
                'app': {'vault_path': './AI_Employee_Vault'},
                'watcher': {'poll_interval': 30}
            }
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        # Note: Signal handlers work differently on Windows
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            self.logger.info("Signal handlers registered")
        except ValueError:
            # Signal handlers can only be set from main thread
            self.logger.warning("Could not register signal handlers (not in main thread)")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        asyncio.create_task(self.shutdown())
    
    # ========== Service Registration ==========
    
    def register_service(self, name: str, service: Any, start_method: str = "start", stop_method: str = "stop"):
        """
        Register a service with the orchestrator.
        
        Args:
            name: Unique service identifier
            service: Service instance
            start_method: Name of the start method
            stop_method: Name of the stop method
        """
        self._services[name] = {
            'instance': service,
            'start_method': start_method,
            'stop_method': stop_method
        }
        self._service_states[name] = ServiceHealth(
            service_name=name,
            state=ServiceState.STOPPED
        )
        self.logger.info(f"Service registered: {name}")
        
        # Publish service registered event
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": name, "action": "registered"},
            source="orchestrator"
        )
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a registered service instance."""
        service_info = self._services.get(name)
        return service_info['instance'] if service_info else None
    
    # ========== Service Lifecycle ==========
    
    async def start_service(self, name: str) -> bool:
        """
        Start a registered service.
        
        Args:
            name: Service name
            
        Returns:
            True if started successfully
        """
        if name not in self._services:
            self.logger.error(f"Service not found: {name}")
            return False
        
        service_info = self._services[name]
        service = service_info['instance']
        
        try:
            self._service_states[name].state = ServiceState.STARTING
            self.logger.info(f"Starting service: {name}")
            
            # Call start method (can be sync or async)
            start_method = getattr(service, service_info['start_method'], None)
            if start_method:
                if asyncio.iscoroutinefunction(start_method):
                    await start_method()
                else:
                    # Run sync method in executor to not block
                    await asyncio.get_event_loop().run_in_executor(None, start_method)
            
            self._service_states[name].state = ServiceState.RUNNING
            self._service_states[name].last_check = get_current_iso_timestamp()
            
            publish_event(
                EventType.SERVICE_STARTED,
                {"service": name, "timestamp": get_current_iso_timestamp()},
                source="orchestrator"
            )
            
            self.logger.info(f"Service started: {name}")
            return True
            
        except Exception as e:
            self._service_states[name].state = ServiceState.ERROR
            self._service_states[name].last_error = str(e)
            self.logger.error(f"Failed to start service {name}: {e}")
            
            publish_event(
                EventType.SERVICE_ERROR,
                {"service": name, "error": str(e)},
                source="orchestrator"
            )
            return False
    
    async def stop_service(self, name: str) -> bool:
        """
        Stop a registered service.
        
        Args:
            name: Service name
            
        Returns:
            True if stopped successfully
        """
        if name not in self._services:
            self.logger.error(f"Service not found: {name}")
            return False
        
        service_info = self._services[name]
        service = service_info['instance']
        
        try:
            self._service_states[name].state = ServiceState.STOPPING
            self.logger.info(f"Stopping service: {name}")
            
            # Cancel any running task for this service
            if name in self._service_tasks:
                self._service_tasks[name].cancel()
                try:
                    await self._service_tasks[name]
                except asyncio.CancelledError:
                    pass
                del self._service_tasks[name]
            
            # Call stop method
            stop_method = getattr(service, service_info['stop_method'], None)
            if stop_method:
                if asyncio.iscoroutinefunction(stop_method):
                    await stop_method()
                else:
                    await asyncio.get_event_loop().run_in_executor(None, stop_method)
            
            self._service_states[name].state = ServiceState.STOPPED
            self._service_states[name].last_check = get_current_iso_timestamp()
            
            publish_event(
                EventType.SERVICE_STOPPED,
                {"service": name, "timestamp": get_current_iso_timestamp()},
                source="orchestrator"
            )
            
            self.logger.info(f"Service stopped: {name}")
            return True
            
        except Exception as e:
            self._service_states[name].state = ServiceState.ERROR
            self._service_states[name].last_error = str(e)
            self.logger.error(f"Error stopping service {name}: {e}")
            return False
    
    async def restart_service(self, name: str) -> bool:
        """Restart a service."""
        self.logger.info(f"Restarting service: {name}")
        await self.stop_service(name)
        await asyncio.sleep(1)  # Brief pause
        return await self.start_service(name)
    
    async def start_all_services(self):
        """Start all registered services."""
        self.logger.info("Starting all services...")
        
        # Start services in order
        for name in self._services.keys():
            await self.start_service(name)
        
        self.logger.info("All services started")
    
    async def stop_all_services(self):
        """Stop all registered services in reverse order."""
        self.logger.info("Stopping all services...")
        
        # Stop in reverse order
        for name in reversed(list(self._services.keys())):
            await self.stop_service(name)
        
        self.logger.info("All services stopped")
    
    # ========== Health Monitoring ==========
    
    async def _health_check_loop(self):
        """Periodic health check loop."""
        while self._running:
            await self._perform_health_checks()
            await asyncio.sleep(self._health_check_interval)
    
    async def _perform_health_checks(self):
        """Perform health checks on all services."""
        for name, service_info in self._services.items():
            if self._service_states[name].state != ServiceState.RUNNING:
                continue
            
            service = service_info['instance']
            
            try:
                # Check if service has a health_check method
                health_check = getattr(service, 'health_check', None)
                if health_check:
                    if asyncio.iscoroutinefunction(health_check):
                        is_healthy = await health_check()
                    else:
                        is_healthy = health_check()
                    
                    if not is_healthy:
                        self._service_states[name].state = ServiceState.UNHEALTHY
                        self.logger.warning(f"Service unhealthy: {name}")
                    else:
                        self._service_states[name].state = ServiceState.RUNNING
                    
                    # Update metrics if available
                    get_metrics = getattr(service, 'get_metrics', None)
                    if get_metrics:
                        if asyncio.iscoroutinefunction(get_metrics):
                            self._service_states[name].metrics = await get_metrics()
                        else:
                            self._service_states[name].metrics = get_metrics()
                
                self._service_states[name].last_check = get_current_iso_timestamp()
                
            except Exception as e:
                self._service_states[name].state = ServiceState.ERROR
                self._service_states[name].last_error = str(e)
                self.logger.error(f"Health check failed for {name}: {e}")
        
        # Publish health status event
        health_status = self.get_system_health()
        publish_event(
            EventType.HEALTH_STATUS,
            health_status,
            source="orchestrator"
        )
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        return {
            "timestamp": get_current_iso_timestamp(),
            "orchestrator_state": "running" if self._running else "stopped",
            "uptime_since": self._start_time,
            "services": {
                name: health.to_dict() 
                for name, health in self._service_states.items()
            },
            "event_bus_stats": self.event_bus.get_stats(),
            "total_events_processed": self._event_count
        }
    
    # ========== Event Handling ==========
    
    def _setup_event_handlers(self):
        """Setup internal event handlers."""
        self.event_bus.subscribe(
            EventType.SYSTEM_SHUTDOWN,
            lambda e: asyncio.create_task(self.shutdown()),
            async_callback=True
        )
        
        self.event_bus.subscribe(
            EventType.SYSTEM_RESTART,
            lambda e: asyncio.create_task(self._handle_restart(e)),
            async_callback=True
        )
        
        # Count all events for metrics
        def count_event(event: Event):
            self._event_count += 1
        
        for event_type in EventType:
            self.event_bus.subscribe(event_type, count_event)
    
    async def _handle_restart(self, event: Event):
        """Handle system restart request."""
        services_to_restart = event.payload.get('services', list(self._services.keys()))
        self.logger.info(f"Restart requested for: {services_to_restart}")
        
        for name in services_to_restart:
            await self.restart_service(name)
    
    # ========== Vault Management ==========
    
    def initialize_vault(self) -> Vault:
        """Initialize or verify the vault."""
        vault_path = self.config.get('app', {}).get('vault_path', './AI_Employee_Vault')
        self.vault = Vault(vault_path)
        
        if not self.vault.exists():
            self.logger.info("Vault does not exist, initializing...")
            self.vault.initialize()
        else:
            self.logger.info("Vault verified")
        
        return self.vault
    
    # ========== Main Run Loop ==========
    
    async def run(self):
        """
        Main run loop - starts all services and runs until shutdown.
        """
        self._running = True
        self._start_time = get_current_iso_timestamp()
        
        self.logger.info("=" * 60)
        self.logger.info("Gold Tier Orchestrator Starting")
        self.logger.info("=" * 60)
        
        try:
            # Initialize vault
            self.initialize_vault()
            
            # Setup event handlers
            self._setup_event_handlers()
            
            # Start all services
            await self.start_all_services()
            
            # Start health check loop
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            self.logger.info("=" * 60)
            self.logger.info("Orchestrator is running. Press Ctrl+C to stop.")
            self.logger.info("=" * 60)
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except asyncio.CancelledError:
            self.logger.info("Orchestrator task cancelled")
        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown of all services."""
        if not self._running:
            return
        
        self.logger.info("Initiating graceful shutdown...")
        self._running = False
        
        # Publish shutdown event
        publish_event(
            EventType.SYSTEM_SHUTDOWN,
            {"timestamp": get_current_iso_timestamp()},
            source="orchestrator"
        )
        
        # Stop health check loop
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Stop all services
        await self.stop_all_services()
        
        # Signal shutdown complete
        self._shutdown_event.set()
        
        self.logger.info("Orchestrator shutdown complete")
    
    def request_shutdown(self):
        """Request shutdown (can be called from sync code)."""
        asyncio.create_task(self.shutdown())
    
    def request_restart(self, services: Optional[List[str]] = None):
        """Request restart of specific services or all."""
        publish_event(
            EventType.SYSTEM_RESTART,
            {"services": services or list(self._services.keys())},
            source="orchestrator"
        )
    
    # ========== Status & Metrics ==========
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "running": self._running,
            "start_time": self._start_time,
            "uptime_seconds": (
                (datetime.utcnow() - datetime.fromisoformat(self._start_time.replace('Z', '+00:00'))).total_seconds()
                if self._start_time else 0
            ),
            "services": {
                name: state.to_dict() 
                for name, state in self._service_states.items()
            },
            "event_bus": self.event_bus.get_stats(),
            "events_processed": self._event_count,
            "vault_path": self.config.get('app', {}).get('vault_path', './AI_Employee_Vault')
        }
    
    def print_status(self):
        """Print formatted status to console."""
        status = self.get_status()
        
        print("\n" + "=" * 60)
        print("ORCHESTRATOR STATUS")
        print("=" * 60)
        print(f"Running: {status['running']}")
        print(f"Uptime: {status['uptime_seconds']:.0f} seconds")
        print(f"Events Processed: {status['events_processed']}")
        print()
        print("SERVICES:")
        for name, state in status['services'].items():
            state_icon = "✅" if state['state'] == 'running' else "❌" if state['state'] == 'error' else "⏸️"
            print(f"  {state_icon} {name}: {state['state']}")
            if state.get('last_error'):
                print(f"      Error: {state['last_error']}")
        print()
        print("EVENT BUS:")
        eb_stats = status['event_bus']
        print(f"  Subscribers: {eb_stats['total_subscribers']}")
        print(f"  Events in History: {eb_stats['events_in_history']}")
        print("=" * 60 + "\n")


# ========== Bootstrap Function ==========

def create_orchestrator(config_path: str = "./config.yaml") -> Orchestrator:
    """
    Factory function to create and configure orchestrator with all services.
    
    This is the main entry point for bootstrapping the Gold Tier system.
    """
    orchestrator = Orchestrator(config_path)
    
    # Import services here to avoid circular imports
    from services.gmail_watcher import GmailWatcher
    from services.claude_service import ClaudeService
    from services.file_monitor import FileMonitor
    from services.mcp_service import MCPService
    from services.logging_service import LoggingService
    from services.workflow_engine import WorkflowEngine
    from services.dashboard_updater import DashboardAutoUpdater
    
    # Initialize vault first
    orchestrator.initialize_vault()
    
    # Create workflow engine (core automation)
    workflow_engine = WorkflowEngine(str(orchestrator.vault.vault_path), config_path)
    
    # Register services
    orchestrator.register_service("logging", LoggingService())
    orchestrator.register_service("workflow_engine", workflow_engine)
    orchestrator.register_service("file_monitor", FileMonitor())
    orchestrator.register_service("gmail_watcher", GmailWatcher())
    orchestrator.register_service("claude_service", ClaudeService())
    orchestrator.register_service("mcp_service", MCPService())
    orchestrator.register_service("dashboard_updater", DashboardAutoUpdater(str(orchestrator.vault.vault_path)))
    
    return orchestrator


async def main():
    """Main entry point."""
    orchestrator = create_orchestrator()
    await orchestrator.run()


if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Run the orchestrator
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOrchestrator stopped by user")
