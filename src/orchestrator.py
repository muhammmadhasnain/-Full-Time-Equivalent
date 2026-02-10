"""
Orchestrator for AI Employee Foundation
Manages the lifecycle of all services and coordinates the automation workflow
"""
import asyncio
import signal
import sys
from pathlib import Path
from typing import Dict, List
import logging
import threading
import time

# Add the src directory to the path so we can import modules
sys.path.insert(0, str(Path(__file__).parent))

from services.gmail_watcher import GmailWatcher
from services.claude_service import ClaudeService
from services.file_monitor import FileMonitor
from services.mcp_stub import MCPStub
from services.logging_service import LoggingService
from models.vault import Vault
from lib.utils import setup_logging


class Orchestrator:
    """
    Main orchestrator that manages all services in the AI Employee system.
    Coordinates the workflow between watchers, Claude service, approval system, and execution.
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        """
        Initialize the orchestrator with the given configuration.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.services = {}
        self.running = False
        self.logger = None
        self.setup_logging()
    
    def setup_logging(self):
        """Set up logging for the orchestrator."""
        setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Orchestrator initialized")
    
    def initialize_services(self):
        """Initialize all services managed by the orchestrator."""
        try:
            # Initialize the vault
            vault_path = self.get_config_value("app.vault_path", "./AI_Employee_Vault")
            self.vault = Vault(vault_path)
            
            if not self.vault.exists():
                self.logger.info("Vault does not exist, initializing...")
                self.vault.initialize()
            
            # Initialize services
            self.services['gmail_watcher'] = GmailWatcher(self.config_path)
            self.services['claude_service'] = ClaudeService(self.config_path)
            self.services['file_monitor'] = FileMonitor(self.config_path)
            self.services['mcp_stub'] = MCPStub(self.config_path)
            self.services['logging_service'] = LoggingService()
            
            self.logger.info("All services initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing services: {str(e)}")
            raise
    
    def get_config_value(self, key: str, default=None):
        """
        Get a configuration value from the config file.
        
        Args:
            key: Dot notation key (e.g., "app.name")
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        # This is a simplified implementation
        # In a real implementation, we would load the config file and navigate the nested structure
        return default
    
    def start_service(self, service_name: str):
        """
        Start a specific service.
        
        Args:
            service_name: Name of the service to start
        """
        if service_name not in self.services:
            self.logger.error(f"Service {service_name} not found")
            return False
        
        service = self.services[service_name]
        try:
            # Attempt to call the start method if it exists
            if hasattr(service, 'start'):
                service.start()
                self.logger.info(f"Service {service_name} started")
                return True
            else:
                self.logger.warning(f"Service {service_name} has no start method")
                return False
        except Exception as e:
            self.logger.error(f"Error starting service {service_name}: {str(e)}")
            return False
    
    def stop_service(self, service_name: str):
        """
        Stop a specific service.
        
        Args:
            service_name: Name of the service to stop
        """
        if service_name not in self.services:
            self.logger.error(f"Service {service_name} not found")
            return False
        
        service = self.services[service_name]
        try:
            # Attempt to call the stop method if it exists
            if hasattr(service, 'stop'):
                service.stop()
                self.logger.info(f"Service {service_name} stopped")
                return True
            else:
                self.logger.warning(f"Service {service_name} has no stop method")
                return False
        except Exception as e:
            self.logger.error(f"Error stopping service {service_name}: {str(e)}")
            return False
    
    def start_all_services(self):
        """Start all services managed by the orchestrator."""
        self.logger.info("Starting all services...")
        
        # Start services in a specific order
        service_order = [
            'logging_service',  # Start logging first
            'file_monitor',     # File monitor next
            'gmail_watcher',    # Then watchers
            'claude_service',   # Then Claude service
            'mcp_stub'          # Finally, the execution service
        ]
        
        for service_name in service_order:
            if service_name in self.services:
                self.start_service(service_name)
        
        self.running = True
        self.logger.info("All services started")
    
    def stop_all_services(self):
        """Stop all services managed by the orchestrator."""
        self.logger.info("Stopping all services...")
        
        # Stop services in reverse order
        service_order = [
            'mcp_stub',         # Stop execution service first
            'claude_service',   # Then Claude service
            'gmail_watcher',    # Then watchers
            'file_monitor',     # Then file monitor
            'logging_service'   # Stop logging last
        ]
        
        for service_name in reversed(service_order):
            if service_name in self.services:
                self.stop_service(service_name)
        
        self.running = False
        self.logger.info("All services stopped")
    
    def run(self):
        """Run the orchestrator and keep it alive."""
        self.logger.info("Starting orchestrator...")
        
        try:
            # Initialize all services
            self.initialize_services()
            
            # Start all services
            self.start_all_services()
            
            # Register signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Keep the orchestrator running
            self.logger.info("Orchestrator is running. Press Ctrl+C to stop.")
            
            # In a real implementation, we would use asyncio or threading to handle
            # multiple services concurrently. For now, we'll just sleep in a loop.
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Error in orchestrator: {str(e)}")
        finally:
            self.shutdown()
    
    def signal_handler(self, signum, frame):
        """Handle signals for graceful shutdown."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    def shutdown(self):
        """Shut down the orchestrator and all services."""
        if self.running:
            self.stop_all_services()
            self.logger.info("Orchestrator shutdown complete")
    
    def get_status(self) -> Dict[str, bool]:
        """
        Get the status of all services.
        
        Returns:
            Dictionary mapping service names to their running status
        """
        status = {}
        for name, service in self.services.items():
            # In a real implementation, we would check if the service is actually running
            # For now, we'll just return a placeholder
            status[name] = hasattr(service, 'is_running') and service.is_running()
        return status