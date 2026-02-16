"""
WhatsApp Watcher Service - Gold Tier
Message monitoring for WhatsApp Business API integration
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

# Add the src directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.event_bus import EventType, publish_event, get_event_bus
from lib.utils import get_current_iso_timestamp, ensure_directory_exists
from models.action_file import ActionFile


class WhatsAppWatcher:
    """
    Gold Tier WhatsApp Watcher - Message monitoring.
    
    Responsibilities:
    - Poll WhatsApp Business API for new messages
    - Convert messages to action files
    - Publish events to the event bus
    
    Note: This is a stub for future WhatsApp Business API integration.
    Currently operates in simulation mode.
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger("WhatsAppWatcher")
        self.event_bus = get_event_bus()
        
        # Configuration
        self.vault_path: Optional[str] = None
        self.poll_interval: int = 60  # seconds
        self.api_token: Optional[str] = None
        self.phone_number_id: Optional[str] = None
        
        # State
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        
        # Metrics
        self._messages_processed = 0
        self._actions_created = 0
        
        # Load configuration
        self._load_config()
        
        self.logger.info("WhatsAppWatcher initialized (stub mode)")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            self.vault_path = self.config.get('app', {}).get('vault_path', './AI_Employee_Vault')
            self.poll_interval = self.config.get('watcher', {}).get('poll_interval', 60)
            
            # WhatsApp API config (not set by default)
            self.api_token = self.config.get('whatsapp', {}).get('api_token')
            self.phone_number_id = self.config.get('whatsapp', {}).get('phone_number_id')
            
            if not all([self.api_token, self.phone_number_id]):
                self.logger.info("WhatsApp API not configured - running in stub mode")
            
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            self.vault_path = './AI_Employee_Vault'
    
    async def start(self):
        """Start the WhatsApp watcher."""
        self._running = True
        
        # In production, start the poll loop
        # For now, just mark as running
        self.logger.info("WhatsAppWatcher started (stub mode - no actual polling)")
        
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": "whatsapp_watcher", "mode": "stub"},
            source="whatsapp_watcher"
        )
    
    async def stop(self):
        """Stop the WhatsApp watcher."""
        if not self._running:
            return
        
        self._running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("WhatsAppWatcher stopped")
        
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "whatsapp_watcher"},
            source="whatsapp_watcher"
        )
    
    def health_check(self) -> bool:
        """Check service health."""
        # Always healthy in stub mode
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "messages_processed": self._messages_processed,
            "actions_created": self._actions_created,
            "api_configured": all([self.api_token, self.phone_number_id]),
            "mode": "stub"
        }
    
    async def _poll_messages(self):
        """Poll WhatsApp for new messages."""
        # TODO: Implement WhatsApp Business API integration
        # API endpoint: https://graph.facebook.com/v17.0/{phone-number-id}/messages
        pass
    
    def _process_message(self, message: Dict[str, Any]):
        """
        Process a WhatsApp message.
        
        Args:
            message: WhatsApp message data
        """
        # Extract message data
        sender = message.get('from', 'unknown')
        content = message.get('text', {}).get('body', '')
        timestamp = message.get('timestamp', '')
        
        # Determine action type
        action_type = self._determine_action_type(content)
        
        # Create action file
        action = ActionFile(
            action_type=action_type,
            priority="medium",
            context={
                'sender': sender,
                'message': content,
                'timestamp': timestamp,
                'source': 'whatsapp'
            },
            source='whatsapp'
        )
        
        # Save action file
        self._save_action_file(action)
        
        # Update metrics
        self._messages_processed += 1
        self._actions_created += 1
        
        # Publish event
        publish_event(
            EventType.ACTION_GENERATED,
            {
                "action_id": action.id,
                "action_type": action.type,
                "source": "whatsapp"
            },
            source="whatsapp_watcher"
        )
        
        self.logger.info(f"WhatsApp message processed from {sender}")
    
    def _determine_action_type(self, content: str) -> str:
        """Determine action type from message content."""
        content_lower = content.lower()
        
        if any(kw in content_lower for kw in ['meeting', 'schedule', 'call']):
            return 'meeting_request'
        elif any(kw in content_lower for kw in ['report', 'summary']):
            return 'report_generation'
        elif any(kw in content_lower for kw in ['analyze', 'data']):
            return 'data_analysis'
        elif any(kw in content_lower for kw in ['document', 'create']):
            return 'document_creation'
        else:
            return 'email_response'
    
    def _save_action_file(self, action: ActionFile) -> Path:
        """Save action file to Needs_Action folder."""
        needs_action_path = Path(self.vault_path) / "Needs_Action"
        ensure_directory_exists(str(needs_action_path))
        
        action_filename = f"{action.id}.action.yaml"
        action_path = needs_action_path / action_filename
        
        action.save_to_file(str(action_path))
        
        return action_path


# Factory function
def create_whatsapp_watcher(config_path: str = "./config.yaml") -> WhatsAppWatcher:
    """Factory function to create WhatsAppWatcher."""
    return WhatsAppWatcher(config_path)
