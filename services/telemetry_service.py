import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import json
import platform
import uuid
import requests
from queue import Queue
from threading import Thread, Event
import os

from .base_service import Service

logger = logging.getLogger(__name__)

class TelemetryService(Service):
    """Handles telemetry, analytics, and error reporting."""
    
    def __init__(self):
        super().__init__()
        self.session_id = str(uuid.uuid4())
        self.user_id = self._get_or_create_user_id()
        self.config_dir = Path.home() / ".video-splitter"
        self.logs_dir = self.config_dir / "logs"
        self.crash_dir = self.config_dir / "crashes"
        self.event_queue = Queue()
        self.stop_event = Event()
        self.sender_thread: Optional[Thread] = None
        
        # Telemetry settings
        self.telemetry_enabled = True
        self.error_reporting_enabled = True
        self.server_url = "https://analytics.example.com"  # Replace with actual URL
        
        # System info
        self.system_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "python_version": platform.python_version(),
            "cpu_count": os.cpu_count(),
            "machine": platform.machine()
        }
    
    def start(self) -> None:
        """Start telemetry service."""
        super().start()
        
        # Create necessary directories
        self.config_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.crash_dir.mkdir(exist_ok=True)
        
        # Set up crash handler
        sys.excepthook = self._handle_uncaught_exception
        
        # Start sender thread
        self.stop_event.clear()
        self.sender_thread = Thread(target=self._send_events_worker, daemon=True)
        self.sender_thread.start()
        
        # Log session start
        self.log_event("session_start", {
            "session_id": self.session_id,
            "system_info": self.system_info
        })
    
    def stop(self) -> None:
        """Stop telemetry service."""
        # Log session end
        self.log_event("session_end", {
            "session_id": self.session_id,
            "duration": self._get_session_duration()
        })
        
        # Stop sender thread
        if self.sender_thread:
            self.stop_event.set()
            self.sender_thread.join(timeout=5.0)
        
        super().stop()
    
    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log a telemetry event."""
        if not self.telemetry_enabled:
            return
            
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "data": data
        }
        
        self.event_queue.put(event)
        logger.debug(f"Logged event: {event_type}")
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None) -> None:
        """Log an error for reporting."""
        if not self.error_reporting_enabled:
            return
            
        error_data = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "system_info": self.system_info,
            "context": context or {}
        }
        
        # Save error report locally
        self._save_error_report(error_data)
        
        # Queue error event
        self.log_event("error", error_data)
        
        logger.error(f"Error logged: {error_data['type']}: {error_data['message']}")
    
    def _handle_uncaught_exception(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Call original excepthook for KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        error_data = {
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": "".join(traceback.format_exception(
                exc_type, exc_value, exc_traceback
            )),
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "system_info": self.system_info,
            "is_crash": True
        }
        
        # Save crash report
        self._save_crash_report(error_data)
        
        # Try to send the crash report
        try:
            self._send_crash_report(error_data)
        except:
            pass
        
        # Call original excepthook
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    def _get_or_create_user_id(self) -> str:
        """Get or create a unique user ID."""
        id_file = self.config_dir / "user_id"
        if id_file.exists():
            return id_file.read_text().strip()
        
        user_id = str(uuid.uuid4())
        self.config_dir.mkdir(exist_ok=True)
        id_file.write_text(user_id)
        return user_id
    
    def _save_error_report(self, error_data: Dict[str, Any]) -> None:
        """Save error report to local log."""
        timestamp = datetime.fromisoformat(error_data["timestamp"])
        filename = self.logs_dir / f"error_{timestamp:%Y%m%d_%H%M%S}_{error_data['type']}.json"
        
        with open(filename, 'w') as f:
            json.dump(error_data, f, indent=2)
    
    def _save_crash_report(self, crash_data: Dict[str, Any]) -> None:
        """Save crash report to local log."""
        timestamp = datetime.fromisoformat(crash_data["timestamp"])
        filename = self.crash_dir / f"crash_{timestamp:%Y%m%d_%H%M%S}_{crash_data['type']}.json"
        
        with open(filename, 'w') as f:
            json.dump(crash_data, f, indent=2)
    
    def _send_events_worker(self) -> None:
        """Worker thread to send queued events."""
        while not self.stop_event.is_set():
            try:
                # Get all available events
                events = []
                while not self.event_queue.empty() and len(events) < 100:
                    events.append(self.event_queue.get_nowait())
                
                if events:
                    self._send_events(events)
                    
                # Wait a bit before next batch
                self.stop_event.wait(timeout=1.0)
                
            except Exception as e:
                logger.error(f"Error sending events: {e}")
                # Wait longer after error
                self.stop_event.wait(timeout=5.0)
    
    def _send_events(self, events: list) -> None:
        """Send events to analytics server."""
        if not self.server_url:
            return
            
        try:
            response = requests.post(
                f"{self.server_url}/events",
                json={"events": events},
                timeout=5.0
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send events: {e}")
            # Re-queue events on failure
            for event in events:
                self.event_queue.put(event)
    
    def _send_crash_report(self, crash_data: Dict[str, Any]) -> None:
        """Send crash report to server."""
        if not self.server_url:
            return
            
        try:
            response = requests.post(
                f"{self.server_url}/crash",
                json=crash_data,
                timeout=5.0
            )
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send crash report: {e}")
    
    def _get_session_duration(self) -> float:
        """Get current session duration in seconds."""
        start_time = None
        for event in list(self.event_queue.queue):
            if event["type"] == "session_start":
                start_time = datetime.fromisoformat(event["timestamp"])
                break
                
        if not start_time:
            return 0.0
            
        return (datetime.utcnow() - start_time).total_seconds()
    
    def get_error_reports(self, days: int = 7) -> list:
        """Get recent error reports."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        reports = []
        
        # Get regular errors
        for error_file in self.logs_dir.glob("error_*.json"):
            if error_file.stat().st_mtime >= cutoff:
                try:
                    with open(error_file) as f:
                        reports.append(json.load(f))
                except Exception as e:
                    logger.error(f"Failed to load error report {error_file}: {e}")
        
        # Get crash reports
        for crash_file in self.crash_dir.glob("crash_*.json"):
            if crash_file.stat().st_mtime >= cutoff:
                try:
                    with open(crash_file) as f:
                        reports.append(json.load(f))
                except Exception as e:
                    logger.error(f"Failed to load crash report {crash_file}: {e}")
        
        # Sort by timestamp
        reports.sort(key=lambda x: x["timestamp"], reverse=True)
        return reports