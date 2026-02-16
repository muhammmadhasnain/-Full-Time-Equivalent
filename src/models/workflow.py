"""
Workflow Models - Gold Tier
State machine definitions and workflow events for vault automation
"""
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.utils import get_current_iso_timestamp


class WorkflowState(Enum):
    """
    Vault workflow states representing the automation pipeline.
    
    Flow: INBOX → NEEDS_ACTION → PLANS → PENDING_APPROVAL → APPROVED → DONE
                                               ↓
                                          REJECTED → ARCHIVED
                                               ↓
                                          FAILED → DEAD_LETTER
    """
    # Initial state
    INBOX = "inbox"
    
    # Action processing
    NEEDS_ACTION = "needs_action"
    ACTION_PROCESSING = "action_processing"
    
    # Plan generation
    PLANS = "plans"
    PLAN_GENERATING = "plan_generating"
    
    # Approval workflow
    PENDING_APPROVAL = "pending_approval"
    APPROVAL_REVIEW = "approval_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    
    # Execution
    EXECUTION_PENDING = "execution_pending"
    EXECUTING = "executing"
    EXECUTED = "executed"
    
    # Terminal states
    DONE = "done"
    ARCHIVED = "archived"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    
    # Error states
    ERROR = "error"
    RETRY = "retry"


class TransitionResult(Enum):
    """Result of a state transition attempt."""
    SUCCESS = "success"
    FAILED = "failed"
    INVALID_TRANSITION = "invalid_transition"
    LOCK_ERROR = "lock_error"
    FILE_NOT_FOUND = "file_not_found"
    RETRYABLE = "retryable"


# Valid state transitions matrix
VALID_TRANSITIONS = {
    WorkflowState.INBOX: [WorkflowState.NEEDS_ACTION, WorkflowState.FAILED],
    WorkflowState.NEEDS_ACTION: [WorkflowState.ACTION_PROCESSING, WorkflowState.FAILED],
    WorkflowState.ACTION_PROCESSING: [WorkflowState.PLANS, WorkflowState.FAILED, WorkflowState.RETRY],
    WorkflowState.PLANS: [WorkflowState.PENDING_APPROVAL, WorkflowState.EXECUTION_PENDING, WorkflowState.FAILED],
    WorkflowState.PLAN_GENERATING: [WorkflowState.PLANS, WorkflowState.FAILED],
    WorkflowState.PENDING_APPROVAL: [WorkflowState.APPROVAL_REVIEW, WorkflowState.FAILED],
    WorkflowState.APPROVAL_REVIEW: [WorkflowState.APPROVED, WorkflowState.REJECTED, WorkflowState.FAILED],
    WorkflowState.APPROVED: [WorkflowState.EXECUTING, WorkflowState.FAILED],
    WorkflowState.REJECTED: [WorkflowState.ARCHIVED, WorkflowState.DEAD_LETTER],
    WorkflowState.EXECUTION_PENDING: [WorkflowState.EXECUTING, WorkflowState.FAILED],
    WorkflowState.EXECUTING: [WorkflowState.EXECUTED, WorkflowState.FAILED, WorkflowState.RETRY],
    WorkflowState.EXECUTED: [WorkflowState.DONE, WorkflowState.FAILED],
    WorkflowState.DONE: [WorkflowState.ARCHIVED],
    WorkflowState.FAILED: [WorkflowState.RETRY, WorkflowState.DEAD_LETTER],
    WorkflowState.RETRY: [WorkflowState.NEEDS_ACTION, WorkflowState.PLANS, WorkflowState.EXECUTING, WorkflowState.DEAD_LETTER],
    WorkflowState.ERROR: [WorkflowState.RETRY, WorkflowState.DEAD_LETTER],
    WorkflowState.ARCHIVED: [],  # Terminal state
    WorkflowState.DEAD_LETTER: [],  # Terminal state
}


