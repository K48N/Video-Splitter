import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QScrollArea,
                           QWidget, QGroupBox, QSpinBox, QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt

from services.service_registry import ServiceRegistry
from services.ai_service import AIService
from services.audio_enhancement_service import AudioEnhancementService
from ..components.dark_widgets import DarkLabel, DarkButton, DarkCheckbutton

logger = logging.getLogger(__name__)

class AIFeaturesDialog(QDialog):
    """Dialog for accessing AI-powered features."""

    def __init__(self, parent=None, video_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("AI Features")
        self.resize(500, 600)
        self.setMinimumSize(400, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        self.video_path = video_path
        self.ai_service = ServiceRegistry().get_service(AIService)
        self.audio_service = ServiceRegistry().get_service(AudioEnhancementService)

        self._create_widgets()

    def _create_widgets(self):
        """Create the dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create scroll area for content
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        # Subtitles Section
        subtitle_group = self._create_section("Subtitle Generation")
        content_layout.addWidget(subtitle_group)

        subtitle_layout = QVBoxLayout(subtitle_group)
        self.auto_translate = DarkCheckbutton("Auto-translate subtitles")
        subtitle_layout.addWidget(self.auto_translate)

        self.speaker_diarization = DarkCheckbutton("Identify speakers")
        subtitle_layout.addWidget(self.speaker_diarization)

        generate_subtitles_btn = DarkButton("Generate Subtitles")
        generate_subtitles_btn.clicked.connect(self._generate_subtitles)
        subtitle_layout.addWidget(generate_subtitles_btn)
        subtitle_layout.addStretch()

        # Scene Analysis Section
        scene_group = self._create_section("Scene Analysis")
        content_layout.addWidget(scene_group)

        scene_layout = QVBoxLayout(scene_group)
        detect_scenes_btn = DarkButton("Detect & Label Scenes")
        detect_scenes_btn.clicked.connect(self._analyze_scenes)
        scene_layout.addWidget(detect_scenes_btn)

        generate_chapters_btn = DarkButton("Generate Chapters")
        generate_chapters_btn.clicked.connect(self._generate_chapters)
        scene_layout.addWidget(generate_chapters_btn)
        scene_layout.addStretch()

        # Audio Enhancement Section
        audio_group = self._create_section("Audio Enhancement")
        content_layout.addWidget(audio_group)

        audio_layout = QVBoxLayout(audio_group)
        self.voice_clarity = DarkCheckbutton("Enhance voice clarity")
        self.voice_clarity.setChecked(True)
        audio_layout.addWidget(self.voice_clarity)

        self.music_ducking = DarkCheckbutton("Auto music ducking")
        self.music_ducking.setChecked(True)
        audio_layout.addWidget(self.music_ducking)

        self.style_matching = DarkCheckbutton("Match audio style")
        self.style_matching.setChecked(True)
        audio_layout.addWidget(self.style_matching)

        process_audio_btn = DarkButton("Process Audio")
        process_audio_btn.clicked.connect(self._process_audio)
        audio_layout.addWidget(process_audio_btn)
        audio_layout.addStretch()

        # Summarization Section
        summary_group = self._create_section("Content Summarization")
        content_layout.addWidget(summary_group)

        summary_layout = QVBoxLayout(summary_group)
        duration_label = DarkLabel("Target Duration:")
        summary_layout.addWidget(duration_label)

        duration_layout = QHBoxLayout()
        self.target_duration = QSpinBox()
        self.target_duration.setRange(30, 300)
        self.target_duration.setSingleStep(30)
        self.target_duration.setValue(60)
        self.target_duration.setSuffix(" seconds")
        duration_layout.addWidget(self.target_duration)
        duration_layout.addStretch()
        summary_layout.addLayout(duration_layout)

        highlight_btn = DarkButton("Generate Highlight")
        highlight_btn.clicked.connect(self._generate_highlight)
        summary_layout.addWidget(highlight_btn)
        summary_layout.addStretch()

        # Bottom Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = DarkButton("Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_section(self, title: str) -> QGroupBox:
        """Create a titled section in the dialog."""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2a2a2a;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 7px;
                padding: 0 5px 0 5px;
            }
        """)
        return group

    def _generate_subtitles(self):
        """Handle subtitle generation."""
        try:
            params = {
                "auto_translate": self.auto_translate.isChecked(),
                "speaker_diarization": self.speaker_diarization.isChecked()
            }
            job_id = self.ai_service.generate_subtitles(self.video_path, **params)
            self._show_queued_message("Subtitle generation", job_id)
        except Exception as e:
            self._show_error("Failed to start subtitle generation", str(e))

    def _analyze_scenes(self):
        """Handle scene analysis."""
        try:
            job_id = self.ai_service.analyze_scenes(self.video_path)
            self._show_queued_message("Scene analysis", job_id)
        except Exception as e:
            self._show_error("Failed to start scene analysis", str(e))

    def _generate_chapters(self):
        """Handle chapter generation."""
        try:
            job_id = self.ai_service.generate_chapters(self.video_path)
            self._show_queued_message("Chapter generation", job_id)
        except Exception as e:
            self._show_error("Failed to start chapter generation", str(e))

    def _process_audio(self):
        """Handle audio enhancement."""
        try:
            params = {
                "voice_clarity": self.voice_clarity.isChecked(),
                "music_ducking": self.music_ducking.isChecked(),
                "style_matching": self.style_matching.isChecked()
            }
            job_id = self.audio_service.enhance_audio(self.video_path, **params)
            self._show_queued_message("Audio enhancement", job_id)
        except Exception as e:
            self._show_error("Failed to start audio enhancement", str(e))

    def _generate_highlight(self):
        """Handle highlight generation."""
        try:
            duration = self.target_duration.value()
            job_id = self.ai_service.generate_highlights(
                self.video_path,
                duration
            )
            self._show_queued_message("Highlight generation", job_id)
        except Exception as e:
            self._show_error("Failed to start highlight generation", str(e))

    def _show_queued_message(self, task: str, job_id: str):
        """Show a message that a task has been queued."""
        QMessageBox.information(
            self,
            "Task Queued",
            f"{task} has been queued.\nJob ID: {job_id}\n\n"
            "You can monitor progress in the Export Queue window."
        )

    def _show_error(self, title: str, message: str):
        """Show an error message."""
        logger.error(f"{title}: {message}")
        QMessageBox.critical(
            self,
            "Error",
            f"{title}:\n{message}"
        )