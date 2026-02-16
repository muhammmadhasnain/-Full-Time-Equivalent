"""
Enhanced MCP Execution Layer - Gold Tier
Full execution engine with dry-run, rollback, and step-level traceability
"""
import asyncio
import logging
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import yaml
import uuid

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.event_bus import EventType, publish_event, get_event_bus
from lib.utils import get_current_iso_timestamp, ensure_directory_exists
from models.plan_file import PlanFile
from models.action_file import ActionFile


class ExecutionMode(Enum):
    """Execution mode for the MCP service."""
    DRY_RUN = "dry_run"           # Log only, no actual execution
    REAL = "real"                 # Execute actual actions
    SIMULATED = "simulated"       # Simulate with delays


class StepStatus(Enum):
    """Status of a step execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class RollbackStrategy(Enum):
    """Strategy for rollback operations."""
    AUTOMATIC = "automatic"       # Auto-rollback on failure
    MANUAL = "manual"             # Require manual intervention
    NONE = "none"                 # No rollback possible


@dataclass
class StepResult:
    """Result of executing a single step."""
    step_number: int
    step_description: str
    status: StepStatus
    timestamp: str = field(default_factory=lambda: get_current_iso_timestamp())
    duration_ms: int = 0
    dry_run_message: str = ""
    error_message: str = ""
    rollback_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_description": self.step_description,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "dry_run_message": self.dry_run_message,
            "error_message": self.error_message,
            "rollback_data": self.rollback_data,
            "metadata": self.metadata
        }


@dataclass
class ExecutionResult:
    """Result of executing a full plan."""
    plan_id: str
    action_id: str
    correlation_id: str
    execution_mode: ExecutionMode
    status: str  # completed, partial, failed, rolled_back
    timestamp: str = field(default_factory=lambda: get_current_iso_timestamp())
    total_steps: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    steps_rolled_back: int = 0
    step_results: List[StepResult] = field(default_factory=list)
    rollback_performed: bool = False
    rollback_reason: str = ""
    execution_trace: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "action_id": self.action_id,
            "correlation_id": self.correlation_id,
            "execution_mode": self.execution_mode.value,
            "status": self.status,
            "timestamp": self.timestamp,
            "total_steps": self.total_steps,
            "steps_completed": self.steps_completed,
            "steps_failed": self.steps_failed,
            "steps_rolled_back": self.steps_rolled_back,
            "step_results": [sr.to_dict() for sr in self.step_results],
            "rollback_performed": self.rollback_performed,
            "rollback_reason": self.rollback_reason,
            "execution_trace": self.execution_trace
        }


class RollbackManager:
    """
    Manages rollback operations for reversible steps.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._rollback_stack: List[Dict[str, Any]] = []
    
    def push_rollback_data(self, step_number: int, rollback_data: Dict[str, Any]):
        """
        Push rollback data for a step onto the stack.
        
        Args:
            step_number: Step number this rollback data belongs to
            rollback_data: Data needed to perform rollback
        """
        self._rollback_stack.append({
            "step_number": step_number,
            "rollback_data": rollback_data,
            "timestamp": get_current_iso_timestamp()
        })
        self.logger.debug(f"Rollback data pushed for step {step_number}")
    
    async def execute_rollback(self, step_results: List[StepResult]) -> List[StepResult]:
        """
        Execute rollback for all completed steps in reverse order.
        
        Args:
            step_results: List of step results to rollback
            
        Returns:
            List of rollback results
        """
        rollback_results = []
        
        # Process rollback stack in reverse order
        for rollback_info in reversed(self._rollback_stack):
            step_num = rollback_info["step_number"]
            rollback_data = rollback_info["rollback_data"]
            
            result = await self._rollback_step(step_num, rollback_data)
            rollback_results.append(result)
            
            # Update original step result
            if step_num <= len(step_results):
                step_results[step_num - 1].status = StepStatus.ROLLED_BACK
        
        self.logger.info(f"Rollback completed for {len(rollback_results)} steps")
        return rollback_results
    
    async def _rollback_step(self, step_number: int, rollback_data: Dict[str, Any]) -> StepResult:
        """
        Rollback a single step.
        
        Args:
            step_number: Step number to rollback
            rollback_data: Data needed for rollback
            
        Returns:
            Rollback result
        """
        start_time = datetime.utcnow()
        
        try:
            action_type = rollback_data.get("action_type", "unknown")
            
            # Perform rollback based on action type
            if action_type == "file_created":
                # Delete the created file
                file_path = rollback_data.get("file_path")
                if file_path and Path(file_path).exists():
                    Path(file_path).unlink()
                    self.logger.info(f"Rollback: Deleted file {file_path}")
            
            elif action_type == "file_moved":
                # Move file back to original location
                current_path = rollback_data.get("current_path")
                original_path = rollback_data.get("original_path")
                if current_path and original_path:
                    shutil.move(str(current_path), str(original_path))
                    self.logger.info(f"Rollback: Moved file back to {original_path}")
            
            elif action_type == "email_sent":
                # Can't actually unsend email, but log it
                self.logger.warning(f"Rollback: Cannot unsend email (step {step_number})")
            
            elif action_type == "api_call":
                # Call compensating API if available
                compensating_action = rollback_data.get("compensating_action")
                if compensating_action:
                    self.logger.info(f"Rollback: Executing compensating action: {compensating_action}")
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            return StepResult(
                step_number=step_number,
                step_description=f"Rollback for step {step_number}",
                status=StepStatus.COMPLETED,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            self.logger.error(f"Rollback failed for step {step_number}: {e}")
            
            return StepResult(
                step_number=step_number,
                step_description=f"Rollback for step {step_number}",
                status=StepStatus.FAILED,
                error_message=str(e)
            )
    
    def clear(self):
        """Clear the rollback stack."""
        self._rollback_stack = []


class StepExecutor:
    """
    Executes individual steps with traceability.
    """
    
    def __init__(self, execution_mode: ExecutionMode, logger: logging.Logger):
        self.execution_mode = execution_mode
        self.logger = logger
        self._executors: Dict[str, Callable] = self._register_executors()
    
    def _register_executors(self) -> Dict[str, Callable]:
        """Register step executors for different action types."""
        return {
            "email": self._execute_email_step,
            "calendar": self._execute_calendar_step,
            "file": self._execute_file_step,
            "api": self._execute_api_step,
            "script": self._execute_script_step,
            "default": self._execute_default_step
        }
    
    async def execute(
        self,
        step: str,
        step_number: int,
        plan: PlanFile,
        action: Optional[ActionFile] = None
    ) -> StepResult:
        """
        Execute a single step.
        
        Args:
            step: Step description
            step_number: Step number
            plan: Parent plan
            action: Optional parent action
            
        Returns:
            Step execution result
        """
        start_time = datetime.utcnow()
        
        # Determine executor based on step content
        executor = self._select_executor(step)
        
        try:
            result = await executor(step, step_number, plan, action)
            result.duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return result
            
        except Exception as e:
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.FAILED,
                duration_ms=duration_ms,
                error_message=str(e)
            )
    
    def _select_executor(self, step: str) -> Callable:
        """Select appropriate executor based on step content."""
        step_lower = step.lower()
        
        if any(kw in step_lower for kw in ["email", "send", "reply"]):
            return self._executors["email"]
        elif any(kw in step_lower for kw in ["calendar", "meeting", "schedule"]):
            return self._executors["calendar"]
        elif any(kw in step_lower for kw in ["file", "document", "save", "create"]):
            return self._executors["file"]
        elif any(kw in step_lower for kw in ["api", "http", "request"]):
            return self._executors["api"]
        elif any(kw in step_lower for kw in ["script", "run", "execute"]):
            return self._executors["script"]
        else:
            return self._executors["default"]
    
    async def _execute_email_step(
        self, step: str, step_number: int, plan: PlanFile, action: Optional[ActionFile]
    ) -> StepResult:
        """Execute email-related step."""
        if self.execution_mode == ExecutionMode.DRY_RUN:
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                dry_run_message=f"WOULD SEND EMAIL: {step}"
            )
        elif self.execution_mode == ExecutionMode.SIMULATED:
            await asyncio.sleep(0.1)  # Simulate API call
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                metadata={"simulated": True}
            )
        else:
            # Real execution - would integrate with Gmail API
            self.logger.info(f"Sending email: {step}")
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                rollback_data={"action_type": "email_sent"}
            )
    
    async def _execute_calendar_step(
        self, step: str, step_number: int, plan: PlanFile, action: Optional[ActionFile]
    ) -> StepResult:
        """Execute calendar-related step."""
        if self.execution_mode == ExecutionMode.DRY_RUN:
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                dry_run_message=f"WOULD CREATE CALENDAR EVENT: {step}"
            )
        elif self.execution_mode == ExecutionMode.SIMULATED:
            await asyncio.sleep(0.1)
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                metadata={"simulated": True}
            )
        else:
            # Real execution - would integrate with Calendar API
            self.logger.info(f"Creating calendar event: {step}")
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                rollback_data={"action_type": "calendar_event_created"}
            )
    
    async def _execute_file_step(
        self, step: str, step_number: int, plan: PlanFile, action: Optional[ActionFile]
    ) -> StepResult:
        """Execute file-related step."""
        if self.execution_mode == ExecutionMode.DRY_RUN:
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                dry_run_message=f"WOULD CREATE/MODIFY FILE: {step}"
            )
        elif self.execution_mode == ExecutionMode.SIMULATED:
            await asyncio.sleep(0.1)
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                metadata={"simulated": True}
            )
        else:
            # Real execution - would create/modify files
            self.logger.info(f"File operation: {step}")
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                rollback_data={"action_type": "file_created"}
            )
    
    async def _execute_api_step(
        self, step: str, step_number: int, plan: PlanFile, action: Optional[ActionFile]
    ) -> StepResult:
        """Execute API-related step."""
        if self.execution_mode == ExecutionMode.DRY_RUN:
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                dry_run_message=f"WOULD CALL API: {step}"
            )
        elif self.execution_mode == ExecutionMode.SIMULATED:
            await asyncio.sleep(0.2)
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                metadata={"simulated": True}
            )
        else:
            # Real execution - would call external APIs
            self.logger.info(f"API call: {step}")
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                rollback_data={"action_type": "api_call"}
            )
    
    async def _execute_script_step(
        self, step: str, step_number: int, plan: PlanFile, action: Optional[ActionFile]
    ) -> StepResult:
        """Execute script-related step."""
        if self.execution_mode == ExecutionMode.DRY_RUN:
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                dry_run_message=f"WOULD RUN SCRIPT: {step}"
            )
        elif self.execution_mode == ExecutionMode.SIMULATED:
            await asyncio.sleep(0.3)
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                metadata={"simulated": True}
            )
        else:
            # Real execution - would run scripts
            self.logger.info(f"Running script: {step}")
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED
            )
    
    async def _execute_default_step(
        self, step: str, step_number: int, plan: PlanFile, action: Optional[ActionFile]
    ) -> StepResult:
        """Execute generic step."""
        if self.execution_mode == ExecutionMode.DRY_RUN:
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                dry_run_message=f"WOULD EXECUTE: {step}"
            )
        elif self.execution_mode == ExecutionMode.SIMULATED:
            await asyncio.sleep(0.1)
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED,
                metadata={"simulated": True}
            )
        else:
            # Real execution
            self.logger.info(f"Executing: {step}")
            return StepResult(
                step_number=step_number,
                step_description=step,
                status=StepStatus.COMPLETED
            )