@dataclass
class WorkflowEvent:
    """Represents an event in the workflow lifecycle."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    correlation_id: str = ""
    action_id: str = ""
    plan_id: str = ""
    approval_id: str = ""
    source_state: WorkflowState = WorkflowState.INBOX
    target_state: WorkflowState = WorkflowState.INBOX
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: get_current_iso_timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "correlation_id": self.correlation_id,
            "action_id": self.action_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "source_state": self.source_state.value,
            "target_state": self.target_state.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class TransitionRequest:
    """Request to transition a file between states."""
    file_path: str
    filename: str
    source_state: WorkflowState
    target_state: WorkflowState
    correlation_id: str = ""
    action_id: str = ""
    plan_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "filename": self.filename,
            "source_state": self.source_state.value,
            "target_state": self.target_state.value,
            "correlation_id": self.correlation_id,
            "action_id": self.action_id,
            "plan_id": self.plan_id,
            "metadata": self.metadata
        }


@dataclass
class TransitionResult:
    """Result of a state transition."""
    success: bool
    result: TransitionResult
    source_state: WorkflowState
    target_state: WorkflowState
    filename: str
    error_message: str = ""
    retry_after: int = 0  # Seconds to wait before retry
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "result": self.result.value,
            "source_state": self.source_state.value,
            "target_state": self.target_state.value,
            "filename": self.filename,
            "error_message": self.error_message,
            "retry_after": self.retry_after,
            "metadata": self.metadata
        }


@dataclass
class WorkflowContext:
    """Context tracking for a workflow instance."""
    correlation_id: str
    action_id: str
    plan_id: str = ""
    approval_id: str = ""
    current_state: WorkflowState = WorkflowState.INBOX
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: get_current_iso_timestamp())
    updated_at: str = field(default_factory=lambda: get_current_iso_timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    error_message: str = ""
    
    def add_state_transition(self, from_state: WorkflowState, to_state: WorkflowState, success: bool, error: str = ""):
        """Record a state transition in history."""
        self.state_history.append({
            "from_state": from_state.value,
            "to_state": to_state.value,
            "success": success,
            "error": error,
            "timestamp": get_current_iso_timestamp()
        })
        self.updated_at = get_current_iso_timestamp()
        if not success:
            self.error_message = error
    
    def increment_retry(self):
        """Increment retry count."""
        self.retry_count += 1
        self.updated_at = get_current_iso_timestamp()
    
    def can_retry(self) -> bool:
        """Check if retries are still available."""
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "correlation_id": self.correlation_id,
            "action_id": self.action_id,
            "plan_id": self.plan_id,
            "approval_id": self.approval_id,
            "current_state": self.current_state.value,
            "state_history": self.state_history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message
        }


def is_valid_transition(source: WorkflowState, target: WorkflowState) -> bool:
    """Check if a state transition is valid."""
    return target in VALID_TRANSITIONS.get(source, [])


def get_valid_transitions(state: WorkflowState) -> List[WorkflowState]:
    """Get all valid transitions from a given state."""
    return VALID_TRANSITIONS.get(state, [])


def get_state_folder(state: WorkflowState) -> str:
    """Map workflow state to vault folder name."""
    mapping = {
        WorkflowState.INBOX: "Inbox",
        WorkflowState.NEEDS_ACTION: "Needs_Action",
        WorkflowState.ACTION_PROCESSING: "Needs_Action",
        WorkflowState.PLANS: "Plans",
        WorkflowState.PLAN_GENERATING: "Plans",
        WorkflowState.PENDING_APPROVAL: "Pending_Approval",
        WorkflowState.APPROVAL_REVIEW: "Pending_Approval",
        WorkflowState.APPROVED: "Approved",
        WorkflowState.REJECTED: "Rejected",
        WorkflowState.EXECUTION_PENDING: "Approved",
        WorkflowState.EXECUTING: "Approved",
        WorkflowState.EXECUTED: "Done",
        WorkflowState.DONE: "Done",
        WorkflowState.ARCHIVED: "Archived",
        WorkflowState.FAILED: "Failed",
        WorkflowState.RETRY: "Retry",
        WorkflowState.ERROR: "Error",
        WorkflowState.DEAD_LETTER: "Dead_Letter",
    }
    return mapping.get(state, "Inbox")


def get_folder_state(folder_name: str) -> WorkflowState:
    """Map vault folder name to workflow state."""
    mapping = {
        "Inbox": WorkflowState.INBOX,
        "Needs_Action": WorkflowState.NEEDS_ACTION,
        "Plans": WorkflowState.PLANS,
        "Pending_Approval": WorkflowState.PENDING_APPROVAL,
        "Approved": WorkflowState.APPROVED,
        "Rejected": WorkflowState.REJECTED,
        "Done": WorkflowState.DONE,
        "Archived": WorkflowState.ARCHIVED,
        "Failed": WorkflowState.FAILED,
        "Retry": WorkflowState.RETRY,
        "Error": WorkflowState.ERROR,
        "Dead_Letter": WorkflowState.DEAD_LETTER,
    }
    return mapping.get(folder_name, WorkflowState.INBOX)
