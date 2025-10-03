from typing import Optional, List
import logging
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget,
                           QTreeWidgetItem, QScrollBar, QHeaderView)
from PyQt5.QtCore import Qt, QTimer

from models.export_job import ExportJob, JobStatus
from services.service_registry import ServiceRegistry
from services.export_queue_service import ExportQueueService
from ..components.dark_widgets import DarkFrame, DarkLabel, DarkButton

logger = logging.getLogger(__name__)

class ExportQueueDialog(QDialog):
    """Dialog showing active and completed export jobs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Queue")
        self.resize(600, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(500, 300)
        
        self.export_service = ServiceRegistry().get_service(ExportQueueService)
        
        self._create_widgets()
        self._update_timer = None
        self.start_updates()
        
        # Make dialog modal
        self.setModal(True)
        
    def _create_widgets(self):
        """Create the dialog widgets."""
        layout = QVBoxLayout(self)
        
        # Main frame
        main_frame = DarkFrame(self)
        layout.addWidget(main_frame)
        
        main_layout = QVBoxLayout(main_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Create tree widget for jobs
        self.tree = QTreeWidget(main_frame)
        self.tree.setHeaderLabels(["Status", "Type", "Progress", "Started", "Completed"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setSortingEnabled(True)
        
        # Configure column widths
        header = self.tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        main_layout.addWidget(self.tree)
        
        # Buttons frame
        button_frame = DarkFrame(self)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add stretch to push buttons to the right
        button_layout.addStretch()
        
        refresh_btn = DarkButton("Refresh", button_frame)
        refresh_btn.clicked.connect(self._update_job_list)
        button_layout.addWidget(refresh_btn)
        
        close_btn = DarkButton("Close", button_frame)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addWidget(button_frame)
        
    def _format_time(self, dt: Optional[datetime]) -> str:
        """Format datetime for display."""
        if dt:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return "N/A"
    
    def _format_progress(self, job: ExportJob) -> str:
        """Format job progress for display."""
        if job.status == JobStatus.COMPLETED:
            return "100%"
        elif job.status == JobStatus.FAILED:
            return "Failed"
        elif job.status == JobStatus.CANCELLED:
            return "Cancelled"
        return f"{job.progress:.1%}"
    
    def _update_job_list(self):
        """Update the jobs displayed in the tree widget."""
        # Clear existing items
        self.tree.clear()
        
        # Get current jobs
        jobs = self.export_service.get_all_jobs()
        
        # Sort jobs by created_at time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Add jobs to tree widget
        for job in jobs:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, job.status.value)
            item.setText(1, job.job_type.value)
            item.setText(2, self._format_progress(job))
            item.setText(3, self._format_time(job.started_at))
            item.setText(4, self._format_time(job.completed_at))
    
    def start_updates(self):
        """Start periodic updates of the job list."""
        self._update_job_list()
        if not self._update_timer:
            self._update_timer = QTimer(self)
            self._update_timer.timeout.connect(self._update_job_list)
            self._update_timer.start(1000)
    
    def stop_updates(self):
        """Stop periodic updates."""
        if self._update_timer:
            self._update_timer.stop()
            self._update_timer = None
    
    def closeEvent(self, event):
        """Clean up and close the dialog."""
        self.stop_updates()
        super().closeEvent(event)