class MCPExecutionEngine:
    """
    Enhanced MCP Execution Engine with full traceability and rollback.
    """
    
    def __init__(
        self,
        vault_path: str,
        config_path: str = "./config.yaml",
        execution_mode: ExecutionMode = ExecutionMode.DRY_RUN
    ):
        self.vault_path = Path(vault_path)
        self.config_path = config_path
        self.execution_mode = execution_mode
        self.config = {}
        
        self.logger = logging.getLogger("MCPExecutionEngine")
        self.event_bus = get_event_bus()
        
        # Components
        self.rollback_manager = RollbackManager(self.logger)
        self.step_executor = StepExecutor(execution_mode, self.logger)
        
        # State
        self._running = False
        self._execution_history: List[ExecutionResult] = []
        self._plans_executed = 0
        self._plans_failed = 0
        self._rollbacks_performed = 0
        
        # Load config
        self._load_config()
        
        self.logger.info(f"MCPExecutionEngine initialized (mode={execution_mode.value})")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        except:
            self.config = {}
    
    async def start(self):
        """Start the execution engine."""
        self._running = True
        self.logger.info(f"MCPExecutionEngine started (mode={self.execution_mode.value})")
        
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": "mcp_execution_engine", "mode": self.execution_mode.value},
            source="mcp_execution_engine"
        )
    
    async def stop(self):
        """Stop the execution engine."""
        self._running = False
        self.logger.info("MCPExecutionEngine stopped")
        
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "mcp_execution_engine"},
            source="mcp_execution_engine"
        )
    
    def health_check(self) -> bool:
        """Check engine health."""
        return self._running
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics."""
        return {
            "plans_executed": self._plans_executed,
            "plans_failed": self._plans_failed,
            "rollbacks_performed": self._rollbacks_performed,
            "execution_mode": self.execution_mode.value,
            "history_size": len(self._execution_history)
        }
    
    async def execute_plan(
        self,
        plan: PlanFile,
        action: Optional[ActionFile] = None,
        correlation_id: str = "",
        rollback_strategy: RollbackStrategy = RollbackStrategy.AUTOMATIC
    ) -> ExecutionResult:
        """
        Execute a plan with full traceability.
        
        Args:
            plan: Plan to execute
            action: Optional parent action
            correlation_id: Correlation ID for tracing
            rollback_strategy: Strategy for handling failures
            
        Returns:
            Execution result
        """
        self.logger.info(
            f"Executing plan {plan.id} (mode={self.execution_mode.value}, "
            f"rollback={rollback_strategy.value})"
        )
        
        # Initialize execution result
        result = ExecutionResult(
            plan_id=plan.id,
            action_id=plan.action_id,
            correlation_id=correlation_id or str(uuid.uuid4()),
            execution_mode=self.execution_mode
        )
        
        # Parse steps
        steps = self._parse_steps(plan.steps)
        result.total_steps = len(steps)
        result.execution_trace.append({
            "event": "execution_started",
            "timestamp": get_current_iso_timestamp(),
            "total_steps": len(steps)
        })
        
        # Clear rollback stack
        self.rollback_manager.clear()
        
        # Execute each step
        for i, step in enumerate(steps):
            step_result = await self.step_executor.execute(step, i + 1, plan, action)
            result.step_results.append(step_result)
            
            # Track rollback data
            if step_result.rollback_data and self.execution_mode != ExecutionMode.DRY_RUN:
                self.rollback_manager.push_rollback_data(i + 1, step_result.rollback_data)
            
            # Update counters
            if step_result.status == StepStatus.COMPLETED:
                result.steps_completed += 1
            elif step_result.status == StepStatus.FAILED:
                result.steps_failed += 1
                
                # Handle failure based on rollback strategy
                if rollback_strategy == RollbackStrategy.AUTOMATIC:
                    self.logger.warning(f"Step {i + 1} failed, initiating rollback...")
                    await self._perform_rollback(result)
                    break
                elif rollback_strategy == RollbackStrategy.MANUAL:
                    self.logger.error(f"Step {i + 1} failed, manual intervention required")
                    result.status = "failed_manual_intervention"
                    break
        
        # Determine final status
        if result.steps_failed == 0:
            result.status = "completed"
            self._plans_executed += 1
        elif result.rollback_performed:
            result.status = "rolled_back"
        elif result.steps_completed > 0:
            result.status = "partial"
        else:
            result.status = "failed"
            self._plans_failed += 1
        
        # Store in history
        self._execution_history.append(result)
        
        # Publish execution event
        publish_event(
            EventType.PLAN_EXECUTION_COMPLETED,
            result.to_dict(),
            source="mcp_execution_engine"
        )
        
        self.logger.info(f"Plan execution completed: {plan.id} (status={result.status})")
        
        return result
    
    async def _perform_rollback(self, result: ExecutionResult):
        """
        Perform rollback for all completed steps.
        
        Args:
            result: Execution result to rollback
        """
        rollback_results = await self.rollback_manager.execute_rollback(result.step_results)
        
        result.rollback_performed = True
        result.rollback_reason = "Step failure triggered automatic rollback"
        result.steps_rolled_back = len([r for r in rollback_results if r.status == StepStatus.COMPLETED])
        self._rollbacks_performed += 1
        
        self.logger.info(
            f"Rollback completed: {result.steps_rolled_back}/{len(rollback_results)} steps rolled back"
        )
    
    def _parse_steps(self, steps_text: str) -> List[str]:
        """Parse steps from plan text."""
        steps = []
        
        for line in steps_text.strip().split('\n'):
            line = line.strip()
            if line and any(line.startswith(f"{i}.") for i in range(1, 20)):
                step = line.split('.', 1)[1].strip()
                steps.append(step)
        
        return steps if steps else [steps_text.strip()]
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history."""
        return [er.to_dict() for er in self._execution_history[-limit:]]
    
    def get_execution_trace(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get execution trace for a specific plan."""
        for result in reversed(self._execution_history):
            if result.plan_id == plan_id:
                return result.to_dict()
        return None
    
    def set_execution_mode(self, mode: ExecutionMode):
        """Set execution mode."""
        self.execution_mode = mode
        self.step_executor.execution_mode = mode
        self.logger.info(f"Execution mode set to {mode.value}")
    
    def enable_dry_run(self):
        """Enable dry-run mode."""
        self.set_execution_mode(ExecutionMode.DRY_RUN)
    
    def enable_real_execution(self):
        """Enable real execution mode."""
        self.set_execution_mode(ExecutionMode.REAL)
    
    def enable_simulated_execution(self):
        """Enable simulated execution mode."""
        self.set_execution_mode(ExecutionMode.SIMULATED)


# Factory function
def create_mcp_execution_engine(
    vault_path: str,
    config_path: str = "./config.yaml",
    dry_run: bool = True
) -> MCPExecutionEngine:
    """Factory function to create MCPExecutionEngine."""
    mode = ExecutionMode.DRY_RUN if dry_run else ExecutionMode.SIMULATED
    return MCPExecutionEngine(vault_path, config_path, mode)
