"""
Action file model for AI Employee Foundation
Represents an action that needs to be processed by the system
"""
import uuid
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

# Add the src directory to the path so we can import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from lib.utils import validate_uuid, get_current_iso_timestamp
from lib.exceptions import ActionFileError, ValidationError
from lib.constants import PRIORITIES, ACTION_TYPES


class ActionFile:
    """
    Represents an action file in the AI Employee system.
    Action files are created by watchers and placed in the /Needs_Action folder.
    """
    
    def __init__(
        self,
        action_id: str = None,
        action_type: str = None,
        priority: str = "medium",
        context: Dict[str, Any] = None,
        created_at: str = None,
        source: str = "unknown",
        **kwargs
    ):
        """
        Initialize an ActionFile instance.
        
        Args:
            action_id: Unique identifier for the action (UUID)
            action_type: Type of action to perform
            priority: Priority level (low, medium, high)
            context: Contextual data for the action
            created_at: Timestamp when the action was created
            source: Source that generated the action (e.g., gmail, filesystem)
        """
        self.id = action_id or str(uuid.uuid4())
        self.type = action_type
        self.priority = priority
        self.context = context or {}
        self.created_at = created_at or get_current_iso_timestamp()
        self.source = source
        
        # Store any additional properties
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionFile':
        """
        Create an ActionFile instance from a dictionary.
        
        Args:
            data: Dictionary containing action file data
            
        Returns:
            ActionFile instance
        """
        required_fields = ['id', 'type']
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        action_id = data['id']
        if not validate_uuid(action_id):
            raise ValidationError(f"Invalid UUID for action id: {action_id}")
        
        action_type = data['type']
        if action_type not in ACTION_TYPES:
            raise ValidationError(f"Invalid action type: {action_type}. Valid types: {ACTION_TYPES}")
        
        priority = data.get('priority', 'medium')
        if priority not in PRIORITIES:
            raise ValidationError(f"Invalid priority: {priority}. Valid priorities: {PRIORITIES}")
        
        return cls(
            action_id=data['id'],
            action_type=action_type,
            priority=priority,
            context=data.get('context', {}),
            created_at=data.get('created_at'),
            source=data.get('source', 'unknown'),
        )
    
    @classmethod
    def from_file(cls, file_path: str) -> 'ActionFile':
        """
        Create an ActionFile instance from a YAML file.
        
        Args:
            file_path: Path to the action file
            
        Returns:
            ActionFile instance
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                raise ActionFileError(f"Action file {file_path} is empty")
            
            return cls.from_dict(data)
        except FileNotFoundError:
            raise ActionFileError(f"Action file not found: {file_path}")
        except yaml.YAMLError as e:
            raise ActionFileError(f"Invalid YAML in action file {file_path}: {str(e)}")
        except Exception as e:
            raise ActionFileError(f"Error loading action file {file_path}: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the ActionFile instance to a dictionary.
        
        Returns:
            Dictionary representation of the action file
        """
        result = {
            'id': self.id,
            'type': self.type,
            'priority': self.priority,
            'context': self.context,
            'created_at': self.created_at,
            'source': self.source
        }
        
        # Add any additional attributes
        for attr_name, attr_value in self.__dict__.items():
            if attr_name not in result:
                result[attr_name] = attr_value
                
        return result
    
    def to_yaml(self) -> str:
        """
        Convert the ActionFile instance to a YAML string.
        
        Returns:
            YAML string representation of the action file
        """
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)
    
    def save_to_file(self, file_path: str) -> None:
        """
        Save the ActionFile instance to a YAML file.
        
        Args:
            file_path: Path where the action file should be saved
        """
        try:
            # Ensure the directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.to_yaml())
        except Exception as e:
            raise ActionFileError(f"Error saving action file {file_path}: {str(e)}")
    
    def validate(self) -> bool:
        """
        Validate the action file data.
        
        Returns:
            True if valid, raises ValidationError if invalid
        """
        if not validate_uuid(self.id):
            raise ValidationError(f"Invalid UUID for action id: {self.id}")
        
        if self.type not in ACTION_TYPES:
            raise ValidationError(f"Invalid action type: {self.type}. Valid types: {ACTION_TYPES}")
        
        if self.priority not in PRIORITIES:
            raise ValidationError(f"Invalid priority: {self.priority}. Valid priorities: {PRIORITIES}")
        
        if not self.created_at:
            raise ValidationError("created_at is required")
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        except ValueError:
            raise ValidationError(f"Invalid timestamp format for created_at: {self.created_at}")
        
        return True
    
    def __repr__(self) -> str:
        """String representation of the ActionFile."""
        return f"ActionFile(id={self.id}, type={self.type}, priority={self.priority})"
    
    def __eq__(self, other) -> bool:
        """Check equality with another ActionFile."""
        if not isinstance(other, ActionFile):
            return False
        return self.id == other.id