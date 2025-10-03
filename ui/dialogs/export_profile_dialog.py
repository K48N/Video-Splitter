from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, 
                             QPushButton, QCheckBox, QGroupBox, QFormLayout,
                             QDialogButtonBox, QMessageBox, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal
from models.export_profile import ExportProfile, VideoCodecSettings, AudioCodecSettings
from services.export_profile_manager import ExportProfileManager

class ExportProfileDialog(QDialog):
    """Dialog for managing export profiles."""
    
    profileUpdated = pyqtSignal(ExportProfile)
    
    def __init__(self, profile_manager: ExportProfileManager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.current_profile = None
        
        self.setWindowTitle("Export Profile Manager")
        self.setup_ui()
        self.load_profiles()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout()
        
        # Profile selection
        profile_group = QGroupBox("Profile Selection")
        profile_layout = QHBoxLayout()
        
        self.profile_combo = QComboBox()
        self.profile_combo.currentIndexChanged.connect(self.on_profile_selected)
        profile_layout.addWidget(self.profile_combo)
        
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self.create_new_profile)
        profile_layout.addWidget(new_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_profile)
        profile_layout.addWidget(delete_btn)
        
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)
        
        # Basic settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        basic_layout.addRow("Name:", self.name_edit)
        
        self.desc_edit = QLineEdit()
        basic_layout.addRow("Description:", self.desc_edit)
        
        self.container_combo = QComboBox()
        self.container_combo.addItems(["mp4", "mov", "mkv", "webm"])
        basic_layout.addRow("Container:", self.container_combo)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Video settings
        video_group = QGroupBox("Video Settings")
        video_layout = QFormLayout()
        
        self.video_codec_combo = QComboBox()
        self.video_codec_combo.addItems(["h264", "h265", "vp9"])
        video_layout.addRow("Codec:", self.video_codec_combo)
        
        self.video_bitrate_edit = QLineEdit()
        video_layout.addRow("Bitrate:", self.video_bitrate_edit)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", 
                                  "fast", "medium", "slow", "slower", "veryslow"])
        video_layout.addRow("Preset:", self.preset_combo)
        
        self.crf_spin = QSpinBox()
        self.crf_spin.setRange(0, 51)
        self.crf_spin.setValue(23)
        video_layout.addRow("CRF:", self.crf_spin)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(0, 7680)
        self.width_spin.setSpecialValueText("Auto")
        video_layout.addRow("Width:", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(0, 4320)
        self.height_spin.setSpecialValueText("Auto")
        video_layout.addRow("Height:", self.height_spin)
        
        self.fps_spin = QDoubleSpinBox()
        self.fps_spin.setRange(0, 240)
        self.fps_spin.setSpecialValueText("Auto")
        video_layout.addRow("FPS:", self.fps_spin)
        
        self.maintain_aspect = QCheckBox("Maintain Aspect Ratio")
        self.maintain_aspect.setChecked(True)
        video_layout.addRow("", self.maintain_aspect)
        
        video_group.setLayout(video_layout)
        layout.addWidget(video_group)
        
        # Audio settings
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout()
        
        self.audio_codec_combo = QComboBox()
        self.audio_codec_combo.addItems(["aac", "mp3", "opus", "flac"])
        audio_layout.addRow("Codec:", self.audio_codec_combo)
        
        self.audio_bitrate_edit = QLineEdit()
        audio_layout.addRow("Bitrate:", self.audio_bitrate_edit)
        
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "96000"])
        audio_layout.addRow("Sample Rate:", self.sample_rate_combo)
        
        self.channels_spin = QSpinBox()
        self.channels_spin.setRange(1, 8)
        self.channels_spin.setValue(2)
        audio_layout.addRow("Channels:", self.channels_spin)
        
        self.normalize_audio = QCheckBox("Normalize Audio")
        audio_layout.addRow("", self.normalize_audio)
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        # Extra settings
        extra_group = QGroupBox("Extra Settings")
        extra_layout = QFormLayout()
        
        self.extra_args_edit = QLineEdit()
        extra_layout.addRow("Extra FFmpeg Args:", self.extra_args_edit)
        
        extra_group.setLayout(extra_layout)
        layout.addWidget(extra_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | 
            QDialogButtonBox.Cancel |
            QDialogButtonBox.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_changes)
        
        import_btn = QPushButton("Import...")
        import_btn.clicked.connect(self.import_profile)
        button_box.addButton(import_btn, QDialogButtonBox.ActionRole)
        
        export_btn = QPushButton("Export...")
        export_btn.clicked.connect(self.export_profile)
        button_box.addButton(export_btn, QDialogButtonBox.ActionRole)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_profiles(self):
        """Load available profiles into combo box."""
        self.profile_combo.clear()
        self.profile_combo.addItems(self.profile_manager.list_profiles())
        
        # Add presets
        self.profile_combo.insertSeparator(self.profile_combo.count())
        self.profile_combo.addItem("YouTube HD (Preset)")
        self.profile_combo.addItem("Vimeo HD (Preset)")
        self.profile_combo.addItem("Device Playback (Preset)")
        self.profile_combo.addItem("Archive Quality (Preset)")
    
    def create_new_profile(self):
        """Create a new blank profile."""
        profile = ExportProfile(
            name="New Profile",
            description="",
            container="mp4",
            video_codec=VideoCodecSettings(),
            audio_codec=AudioCodecSettings()
        )
        self.profile_manager.save_profile(profile)
        self.load_profiles()
        self.profile_combo.setCurrentText(profile.name)
    
    def delete_profile(self):
        """Delete the current profile."""
        if not self.current_profile:
            return
            
        name = self.current_profile.name
        if " (Preset)" in name:
            QMessageBox.warning(self, "Error", "Cannot delete preset profiles.")
            return
            
        reply = QMessageBox.question(
            self, 
            "Confirm Delete",
            f"Are you sure you want to delete the profile '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.profile_manager.delete_profile(name)
            self.load_profiles()
    
    def on_profile_selected(self, index):
        """Handle profile selection change."""
        name = self.profile_combo.currentText()
        
        if " (Preset)" in name:
            # Create from preset
            preset_name = name.replace(" (Preset)", "").lower()
            try:
                self.current_profile = ExportProfile.create_preset(preset_name)
            except ValueError:
                return
        else:
            # Load existing profile
            try:
                self.current_profile = self.profile_manager.get_profile(name)
            except KeyError:
                return
        
        self.update_ui_from_profile()
    
    def update_ui_from_profile(self):
        """Update UI controls from current profile."""
        if not self.current_profile:
            return
            
        # Basic settings
        self.name_edit.setText(self.current_profile.name)
        self.desc_edit.setText(self.current_profile.description)
        self.container_combo.setCurrentText(self.current_profile.container)
        
        # Video settings
        self.video_codec_combo.setCurrentText(self.current_profile.video_codec.codec)
        self.video_bitrate_edit.setText(self.current_profile.video_codec.bitrate)
        self.preset_combo.setCurrentText(self.current_profile.video_codec.preset)
        self.crf_spin.setValue(self.current_profile.video_codec.crf)
        
        self.width_spin.setValue(self.current_profile.width or 0)
        self.height_spin.setValue(self.current_profile.height or 0)
        self.fps_spin.setValue(self.current_profile.fps or 0)
        self.maintain_aspect.setChecked(self.current_profile.maintain_aspect_ratio)
        
        # Audio settings
        self.audio_codec_combo.setCurrentText(self.current_profile.audio_codec.codec)
        self.audio_bitrate_edit.setText(self.current_profile.audio_codec.bitrate)
        self.sample_rate_combo.setCurrentText(str(self.current_profile.audio_codec.sample_rate))
        self.channels_spin.setValue(self.current_profile.audio_codec.channels)
        self.normalize_audio.setChecked(self.current_profile.normalize_audio)
        
        # Extra settings
        self.extra_args_edit.setText(self.current_profile.extra_ffmpeg_args)
    
    def update_profile_from_ui(self):
        """Update current profile from UI controls."""
        if not self.current_profile:
            return
            
        # Basic settings
        self.current_profile.name = self.name_edit.text()
        self.current_profile.description = self.desc_edit.text()
        self.current_profile.container = self.container_combo.currentText()
        
        # Video settings
        self.current_profile.video_codec.codec = self.video_codec_combo.currentText()
        self.current_profile.video_codec.bitrate = self.video_bitrate_edit.text()
        self.current_profile.video_codec.preset = self.preset_combo.currentText()
        self.current_profile.video_codec.crf = self.crf_spin.value()
        
        self.current_profile.width = self.width_spin.value() or None
        self.current_profile.height = self.height_spin.value() or None
        self.current_profile.fps = self.fps_spin.value() or None
        self.current_profile.maintain_aspect_ratio = self.maintain_aspect.isChecked()
        
        # Audio settings
        self.current_profile.audio_codec.codec = self.audio_codec_combo.currentText()
        self.current_profile.audio_codec.bitrate = self.audio_bitrate_edit.text()
        self.current_profile.audio_codec.sample_rate = int(self.sample_rate_combo.currentText())
        self.current_profile.audio_codec.channels = self.channels_spin.value()
        self.current_profile.normalize_audio = self.normalize_audio.isChecked()
        
        # Extra settings
        self.current_profile.extra_ffmpeg_args = self.extra_args_edit.text()
    
    def apply_changes(self):
        """Apply changes to current profile."""
        if not self.current_profile:
            return
            
        self.update_profile_from_ui()
        if " (Preset)" not in self.current_profile.name:
            self.profile_manager.save_profile(self.current_profile)
        self.profileUpdated.emit(self.current_profile)
        self.load_profiles()
    
    def accept(self):
        """Handle dialog acceptance."""
        self.apply_changes()
        super().accept()
    
    def import_profile(self):
        """Import a profile from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profile",
            "",
            "JSON Files (*.json)"
        )
        
        if filepath:
            try:
                self.profile_manager.import_profile(filepath)
                self.load_profiles()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to import profile: {e}")
    
    def export_profile(self):
        """Export current profile to file."""
        if not self.current_profile:
            return
            
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            f"{self.current_profile.name}.json",
            "JSON Files (*.json)"
        )
        
        if filepath:
            try:
                self.current_profile.save(filepath)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to export profile: {e}")