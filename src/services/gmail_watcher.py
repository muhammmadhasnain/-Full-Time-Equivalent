"""
Gmail Watcher Service - Gold Tier
Event-driven email monitoring with OAuth2 authentication
"""
import asyncio
import logging
import os
import base64
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import yaml

# Add the src directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.event_bus import EventType, publish_event, get_event_bus
from lib.utils import get_current_iso_timestamp, ensure_directory_exists
from lib.constants import ENV_GMAIL_CLIENT_ID, ENV_GMAIL_CLIENT_SECRET, ENV_GMAIL_REFRESH_TOKEN
from lib.exceptions import GmailWatcherError, AuthenticationError
from models.action_file import ActionFile


class GmailWatcher:
    """
    Gold Tier Gmail Watcher - Event-driven email monitoring.
    
    Responsibilities:
    - Poll Gmail inbox for new emails using Gmail API
    - Convert emails to action files
    - Publish events to the event bus
    - Handle OAuth2 authentication
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger("GmailWatcher")
        self.event_bus = get_event_bus()
        
        # Configuration
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.vault_path: Optional[str] = None
        self.poll_interval: int = 60  # seconds
        
        # State
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._credentials: Optional[Any] = None
        self._service: Optional[Any] = None
        self._processed_email_ids: set = set()
        
        # Metrics
        self._emails_processed = 0
        self._actions_created = 0
        self._errors = 0
        self._last_poll: Optional[str] = None
        
        # Load configuration
        self._load_config()
        
        self.logger.info("GmailWatcher initialized")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            # Load credentials from environment or config
            self.client_id = (
                os.getenv(ENV_GMAIL_CLIENT_ID) or 
                self.config.get('gmail', {}).get('client_id')
            )
            self.client_secret = (
                os.getenv(ENV_GMAIL_CLIENT_SECRET) or 
                self.config.get('gmail', {}).get('client_secret')
            )
            self.refresh_token = (
                os.getenv(ENV_GMAIL_REFRESH_TOKEN) or 
                self.config.get('gmail', {}).get('refresh_token')
            )
            
            self.vault_path = self.config.get('app', {}).get('vault_path', './AI_Employee_Vault')
            self.poll_interval = self.config.get('watcher', {}).get('poll_interval', 60)
            
            # Validate credentials
            if not all([self.client_id, self.client_secret, self.refresh_token]):
                self.logger.warning("Gmail credentials not fully configured. Email monitoring disabled.")
            
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            self.vault_path = './AI_Employee_Vault'
    
    async def start(self):
        """Start the Gmail watcher."""
        if self._running:
            self.logger.warning("GmailWatcher already running")
            return
        
        # Check if credentials are configured
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            self.logger.warning("Cannot start Gmail watcher - credentials not configured")
            self._running = True  # Mark as running but inactive
            return
        
        self._running = True
        
        try:
            # Authenticate
            await self._authenticate()
            
            # Start polling task
            self._poll_task = asyncio.create_task(self._poll_loop())
            
            self.logger.info(f"GmailWatcher started (poll interval: {self.poll_interval}s)")
            
            publish_event(
                EventType.SERVICE_STARTED,
                {"service": "gmail_watcher"},
                source="gmail_watcher"
            )
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Failed to start Gmail watcher: {e}")
            self._running = False
    
    async def stop(self):
        """Stop the Gmail watcher."""
        if not self._running:
            return
        
        self._running = False
        
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("GmailWatcher stopped")
        
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "gmail_watcher"},
            source="gmail_watcher"
        )
    
    def health_check(self) -> bool:
        """Check service health."""
        if not self._running:
            return False
        
        # If credentials not configured, consider healthy but inactive
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            return True
        
        # Check if poll task is running
        return self._poll_task is not None and not self._poll_task.done()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "emails_processed": self._emails_processed,
            "actions_created": self._actions_created,
            "errors": self._errors,
            "last_poll": self._last_poll,
            "poll_interval": self.poll_interval,
            "credentials_configured": all([self.client_id, self.client_secret, self.refresh_token])
        }
    
    async def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            
            # Try to load existing credentials
            self._credentials = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=[
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.modify'
                ]
            )
            
            # Refresh token
            if self._credentials.expired or not self._credentials.valid:
                self._credentials.refresh(Request())
            
            # Build Gmail service
            self._service = build('gmail', 'v1', credentials=self._credentials)
            
            self.logger.info("Gmail authentication successful")
            
        except ImportError:
            self.logger.warning("Google API packages not installed. Email monitoring disabled.")
            self._service = None
        except Exception as e:
            self._errors += 1
            raise GmailWatcherError(f"Authentication failed: {e}")
    
    async def _poll_loop(self):
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_inbox()
                self._last_poll = get_current_iso_timestamp()
            except Exception as e:
                self._errors += 1
                self.logger.error(f"Poll error: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def _poll_inbox(self):
        """Poll Gmail inbox for new emails."""
        if not self._service:
            return
        
        try:
            # Fetch unread emails
            results = self._service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                self.logger.debug("No new emails")
                return
            
            self.logger.info(f"Found {len(messages)} new emails")
            
            for msg in messages:
                await self._process_email(msg['id'])
            
        except Exception as e:
            self._errors += 1
            raise GmailWatcherError(f"Poll failed: {e}")
    
    async def _process_email(self, email_id: str):
        """
        Process a single email.
        
        Args:
            email_id: Gmail message ID
        """
        try:
            # Skip if already processed
            if email_id in self._processed_email_ids:
                return
            
            # Fetch email details
            message = self._service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            
            # Extract email data
            email_data = self._extract_email_data(message)
            
            # Create action file from email
            action = self._create_action_from_email(email_data)
            
            # Save action file
            action_path = self._save_action_file(action)
            
            # Mark email as read
            self._mark_email_read(email_id)
            
            # Update metrics
            self._emails_processed += 1
            self._actions_created += 1
            self._processed_email_ids.add(email_id)
            
            self.logger.info(f"Email processed: {email_data['subject'][:50]}...")
            
            # Publish action generated event
            publish_event(
                EventType.ACTION_GENERATED,
                {
                    "action_id": action.id,
                    "action_type": action.type,
                    "action_path": str(action_path),
                    "source": "gmail",
                    "email_id": email_id
                },
                source="gmail_watcher"
            )
            
        except Exception as e:
            self._errors += 1
            self.logger.error(f"Error processing email {email_id}: {e}")
    
    def _extract_email_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from Gmail message."""
        headers = {
            h['name']: h['value'] 
            for h in message['payload'].get('headers', [])
        }
        
        body = self._extract_email_body(message)
        
        return {
            'id': message['id'],
            'thread_id': message['threadId'],
            'snippet': message.get('snippet', ''),
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'date': headers.get('Date', ''),
            'labels': message.get('labelIds', []),
            'body': body
        }
    
    def _extract_email_body(self, message: Dict[str, Any]) -> str:
        """Extract body content from Gmail message."""
        body = ""
        
        # Check for direct body
        if 'body' in message['payload']:
            if 'data' in message['payload']['body']:
                data = message['payload']['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            # Check parts
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        if 'data' in part['body']:
                            data = part['body']['data']
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
                            break
        
        return body
    
    def _create_action_from_email(self, email_data: Dict[str, Any]) -> ActionFile:
        """Create action file from email data."""
        action_type = self._determine_action_type(email_data)
        priority = self._determine_priority(email_data)
        
        context = {
            'sender': email_data['from'],
            'subject': email_data['subject'],
            'snippet': email_data['snippet'],
            'body_preview': email_data['body'][:500] if email_data['body'] else '',
            'received_date': email_data['date'],
            'email_id': email_data['id'],
            'thread_id': email_data['thread_id']
        }
        
        return ActionFile(
            action_type=action_type,
            priority=priority,
            context=context,
            created_at=get_current_iso_timestamp(),
            source='gmail'
        )
    
    def _determine_action_type(self, email_data: Dict[str, Any]) -> str:
        """Determine action type from email content."""
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        content = f"{subject} {body}"
        
        if any(kw in content for kw in ['meeting', 'schedule', 'calendar', 'appointment']):
            return 'meeting_request'
        elif any(kw in content for kw in ['report', 'summary', 'overview']):
            return 'report_generation'
        elif any(kw in content for kw in ['analyze', 'analysis', 'data', 'metrics']):
            return 'data_analysis'
        elif any(kw in content for kw in ['document', 'create', 'write', 'draft']):
            return 'document_creation'
        elif any(kw in content for kw in ['follow up', 'follow-up', 'remind']):
            return 'follow_up'
        else:
            return 'email_response'
    
    def _determine_priority(self, email_data: Dict[str, Any]) -> str:
        """Determine priority from email."""
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('from', '').lower()
        
        # Urgent keywords
        if any(kw in subject for kw in ['urgent', 'asap', 'immediate', 'today', 'now']):
            return 'high'
        
        # VIP sender indicators
        if any(vip in sender for vip in ['boss', 'manager', 'ceo', 'cto', 'director']):
            return 'high'
        
        return 'medium'
    
    def _save_action_file(self, action: ActionFile) -> Path:
        """Save action file to Needs_Action folder."""
        needs_action_path = Path(self.vault_path) / "Needs_Action"
        ensure_directory_exists(str(needs_action_path))
        
        action_filename = f"{action.id}.action.yaml"
        action_path = needs_action_path / action_filename
        
        action.save_to_file(str(action_path))
        
        return action_path
    
    def _mark_email_read(self, email_id: str):
        """Mark email as read in Gmail."""
        try:
            self._service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
        except Exception as e:
            self.logger.error(f"Failed to mark email as read: {e}")


# Factory function
def create_gmail_watcher(config_path: str = "./config.yaml") -> GmailWatcher:
    """Factory function to create GmailWatcher."""
    return GmailWatcher(config_path)
