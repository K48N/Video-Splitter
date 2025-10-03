"""
Smart scene detection dialog with ML analysis
"""
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem,
    QProgressBar, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QFrame, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QPixmap, QIcon

from core.scene_detector import SceneDetector
from models.scene_models import SceneMetadata
from core.segment import Segment
from services.service_registry import ServiceRegistry
from services.ml_service import MLService
from utils.ffmpeg_wrapper import FFmpegWrapper
from ui.components.dark_widgets import DarkDialog

logger = logging.getLogger(__name__)


class SceneAnalysisThread(QThread):
    """Background thread for scene analysis"""
    progress = pyqtSignal(int)
    complete = pyqtSignal(list)  # List[SceneMetadata]
    error = pyqtSignal(str)
    
    def __init__(self, video_path: str):
        super().__init__()
        self.video_path = video_path
        self.detector = SceneDetector()
    
    def run(self):
        """Run scene analysis"""
        try:
            # Initialize progress
            self.progress.emit(0)
            
            # Detect and analyze scenes
            scenes = self.detector.detect_scenes(
                self.video_path,
                analyze_content=True
            )
            
            self.progress.emit(100)
            self.complete.emit(scenes)
            
        except Exception as e:
            logger.error(f"Scene analysis failed: {e}")
            self.error.emit(str(e))


