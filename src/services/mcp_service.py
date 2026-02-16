"""
MCP Service - Gold Tier
Model Context Protocol execution service for approved actions
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import yaml
import json

# Add the src directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.event_bus import EventType, publish_event, get_event_bus
from lib.utils import get_current_iso_timestamp, ensure_directory_exists
from lib.exceptions import MCPStubError
from models.plan_file import PlanFile


class MCPService:
    """
    Gold Tier MCP Service - Plan execution with dry-run support.
    
    Responsibilities:
    - Execute approved plans from the Approved/ folder
    - Support dry-run mode with "WOULD SEND" logging
    - Track execution results
    - Move completed plans to Done/
    - Publish execution events
    """
    
    def __init__(self, config_path: str = "./config.yaml", dry_run: bool = True):
        self.config_path = config_path
        self.config = {}
        self.dry_run = dry_run
        self.vault_path: Optional[str] = None
        self.logger = logging.getLogger("MCPService")
        self.event_bus = get_event_bus()
        
        # State
        self._running = False
        self._execution_task: Optional[asyncio.Task] = None
        self._poll_interval: int = 30  # seconds
        
        # Execution tracking
        self._execution_history: List[Dict[str, Any]] = []
        self._plans_executed = 0
        self._plans_failed = 0
        self._last_execution: Optional[str] = None
        
        # Load configuration
        self._load_config()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        self.logger.info(f"MCPService initialized (dry_run={self.dry_run})")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            self.vault_path = self.config.get('app', {}).get('vault_path', './AI_Employee_Vault')
            self.dry_run = self.config.get('approval', {}).get('dry_run', True)
            self._poll_interval = self.config.get('watcher', {}).get('poll_interval', 30)
            
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            self.vault_path = './AI_Employee_Vault'
    
    def _setup_event_handlers(self):
        """Setup event bus handlers."""
        # Listen for approval granted events
        self.event_bus.subscribe(
            EventType.ACTION_APPROVED,
            self._on_action_approved,
            async_callback=True
        )
        
        self.logger.info("MCPService event handlers registered")
    
    async def _on_action_approved(self, event):
        """Handle action.approved events."""
        plan_path = event.payload.get('path')
        if plan_path:
            await self.execute_plan_from_path(plan_path)
    
    async def start(self):
        """Start the MCP service."""
        self._running = True
        
        # Start execution monitoring loop
        self._execution_task = asyncio.create_task(self._execution_loop())
        
        self.logger.info(f"MCPService started (dry_run={self.dry_run})")
        
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": "mcp_service"},
            source="mcp_service"
        )
    
    async def stop(self):
        """Stop the MCP service."""
        if not self._running:
            return
        
        self._running = False
        
        if self._execution_task:
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("MCPService stopped")
        
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "mcp_service"},
            source="mcp_service"
        )
    
    def health_check(self) -> bool:
        """Check service health."""
        if not self._running:
            return False
        
        # Check if execution task is running
        return self._execution_task is not None and not self._execution_task.done()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "plans_executed": self._plans_executed,
            "plans_failed": self._plans_failed,
            "last_execution": self._last_execution,
            "dry_run": self.dry_run,
            "execution_history_count": len(self._execution_history),
            "poll_interval": self._poll_interval
        }
    
    async def _execution_loop(self):
        """Main execution monitoring loop."""
        while self._running:
            try:
                await self._check_approved_plans()
            except Exception as e:
                self.logger.error(f"Execution loop error: {e}")
            
            await asyncio.sleep(self._poll_interval)
    
    async def _check_approved_plans(self):
        """Check for approved plans to execute."""
        approved_path = Path(self.vault_path) / "Approved"
        
        if not approved_path.exists():
            return
        
        # Find plan files
        plan_files = list(approved_path.glob("*.plan.md"))
        
        if not plan_files:
            self.logger.debug("No approved plans to execute")
            return
        
        self.logger.info(f"Found {len(plan_files)} approved plans")
        
        for plan_file in plan_files:
            await self.execute_plan_from_path(str(plan_file))
    
    async def execute_plan_from_path(self, plan_path: str) -> Optional[Dict[str, Any]]:
        """
        Execute a plan from its file path.
        
        Args:
            plan_path: Path to the plan file
            
        Returns:
            Execution result or None if failed
        """
        try:
            plan = PlanFile.from_file(plan_path)
            return await self.execute_plan(plan, plan_path)
        except Exception as e:
            self._plans_failed += 1
            self.logger.error(f"Failed to load plan from {plan_path}: {e}")
            publish_event(
                EventType.ACTION_FAILED,
                {"plan_path": plan_path, "error": str(e)},
                source="mcp_service"
            )
            return None
    
    async def execute_plan(self, plan: PlanFile, plan_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a plan.
        
        Args:
            plan: PlanFile to execute
            plan_path: Optional path to the plan file
            
        Returns:
            Execution result
        """
        self.logger.info(f"Executing plan: {plan.id} (dry_run={self.dry_run})")
        
        try:
            # Parse steps
            steps = self._parse_steps(plan.steps)
            
            # Execute each step
            step_results = []
            for i, step in enumerate(steps):
                step_result = await self._execute_step(step, i + 1, plan)
                step_results.append(step_result)
                
                if step_result.get('status') == 'failed':
                    break
            
            # Build execution result
            result = {
                "plan_id": plan.id,
                "action_id": plan.action_id,
                "status": "completed" if all(s.get('status') == 'completed' for s in step_results) else "partial",
                "dry_run": self.dry_run,
                "timestamp": get_current_iso_timestamp(),
                "steps_executed": len([s for s in step_results if s.get('status') == 'completed']),
                "total_steps": len(steps),
                "step_results": step_results
            }
            
            # Store in history
            self._execution_history.append(result)
            self._plans_executed += 1
            self._last_execution = get_current_iso_timestamp()
            
            # Move plan to Done if successful
            if result["status"] == "completed" and plan_path:
                self._move_to_done(plan_path)
            
            # Publish execution completed event
            publish_event(
                EventType.PLAN_EXECUTION_COMPLETED,
                result,
                source="mcp_service"
            )
            
            self.logger.info(f"Plan execution completed: {plan.id}")
            
            return result
            
        except Exception as e:
            self._plans_failed += 1
            self.logger.error(f"Plan execution failed: {plan.id}: {e}")
            
            result = {
                "plan_id": plan.id,
                "status": "failed",
                "error": str(e),
                "timestamp": get_current_iso_timestamp()
            }
            
            publish_event(
                EventType.ACTION_FAILED,
                result,
                source="mcp_service"
            )
            
            return result
    
    async def _execute_step(self, step: str, step_number: int, plan: PlanFile) -> Dict[str, Any]:
        """
        Execute a single step.
        
        Args:
            step: Step description
            step_number: Step number
            plan: Parent plan
            
        Returns:
            Step execution result
        """
        self.logger.info(f"Executing step {step_number}: {step}")
        
        result = {
            "step_number": step_number,
            "step": step,
            "status": "completed",
            "timestamp": get_current_iso_timestamp()
        }
        
        if self.dry_run:
            # Log what would happen
            self._log_dry_run_action(plan.action_id, step)
            result["dry_run_message"] = f"WOULD EXECUTE: {step}"
        else:
            # Execute actual step
            try:
                await self._perform_actual_step(step, plan)
            except Exception as e:
                result["status"] = "failed"
                result["error"] = str(e)
        
        return result
    
    async def _perform_actual_step(self, step: str, plan: PlanFile):
        """
        Perform actual step execution.
        
        This is where you would integrate with actual tools/APIs.
        For now, it simulates execution.
        """
        # Simulate execution time
        await asyncio.sleep(0.1)
        
        # In production, this would:
        # - Send emails via Gmail API
        # - Create calendar events
        # - Generate documents
        # - Call external APIs
        # - Run scripts
        
        self.logger.debug(f"Executed step: {step}")
    
    def _parse_steps(self, steps_text: str) -> List[str]:
        """Parse steps from plan text."""
        steps = []
        
        for line in steps_text.strip().split('\n'):
            line = line.strip()
            # Look for numbered steps
            if line and any(line.startswith(f"{i}.") for i in range(1, 20)):
                # Remove number prefix
                step = line.split('.', 1)[1].strip()
                steps.append(step)
        
        return steps if steps else [steps_text.strip()]
    
    def _log_dry_run_action(self, action_id: str, description: str):
        """Log dry-run action."""
        log_entry = f"WOULD SEND: ACTION_ID={action_id}, DESCRIPTION={description}"
        self.logger.info(log_entry)
    
    def _move_to_done(self, plan_path: str):
        """Move completed plan to Done folder."""
        try:
            plan_file = Path(plan_path)
            done_path = Path(self.vault_path) / "Done"
            ensure_directory_exists(str(done_path))
            
            dest_path = done_path / plan_file.name
            plan_file.rename(dest_path)
            
            self.logger.info(f"Plan moved to Done: {dest_path.name}")
            
        except Exception as e:
            self.logger.error(f"Failed to move plan to Done: {e}")
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history."""
        return self._execution_history[-limit:]
    
    def enable_dry_run(self):
        """Enable dry-run mode."""
        self.dry_run = True
        self.logger.info("Dry-run mode enabled")
    
    def disable_dry_run(self):
        """Disable dry-run mode (enable real execution)."""
        self.dry_run = False
        self.logger.info("Real execution mode enabled - actions will be performed!")


# Factory function
def create_mcp_service(config_path: str = "./config.yaml", dry_run: bool = True) -> MCPService:
    """Factory function to create MCPService."""
    return MCPService(config_path, dry_run)
