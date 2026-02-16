"""
Workflow Engine - Gold Tier
State machine-based workflow automation with file locking and atomic transitions
"""
import asyncio
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Awaitable
from datetime import datetime
import yaml
import uuid

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.workflow import (
    WorkflowState, WorkflowEvent, TransitionRequest, TransitionResult,
    WorkflowContext, is_valid_transition, get_valid_transitions,
    get_state_folder, get_folder_state, VALID_TRANSITIONS
)
from lib.event_bus import get_event_bus, EventType, publish_event
from lib.utils import get_current_iso_timestamp, ensure_directory_exists


class FileLock:
    """
    File-level locking to prevent race conditions during transitions.
    Uses a combination of lock files and atomic operations.
    """
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.lock_dir = self.vault_path / ".locks"
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()  # Global lock for lock management
        
        ensure_directory_exists(str(self.lock_dir))
    
    def _get_lock_file_path(self, filename: str) -> Path:
        """Get the lock file path for a given filename."""
        safe_name = filename.replace("/", "_").replace("\\", "_")
        return self.lock_dir / f"{safe_name}.lock"
    
    async def acquire(self, filename: str, timeout: float = 10.0) -> bool:
        """
        Acquire a lock for a file.
        
        Args:
            filename: Name of the file to lock
            timeout: Maximum time to wait for lock
            
        Returns:
            True if lock acquired, False if timeout
        """
        async with self._lock:
            if filename not in self._locks:
                self._locks[filename] = asyncio.Lock()
        
        lock = self._locks[filename]
        
        try:
            # Try to acquire with timeout
            await asyncio.wait_for(lock.acquire(), timeout=timeout)
            
            # Create lock file as secondary mechanism
            lock_file = self._get_lock_file_path(filename)
            lock_file.write_text(f"{get_current_iso_timestamp()}\n{uuid.uuid4()}")
            
            return True
        except asyncio.TimeoutError:
            return False
    
    async def release(self, filename: str):
        """Release a lock for a file."""
        async with self._lock:
            if filename not in self._locks:
                return
            
            lock = self._locks[filename]
            if lock.locked():
                lock.release()
            
            # Remove lock file
            lock_file = self._get_lock_file_path(filename)
            if lock_file.exists():
                try:
                    lock_file.unlink()
                except:
                    pass
    
    async def is_locked(self, filename: str) -> bool:
        """Check if a file is currently locked."""
        async with self._lock:
            if filename not in self._locks:
                return False
            return self._locks[filename].locked()
    
    def cleanup_stale_locks(self, max_age_seconds: int = 300):
        """Clean up stale lock files older than max_age_seconds."""
        now = datetime.utcnow()
        
        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                mtime = datetime.fromtimestamp(lock_file.stat().st_mtime)
                age = (now - mtime).total_seconds()
                
                if age > max_age_seconds:
                    lock_file.unlink()
            except:
                pass


class RetryHandler:
    """
    Handles retry logic with exponential backoff.
    """
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, max_retries: int = 5):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt using exponential backoff with jitter.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        import random
        
        # Exponential backoff
        delay = self.base_delay * (2 ** attempt)
        
        # Add jitter (±25%)
        jitter = delay * 0.25 * (2 * random.random() - 1)
        delay += jitter
        
        # Cap at max delay
        return min(delay, self.max_delay)
    
    def should_retry(self, attempt: int, error: Optional[str] = None) -> bool:
        """
        Determine if a retry should be attempted.
        
        Args:
            attempt: Current attempt number
            error: Error message if any
            
        Returns:
            True if should retry
        """
        if attempt >= self.max_retries:
            return False
        
        # Don't retry certain errors
        non_retryable_errors = [
            "file not found",
            "invalid state",
            "permission denied"
        ]
        
        if error:
            error_lower = error.lower()
            if any(nr in error_lower for nr in non_retryable_errors):
                return False
        
        return True


