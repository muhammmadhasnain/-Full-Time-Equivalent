"""
Approval file model for AI Employee Foundation
Represents an approval request for an action that requires human oversight
"""
import uuid
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import re

# Add the src directory to the path so we can import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from lib.utils import validate_uuid, get_current_iso_timestamp
from lib.exceptions import ApprovalFileError, ValidationError


class ApprovalFile:
    """
    Represents an approval file in the AI Employee system.
    Approval files are created when an action requires human approval and are placed in the /Pending_Approval folder.
    """
    
    def __init__(
        self,
        action_id: str,
        plan_id: str,
        approval_id: str = None,
        description: str = "",
        created_at: str = None,
        requested_by: str = "system",
        **kwargs
    ):
        """
        Initialize an ApprovalFile instance.
        
        Args:
            action_id: Reference to the action being approved (UUID)
            plan_id: Reference to the associated plan (UUID)
            approval_id: Unique identifier for the approval request (UUID)
            description: Brief description of the action
            created_at: Request timestamp
            requested_by: Requesting system/user
        """
        self.action_id = action_id
        self.plan_id = plan_id
        self.id = approval_id or str(uuid.uuid4())
        self.description = description
        self.created_at = created_at or get_current_iso_timestamp()
        self.requested_by = requested_by
        
        # Store any additional properties
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalFile':
        """
        Create an ApprovalFile instance from a dictionary.
        
        Args:
            data: Dictionary containing approval file data
            
        Returns:
            ApprovalFile instance
        """
        # Validate required fields
        action_id = data.get('action_id')
        if not action_id or not validate_uuid(action_id):
            raise ValidationError(f"Invalid or missing action_id: {action_id}")
        
        plan_id = data.get('plan_id')
        if not plan_id or not validate_uuid(plan_id):
            raise ValidationError(f"Invalid or missing plan_id: {plan_id}")
        
        approval_id = data.get('id') or data.get('approval_id')
        if approval_id and not validate_uuid(approval_id):
            raise ValidationError(f"Invalid approval_id: {approval_id}")
        
        return cls(
            action_id=action_id,
            plan_id=plan_id,
            approval_id=approval_id,
            description=data.get('description', ''),
            created_at=data.get('created_at'),
            requested_by=data.get('requested_by', 'system'),
        )
    
    @classmethod
    def from_file(cls, file_path: str) -> 'ApprovalFile':
        """
        Create an ApprovalFile instance from a Markdown file.
        
        Args:
            file_path: Path to the approval file
            
        Returns:
            ApprovalFile instance
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract action_id and plan_id from the content
            # Look for patterns like "Action ID: ..." and "Plan ID: ..."
            action_id_match = re.search(r'Action ID[:\s]+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', content, re.IGNORECASE)
            plan_id_match = re.search(r'Plan ID[:\s]+([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', content, re.IGNORECASE)
            
            # Also look for IDs in the filename
            filename = Path(file_path).stem
            # Extract UUID from filename if it follows the pattern {uuid}.approval.md
            id_match = re.match(r'^([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', filename, re.IGNORECASE)
            
            action_id = action_id_match.group(1) if action_id_match else id_match.group(1) if id_match else None
            plan_id = plan_id_match.group(1) if plan_id_match else None
            
            if not action_id:
                raise ApprovalFileError(f"Could not extract action_id from approval file: {file_path}")
            
            if not plan_id:
                raise ApprovalFileError(f"Could not extract plan_id from approval file: {file_path}")
            
            # Extract description from the content
            description_match = re.search(r'Description[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
            description = description_match.group(1).strip() if description_match else ""
            
            # Extract creation date if available
            created_at_match = re.search(r'Created[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
            created_at = created_at_match.group(1).strip() if created_at_match else None
            
            # Extract requested by if available
            requested_by_match = re.search(r'Requested By[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
            requested_by = requested_by_match.group(1).strip() if requested_by_match else "system"
            
            return cls(
                action_id=action_id,
                plan_id=plan_id,
                description=description,
                created_at=created_at,
                requested_by=requested_by
            )
        except FileNotFoundError:
            raise ApprovalFileError(f"Approval file not found: {file_path}")
        except Exception as e:
            raise ApprovalFileError(f"Error loading approval file {file_path}: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ApprovalFile instance to a dictionary.
        
        Returns:
            Dictionary representation of the approval file
        """
        return {
            'action_id': self.action_id,
            'plan_id': self.plan_id,
            'id': self.id,
            'description': self.description,
            'created_at': self.created_at,
            'requested_by': self.requested_by
        }
    
    def to_markdown(self) -> str:
        """
        Convert the ApprovalFile instance to a Markdown string.
        
        Returns:
            Markdown string representation of the approval file
        """
        markdown_content = f"""# Approval Request

**Action ID**: {self.action_id}
**Plan ID**: {self.plan_id}
**Approval ID**: {self.id}
**Description**: {self.description}
**Created**: {self.created_at}
**Requested By**: {self.requested_by}

## Action Details
[Detailed information about the action would go here]

## Approval Checkboxes
- [ ] I have reviewed the action details
- [ ] I approve the execution of this action
- [ ] I understand the implications of this action

## Notes
[Any additional notes or concerns about this action]
"""
        return markdown_content
    
    def save_to_file(self, file_path: str) -> None:
        """
        Save the ApprovalFile instance to a Markdown file.
        
        Args:
            file_path: Path where the approval file should be saved
        """
        try:
            # Ensure the directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.to_markdown())
        except Exception as e:
            raise ApprovalFileError(f"Error saving approval file {file_path}: {str(e)}")
    
    def validate(self) -> bool:
        """
        Validate the approval file data.
        
        Returns:
            True if valid, raises ValidationError if invalid
        """
        if not validate_uuid(self.action_id):
            raise ValidationError(f"Invalid UUID for action_id: {self.action_id}")
        
        if not validate_uuid(self.plan_id):
            raise ValidationError(f"Invalid UUID for plan_id: {self.plan_id}")
        
        if not validate_uuid(self.id):
            raise ValidationError(f"Invalid UUID for approval id: {self.id}")
        
        if not self.created_at:
            raise ValidationError("created_at is required")
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError(f"Invalid timestamp format for created_at: {self.created_at}")
        
        return True
    
    def __repr__(self) -> str:
        """String representation of the ApprovalFile."""
        return f"ApprovalFile(id={self.id}, action_id={self.action_id}, plan_id={self.plan_id})"
    
    def __eq__(self, other) -> bool:
        """Check equality with another ApprovalFile."""
        if not isinstance(other, ApprovalFile):
            return False
        return self.id == other.id