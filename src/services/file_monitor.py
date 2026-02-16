"""
File Monitor Service - Gold Tier
Event-driven filesystem watcher using watchdog
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent, FileMovedEvent, FileDeletedEvent
import yaml
import time

# Add the src directory to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.event_bus import EventType, publish_event, get_event_bus
from lib.utils import get_current_iso_timestamp, ensure_directory_exists
from lib.constants import ACTION_FILE_EXT
from models.action_file import ActionFile


class FileEventHandler(FileSystemEventHandler):
    """Handler for file system events with event bus integration."""
    
    def __init__(self, folder_name: str, event_bus, logger: logging.Logger):
        self.folder_name = folder_name
        self.event_bus = event_bus
        self.logger = logger
        self._debounce: Dict[str, float] = {}
        self._debounce_interval = 0.5  # seconds
    
    def _should_process(self, path: str) -> bool:
        """Debounce rapid file events."""
        now = time.time()
        last_time = self._debounce.get(path, 0)
        
        if now - last_time < self._debounce_interval:
            return False
        
        self._debounce[path] = now
        return True
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        file_path = Path(event.src_path)
        self.logger.debug(f"File created in {self.folder_name}: {file_path.name}")
        
        publish_event(
            EventType.FILE_CREATED,
            {
                "path": str(file_path),
                "filename": file_path.name,
                "folder": self.folder_name,
                "size": file_path.stat().st_size if file_path.exists() else 0
            },
            source=f"file_monitor.{self.folder_name}"
        )
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        file_path = Path(event.src_path)
        self.logger.debug(f"File modified in {self.folder_name}: {file_path.name}")
        
        publish_event(
            EventType.FILE_MODIFIED,
            {
                "path": str(file_path),
                "filename": file_path.name,
                "folder": self.folder_name
            },
            source=f"file_monitor.{self.folder_name}"
        )
    
    def on_moved(self, event):
        """Handle file move events."""
        if event.is_directory:
            return
        
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        
        self.logger.debug(f"File moved: {src_path.name} -> {dest_path}")
        
        publish_event(
            EventType.FILE_MOVED,
            {
                "src_path": str(src_path),
                "dest_path": str(dest_path),
                "filename": dest_path.name,
                "src_folder": src_path.parent.name,
                "dest_folder": dest_path.parent.name
            },
            source=f"file_monitor.{self.folder_name}"
        )
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        self.logger.debug(f"File deleted in {self.folder_name}: {file_path.name}")
        
        publish_event(
            EventType.FILE_DELETED,
            {
                "path": str(file_path),
                "filename": file_path.name,
                "folder": self.folder_name
            },
            source=f"file_monitor.{self.folder_name}"
        )


class FileMonitor:
    """
    Gold Tier File Monitor - Event-driven filesystem watcher.
    
    Responsibilities:
    - Monitor vault folders for file changes using watchdog
    - Publish events to the event bus
    - Convert inbox files to action files
    - Track file workflow transitions
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.vault_path: Optional[str] = None
        self.logger = logging.getLogger("FileMonitor")
        self.event_bus = get_event_bus()
        
        # Watchdog observer
        self._observer: Optional[Observer] = None
        self._running = False
        
        # Folder handlers
        self._handlers: Dict[str, FileEventHandler] = {}
        
        # Metrics
        self._events_processed = 0
        self._actions_created = 0
        
        # Load configuration
        self._load_config()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        self.logger.info("FileMonitor initialized")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            self.vault_path = self.config.get('app', {}).get('vault_path', './AI_Employee_Vault')
            
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            self.vault_path = './AI_Employee_Vault'
    
    def _setup_event_handlers(self):
        """Setup event bus handlers for file events."""
        # Handle inbox file creation - convert to action
        self.event_bus.subscribe(
            EventType.FILE_CREATED,
            self._on_file_created,
            async_callback=True
        )
        
        # Handle file moves (for workflow transitions)
        self.event_bus.subscribe(
            EventType.FILE_MOVED,
            self._on_file_moved,
            async_callback=True
        )
        
        self.logger.info("FileMonitor event handlers registered")
    
    async def _on_file_created(self, event):
        """Handle file created events."""
        folder = event.payload.get('folder', '')
        file_path = event.payload.get('path', '')
        filename = event.payload.get('filename', '')
        
        self._events_processed += 1
        
        # If file created in Inbox, create action file
        if folder == 'Inbox':
            await self._process_inbox_file(Path(file_path))
    
    async def _on_file_moved(self, event):
        """Handle file moved events - track workflow transitions."""
        src_folder = event.payload.get('src_folder', '')
        dest_folder = event.payload.get('dest_folder', '')
        filename = event.payload.get('filename', '')
        
        self._events_processed += 1
        self.logger.info(f"Workflow transition: {filename} ({src_folder} -> {dest_folder})")
        
        # Track specific transitions
        if dest_folder == 'Approved':
            publish_event(
                EventType.ACTION_APPROVED,
                {"filename": filename, "path": event.payload.get('dest_path')},
                source="file_monitor"
            )
        elif dest_folder == 'Done':
            publish_event(
                EventType.ACTION_EXECUTED,
                {"filename": filename, "path": event.payload.get('dest_path')},
                source="file_monitor"
            )
    
    async def _process_inbox_file(self, file_path: Path):
        """
        Process a file created in Inbox - create action file.
        
        Args:
            file_path: Path to the inbox file
        """
        try:
            self.logger.info(f"Processing inbox file: {file_path.name}")
            
            # Read file content
            content = ""
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')
                except:
                    content = file_path.read_text(encoding='latin-1')
            
            # Determine action type based on content/filename
            action_type = self._determine_action_type(file_path.name, content)
            
            # Create action file
            action = ActionFile(
                action_type=action_type,
                priority="medium",
                context={
                    "source_file": file_path.name,
                    "content_preview": content[:500] if content else "",
                    "file_path": str(file_path)
                },
                source="filesystem"
            )
            
            # Save action file to Needs_Action
            needs_action_path = Path(self.vault_path) / "Needs_Action"
            ensure_directory_exists(str(needs_action_path))
            
            action_filename = f"{action.id}.action.yaml"
            action_path = needs_action_path / action_filename
            
            action.save_to_file(str(action_path))
            
            self._actions_created += 1
            self.logger.info(f"Action file created: {action_path.name}")
            
            # Publish action generated event
            publish_event(
                EventType.ACTION_GENERATED,
                {
                    "action_id": action.id,
                    "action_type": action.type,
                    "action_path": str(action_path),
                    "source": "filesystem"
                },
                source="file_monitor"
            )
            
            # Move original file to processed (optional - can be configured)
            # For now, we leave it in Inbox
            
        except Exception as e:
            self.logger.error(f"Error processing inbox file {file_path.name}: {e}")
    
    def _determine_action_type(self, filename: str, content: str) -> str:
        """Determine action type based on filename and content."""
        filename_lower = filename.lower()
        content_lower = content.lower()
        
        # Check filename patterns
        if 'meeting' in filename_lower or 'calendar' in filename_lower:
            return 'meeting_request'
        elif 'report' in filename_lower:
            return 'report_generation'
        elif 'analysis' in filename_lower or 'data' in filename_lower:
            return 'data_analysis'
        elif 'doc' in filename_lower or 'document' in filename_lower:
            return 'document_creation'
        
        # Check content patterns
        if 'meeting' in content_lower or 'schedule' in content_lower:
            return 'meeting_request'
        elif 'report' in content_lower or 'summary' in content_lower:
            return 'report_generation'
        elif 'analyze' in content_lower or 'analysis' in content_lower:
            return 'data_analysis'
        elif 'document' in content_lower or 'create' in content_lower:
            return 'document_creation'
        elif 'follow up' in content_lower or 'follow-up' in content_lower:
            return 'follow_up'
        
        return 'email_response'  # Default
    
    def start(self):
        """Start the file monitor."""
        if self._running:
            self.logger.warning("FileMonitor already running")
            return
        
        self._running = True
        
        # Create observer
        self._observer = Observer()
        
        # Setup folders to monitor
        folders = ['Inbox', 'Needs_Action', 'Plans', 'Pending_Approval', 'Approved', 'Done']
        
        for folder_name in folders:
            folder_path = Path(self.vault_path) / folder_name
            ensure_directory_exists(str(folder_path))
            
            # Create handler for this folder
            handler = FileEventHandler(folder_name, self.event_bus, self.logger)
            self._handlers[folder_name] = handler
            
            # Schedule monitoring
            self._observer.schedule(handler, str(folder_path), recursive=False)
            self.logger.debug(f"Monitoring folder: {folder_name}")
        
        # Start observer
        self._observer.start()
        
        self.logger.info("FileMonitor started")
        
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": "file_monitor"},
            source="file_monitor"
        )
    
    def stop(self):
        """Stop the file monitor."""
        if not self._running:
            return
        
        self._running = False
        
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        
        self.logger.info("FileMonitor stopped")
        
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "file_monitor"},
            source="file_monitor"
        )
    
    def health_check(self) -> bool:
        """Check service health."""
        if not self._running:
            return False
        
        if not self._observer or not self._observer.is_alive():
            return False
        
        # Check vault path exists
        return Path(self.vault_path).exists()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "events_processed": self._events_processed,
            "actions_created": self._actions_created,
            "folders_monitored": len(self._handlers),
            "vault_path": self.vault_path,
            "observer_alive": self._observer.is_alive() if self._observer else False
        }


# Factory function
def create_file_monitor(config_path: str = "./config.yaml") -> FileMonitor:
    """Factory function to create FileMonitor."""
    return FileMonitor(config_path)
