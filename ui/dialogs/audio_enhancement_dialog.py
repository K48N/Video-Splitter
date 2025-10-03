import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget,
                           QGroupBox, QSlider, QLabel, QPushButton)
from PyQt5.QtCore import Qt

from services.service_registry import ServiceRegistry
from services.audio_enhancement_service import AudioEnhancementService
from ..components.dark_widgets import DarkLabel, DarkButton

logger = logging.getLogger(__name__)

class AudioEnhancementDialog(QDialog):
    """Dialog for audio enhancement settings."""

    def __init__(self, parent=None, video_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Audio Enhancement")
        self.resize(400, 300)
        self.setMinimumSize(350, 250)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setModal(True)

        self.video_path = video_path
        self.audio_service = ServiceRegistry().get_service(AudioEnhancementService)

        self._create_widgets()

    def _create_widgets(self):
        """Create the dialog widgets."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Slider styles
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #2a2a2a;
            }
            QSlider::handle:horizontal {
                background: #4a4a4a;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
        """)

        # Voice Enhancement Section
        voice_group = self._create_section("Voice Enhancement")
        layout.addWidget(voice_group)

        voice_layout = QVBoxLayout(voice_group)
        voice_label = DarkLabel("Voice Clarity:")
        voice_layout.addWidget(voice_label)

        self.voice_clarity = QSlider(Qt.Horizontal)
        self.voice_clarity.setRange(0, 100)
        self.voice_clarity.setValue(50)
        voice_layout.addWidget(self.voice_clarity)

        # Background Music Section
        music_group = self._create_section("Background Music")
        layout.addWidget(music_group)

        music_layout = QVBoxLayout(music_group)
        music_label = DarkLabel("Music Level:")
        music_layout.addWidget(music_label)

        self.music_level = QSlider(Qt.Horizontal)
        self.music_level.setRange(0, 100)
        self.music_level.setValue(50)
        music_layout.addWidget(self.music_level)

        # Noise Reduction Section
        noise_group = self._create_section("Noise Reduction")
        layout.addWidget(noise_group)

        noise_layout = QVBoxLayout(noise_group)
        noise_label = DarkLabel("Reduction Level:")
        noise_layout.addWidget(noise_label)

        self.noise_reduction = QSlider(Qt.Horizontal)
        self.noise_reduction.setRange(0, 100)
        self.noise_reduction.setValue(50)
        noise_layout.addWidget(self.noise_reduction)

        # Bottom Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        apply_btn = DarkButton("Apply")
        apply_btn.clicked.connect(self._apply_enhancement)
        button_layout.addWidget(apply_btn)

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

    def _apply_enhancement(self):
        """Apply audio enhancement settings."""
        try:
            params = {
                "voice_clarity": self.voice_clarity.value() / 100.0,
                "music_level": self.music_level.value() / 100.0,
                "noise_reduction": self.noise_reduction.value() / 100.0
            }
            job_id = self.audio_service.enhance_audio(self.video_path, **params)
            self._show_queued_message("Audio enhancement", job_id)
            self.close()
        except Exception as e:
            self._show_error("Failed to start audio enhancement", str(e))

    def _show_queued_message(self, task: str, job_id: str):
        """Show a message that a task has been queued."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Task Queued",
            f"{task} has been queued.\nJob ID: {job_id}\n\n"
            "You can monitor progress in the Export Queue window."
        )

    def _show_error(self, title: str, message: str):
        """Show an error message."""
        from PyQt5.QtWidgets import QMessageBox
        logger.error(f"{title}: {message}")
        QMessageBox.critical(
            self,
            "Error",
            f"{title}:\n{message}"
        )