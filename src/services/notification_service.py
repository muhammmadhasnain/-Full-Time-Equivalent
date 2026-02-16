"""
Notification Service - Gold Tier
Sends notifications when Pending_Approval receives new files
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.event_bus import EventType, get_event_bus, Event
from lib.utils import get_current_iso_timestamp


class NotificationChannel:
    """Base notification channel."""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.logger = logging.getLogger(f"NotificationChannel.{name}")
    
    async def send(self, title: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        """Send a notification."""
        raise NotImplementedError


class ConsoleNotificationChannel(NotificationChannel):
    """Console notification channel (for testing)."""
    
    def __init__(self):
        super().__init__("console", enabled=True)
    
    async def send(self, title: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        """Print notification to console."""
        print(f"\n🔔 NOTIFICATION: {title}")
        print(f"   {message}")
        if metadata:
            for key, value in metadata.items():
                print(f"   {key}: {value}")
        print()
        return True


class LogNotificationChannel(NotificationChannel):
    """Log-based notification channel."""
    
    def __init__(self, log_path: str):
        super().__init__("log", enabled=True)
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def send(self, title: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        """Write notification to log file."""
        entry = {
            "timestamp": get_current_iso_timestamp(),
            "type": "notification",
            "title": title,
            "message": message,
            "metadata": metadata or {}
        }
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            import json
            f.write(json.dumps(entry) + "\n")
        
        self.logger.info(f"Notification logged: {title}")
        return True


class WebhookNotificationChannel(NotificationChannel):
    """Webhook notification channel (Slack, Teams, etc.)."""
    
    def __init__(self, webhook_url: str, channel_type: str = "slack"):
        super().__init__(f"webhook.{channel_type}", enabled=True)
        self.webhook_url = webhook_url
        self.channel_type = channel_type
    
    async def send(self, title: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        """Send notification via webhook."""
        try:
            import aiohttp
            
            if self.channel_type == "slack":
                payload = {
                    "text": title,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": title}
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": message}
                        }
                    ]
                }
            elif self.channel_type == "teams":
                payload = {
                    "title": title,
                    "text": message
                }
            else:
                payload = {"title": title, "message": message, "metadata": metadata}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info(f"Webhook notification sent: {title}")
                        return True
                    else:
                        self.logger.error(f"Webhook failed: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Webhook error: {e}")
            return False


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        recipients: List[str],
        username: str = "",
        password: str = ""
    ):
        super().__init__("email", enabled=True)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients
        self.username = username
        self.password = password
    
    async def send(self, title: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        """Send notification via email."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f"[AI Employee] {title}"
            
            body = f"{title}\n\n{message}\n\nMetadata: {metadata}"
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.username and self.password:
                server.starttls()
                server.login(self.username, self.password)
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email notification sent to {len(self.recipients)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Email error: {e}")
            return False


class NotificationService:
    """
    Central notification service for all system events.
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger("NotificationService")
        self.event_bus = get_event_bus()
        
        # Notification channels
        self._channels: Dict[str, NotificationChannel] = {}
        
        # Notification rules
        self._rules: Dict[str, bool] = {
            "approval_required": True,
            "execution_completed": False,
            "execution_failed": True,
            "workflow_error": True
        }
        
        # Initialize
        self._load_config()
        self._setup_channels()
        self._setup_event_handlers()
        
        self.logger.info(f"NotificationService initialized ({len(self._channels)} channels)")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            # Load notification rules
            notification_config = self.config.get('notifications', {})
            self._rules.update(notification_config.get('rules', {}))
            
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
    
    def _setup_channels(self):
        """Setup notification channels from config."""
        # Always add console channel for testing
        self._channels["console"] = ConsoleNotificationChannel()
        
        # Add log channel
        log_path = self.config.get('notifications', {}).get('log_path', './logs/notifications.log')
        self._channels["log"] = LogNotificationChannel(log_path)
        
        # Add webhook channels if configured
        webhooks = self.config.get('notifications', {}).get('webhooks', {})
        for name, webhook_config in webhooks.items():
            if webhook_config.get('enabled', False):
                self._channels[f"webhook.{name}"] = WebhookNotificationChannel(
                    webhook_config.get('url'),
                    webhook_config.get('type', 'slack')
                )
        
        # Add email channel if configured
        email_config = self.config.get('notifications', {}).get('email', {})
        if email_config.get('enabled', False):
            self._channels["email"] = EmailNotificationChannel(
                email_config.get('smtp_host'),
                email_config.get('smtp_port', 587),
                email_config.get('sender'),
                email_config.get('recipients', []),
                email_config.get('username', ''),
                email_config.get('password', '')
            )
    
    def _setup_event_handlers(self):
        """Setup event bus handlers for automatic notifications."""
        # Approval required - always notify
        self.event_bus.subscribe(
            EventType.APPROVAL_REQUIRED,
            self._on_approval_required,
            async_callback=True
        )
        
        # Execution failed - notify if enabled
        self.event_bus.subscribe(
            EventType.ACTION_FAILED,
            self._on_execution_failed,
            async_callback=True
        )
        
        self.logger.info("NotificationService event handlers registered")
    
    async def _on_approval_required(self, event: Event):
        """Handle approval required events."""
        if not self._rules.get("approval_required", True):
            return
        
        approval_id = event.payload.get('approval_id', 'unknown')[:8]
        action_id = event.payload.get('action_id', 'unknown')[:8]
        reason = event.payload.get('reason', 'Standard approval required')
        
        title = "📋 Approval Required"
        message = f"Action {action_id}... requires approval before execution.\nReason: {reason}"
        
        metadata = {
            "approval_id": approval_id,
            "action_id": action_id,
            "event_type": event.event_type.value
        }
        
        await self.notify(title, message, metadata, priority="high")
    
    async def _on_execution_failed(self, event: Event):
        """Handle execution failed events."""
        if not self._rules.get("execution_failed", True):
            return
        
        plan_id = event.payload.get('plan_id', 'unknown')[:8]
        error = event.payload.get('error', 'Unknown error')
        
        title = "❌ Execution Failed"
        message = f"Plan {plan_id}... failed during execution.\nError: {error}"
        
        metadata = {
            "plan_id": plan_id,
            "error": error,
            "event_type": event.event_type.value
        }
        
        await self.notify(title, message, metadata, priority="high")
    
    async def notify(
        self,
        title: str,
        message: str,
        metadata: Dict[str, Any] = None,
        priority: str = "normal",
        channels: List[str] = None
    ):
        """
        Send notification through configured channels.
        
        Args:
            title: Notification title
            message: Notification message
            metadata: Additional metadata
            priority: Priority level (low, normal, high, urgent)
            channels: Specific channels to use (None = all enabled)
        """
        tasks = []
        
        # Determine channels to use
        target_channels = channels or list(self._channels.keys())
        
        for channel_name in target_channels:
            channel = self._channels.get(channel_name)
            if channel and channel.enabled:
                tasks.append(channel.send(title, message, metadata))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)
            self.logger.debug(f"Notification sent to {success_count}/{len(tasks)} channels")
    
    def add_channel(self, name: str, channel: NotificationChannel):
        """Add a notification channel."""
        self._channels[name] = channel
        self.logger.info(f"Notification channel added: {name}")
    
    def remove_channel(self, name: str):
        """Remove a notification channel."""
        if name in self._channels:
            del self._channels[name]
            self.logger.info(f"Notification channel removed: {name}")
    
    def enable_rule(self, rule: str):
        """Enable a notification rule."""
        self._rules[rule] = True
        self.logger.info(f"Notification rule enabled: {rule}")
    
    def disable_rule(self, rule: str):
        """Disable a notification rule."""
        self._rules[rule] = False
        self.logger.info(f"Notification rule disabled: {rule}")
    
    def get_channels(self) -> List[str]:
        """Get list of enabled channel names."""
        return [name for name, channel in self._channels.items() if channel.enabled]
    
    def get_rules(self) -> Dict[str, bool]:
        """Get notification rules."""
        return self._rules.copy()


# Factory function
def create_notification_service(config_path: str = "./config.yaml") -> NotificationService:
    """Factory function to create NotificationService."""
    return NotificationService(config_path)


# Import asyncio for the notify method
import asyncio
