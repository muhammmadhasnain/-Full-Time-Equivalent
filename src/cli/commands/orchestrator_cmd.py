"""
Orchestrator CLI Command - Gold Tier
Control the Gold Tier Orchestrator from CLI
"""
import argparse
import sys
import asyncio
import signal
from pathlib import Path
from typing import Optional

# Add the src directory to the path
src_dir = Path(__file__).parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from lib.utils import setup_logging
from lib.event_bus import get_event_bus, EventType


class OrchestratorCommand:
    """Handle orchestrator-related CLI commands."""
    
    def __init__(self, subparsers):
        self.parser = subparsers.add_parser(
            "start",
            help="Start the Gold Tier Orchestrator"
        )
        self.parser.add_argument(
            "--config",
            type=str,
            default="./config.yaml",
            help="Path to configuration file"
        )
        self.parser.add_argument(
            "--log-level",
            type=str,
            default="INFO",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            help="Logging level"
        )
        self.parser.set_defaults(func=self.start)
        
        # Add stop command
        self.stop_parser = subparsers.add_parser(
            "stop",
            help="Stop the Gold Tier Orchestrator"
        )
        self.stop_parser.set_defaults(func=self.stop)
        
        # Add status command
        self.status_parser = subparsers.add_parser(
            "status",
            help="Show orchestrator status"
        )
        self.status_parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON"
        )
        self.status_parser.set_defaults(func=self.status)
        
        # Add restart command
        self.restart_parser = subparsers.add_parser(
            "restart",
            help="Restart the orchestrator or specific services"
        )
        self.restart_parser.add_argument(
            "--services",
            nargs="+",
            help="Specific services to restart"
        )
        self.restart_parser.set_defaults(func=self.restart)
    
    def execute(self, args):
        """Execute the orchestrator command."""
        if hasattr(args, 'func'):
            args.func(args)
        else:
            self.start(args)
    
    def start(self, args):
        """Start the orchestrator."""
        print("=" * 60)
        print("AI Employee Foundation - Gold Tier")
        print("=" * 60)
        
        # Setup logging
        setup_logging(log_level=args.log_level)
        
        try:
            from orchestrator import create_orchestrator
            
            # Create orchestrator with all services
            print(f"Loading configuration from: {args.config}")
            orchestrator = create_orchestrator(args.config)
            
            print("Starting Gold Tier Orchestrator...")
            print()
            
            # Run the orchestrator
            asyncio.run(orchestrator.run())
            
        except KeyboardInterrupt:
            print("\nOrchestrator stopped by user")
        except Exception as e:
            print(f"Error starting orchestrator: {e}")
            sys.exit(1)
    
    def stop(self, args):
        """Stop the orchestrator."""
        print("Sending shutdown signal to orchestrator...")
        
        # In a real implementation, this would send a signal to the running process
        # For now, we just publish a shutdown event
        try:
            event_bus = get_event_bus()
            event_bus.publish(
                EventType.SYSTEM_SHUTDOWN,
                {"source": "cli"},
                source="cli"
            )
            print("Shutdown signal sent")
        except Exception as e:
            print(f"Error sending shutdown signal: {e}")
    
    def status(self, args):
        """Show orchestrator status."""
        try:
            from orchestrator import Orchestrator
            
            orchestrator = Orchestrator()
            status = orchestrator.get_status()
            
            if args.json:
                import json
                print(json.dumps(status, indent=2))
            else:
                orchestrator.print_status()
                
        except Exception as e:
            print(f"Error getting status: {e}")
    
    def restart(self, args):
        """Restart the orchestrator or specific services."""
        print("Sending restart signal...")
        
        try:
            event_bus = get_event_bus()
            event_bus.publish(
                EventType.SYSTEM_RESTART,
                {"services": args.services} if args.services else {},
                source="cli"
            )
            print("Restart signal sent")
            
            if args.services:
                print(f"Services to restart: {', '.join(args.services)}")
            else:
                print("All services will be restarted")
                
        except Exception as e:
            print(f"Error sending restart signal: {e}")
