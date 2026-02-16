"""
Audit Logging Service - Gold Tier
Comprehensive audit logging for approvals, rejections, and execution traces
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.utils import get_current_iso_timestamp, ensure_directory_exists
from lib.event_bus import EventType, get_event_bus, Event


class AuditEventType(Enum):
    """Types of audit events."""
    # Approval events
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVAL_ESCALATED = "approval_escalated"
    APPROVAL_AUTO_APPROVED = "approval_auto_approved"
    APPROVAL_AUTO_REJECTED = "approval_auto_rejected"
    
    # Execution events
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_ROLLED_BACK = "execution_rolled_back"
    STEP_EXECUTED = "step_executed"
    STEP_FAILED = "step_failed"
    STEP_ROLLED_BACK = "step_rolled_back"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    STATE_TRANSITION = "state_transition"
    
    # System events
    CONFIG_CHANGED = "config_changed"
    MODE_CHANGED = "mode_changed"
    RULE_ADDED = "rule_added"
    RULE_REMOVED = "rule_removed"


@dataclass
class AuditEntry:
    """
    Represents a single audit log entry.
    """
    entry_id: str
    event_type: AuditEventType
    timestamp: str
    actor: str  # User or system that triggered the event
    action_id: str = ""
    plan_id: str = ""
    approval_id: str = ""
    correlation_id: str = ""
    
    # Event-specific data
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Context
    ip_address: str = ""
    user_agent: str = ""
    session_id: str = ""
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action_id": self.action_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "correlation_id": self.correlation_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "tags": self.tags
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ApprovalAuditEntry(AuditEntry):
    """Audit entry specifically for approval events."""
    decision: str = ""  # approved, rejected, escalated
    reason: str = ""
    approver: str = ""
    previous_status: str = ""
    new_status: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["decision"] = self.decision
        data["reason"] = self.reason
        data["approver"] = self.approver
        data["previous_status"] = self.previous_status
        data["new_status"] = self.new_status
        return data


@dataclass
class ExecutionAuditEntry(AuditEntry):
    """Audit entry specifically for execution events."""
    execution_mode: str = ""  # dry_run, real, simulated
    step_number: int = 0
    step_description: str = ""
    step_status: str = ""
    error_message: str = ""
    duration_ms: int = 0
    rollback_performed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["execution_mode"] = self.execution_mode
        data["step_number"] = self.step_number
        data["step_description"] = self.step_description
        data["step_status"] = self.step_status
        data["error_message"] = self.error_message
        data["duration_ms"] = self.duration_ms
        data["rollback_performed"] = self.rollback_performed
        return data


class AuditLogger:
    """
    Comprehensive audit logging service.
    """
    
    def __init__(self, vault_path: str, config_path: str = "./config.yaml"):
        self.vault_path = Path(vault_path)
        self.config_path = config_path
        self.config = {}
        
        # Audit log paths
        self.audit_dir = self.vault_path / "System_Log" / "Audit"
        self.approval_log_path = self.audit_dir / "approval_history.jsonl"
        self.execution_log_path = self.audit_dir / "execution_traces.jsonl"
        self.general_log_path = self.audit_dir / "audit_log.jsonl"
        
        self.logger = logging.getLogger("AuditLogger")
        self.event_bus = get_event_bus()
        
        # In-memory buffer for recent entries
        self._buffer: List[AuditEntry] = []
        self._buffer_size = 1000
        
        # Statistics
        self._stats = {
            "total_entries": 0,
            "approval_events": 0,
            "execution_events": 0,
            "rejections": 0,
            "rollbacks": 0
        }
        
        # Initialize
        self._ensure_directories()
        self._load_config()
        self._setup_event_handlers()
        
        self.logger.info(f"AuditLogger initialized (vault: {vault_path})")
    
    def _ensure_directories(self):
        """Ensure audit directories exist."""
        ensure_directory_exists(str(self.audit_dir))
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        except:
            self.config = {}
    
    def _setup_event_handlers(self):
        """Setup event bus handlers for automatic audit logging."""
        # Approval events
        self.event_bus.subscribe(EventType.APPROVAL_REQUIRED, self._on_approval_event)
        self.event_bus.subscribe(EventType.ACTION_APPROVED, self._on_approval_event)
        self.event_bus.subscribe(EventType.ACTION_REJECTED, self._on_approval_event)
        
        # Execution events
        self.event_bus.subscribe(EventType.PLAN_EXECUTION_COMPLETED, self._on_execution_event)
        self.event_bus.subscribe(EventType.ACTION_FAILED, self._on_execution_event)
        
        self.logger.info("AuditLogger event handlers registered")
    
    def _on_approval_event(self, event: Event):
        """Handle approval-related events."""
        if event.event_type == EventType.APPROVAL_REQUIRED:
            self.log_approval_requested(
                approval_id=event.payload.get('approval_id', ''),
                action_id=event.payload.get('action_id', ''),
                plan_id=event.payload.get('plan_id', ''),
                reason=event.payload.get('reason', ''),
                actor="system"
            )
        elif event.event_type == EventType.ACTION_APPROVED:
            self.log_approval_granted(
                approval_id=event.payload.get('approval_id', ''),
                action_id=event.payload.get('action_id', ''),
                plan_id=event.payload.get('plan_id', ''),
                approver=event.payload.get('approver', 'system'),
                actor=event.payload.get('approver', 'system')
            )
    
    def _on_execution_event(self, event: Event):
        """Handle execution-related events."""
        if event.event_type == EventType.PLAN_EXECUTION_COMPLETED:
            result = event.payload
            self.log_execution_completed(
                plan_id=result.get('plan_id', ''),
                action_id=result.get('action_id', ''),
                correlation_id=result.get('correlation_id', ''),
                status=result.get('status', ''),
                execution_mode=result.get('execution_mode', 'dry_run'),
                steps_completed=result.get('steps_completed', 0),
                steps_failed=result.get('steps_failed', 0),
                rollback_performed=result.get('rollback_performed', False),
                actor="mcp_execution_engine"
            )
        elif event.event_type == EventType.ACTION_FAILED:
            self.log_execution_failed(
                plan_id=event.payload.get('plan_id', ''),
                action_id=event.payload.get('action_id', ''),
                error=event.payload.get('error', ''),
                actor="system"
            )
    
    def log(self, entry: AuditEntry):
        """
        Log an audit entry.
        
        Args:
            entry: Audit entry to log
        """
        # Add to buffer
        self._buffer.append(entry)
        if len(self._buffer) > self._buffer_size:
            self._buffer = self._buffer[-self._buffer_size:]
        
        # Update stats
        self._stats["total_entries"] += 1
        
        # Write to appropriate log file
        self._write_entry(entry)
        
        self.logger.debug(f"Audit entry logged: {entry.event_type.value}")
    
    def _write_entry(self, entry: AuditEntry):
        """Write entry to log files."""
        entry_dict = entry.to_dict()
        entry_json = json.dumps(entry_dict) + "\n"
        
        # Write to general audit log
        with open(self.general_log_path, 'a', encoding='utf-8') as f:
            f.write(entry_json)
        
        # Write to specific logs based on type
        if isinstance(entry, ApprovalAuditEntry) or entry.event_type.value.startswith('approval'):
            self._stats["approval_events"] += 1
            if entry.event_type == EventType.APPROVAL_REJECTED:
                self._stats["rejections"] += 1
            with open(self.approval_log_path, 'a', encoding='utf-8') as f:
                f.write(entry_json)
        
        elif isinstance(entry, ExecutionAuditEntry) or entry.event_type.value.startswith('execution'):
            self._stats["execution_events"] += 1
            if entry.event_type == EventType.EXECUTION_ROLLED_BACK:
                self._stats["rollbacks"] += 1
            with open(self.execution_log_path, 'a', encoding='utf-8') as f:
                f.write(entry_json)
    
    # ========== Approval Logging Methods ==========
    
    def log_approval_requested(
        self,
        approval_id: str,
        action_id: str,
        plan_id: str,
        reason: str,
        actor: str = "system",
        details: Dict[str, Any] = None
    ) -> str:
        """Log an approval request."""
        import uuid
        entry = ApprovalAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=AuditEventType.APPROVAL_REQUESTED,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            approval_id=approval_id,
            details=details or {"reason": reason},
            previous_status="pending",
            new_status="pending"
        )
        self.log(entry)
        return entry.entry_id
    
    def log_approval_granted(
        self,
        approval_id: str,
        action_id: str,
        plan_id: str,
        approver: str,
        actor: str,
        reason: str = "",
        details: Dict[str, Any] = None
    ) -> str:
        """Log an approval granted."""
        import uuid
        entry = ApprovalAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=AuditEventType.APPROVAL_GRANTED,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            approval_id=approval_id,
            details=details or {},
            decision="approved",
            reason=reason,
            approver=approver,
            previous_status="pending",
            new_status="approved"
        )
        self.log(entry)
        return entry.entry_id
    
    def log_approval_rejected(
        self,
        approval_id: str,
        action_id: str,
        plan_id: str,
        approver: str,
        actor: str,
        reason: str,
        details: Dict[str, Any] = None
    ) -> str:
        """Log an approval rejected."""
        import uuid
        entry = ApprovalAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=AuditEventType.APPROVAL_REJECTED,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            approval_id=approval_id,
            details=details or {},
            decision="rejected",
            reason=reason,
            approver=approver,
            previous_status="pending",
            new_status="rejected"
        )
        self.log(entry)
        return entry.entry_id
    
    def log_approval_escalated(
        self,
        approval_id: str,
        action_id: str,
        plan_id: str,
        escalation_target: str,
        actor: str = "system",
        reason: str = "",
        details: Dict[str, Any] = None
    ) -> str:
        """Log an approval escalated."""
        import uuid
        entry = ApprovalAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=AuditEventType.APPROVAL_ESCALATED,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            approval_id=approval_id,
            details=details or {"escalation_target": escalation_target, "reason": reason},
            decision="escalated",
            reason=reason,
            previous_status="pending",
            new_status="escalated"
        )
        self.log(entry)
        return entry.entry_id
    
    # ========== Execution Logging Methods ==========
    
    def log_execution_started(
        self,
        plan_id: str,
        action_id: str,
        correlation_id: str,
        execution_mode: str,
        actor: str = "system",
        details: Dict[str, Any] = None
    ) -> str:
        """Log execution started."""
        import uuid
        entry = ExecutionAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=AuditEventType.EXECUTION_STARTED,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            correlation_id=correlation_id,
            details=details or {},
            execution_mode=execution_mode
        )
        self.log(entry)
        return entry.entry_id
    
    def log_execution_completed(
        self,
        plan_id: str,
        action_id: str,
        correlation_id: str,
        status: str,
        execution_mode: str,
        steps_completed: int,
        steps_failed: int,
        rollback_performed: bool,
        actor: str = "system",
        details: Dict[str, Any] = None
    ) -> str:
        """Log execution completed."""
        import uuid
        entry = ExecutionAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=AuditEventType.EXECUTION_COMPLETED,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            correlation_id=correlation_id,
            details=details or {
                "steps_completed": steps_completed,
                "steps_failed": steps_failed
            },
            execution_mode=execution_mode,
            step_status=status,
            rollback_performed=rollback_performed
        )
        self.log(entry)
        return entry.entry_id
    
    def log_execution_failed(
        self,
        plan_id: str,
        action_id: str,
        error: str,
        correlation_id: str = "",
        actor: str = "system",
        details: Dict[str, Any] = None
    ) -> str:
        """Log execution failed."""
        import uuid
        entry = ExecutionAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=AuditEventType.EXECUTION_FAILED,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            correlation_id=correlation_id,
            details=details or {},
            error_message=error
        )
        self.log(entry)
        return entry.entry_id
    
    def log_step_executed(
        self,
        plan_id: str,
        action_id: str,
        step_number: int,
        step_description: str,
        status: str,
        duration_ms: int,
        execution_mode: str,
        actor: str = "system",
        error_message: str = "",
        details: Dict[str, Any] = None
    ) -> str:
        """Log a step execution."""
        import uuid
        event_type = AuditEventType.STEP_EXECUTED if status == "completed" else AuditEventType.STEP_FAILED
        
        entry = ExecutionAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            details=details or {},
            execution_mode=execution_mode,
            step_number=step_number,
            step_description=step_description,
            step_status=status,
            error_message=error_message,
            duration_ms=duration_ms
        )
        self.log(entry)
        return entry.entry_id
    
    def log_rollback(
        self,
        plan_id: str,
        action_id: str,
        steps_rolled_back: int,
        reason: str,
        actor: str = "system",
        details: Dict[str, Any] = None
    ) -> str:
        """Log a rollback operation."""
        import uuid
        entry = ExecutionAuditEntry(
            entry_id=str(uuid.uuid4()),
            event_type=AuditEventType.EXECUTION_ROLLED_BACK,
            timestamp=get_current_iso_timestamp(),
            actor=actor,
            action_id=action_id,
            plan_id=plan_id,
            details=details or {"reason": reason, "steps_rolled_back": steps_rolled_back},
            rollback_performed=True
        )
        self.log(entry)
        return entry.entry_id
    
    # ========== Query Methods ==========
    
    def get_approval_history(
        self,
        action_id: str = "",
        plan_id: str = "",
        approval_id: str = "",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get approval history.
        
        Args:
            action_id: Filter by action ID
            plan_id: Filter by plan ID
            approval_id: Filter by approval ID
            limit: Maximum entries to return
            
        Returns:
            List of approval audit entries
        """
        return self._read_log_file(
            self.approval_log_path,
            filters={
                "action_id": action_id,
                "plan_id": plan_id,
                "approval_id": approval_id
            },
            limit=limit
        )
    
    def get_execution_trace(
        self,
        plan_id: str = "",
        action_id: str = "",
        correlation_id: str = "",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get execution trace.
        
        Args:
            plan_id: Filter by plan ID
            action_id: Filter by action ID
            correlation_id: Filter by correlation ID
            limit: Maximum entries to return
            
        Returns:
            List of execution audit entries
        """
        return self._read_log_file(
            self.execution_log_path,
            filters={
                "plan_id": plan_id,
                "action_id": action_id,
                "correlation_id": correlation_id
            },
            limit=limit
        )
    
    def get_audit_log(
        self,
        event_type: str = "",
        actor: str = "",
        start_date: str = "",
        end_date: str = "",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get general audit log.
        
        Args:
            event_type: Filter by event type
            actor: Filter by actor
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            limit: Maximum entries to return
            
        Returns:
            List of audit entries
        """
        return self._read_log_file(
            self.general_log_path,
            filters={
                "event_type": event_type,
                "actor": actor,
                "start_date": start_date,
                "end_date": end_date
            },
            limit=limit
        )
    
    def _read_log_file(
        self,
        log_path: Path,
        filters: Dict[str, str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Read and filter a log file."""
        if not log_path.exists():
            return []
        
        results = []
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in reversed(f.readlines()):
                    if len(results) >= limit:
                        break
                    
                    try:
                        entry = json.loads(line.strip())
                        
                        # Apply filters
                        match = True
                        for key, value in filters.items():
                            if value:
                                if key in ['start_date', 'end_date']:
                                    continue  # Date filtering handled separately
                                elif entry.get(key) != value:
                                    match = False
                                    break
                        
                        # Date filtering
                        if filters.get('start_date'):
                            entry_date = entry.get('timestamp', '')[:10]
                            if entry_date < filters['start_date']:
                                match = False
                        
                        if filters.get('end_date'):
                            entry_date = entry.get('timestamp', '')[:10]
                            if entry_date > filters['end_date']:
                                match = False
                        
                        if match:
                            results.append(entry)
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            self.logger.error(f"Error reading log file: {e}")
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        return {
            **self._stats,
            "buffer_size": len(self._buffer),
            "log_files": {
                "approval_history": str(self.approval_log_path),
                "execution_traces": str(self.execution_log_path),
                "audit_log": str(self.general_log_path)
            }
        }
    
    def export_audit_log(
        self,
        output_path: str,
        start_date: str = "",
        end_date: str = ""
    ) -> int:
        """
        Export audit log to a file.
        
        Args:
            output_path: Path to export file
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Number of entries exported
        """
        entries = self.get_audit_log(start_date=start_date, end_date=end_date, limit=10000)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2)
        
        self.logger.info(f"Exported {len(entries)} audit entries to {output_path}")
        return len(entries)


# Factory function
def create_audit_logger(vault_path: str, config_path: str = "./config.yaml") -> AuditLogger:
    """Factory function to create AuditLogger."""
    return AuditLogger(vault_path, config_path)
