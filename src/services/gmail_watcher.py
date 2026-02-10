"""
Gmail watcher service for AI Employee Foundation
Monitors Gmail inbox for new emails and creates action files
"""
import os
import pickle
import os.path
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import hashlib
import hmac
from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add the src directory to the path so we can import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from models.action_file import ActionFile
from lib.utils import get_current_iso_timestamp, get_environment_variable
from lib.exceptions import GmailWatcherError, AuthenticationError
from lib.constants import ENV_GMAIL_CLIENT_ID, ENV_GMAIL_CLIENT_SECRET, ENV_GMAIL_REFRESH_TOKEN


class GmailWatcher:
    """
    Service that watches Gmail inbox for new emails and creates action files based on the content.
    """

    # Define the scopes required for the Gmail API
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    def __init__(self, config_path: str = "./config.yaml", encryption_key: bytes = None):
        """
        Initialize the Gmail watcher with configuration.

        Args:
            config_path: Path to the configuration file
            encryption_key: Optional encryption key for securing credentials
        """
        self.config_path = config_path
        self.service = None
        self.credentials = None
        self.token_path = "token.pickle"
        self.encryption_key = encryption_key or self._get_or_create_encryption_key()

        # Load configuration
        self.load_config()

        # Authenticate with Gmail
        self.authenticate()

    def _get_or_create_encryption_key(self) -> bytes:
        """
        Get or create an encryption key for securing credentials.
        
        Returns:
            Encryption key as bytes
        """
        key_path = "credentials.key"
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as key_file:
                return key_file.read()
        else:
            # Generate a new key and save it securely
            key = Fernet.generate_key()
            with open(key_path, "wb") as key_file:
                key_file.write(key)
            # Set restrictive permissions on the key file
            os.chmod(key_path, 0o600)  # Read/write for owner only
            return key

    def load_config(self):
        """Load configuration from the config file."""
        # In a real implementation, we would load the config file and extract the necessary values
        # For now, we'll use environment variables with secure retrieval
        self.client_id = get_environment_variable(ENV_GMAIL_CLIENT_ID)
        self.client_secret = get_environment_variable(ENV_GMAIL_CLIENT_SECRET)
        self.refresh_token = get_environment_variable(ENV_GMAIL_REFRESH_TOKEN)

        # Validate that required credentials are present
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise AuthenticationError(
                "Missing required Gmail credentials. Please set GMAIL_CLIENT_ID, "
                "GMAIL_CLIENT_SECRET, and GMAIL_REFRESH_TOKEN environment variables."
            )

    def authenticate(self):
        """Authenticate with the Gmail API using OAuth2."""
        try:
            # Load existing credentials if available
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    encrypted_token_data = token.read()
                    
                # Decrypt the token data
                fernet = Fernet(self.encryption_key)
                decrypted_token_data = fernet.decrypt(encrypted_token_data)
                
                # Load credentials from decrypted data
                import io
                token_buffer = io.BytesIO(decrypted_token_data)
                self.credentials = pickle.load(token_buffer)

            # If there are no valid credentials, request authorization
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    # Validate that required credentials are available
                    if not self.client_id or not self.client_secret:
                        raise AuthenticationError(
                            "Gmail credentials not found. Please set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET environment variables."
                        )

                    # For this implementation, we'll skip the full OAuth flow and just store dummy credentials
                    # In a real implementation, we would run the OAuth flow
                    print("Gmail authentication would normally happen here. Using dummy credentials for this implementation.")
                    self.credentials = Credentials(
                        token="dummy_token",
                        refresh_token=self.refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=self.client_id,
                        client_secret=self.client_secret,
                        scopes=self.SCOPES
                    )

                # Encrypt and save the credentials for the next run
                import io
                token_buffer = io.BytesIO()
                pickle.dump(self.credentials, token_buffer)
                token_data = token_buffer.getvalue()
                
                fernet = Fernet(self.encryption_key)
                encrypted_token_data = fernet.encrypt(token_data)
                
                with open(self.token_path, 'wb') as token:
                    token.write(encrypted_token_data)
                    
                # Set restrictive permissions on the token file
                os.chmod(self.token_path, 0o600)  # Read/write for owner only

            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=self.credentials)

        except AuthenticationError:
            raise
        except Exception as e:
            raise GmailWatcherError(f"Error authenticating with Gmail: {str(e)}")
    
    def get_new_emails(self, max_results: int = 10) -> list:
        """
        Get new unread emails from the Gmail inbox.
        
        Args:
            max_results: Maximum number of emails to retrieve
            
        Returns:
            List of email message objects
        """
        try:
            # Query for unread emails
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            for msg in messages:
                # Get the full message details
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                email_list.append(message)
            
            return email_list
            
        except HttpError as e:
            raise GmailWatcherError(f"Gmail API error: {str(e)}")
        except Exception as e:
            raise GmailWatcherError(f"Error retrieving emails: {str(e)}")
    
    def extract_email_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant data from a Gmail message.
        
        Args:
            message: Gmail message object
            
        Returns:
            Dictionary containing extracted email data
        """
        headers = {header['name']: header['value'] for header in message['payload'].get('headers', [])}
        
        # Extract relevant information
        email_data = {
            'id': message['id'],
            'thread_id': message['threadId'],
            'snippet': message.get('snippet', ''),
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'to': headers.get('To', ''),
            'date': headers.get('Date', ''),
            'labels': message.get('labelIds', []),
        }
        
        # Extract the body content
        body = self.extract_body(message)
        email_data['body'] = body
        
        return email_data
    
    def extract_body(self, message: Dict[str, Any]) -> str:
        """
        Extract the body content from a Gmail message.
        
        Args:
            message: Gmail message object
            
        Returns:
            Body content as a string
        """
        body = ""
        
        # Check if the message has a body in the payload
        if 'body' in message['payload']:
            if 'data' in message['payload']['body']:
                import base64
                body_data = message['payload']['body']['data']
                body = base64.urlsafe_b64decode(body_data).decode('utf-8')
        else:
            # If no direct body, look for parts
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        import base64
                        body_data = part['body']['data']
                        body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
        
        return body
    
    def create_action_from_email(self, email_data: Dict[str, Any], vault_path: str) -> ActionFile:
        """
        Create an action file based on the email data.
        
        Args:
            email_data: Dictionary containing email data
            vault_path: Path to the vault where the action file should be created
            
        Returns:
            ActionFile instance
        """
        # Determine the action type based on the email content
        action_type = self.determine_action_type(email_data)
        
        # Determine priority based on sender or other factors
        priority = self.determine_priority(email_data)
        
        # Create context based on email data
        context = {
            'sender': email_data['from'],
            'subject': email_data['subject'],
            'snippet': email_data['snippet'],
            'body_preview': email_data['body'][:200] if email_data['body'] else '',  # First 200 chars
            'received_date': email_data['date'],
        }
        
        # Create the action file
        action = ActionFile(
            action_type=action_type,
            priority=priority,
            context=context,
            created_at=get_current_iso_timestamp(),
            source='gmail'
        )
        
        # Validate the action
        action.validate()
        
        # Save the action file to the Needs_Action folder in the vault
        needs_action_path = Path(vault_path) / "Needs_Action"
        action_filename = f"{action.id}.action.yaml"
        action_path = needs_action_path / action_filename
        
        action.save_to_file(str(action_path))
        
        return action
    
    def determine_action_type(self, email_data: Dict[str, Any]) -> str:
        """
        Determine the action type based on the email content.
        
        Args:
            email_data: Dictionary containing email data
            
        Returns:
            Action type string
        """
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        
        # Simple heuristics to determine action type
        if any(keyword in subject or keyword in body for keyword in ['meeting', 'schedule', 'appointment']):
            return 'meeting_request'
        elif any(keyword in subject or keyword in body for keyword in ['email', 'reply', 'response']):
            return 'email_response'
        elif any(keyword in subject or keyword in body for keyword in ['document', 'create', 'write']):
            return 'document_creation'
        elif any(keyword in subject or keyword in body for keyword in ['analyze', 'analysis', 'data']):
            return 'data_analysis'
        elif any(keyword in subject or keyword in body for keyword in ['report', 'summary']):
            return 'report_generation'
        elif any(keyword in subject or keyword in body for keyword in ['follow up', 'follow-up', 'remind']):
            return 'follow_up'
        else:
            return 'email_response'  # Default action type
    
    def determine_priority(self, email_data: Dict[str, Any]) -> str:
        """
        Determine the priority based on the email content.
        
        Args:
            email_data: Dictionary containing email data
            
        Returns:
            Priority string ('low', 'medium', 'high')
        """
        # Simple heuristic: check for urgency keywords
        subject = email_data.get('subject', '').lower()
        sender = email_data.get('from', '').lower()
        
        # Check for urgency keywords in subject
        urgent_keywords = ['urgent', 'asap', 'immediate', 'today', 'now']
        if any(keyword in subject for keyword in urgent_keywords):
            return 'high'
        
        # Check if sender is in a VIP list (would come from config in real implementation)
        # For now, we'll just check for common VIP indicators
        if any(vip in sender for vip in ['boss', 'manager', 'ceo', 'cto', 'important']):
            return 'high'
        
        # Default to medium priority
        return 'medium'
    
    def mark_as_read(self, email_id: str):
        """
        Mark an email as read in Gmail.
        
        Args:
            email_id: ID of the email to mark as read
        """
        try:
            # Remove the UNREAD label
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
        except HttpError as e:
            raise GmailWatcherError(f"Error marking email as read: {str(e)}")
    
    def start_monitoring(self, vault_path: str, poll_interval: int = 30):
        """
        Start monitoring Gmail for new emails.
        
        Args:
            vault_path: Path to the vault where action files should be created
            poll_interval: Interval in seconds between checking for new emails
        """
        print(f"Starting Gmail monitoring. Checking every {poll_interval} seconds...")
        
        try:
            while True:
                # Get new emails
                emails = self.get_new_emails()
                
                if emails:
                    print(f"Found {len(emails)} new emails")
                    
                    for email in emails:
                        try:
                            # Extract email data
                            email_data = self.extract_email_data(email)
                            
                            # Create action file from email
                            action = self.create_action_from_email(email_data, vault_path)
                            
                            print(f"Created action file: {action.id} for email '{email_data['subject']}'")
                            
                            # Mark email as read
                            self.mark_as_read(email['id'])
                            
                        except Exception as e:
                            print(f"Error processing email {email.get('id', 'unknown')}: {str(e)}")
                            continue
                
                # Wait before checking again
                import time
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print("Gmail monitoring stopped by user")
        except Exception as e:
            raise GmailWatcherError(f"Error in Gmail monitoring: {str(e)}")
    
    def stop_monitoring(self):
        """Stop monitoring Gmail."""
        print("Stopping Gmail monitoring...")
        # In a real implementation, we would have a mechanism to stop the monitoring loop
        # For now, we'll just print a message