class ScenePreviewWidget(QFrame):
    """Widget for displaying scene preview and metadata"""
    
    def __init__(
        self,
        scene: SceneMetadata,
        video_path: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.scene = scene
        self.video_path = video_path
        self.ffmpeg = FFmpegWrapper()
        
        # UI setup
        layout = QHBoxLayout(self)
        
        # Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(160, 90)
        self.load_thumbnail()
        layout.addWidget(self.thumb_label)
        
        # Scene info
        info_layout = QVBoxLayout()
        
        # Timecode and duration
        time_label = QLabel(
            f"Start: {self._format_time(scene.start_time)} | "
            f"Duration: {self._format_time(scene.duration)}"
        )
        info_layout.addWidget(time_label)
        
        # Labels and confidence
        if scene.labels:
            labels_str = " | ".join(
                f"{label} ({conf:.0%})"
                for label, conf in zip(
                    scene.labels[:3],
                    [scene.confidence] + [0.0] * 2
                )
            )
            labels_label = QLabel(f"Content: {labels_str}")
            info_layout.addWidget(labels_label)
        
        # Shot type
        shot_label = QLabel(f"Shot Type: {scene.shot_type}")
        info_layout.addWidget(shot_label)
        
        # Action/dialog scores
        scores_label = QLabel(
            f"Action: {scene.action_score:.0%} | "
            f"Dialog: {scene.dialog_score:.0%}"
        )
        info_layout.addWidget(scores_label)
        
        layout.addLayout(info_layout)
    
    def load_thumbnail(self):
        """Generate and display thumbnail"""
        try:
            thumb_path = Path("temp_thumb.jpg")
            if self.ffmpeg.generate_thumbnail(
                self.video_path,
                str(thumb_path),
                self.scene.start_time + (self.scene.duration / 2),
                width=160,
                height=90
            ):
                pixmap = QPixmap(str(thumb_path))
                self.thumb_label.setPixmap(pixmap)
                thumb_path.unlink()
        except:
            pass
    
    def _format_time(self, seconds: float) -> str:
        """Format time in HH:MM:SS.mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


class SmartSceneDialog(DarkDialog):
    """Dialog for ML-based scene detection and analysis"""
    
    scenes_selected = pyqtSignal(list)  # List[Segment]
    
    def __init__(
        self,
        video_path: str,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.video_path = video_path
        self.scenes: List[SceneMetadata] = []
        
        self.setWindowTitle("Smart Scene Detection")
        self.resize(800, 600)
        
        # Layout setup
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Scene detection settings
        settings_layout = QVBoxLayout()
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Threshold:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.1, 0.9)
        self.threshold_spin.setValue(0.3)
        self.threshold_spin.setSingleStep(0.1)
        threshold_layout.addWidget(self.threshold_spin)
        settings_layout.addLayout(threshold_layout)
        
        min_length_layout = QHBoxLayout()
        min_length_layout.addWidget(QLabel("Min Length:"))
        self.min_length_spin = QDoubleSpinBox()
        self.min_length_spin.setRange(0.5, 10.0)
        self.min_length_spin.setValue(2.0)
        self.min_length_spin.setSingleStep(0.5)
        min_length_layout.addWidget(self.min_length_spin)
        settings_layout.addLayout(min_length_layout)
        
        controls_layout.addLayout(settings_layout)
        
        # Filters
        filters_layout = QVBoxLayout()
        
        # Shot type filter
        self.shot_filter = QComboBox()
        self.shot_filter.addItem("All Shot Types")
        self.shot_filter.addItems(SceneDetector.SHOT_TYPES)
        self.shot_filter.currentTextChanged.connect(self._apply_filters)
        filters_layout.addWidget(self.shot_filter)
        
        # Action/dialog filters
        self.action_check = QCheckBox("High Action")
        self.action_check.stateChanged.connect(self._apply_filters)
        filters_layout.addWidget(self.action_check)
        
        self.dialog_check = QCheckBox("Dialog Scenes")
        self.dialog_check.stateChanged.connect(self._apply_filters)
        filters_layout.addWidget(self.dialog_check)
        
        controls_layout.addLayout(filters_layout)
        
        # Detect button
        self.detect_button = QPushButton("Detect Scenes")
        self.detect_button.clicked.connect(self._start_detection)
        controls_layout.addWidget(self.detect_button)
        
        layout.addLayout(controls_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Scene list
        self.scene_list = QListWidget()
        self.scene_list.setVerticalScrollMode(
            QListWidget.ScrollPerPixel
        )
        layout.addWidget(self.scene_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self._select_all)
        button_layout.addWidget(self.select_all_btn)
        
        self.clear_btn = QPushButton("Clear Selection")
        self.clear_btn.clicked.connect(self._clear_selection)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("Create Segments")
        self.ok_btn.clicked.connect(self._create_segments)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
    
    def _start_detection(self):
        """Start scene detection"""
        self.detect_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start analysis thread
        self.analysis_thread = SceneAnalysisThread(self.video_path)
        self.analysis_thread.progress.connect(self.progress_bar.setValue)
        self.analysis_thread.complete.connect(self._detection_complete)
        self.analysis_thread.error.connect(self._detection_error)
        self.analysis_thread.start()
    
    def _detection_complete(self, scenes: List[SceneMetadata]):
        """Handle completed scene detection"""
        self.scenes = scenes
        self.progress_bar.setVisible(False)
        self.detect_button.setEnabled(True)
        self._update_scene_list()
    
    def _detection_error(self, error: str):
        """Handle scene detection error"""
        self.progress_bar.setVisible(False)
        self.detect_button.setEnabled(True)
        # TODO: Show error dialog
    
    def _update_scene_list(self):
        """Update scene list with current filters"""
        self.scene_list.clear()
        
        shot_filter = self.shot_filter.currentText()
        require_action = self.action_check.isChecked()
        require_dialog = self.dialog_check.isChecked()
        
        for scene in self.scenes:
            # Apply filters
            if shot_filter != "All Shot Types" and scene.shot_type != shot_filter:
                continue
            
            if require_action and scene.action_score < 0.7:
                continue
            
            if require_dialog and scene.dialog_score < 0.7:
                continue
            
            # Create list item with preview
            item = QListWidgetItem()
            preview = ScenePreviewWidget(scene, self.video_path)
            item.setSizeHint(preview.sizeHint())
            
            self.scene_list.addItem(item)
            self.scene_list.setItemWidget(item, preview)
    
    def _apply_filters(self):
        """Apply current filters to scene list"""
        if self.scenes:
            self._update_scene_list()
    
    def _select_all(self):
        """Select all visible scenes"""
        for i in range(self.scene_list.count()):
            self.scene_list.item(i).setSelected(True)
    
    def _clear_selection(self):
        """Clear scene selection"""
        for i in range(self.scene_list.count()):
            self.scene_list.item(i).setSelected(False)
    
    def _create_segments(self):
        """Create segments from selected scenes"""
        selected_items = self.scene_list.selectedItems()
        if not selected_items:
            return
        
        segments = []
        for i in range(self.scene_list.count()):
            item = self.scene_list.item(i)
            if item.isSelected():
                preview = self.scene_list.itemWidget(item)
                scene = preview.scene
                
                # Create label from scene info
                label_parts = [
                    f"Scene {len(segments) + 1}",
                    scene.shot_type
                ]
                if scene.labels:
                    label_parts.extend(scene.labels[:2])
                
                segment = Segment(
                    start=scene.start_time,
                    end=scene.end_time,
                    label=" - ".join(label_parts)
                )
                segment.metadata = scene.to_dict()
                segments.append(segment)
        
        if segments:
            self.scenes_selected.emit(segments)
            self.accept()