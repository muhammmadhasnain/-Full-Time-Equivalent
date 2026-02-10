"""
Logging service for AI Employee Foundation
Provides comprehensive audit trails for all automated actions
"""
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Add the src directory to the path so we can import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from lib.utils import setup_logging, get_current_iso_timestamp
from lib.constants import LOG_FORMAT, DEFAULT_LOG_LEVEL


class LoggingService:
    """
    Provides comprehensive logging and audit trail functionality for the AI Employee system.
    All automated actions are logged to ensure traceability and compliance with constitutional principles.
    """
    
    def __init__(self, log_level: str = None, log_format: str = None, log_file: str = None):
        """
        Initialize the logging service.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Format string for log messages
            log_file: Path to log file (optional, logs to console if not specified)
        """
        self.log_level = log_level or os.getenv('LOG_LEVEL', DEFAULT_LOG_LEVEL)
        self.log_format = log_format or LOG_FORMAT
        self.log_file = log_file
        
        # Set up the root logger
        setup_logging(self.log_level, self.log_format, self.log_file)
        
        # Get a logger for this service
        self.logger = logging.getLogger(__name__)
        
        # Log service initialization
        self.logger.info("Logging service initialized")
    
    def log_action_created(self, action_id: str, action_type: str, source: str, details: Dict[str, Any] = None):
        """
        Log when an action is created.
        
        Args:
            action_id: Unique identifier of the action
            action_type: Type of action
            source: Source of the action (e.g., gmail, filesystem)
            details: Additional details about the action
        """
        message = f"ACTION_CREATED: ID={action_id}, TYPE={action_type}, SOURCE={source}"
        if details:
            message += f", DETAILS={details}"
        
        self.logger.info(message)
    
    def log_action_processed(self, action_id: str, processor: str, result: str):
        """
        Log when an action is processed by a service.
        
        Args:
            action_id: Unique identifier of the action
            processor: Name of the service that processed the action
            result: Result of the processing
        """
        message = f"ACTION_PROCESSED: ID={action_id}, PROCESSOR={processor}, RESULT={result}"
        self.logger.info(message)
    
    def log_plan_created(self, plan_id: str, action_id: str, creator: str):
        """
        Log when a plan is created.
        
        Args:
            plan_id: Unique identifier of the plan
            action_id: ID of the action that originated this plan
            creator: Name of the service that created the plan
        """
        message = f"PLAN_CREATED: ID={plan_id}, ACTION_ID={action_id}, CREATOR={creator}"
        self.logger.info(message)
    
    def log_approval_requested(self, approval_id: str, action_id: str, plan_id: str):
        """
        Log when an approval is requested.
        
        Args:
            approval_id: Unique identifier of the approval request
            action_id: ID of the action requiring approval
            plan_id: ID of the plan associated with the action
        """
        message = f"APPROVAL_REQUESTED: ID={approval_id}, ACTION_ID={action_id}, PLAN_ID={plan_id}"
        self.logger.info(message)
    
    def log_approval_completed(self, approval_id: str, action_id: str, decision: str, approver: str = "human"):
        """
        Log when an approval is completed.
        
        Args:
            approval_id: Unique identifier of the approval request
            action_id: ID of the action that was approved/rejected
            decision: Decision made ('approved' or 'rejected')
            approver: Who made the decision ('human' or service name)
        """
        message = f"APPROVAL_COMPLETED: ID={approval_id}, ACTION_ID={action_id}, DECISION={decision}, APPROVER={approver}"
        self.logger.info(message)
    
    def log_action_executed(self, action_id: str, executor: str, result: str):
        """
        Log when an action is executed.
        
        Args:
            action_id: Unique identifier of the action
            executor: Name of the service that executed the action
            result: Result of the execution
        """
        message = f"ACTION_EXECUTED: ID={action_id}, EXECUTOR={executor}, RESULT={result}"
        self.logger.info(message)
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """
        Log an error that occurred in the system.
        
        Args:
            error_type: Type/classification of the error
            error_message: Detailed error message
            context: Additional context about where/when the error occurred
        """
        message = f"ERROR: TYPE={error_type}, MESSAGE={error_message}"
        if context:
            message += f", CONTEXT={context}"
        
        self.logger.error(message)
    
    def log_system_event(self, event_type: str, description: str, details: Dict[str, Any] = None):
        """
        Log a general system event.
        
        Args:
            event_type: Type of system event
            description: Description of the event
            details: Additional details about the event
        """
        message = f"SYSTEM_EVENT: TYPE={event_type}, DESCRIPTION={description}"
        if details:
            message += f", DETAILS={details}"
        
        self.logger.info(message)
    
    def log_dry_run_action(self, action_id: str, action_type: str, description: str):
        """
        Log a dry-run action (WOULD SEND pattern).
        
        Args:
            action_id: Unique identifier of the action
            action_type: Type of action that would be performed
            description: Description of what would happen
        """
        message = f"WOULD SEND: ACTION_ID={action_id}, TYPE={action_type}, DESCRIPTION={description}"
        self.logger.info(message)
    
    def get_log_file_path(self) -> Optional[str]:
        """
        Get the path to the log file if logging to file is enabled.
        
        Returns:
            Path to log file or None if not logging to file
        """
        return self.log_file