class DeadLetterQueue:
    """
    Dead letter queue for failed actions that cannot be processed.
    """
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.dlq_path = self.vault_path / "Dead_Letter"
        self.logger = logging.getLogger("DeadLetterQueue")
        
        ensure_directory_exists(str(self.dlq_path))
    
    def add(self, filename: str, source_folder: str, error: str, 
            context: Optional[WorkflowContext] = None) -> Path:
        """
        Add a file to the dead letter queue.
        
        Args:
            filename: Name of the failed file
            source_folder: Original folder name
            error: Error message
            context: Optional workflow context
            
        Returns:
            Path to the DLQ entry file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        dlq_filename = f"{timestamp}_{filename}"
        dlq_path = self.dlq_path / dlq_filename
        
        # Create metadata file
        metadata = {
            "original_filename": filename,
            "source_folder": source_folder,
            "error": error,
            "timestamp": get_current_iso_timestamp(),
            "context": context.to_dict() if context else None
        }
        
        metadata_path = dlq_path.with_suffix(".meta.yaml")
        
        try:
            # Move the failed file to DLQ
            source_path = self.vault_path / source_folder / filename
            if source_path.exists():
                shutil.copy2(str(source_path), str(dlq_path))
            
            # Write metadata
            with open(metadata_path, 'w') as f:
                yaml.dump(metadata, f)
            
            self.logger.warning(f"Added to DLQ: {filename} (error: {error})")
            
            # Publish event
            publish_event(
                EventType.ACTION_FAILED,
                {
                    "filename": filename,
                    "error": error,
                    "dlq_path": str(dlq_path),
                    "source_folder": source_folder
                },
                source="dead_letter_queue"
            )
            
            return dlq_path
            
        except Exception as e:
            self.logger.error(f"Failed to add to DLQ: {e}")
            raise
    
    def get_entries(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent DLQ entries."""
        entries = []
        
        for meta_file in sorted(self.dlq_path.glob("*.meta.yaml"), reverse=True)[:limit]:
            try:
                with open(meta_file, 'r') as f:
                    metadata = yaml.safe_load(f)
                
                metadata['meta_file'] = str(meta_file)
                entries.append(metadata)
            except:
                pass
        
        return entries
    
    def retry_entry(self, meta_filename: str) -> bool:
        """
        Retry a DLQ entry by moving it back to the appropriate folder.
        
        Args:
            meta_filename: Name of the metadata file
            
        Returns:
            True if successfully queued for retry
        """
        meta_path = self.dlq_path / meta_filename
        
        if not meta_path.exists():
            return False
        
        try:
            with open(meta_path, 'r') as f:
                metadata = yaml.safe_load(f)
            
            # Get the corresponding data file
            data_filename = meta_filename.replace(".meta.yaml", "")
            data_path = self.dlq_path / data_filename
            
            if not data_path.exists():
                return False
            
            # Determine target folder from context
            target_folder = metadata.get('source_folder', 'Needs_Action')
            target_path = self.vault_path / target_folder / data_path.name
            
            # Move back
            shutil.copy2(str(data_path), str(target_path))
            
            # Remove from DLQ
            meta_path.unlink()
            data_path.unlink()
            
            self.logger.info(f"Retried DLQ entry: {data_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to retry DLQ entry: {e}")
            return False
    
    def purge(self, older_than_days: int = 30) -> int:
        """
        Purge old DLQ entries.
        
        Args:
            older_than_days: Purge entries older than this many days
            
        Returns:
            Number of entries purged
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        purged = 0
        
        for meta_file in self.dlq_path.glob("*.meta.yaml"):
            try:
                mtime = datetime.fromtimestamp(meta_file.stat().st_mtime)
                if mtime < cutoff:
                    # Remove both meta and data files
                    data_filename = meta_file.name.replace(".meta.yaml", "")
                    data_path = self.dlq_path / data_filename
                    
                    if data_path.exists():
                        data_path.unlink()
                    
                    meta_file.unlink()
                    purged += 1
            except:
                pass
        
        return purged


class CorrelationTracker:
    """
    Tracks correlation between Action → Plan → Execution.
    Provides end-to-end visibility of workflow instances.
    """
    
    def __init__(self):
        self._contexts: Dict[str, WorkflowContext] = {}
        self._action_to_correlation: Dict[str, str] = {}
        self._plan_to_correlation: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger("CorrelationTracker")
    
    async def create_context(
        self,
        action_id: str,
        plan_id: str = "",
        approval_id: str = ""
    ) -> str:
        """
        Create a new correlation context.
        
        Args:
            action_id: Action UUID
            plan_id: Optional plan UUID
            approval_id: Optional approval UUID
            
        Returns:
            Correlation ID
        """
        async with self._lock:
            correlation_id = str(uuid.uuid4())
            
            context = WorkflowContext(
                correlation_id=correlation_id,
                action_id=action_id,
                plan_id=plan_id,
                approval_id=approval_id
            )
            
            self._contexts[correlation_id] = context
            self._action_to_correlation[action_id] = correlation_id
            
            if plan_id:
                self._plan_to_correlation[plan_id] = correlation_id
            
            self.logger.debug(f"Created correlation context: {correlation_id}")
            return correlation_id
    
    async def update_context(
        self,
        correlation_id: str,
        plan_id: str = "",
        approval_id: str = "",
        state: WorkflowState = None
    ):
        """Update an existing correlation context."""
        async with self._lock:
            if correlation_id not in self._contexts:
                raise ValueError(f"Unknown correlation ID: {correlation_id}")
            
            context = self._contexts[correlation_id]
            
            if plan_id and not context.plan_id:
                context.plan_id = plan_id
                self._plan_to_correlation[plan_id] = correlation_id
            
            if approval_id and not context.approval_id:
                context.approval_id = approval_id
            
            if state:
                context.current_state = state
    
    async def get_context(self, correlation_id: str) -> Optional[WorkflowContext]:
        """Get context by correlation ID."""
        return self._contexts.get(correlation_id)
    
    async def get_context_by_action_id(self, action_id: str) -> Optional[WorkflowContext]:
        """Get context by action ID."""
        correlation_id = self._action_to_correlation.get(action_id)
        if correlation_id:
            return self._contexts.get(correlation_id)
        return None
    
    async def get_context_by_plan_id(self, plan_id: str) -> Optional[WorkflowContext]:
        """Get context by plan ID."""
        correlation_id = self._plan_to_correlation.get(plan_id)
        if correlation_id:
            return self._contexts.get(correlation_id)
        return None
    
    async def record_transition(
        self,
        correlation_id: str,
        from_state: WorkflowState,
        to_state: WorkflowState,
        success: bool,
        error: str = ""
    ):
        """Record a state transition in the context."""
        async with self._lock:
            if correlation_id in self._contexts:
                context = self._contexts[correlation_id]
                context.add_state_transition(from_state, to_state, success, error)
    
    async def get_full_trace(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get the full trace for a correlation ID."""
        context = await self.get_context(correlation_id)
        if context:
            return context.to_dict()
        return None


