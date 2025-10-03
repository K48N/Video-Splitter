"""
Batch processing dialog
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QListWidget, QFileDialog, QMessageBox,
                            QProgressBar, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path
from typing import List

from core.batch_processor import BatchProcessor, BatchJob
from core.segment import Segment
from core.video_engine import ProcessingOptions
from ui.themes.dark_theme import PortfolioTheme


class BatchProcessingThread(QThread):
    """Thread for batch processing"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)
    
    def __init__(self, processor, options):
        super().__init__()
        self.processor = processor
        self.options = options
    
    def run(self):
        results = self.processor.process_all(
            self.options,
            progress_callback=self.progress.emit
        )
        self.finished.emit(results)


class BatchDialog(QDialog):
    """Batch processing dialog"""
    
    def __init__(self, segments: List[Segment], parent=None):
        super().__init__(parent)
        self.segments = segments
        self.processor = BatchProcessor()
        self.processing_thread = None
        
        self.setWindowTitle("Batch Processing")
        self.setMinimumSize(600, 500)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Batch Process Multiple Videos")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {PortfolioTheme.WHITE};
            padding: 10px;
        """)
        layout.addWidget(title)
        
        # Info
        info = QLabel(f"Apply current segments ({len(self.segments)}) to multiple videos")
        info.setStyleSheet(f"color: {PortfolioTheme.GRAY_LIGHTER}; padding: 5px 10px;")
        layout.addWidget(info)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.setStyleSheet(f"""
            QListWidget {{
                background: {PortfolioTheme.SECONDARY};
                color: {PortfolioTheme.WHITE};
                border: 1px solid {PortfolioTheme.BORDER};
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
            }}
            QListWidget::item:selected {{
                background: {PortfolioTheme.ACCENT};
            }}
        """)
        layout.addWidget(self.video_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Videos")
        add_btn.clicked.connect(self._add_videos)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(remove_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(clear_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {PortfolioTheme.BORDER};
                border-radius: 4px;
                background: {PortfolioTheme.TERTIARY};
                text-align: center;
                color: {PortfolioTheme.WHITE};
            }}
            QProgressBar::chunk {{
                background: {PortfolioTheme.ACCENT};
            }}
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {PortfolioTheme.GRAY_LIGHTER}; padding: 5px;")
        layout.addWidget(self.status_label)
        
        # Process button
        process_layout = QHBoxLayout()
        process_layout.addStretch()
        
        self.process_btn = QPushButton("Start Batch Processing")
        self.process_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PortfolioTheme.ACCENT};
                color: {PortfolioTheme.WHITE};
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {PortfolioTheme.ACCENT_HOVER};
            }}
            QPushButton:disabled {{
                background: {PortfolioTheme.GRAY};
            }}
        """)
        self.process_btn.clicked.connect(self._start_processing)
        self.process_btn.setEnabled(False)
        process_layout.addWidget(self.process_btn)
        
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.reject)
        process_layout.addWidget(cancel_btn)
        
        layout.addLayout(process_layout)
        
        self.setStyleSheet(f"""
            QDialog {{
                background: {PortfolioTheme.PRIMARY};
            }}
            QPushButton {{
                background: {PortfolioTheme.TERTIARY};
                color: {PortfolioTheme.WHITE};
                border: 1px solid {PortfolioTheme.BORDER};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {PortfolioTheme.GRAY};
            }}
        """)
    
    def _add_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Videos",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv);;All Files (*)"
        )
        
        if files:
            for file_path in files:
                item = QListWidgetItem(Path(file_path).name)
                item.setData(Qt.UserRole, file_path)
                self.video_list.addItem(item)
            
            self.process_btn.setEnabled(self.video_list.count() > 0)
    
    def _remove_selected(self):
        for item in self.video_list.selectedItems():
            self.video_list.takeItem(self.video_list.row(item))
        
        self.process_btn.setEnabled(self.video_list.count() > 0)
    
    def _clear_all(self):
        self.video_list.clear()
        self.process_btn.setEnabled(False)
    
    def _start_processing(self):
        if not self.segments:
            QMessageBox.warning(self, "No Segments", "Please add segments first.")
            return
        
        # Select output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        
        if not output_dir:
            return
        
        # Get processing options from parent
        if hasattr(self.parent(), 'control_panel'):
            options = self.parent().control_panel.get_processing_options()
        else:
            options = ProcessingOptions()
        
        # Add jobs
        self.processor.clear_jobs()
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            video_path = item.data(Qt.UserRole)
            self.processor.add_job(video_path, self.segments, output_dir)
        
        # Start processing
        self.processing_thread = BatchProcessingThread(self.processor, options)
        self.processing_thread.progress.connect(self._on_progress)
        self.processing_thread.finished.connect(self._on_finished)
        
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.processing_thread.start()
    
    def _on_progress(self, current, total, message):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(message)
    
    def _on_finished(self, results):
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        
        summary = self.processor.get_summary()
        
        QMessageBox.information(
            self,
            "Batch Processing Complete",
            f"Complete: {summary['complete']}\n"
            f"Failed: {summary['failed']}\n"
            f"Total: {summary['total']}"
        )
        
        self.accept()