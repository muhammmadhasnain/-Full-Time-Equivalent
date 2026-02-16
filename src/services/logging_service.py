"""
Logging Service - Gold Tier
Centralized structured logging with log aggregation
"""
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import yaml
import sys

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.event_bus import EventType, get_event_bus, Event
from lib.utils import get_current_iso_timestamp


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName', 
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName']:
                log_data[key] = value
        
        return json.dumps(log_data)


class LoggingService:
    """
    Gold Tier Logging Service - Centralized structured logging.
    
    Responsibilities:
    - Configure application-wide logging
    - Support multiple log formats (JSON, text)
    - Log aggregation to file
    - Event bus integration for system events
    """
    
    def __init__(self, config_path: str = "./config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger("LoggingService")
        self.event_bus = get_event_bus()
        
        # Configuration
        self.log_level: str = "INFO"
        self.log_format: str = "json"  # json or text
        self.log_file: Optional[str] = None
        self.log_dir: str = "./logs"
        
        # Metrics
        self._events_logged = 0
        
        # Load configuration
        self._load_config()
        
        # Setup logging
        self._setup_logging()
        
        # Setup event handlers
        self._setup_event_handlers()
        
        self.logger.info("LoggingService initialized")
    
    def _load_config(self):
        """Load configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
            
            logging_config = self.config.get('logging', {})
            self.log_level = logging_config.get('level', 'INFO')
            self.log_format = logging_config.get('format', 'json').split('%')[0]  # Simple check
            self.log_file = logging_config.get('file', './logs/app.log')
            self.log_dir = str(Path(self.log_file).parent) if self.log_file else './logs'
            
        except Exception as e:
            self.log_level = 'INFO'
            self.log_file = './logs/app.log'
            self.log_dir = './logs'
    
    def _setup_logging(self):
        """Configure application logging."""
        # Ensure log directory exists
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.log_level.upper(), logging.INFO))
        
        # Clear existing handlers
        root_logger.handlers = []
        
        # Create handlers
        handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        if self.log_format == 'json':
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
        
        handlers.append(console_handler)
        
        # File handler
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(JSONFormatter())
            handlers.append(file_handler)
        
        # Add handlers to root logger
        for handler in handlers:
            root_logger.addHandler(handler)
        
        self.logger = logging.getLogger("LoggingService")
        self.logger.info(f"Logging configured: level={self.log_level}, format={self.log_format}, file={self.log_file}")
    
    def _setup_event_handlers(self):
        """Setup event bus handlers for system events."""
        # Log all system events
        for event_type in EventType:
            self.event_bus.subscribe(
                event_type,
                self._on_event,
                async_callback=False
            )
        
        self.logger.info("LoggingService event handlers registered")
    
    def _on_event(self, event: Event):
        """Handle system events - log them."""
        self._events_logged += 1
        
        # Log based on event type
        if event.event_type in [EventType.SERVICE_ERROR, EventType.ACTION_FAILED]:
            self.logger.warning(f"Event: {event.event_type.value} - {event.payload}")
        elif event.event_type in [EventType.SYSTEM_SHUTDOWN, EventType.SYSTEM_RESTART]:
            self.logger.info(f"System event: {event.event_type.value}")
        else:
            self.logger.debug(f"Event: {event.event_type.value} from {event.source}")
    
    def start(self):
        """Start the logging service."""
        self.logger.info("LoggingService started")
        
        publish_event = self.event_bus.publish
        publish_event(
            EventType.SERVICE_STARTED,
            {"service": "logging_service"},
            source="logging_service"
        )
    
    def stop(self):
        """Stop the logging service."""
        # Flush all handlers
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        self.logger.info("LoggingService stopped")
        
        publish_event = self.event_bus.publish
        publish_event(
            EventType.SERVICE_STOPPED,
            {"service": "logging_service"},
            source="logging_service"
        )
    
    def health_check(self) -> bool:
        """Check service health."""
        # Logging is always healthy if we got here
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        return {
            "events_logged": self._events_logged,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "log_file": self.log_file
        }
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance.
        
        Args:
            name: Logger name (usually __name__)
            
        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)


# Factory function
def create_logging_service(config_path: str = "./config.yaml") -> LoggingService:
    """Factory function to create LoggingService."""
    return LoggingService(config_path)
