"""
Scene detection dialog
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QSlider, QSpinBox, QGroupBox,
                            QRadioButton, QButtonGroup, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from typing import List

from core.scene_detector import SceneDetector
from core.segment import Segment
from ui.themes.dark_theme import PortfolioTheme


class DetectionThread(QThread):
    """Thread for scene/silence detection"""
    
    finished = pyqtSignal(list)  # List of segments
    error = pyqtSignal(str)
    
    def __init__(self, video_path, mode, **kwargs):
        super().__init__()
        self.video_path = video_path
        self.mode = mode
        self.kwargs = kwargs
        self.detector = SceneDetector()
    
    def run(self):
        try:
            if self.mode == 'scene':
                scenes = self.detector.detect_scenes(
                    self.video_path,
                    threshold=self.kwargs.get('threshold', 0.3),
                    min_scene_length=self.kwargs.get('min_scene_length', 2.0)
                )
                segments = self.detector.create_segments_from_scenes(scenes)
                
            elif self.mode == 'silence':
                silences = self.detector.detect_silence(
                    self.video_path,
                    noise_threshold=self.kwargs.get('noise_threshold', '-30dB'),
                    min_silence_duration=self.kwargs.get('min_silence_duration', 1.0)
                )
                segments = self.detector.create_segments_between_silences(
                    self.video_path,
                    silences
                )
            else:
                self.error.emit("Unknown detection mode")
                return
            
            self.finished.emit(segments)
            
        except Exception as e:
            self.error.emit(str(e))


class SceneDetectionDialog(QDialog):
    """Scene detection dialog"""
    
    segments_detected = pyqtSignal(list)  # Emits detected segments
    
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.detection_thread = None
        
        self.setWindowTitle("Auto-Detect Segments")
        self.setMinimumSize(500, 400)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Automatic Segment Detection")
        title.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {PortfolioTheme.WHITE};
            padding: 10px;
        """)
        layout.addWidget(title)
        
        # Mode selection
        mode_group = QGroupBox("Detection Mode")
        mode_layout = QVBoxLayout()
        
        self.mode_group = QButtonGroup()
        
        self.scene_radio = QRadioButton("Scene Changes")
        self.scene_radio.setChecked(True)
        self.mode_group.addButton(self.scene_radio, 0)
        mode_layout.addWidget(self.scene_radio)
        
        scene_desc = QLabel("Detect visual scene changes (cuts, transitions)")
        scene_desc.setStyleSheet(f"color: {PortfolioTheme.GRAY_LIGHTER}; padding-left: 25px;")
        mode_layout.addWidget(scene_desc)
        
        self.silence_radio = QRadioButton("Silent Breaks")
        self.mode_group.addButton(self.silence_radio, 1)
        mode_layout.addWidget(self.silence_radio)
        
        silence_desc = QLabel("Detect silence in audio and split between them")
        silence_desc.setStyleSheet(f"color: {PortfolioTheme.GRAY_LIGHTER}; padding-left: 25px;")
        mode_layout.addWidget(silence_desc)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Scene detection settings
        self.scene_settings = QGroupBox("Scene Detection Settings")
        scene_layout = QVBoxLayout()
        
        # Threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Sensitivity:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(1, 10)
        self.threshold_slider.setValue(3)
        self.threshold_label = QLabel("0.3")
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_label.setText(f"{v/10:.1f}")
        )
        threshold_layout.addWidget(self.threshold_slider)
        threshold_layout.addWidget(self.threshold_label)
        scene_layout.addLayout(threshold_layout)
        
        # Min scene length
        min_scene_layout = QHBoxLayout()
        min_scene_layout.addWidget(QLabel("Min Scene Length (s):"))
        self.min_scene_spin = QSpinBox()
        self.min_scene_spin.setRange(1, 60)
        self.min_scene_spin.setValue(2)
        min_scene_layout.addWidget(self.min_scene_spin)
        min_scene_layout.addStretch()
        scene_layout.addLayout(min_scene_layout)
        
        self.scene_settings.setLayout(scene_layout)
        layout.addWidget(self.scene_settings)
        
        # Silence detection settings
        self.silence_settings = QGroupBox("Silence Detection Settings")
        silence_layout = QVBoxLayout()
        
        # Noise threshold
        noise_layout = QHBoxLayout()
        noise_layout.addWidget(QLabel("Silence Threshold (dB):"))
        self.noise_spin = QSpinBox()
        self.noise_spin.setRange(-60, -10)
        self.noise_spin.setValue(-30)
        noise_layout.addWidget(self.noise_spin)
        noise_layout.addStretch()
        silence_layout.addLayout(noise_layout)
        
        # Min silence duration
        min_silence_layout = QHBoxLayout()
        min_silence_layout.addWidget(QLabel("Min Silence (s):"))
        self.min_silence_spin = QSpinBox()
        self.min_silence_spin.setRange(1, 10)
        self.min_silence_spin.setValue(1)
        min_silence_layout.addWidget(self.min_silence_spin)
        min_silence_layout.addStretch()
        silence_layout.addLayout(min_silence_layout)
        
        self.silence_settings.setLayout(silence_layout)
        self.silence_settings.setVisible(False)
        layout.addWidget(self.silence_settings)
        
        # Connect mode change
        self.mode_group.buttonClicked.connect(self._on_mode_changed)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
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
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.detect_btn = QPushButton("Detect Segments")
        self.detect_btn.setStyleSheet(f"""
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
        self.detect_btn.clicked.connect(self._start_detection)
        btn_layout.addWidget(self.detect_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # Styling
        self.setStyleSheet(f"""
            QDialog {{
                background: {PortfolioTheme.PRIMARY};
            }}
            QGroupBox {{
                background: {PortfolioTheme.SECONDARY};
                border: 1px solid {PortfolioTheme.BORDER};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
                font-weight: 600;
                color: {PortfolioTheme.WHITE};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {PortfolioTheme.ACCENT};
            }}
            QLabel {{
                color: {PortfolioTheme.WHITE};
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
            QSpinBox {{
                background: {PortfolioTheme.TERTIARY};
                color: {PortfolioTheme.WHITE};
                border: 1px solid {PortfolioTheme.BORDER};
                border-radius: 4px;
                padding: 5px;
            }}
            QSlider::groove:horizontal {{
                background: {PortfolioTheme.TERTIARY};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {PortfolioTheme.ACCENT};
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }}
        """)
    
    def _on_mode_changed(self):
        is_scene = self.scene_radio.isChecked()
        self.scene_settings.setVisible(is_scene)
        self.silence_settings.setVisible(not is_scene)
    
    def _start_detection(self):
        mode = 'scene' if self.scene_radio.isChecked() else 'silence'
        
        if mode == 'scene':
            kwargs = {
                'threshold': self.threshold_slider.value() / 10.0,
                'min_scene_length': self.min_scene_spin.value()
            }
        else:
            kwargs = {
                'noise_threshold': f"{self.noise_spin.value()}dB",
                'min_silence_duration': self.min_silence_spin.value()
            }
        
        self.detection_thread = DetectionThread(self.video_path, mode, **kwargs)
        self.detection_thread.finished.connect(self._on_detection_finished)
        self.detection_thread.error.connect(self._on_detection_error)
        
        self.detect_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Analyzing video...")
        
        self.detection_thread.start()
    
    def _on_detection_finished(self, segments):
        self.progress_bar.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        if not segments:
            QMessageBox.information(
                self,
                "No Segments",
                "No segments were detected with the current settings."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Segments Detected",
            f"Found {len(segments)} segments.\n\nAdd them to the timeline?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.segments_detected.emit(segments)
            self.accept()
    
    def _on_detection_error(self, error):
        self.progress_bar.setVisible(False)
        self.detect_btn.setEnabled(True)
        
        QMessageBox.critical(
            self,
            "Detection Error",
            f"Failed to detect segments:\n{error}"
        )