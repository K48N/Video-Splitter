"""
Video preview panel with playback controls
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QSlider, QStyle)
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from typing import Optional

from ui.themes.dark_theme import PortfolioTheme


class VideoPreview(QWidget):
    """Video preview with playback controls"""
    
    position_changed = pyqtSignal(float)  # Current position in seconds
    
    def __init__(self):
        super().__init__()
        
        # Media player
        self.player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)
        
        # State
        self.duration = 0.0
        self.is_playing = False
        
        # Markers
        self.in_point = 0.0
        self.out_point = 0.0
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Preview")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {PortfolioTheme.WHITE};
            padding: 10px;
        """)
        header.addWidget(title)
        
        # Time display
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet(f"""
            color: {PortfolioTheme.GRAY_LIGHTER};
            font-family: {PortfolioTheme.FONT_MONO};
            padding: 10px;
        """)
        header.addWidget(self.time_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Video widget
        self.video_widget.setStyleSheet(f"""
            QVideoWidget {{
                background: {PortfolioTheme.BLACK};
                border: 1px solid {PortfolioTheme.BORDER};
                border-radius: 4px;
            }}
        """)
        self.video_widget.setMinimumHeight(400)
        layout.addWidget(self.video_widget)
        
        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setStyleSheet(f"""
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
            QSlider::handle:horizontal:hover {{
                background: {PortfolioTheme.ACCENT_HOVER};
            }}
        """)
        layout.addWidget(self.seek_slider)
        
        # Controls
        controls = QHBoxLayout()
        controls.setSpacing(10)
        
        # Play/Pause button
        self.play_button = QPushButton("Play")
        self.play_button.setStyleSheet(f"""
            QPushButton {{
                background: {PortfolioTheme.ACCENT};
                color: {PortfolioTheme.WHITE};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {PortfolioTheme.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background: {PortfolioTheme.ACCENT_PRESSED};
            }}
        """)
        self.play_button.clicked.connect(self.toggle_play)
        controls.addWidget(self.play_button)
        
        # Skip buttons
        skip_back = QPushButton("← 10s")
        skip_back.clicked.connect(lambda: self.skip(-10))
        controls.addWidget(skip_back)
        
        skip_forward = QPushButton("30s →")
        skip_forward.clicked.connect(lambda: self.skip(30))
        controls.addWidget(skip_forward)
        
        controls.addStretch()
        
        # Marker buttons
        self.set_in_button = QPushButton("Set In (I)")
        self.set_in_button.clicked.connect(self.set_in_point)
        controls.addWidget(self.set_in_button)
        
        self.set_out_button = QPushButton("Set Out (O)")
        self.set_out_button.clicked.connect(self.set_out_point)
        controls.addWidget(self.set_out_button)
        
        self.add_segment_button = QPushButton("Add Segment")
        self.add_segment_button.setStyleSheet(f"""
            QPushButton {{
                background: {PortfolioTheme.SUCCESS};
                color: {PortfolioTheme.WHITE};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: #218838;
            }}
            QPushButton:disabled {{
                background: {PortfolioTheme.GRAY};
                color: {PortfolioTheme.GRAY_LIGHT};
            }}
        """)
        self.add_segment_button.clicked.connect(self._emit_add_segment)
        self.add_segment_button.setEnabled(False)
        controls.addWidget(self.add_segment_button)
        
        # Style other buttons
        button_style = f"""
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
        """
        skip_back.setStyleSheet(button_style)
        skip_forward.setStyleSheet(button_style)
        self.set_in_button.setStyleSheet(button_style)
        self.set_out_button.setStyleSheet(button_style)
        
        layout.addLayout(controls)
        
        # Keyboard shortcuts info
        shortcuts = QLabel("Shortcuts: Space=Play/Pause | ←=Back 10s | →=Forward 30s | ↑=+1s | ↓=-1s | I=In | O=Out")
        shortcuts.setStyleSheet(f"""
            color: {PortfolioTheme.GRAY_LIGHTER};
            font-size: 11px;
            padding: 5px 10px;
        """)
        layout.addWidget(shortcuts)
    
    def _connect_signals(self):
        """Connect signals"""
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.stateChanged.connect(self._on_state_changed)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
    
    def load_video(self, file_path: str):
        """Load video file"""
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
        self.in_point = 0.0
        self.out_point = 0.0
        self.add_segment_button.setEnabled(False)
    
    def toggle_play(self):
        """Toggle play/pause"""
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()
    
    def skip(self, seconds: float):
        """Skip forward/backward"""
        current_ms = self.player.position()
        new_ms = current_ms + int(seconds * 1000)
        new_ms = max(0, min(new_ms, self.player.duration()))
        self.player.setPosition(new_ms)
    
    def seek_to(self, time: float):
        """Seek to specific time in seconds"""
        ms = int(time * 1000)
        self.player.setPosition(ms)
    
    def set_in_point(self):
        """Set in point at current position"""
        self.in_point = self.player.position() / 1000.0
        self._update_segment_button()
        self._update_time_display()
    
    def set_out_point(self):
        """Set out point at current position"""
        self.out_point = self.player.position() / 1000.0
        self._update_segment_button()
        self._update_time_display()
    
    def _update_segment_button(self):
        """Update add segment button state"""
        can_add = (self.out_point > self.in_point and 
                  self.out_point - self.in_point >= 1.0)
        self.add_segment_button.setEnabled(can_add)
    
    def _emit_add_segment(self):
        """Emit add segment signal"""
        # This will be connected in main app
        pass
    
    def get_segment_range(self):
        """Get current in/out range"""
        return (self.in_point, self.out_point)
    
    def clear_markers(self):
        """Clear in/out markers"""
        self.in_point = 0.0
        self.out_point = 0.0
        self.add_segment_button.setEnabled(False)
        self._update_time_display()
    
    def _on_duration_changed(self, duration_ms):
        """Handle duration change"""
        self.duration = duration_ms / 1000.0
        self.seek_slider.setMaximum(duration_ms)
        self.out_point = self.duration
        self._update_time_display()
    
    def _on_position_changed(self, position_ms):
        """Handle position change"""
        self.seek_slider.setValue(position_ms)
        self._update_time_display()
        self.position_changed.emit(position_ms / 1000.0)
    
    def _on_state_changed(self, state):
        """Handle state change"""
        if state == QMediaPlayer.PlayingState:
            self.play_button.setText("Pause")
            self.is_playing = True
        else:
            self.play_button.setText("Play")
            self.is_playing = False
    
    def _on_slider_moved(self, position):
        """Handle slider moved"""
        self.player.setPosition(position)
    
    def _update_time_display(self):
        """Update time display"""
        current = self.player.position() / 1000.0
        total = self.duration
        
        current_str = self._format_time(current)
        total_str = self._format_time(total)
        
        if self.in_point > 0 or self.out_point < total:
            in_str = self._format_time(self.in_point)
            out_str = self._format_time(self.out_point)
            self.time_label.setText(
                f"{current_str} / {total_str} | In: {in_str} Out: {out_str}"
            )
        else:
            self.time_label.setText(f"{current_str} / {total_str}")
    
    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key_Left:
            self.skip(-10)
        elif event.key() == Qt.Key_Right:
            self.skip(30)
        elif event.key() == Qt.Key_Up:
            self.skip(1)
        elif event.key() == Qt.Key_Down:
            self.skip(-1)
        elif event.key() == Qt.Key_I:
            self.set_in_point()
        elif event.key() == Qt.Key_O:
            self.set_out_point()
        else:
            super().keyPressEvent(event)