class WorkflowEngine:
    """
    Main workflow engine that orchestrates state transitions.
    Implements the state machine for vault automation.
    """
    
    def __init__(self, vault_path: str, config_path: str = "./config.yaml"):
        self.vault_path = Path(vault_path)
        self.config_path = config_path
        self.config = {}
        
        self.logger = logging.getLogger("WorkflowEngine")
        self.event_bus = get_event_bus()
        
        # Components
        self.file_lock = FileLock(vault_path)
        self.retry_handler = RetryHandler()
        self.dead_letter_queue = DeadLetterQueue(vault_path)
        self.correlation_tracker = CorrelationTracker()
        
        # State
        self._running = False
        self._transition_handlers: Dict[WorkflowState, Callable] = {}
        
        # Metrics
        self._transitions_completed = 0
        self._transitions_failed = 0
        self._retries = 0
        
        # Load config
        self._load_config()
        
        self.logger.info("WorkflowEngine initialized")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        except:
            self.config = {}
    
    async def start(self):
        """Start the workflow engine."""
        self._running = True
        self.logger.info("WorkflowEngine started")
        
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": "workflow_engine"},
            source="workflow_engine"
        )
    
    async def stop(self):
        """Stop the workflow engine."""
        self._running = False
        self.logger.info("WorkflowEngine stopped")
        
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "workflow_engine"},
            source="workflow_engine"
        )
    
    def health_check(self) -> bool:
        """Check engine health."""
        return self._running
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics."""
        return {
            "transitions_completed": self._transitions_completed,
            "transitions_failed": self._transitions_failed,
            "retries": self._retries,
            "dlq_size": len(list(self.dead_letter_queue.dlq_path.glob("*.meta.yaml"))),
            "active_correlations": len(self.correlation_tracker._contexts)
        }
    
    async def transition(
        self,
        request: TransitionRequest
    ) -> TransitionResult:
        """
        Execute a state transition.
        
        Args:
            request: Transition request
            
        Returns:
            Transition result
        """
        # Validate transition
        if not is_valid_transition(request.source_state, request.target_state):
            return TransitionResult(
                success=False,
                result=TransitionResult.INVALID_TRANSITION,
                source_state=request.source_state,
                target_state=request.target_state,
                filename=request.filename,
                error_message=f"Invalid transition: {request.source_state.value} → {request.target_state.value}"
            )
        
        # Acquire lock
        if not await self.file_lock.acquire(request.filename):
            return TransitionResult(
                success=False,
                result=TransitionResult.LOCK_ERROR,
                source_state=request.source_state,
                target_state=request.target_state,
                filename=request.filename,
                error_message="Failed to acquire file lock"
            )
        
        try:
            # Get source and target paths
            source_folder = get_state_folder(request.source_state)
            target_folder = get_state_folder(request.target_state)
            
            source_path = self.vault_path / source_folder / request.filename
            target_path = self.vault_path / target_folder / request.filename
            
            # Check source exists
            if not source_path.exists():
                return TransitionResult(
                    success=False,
                    result=TransitionResult.FILE_NOT_FOUND,
                    source_state=request.source_state,
                    target_state=request.target_state,
                    filename=request.filename,
                    error_message=f"Source file not found: {source_path}"
                )
            
            # Perform atomic move
            await self._atomic_move(source_path, target_path)
            
            # Update correlation tracker
            if request.correlation_id:
                await self.correlation_tracker.record_transition(
                    request.correlation_id,
                    request.source_state,
                    request.target_state,
                    success=True
                )
            
            # Publish event
            self._publish_transition_event(
                request,
                success=True
            )
            
            self._transitions_completed += 1
            self.logger.info(
                f"Transition: {request.filename} "
                f"({request.source_state.value} → {request.target_state.value})"
            )
            
            return TransitionResult(
                success=True,
                result=TransitionResult.SUCCESS,
                source_state=request.source_state,
                target_state=request.target_state,
                filename=request.filename,
                metadata={"source_path": str(source_path), "target_path": str(target_path)}
            )
            
        except Exception as e:
            error_msg = str(e)
            
            # Update correlation tracker
            if request.correlation_id:
                await self.correlation_tracker.record_transition(
                    request.correlation_id,
                    request.source_state,
                    request.target_state,
                    success=False,
                    error=error_msg
                )
            
            # Publish event
            self._publish_transition_event(
                request,
                success=False,
                error=error_msg
            )
            
            self._transitions_failed += 1
            self.logger.error(f"Transition failed: {error_msg}")
            
            return TransitionResult(
                success=False,
                result=TransitionResult.FAILED,
                source_state=request.source_state,
                target_state=request.target_state,
                filename=request.filename,
                error_message=error_msg
            )
            
        finally:
            await self.file_lock.release(request.filename)
    
    async def _atomic_move(self, source: Path, target: Path):
        """
        Perform an atomic file move operation.
        Uses copy + rename + delete pattern for safety.
        """
        # Ensure target directory exists
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # Use temporary file for atomic operation
        temp_target = target.with_suffix(target.suffix + '.tmp')
        
        # Copy to temp
        shutil.copy2(str(source), str(temp_target))
        
        # Atomic rename
        temp_target.rename(target)
        
        # Remove source
        source.unlink()
    
    def _publish_transition_event(
        self,
        request: TransitionRequest,
        success: bool,
        error: str = ""
    ):
        """Publish a transition event."""
        event_type = EventType.ACTION_PROCESSED if success else EventType.ACTION_FAILED
        
        publish_event(
            event_type,
            {
                "filename": request.filename,
                "source_state": request.source_state.value,
                "target_state": request.target_state.value,
                "correlation_id": request.correlation_id,
                "action_id": request.action_id,
                "plan_id": request.plan_id,
                "success": success,
                "error": error
            },
            source="workflow_engine"
        )
    
    async def transition_with_retry(
        self,
        request: TransitionRequest
    ) -> TransitionResult:
        """
        Execute a transition with retry logic.
        
        Args:
            request: Transition request
            
        Returns:
            Transition result
        """
        attempt = 0
        
        while True:
            result = await self.transition(request)
            
            if result.success:
                return result
            
            # Check if should retry
            if not self.retry_handler.should_retry(attempt, result.error_message):
                # Move to dead letter queue
                self.dead_letter_queue.add(
                    request.filename,
                    get_state_folder(request.source_state),
                    result.error_message
                )
                return result
            
            # Wait and retry
            delay = self.retry_handler.get_delay(attempt)
            self.logger.warning(
                f"Transition failed, retrying in {delay:.1f}s "
                f"(attempt {attempt + 1})"
            )
            
            await asyncio.sleep(delay)
            attempt += 1
            self._retries += 1
    
    async def process_inbox(self, filename: str) -> Optional[str]:
        """
        Process a file from Inbox → Needs_Action.
        
        Args:
            filename: Name of the file in Inbox
            
        Returns:
            Correlation ID or None if failed
        """
        source_path = self.vault_path / "Inbox" / filename
        
        if not source_path.exists():
            self.logger.error(f"File not found in Inbox: {filename}")
            return None
        
        # Create correlation context
        correlation_id = await self.correlation_tracker.create_context(
            action_id=str(uuid.uuid4())  # Will be updated when action file is created
        )
        
        # Transition to Needs_Action
        request = TransitionRequest(
            file_path=str(source_path),
            filename=filename,
            source_state=WorkflowState.INBOX,
            target_state=WorkflowState.NEEDS_ACTION,
            correlation_id=correlation_id
        )
        
        result = await self.transition_with_retry(request)
        
        if result.success:
            # Publish event for action file creation
            publish_event(
                EventType.ACTION_GENERATED,
                {
                    "filename": filename,
                    "correlation_id": correlation_id,
                    "target_folder": "Needs_Action"
                },
                source="workflow_engine"
            )
            return correlation_id
        
        return None
    
    async def process_needs_action(self, filename: str, action_id: str) -> Optional[str]:
        """
        Process action file: Needs_Action → Plans.
        
        Args:
            filename: Action file name
            action_id: Action UUID
            
        Returns:
            Correlation ID
        """
        # Get or create correlation context
        context = await self.correlation_tracker.get_context_by_action_id(action_id)
        
        if not context:
            correlation_id = await self.correlation_tracker.create_context(action_id=action_id)
        else:
            correlation_id = context.correlation_id
        
        # Transition through processing to Plans
        request = TransitionRequest(
            file_path=str(self.vault_path / "Needs_Action" / filename),
            filename=filename,
            source_state=WorkflowState.NEEDS_ACTION,
            target_state=WorkflowState.PLANS,
            correlation_id=correlation_id,
            action_id=action_id
        )
        
        result = await self.transition_with_retry(request)
        
        if result.success:
            return correlation_id
        
        return None
    
    async def submit_for_approval(self, filename: str, plan_id: str, action_id: str) -> bool:
        """
        Submit plan for approval: Plans → Pending_Approval.
        
        Args:
            filename: Plan file name
            plan_id: Plan UUID
            action_id: Action UUID
            
        Returns:
            True if successful
        """
        # Get correlation context
        context = await self.correlation_tracker.get_context_by_action_id(action_id)
        correlation_id = context.correlation_id if context else str(uuid.uuid4())
        
        # Update context with plan_id
        if context:
            await self.correlation_tracker.update_context(correlation_id, plan_id=plan_id)
        
        request = TransitionRequest(
            file_path=str(self.vault_path / "Plans" / filename),
            filename=filename,
            source_state=WorkflowState.PLANS,
            target_state=WorkflowState.PENDING_APPROVAL,
            correlation_id=correlation_id,
            action_id=action_id,
            plan_id=plan_id
        )
        
        result = await self.transition_with_retry(request)
        return result.success
    
    async def approve_action(self, filename: str, plan_id: str) -> bool:
        """
        Approve action: Pending_Approval → Approved.
        
        Args:
            filename: Approval/plan file name
            plan_id: Plan UUID
            
        Returns:
            True if successful
        """
        context = await self.correlation_tracker.get_context_by_plan_id(plan_id)
        correlation_id = context.correlation_id if context else str(uuid.uuid4())
        
        request = TransitionRequest(
            file_path=str(self.vault_path / "Pending_Approval" / filename),
            filename=filename,
            source_state=WorkflowState.PENDING_APPROVAL,
            target_state=WorkflowState.APPROVED,
            correlation_id=correlation_id,
            plan_id=plan_id
        )
        
        result = await self.transition_with_retry(request)
        
        if result.success:
            publish_event(
                EventType.ACTION_APPROVED,
                {
                    "filename": filename,
                    "plan_id": plan_id,
                    "correlation_id": correlation_id
                },
                source="workflow_engine"
            )
        
        return result.success
    
    async def execute_plan(self, filename: str, plan_id: str) -> bool:
        """
        Execute plan: Approved → Done.
        
        Args:
            filename: Plan file name
            plan_id: Plan UUID
            
        Returns:
            True if successful
        """
        context = await self.correlation_tracker.get_context_by_plan_id(plan_id)
        correlation_id = context.correlation_id if context else str(uuid.uuid4())
        
        # Transition through Executing to Done
        request = TransitionRequest(
            file_path=str(self.vault_path / "Approved" / filename),
            filename=filename,
            source_state=WorkflowState.APPROVED,
            target_state=WorkflowState.DONE,
            correlation_id=correlation_id,
            plan_id=plan_id
        )
        
        result = await self.transition_with_retry(request)
        
        if result.success:
            publish_event(
                EventType.ACTION_EXECUTED,
                {
                    "filename": filename,
                    "plan_id": plan_id,
                    "correlation_id": correlation_id
                },
                source="workflow_engine"
            )
        
        return result.success
    
    def get_workflow_trace(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get the full workflow trace for a correlation ID."""
        # This would be async in production
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use run_until_complete in running loop
            return None
        
        return asyncio.run(self.correlation_tracker.get_full_trace(correlation_id))


# Factory function
def create_workflow_engine(vault_path: str, config_path: str = "./config.yaml") -> WorkflowEngine:
    """Factory function to create WorkflowEngine."""
    return WorkflowEngine(vault_path, config_path)
