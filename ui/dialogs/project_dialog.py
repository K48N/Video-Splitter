from pathlib import Path
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QLineEdit, QPushButton, QFileDialog, QComboBox,
                           QSpinBox, QCheckBox, QGroupBox, QMessageBox)
from PyQt5.QtCore import Qt

from services.service_registry import ServiceRegistry
from services.project_manager import ProjectManager
from ..components.dark_widgets import DarkButton, DarkLabel, DarkCheckbutton

class ProjectDialog(QDialog):
    """Dialog for creating or editing projects."""
    
    def __init__(self, parent=None, project_path: str = None):
        super().__init__(parent)
        self.setWindowTitle("Project Settings")
        self.resize(600, 400)
        self.setModal(True)
        
        self.project_manager = ServiceRegistry().get_service(ProjectManager)
        self.project_path = project_path
        
        self._create_widgets()
        if project_path:
            self._load_project(project_path)
    
    def _create_widgets(self):
        """Create the dialog widgets."""
        layout = QVBoxLayout(self)
        
        # Basic Settings
        basic_group = QGroupBox("Basic Settings")
        basic_layout = QVBoxLayout(basic_group)
        
        # Project name
        name_layout = QHBoxLayout()
        name_layout.addWidget(DarkLabel("Project Name:"))
        self.name_input = QLineEdit()
        name_layout.addWidget(self.name_input)
        basic_layout.addLayout(name_layout)
        
        # Video file
        video_layout = QHBoxLayout()
        video_layout.addWidget(DarkLabel("Video File:"))
        self.video_path = QLineEdit()
        video_layout.addWidget(self.video_path)
        browse_btn = DarkButton("Browse")
        browse_btn.clicked.connect(self._browse_video)
        video_layout.addWidget(browse_btn)
        basic_layout.addLayout(video_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(DarkLabel("Output Directory:"))
        self.output_dir = QLineEdit()
        output_layout.addWidget(self.output_dir)
        browse_output_btn = DarkButton("Browse")
        browse_output_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(browse_output_btn)
        basic_layout.addLayout(output_layout)
        
        layout.addWidget(basic_group)
        
        # Export Settings
        export_group = QGroupBox("Export Settings")
        export_layout = QVBoxLayout(export_group)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_layout.addWidget(DarkLabel("Output Format:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4", "mov", "avi", "mkv"])
        format_layout.addWidget(self.format_combo)
        export_layout.addLayout(format_layout)
        
        # Quality setting
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(DarkLabel("Quality:"))
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        self.quality_spin.setSuffix("%")
        quality_layout.addWidget(self.quality_spin)
        export_layout.addLayout(quality_layout)
        
        # Audio preservation
        self.preserve_audio = DarkCheckbutton("Preserve Original Audio")
        self.preserve_audio.setChecked(True)
        export_layout.addWidget(self.preserve_audio)
        
        layout.addWidget(export_group)
        
        # AI Settings
        ai_group = QGroupBox("AI Features")
        ai_layout = QVBoxLayout(ai_group)
        
        self.auto_scene = DarkCheckbutton("Auto Scene Detection")
        self.auto_scene.setChecked(True)
        ai_layout.addWidget(self.auto_scene)
        
        self.auto_subtitle = DarkCheckbutton("Auto Subtitle Generation")
        ai_layout.addWidget(self.auto_subtitle)
        
        highlight_layout = QHBoxLayout()
        highlight_layout.addWidget(DarkLabel("Auto Highlight Duration:"))
        self.highlight_duration = QSpinBox()
        self.highlight_duration.setRange(30, 300)
        self.highlight_duration.setValue(60)
        self.highlight_duration.setSuffix(" seconds")
        highlight_layout.addWidget(self.highlight_duration)
        ai_layout.addLayout(highlight_layout)
        
        layout.addWidget(ai_group)
        
        # Template
        template_layout = QHBoxLayout()
        template_layout.addWidget(DarkLabel("Save as Template:"))
        self.template_name = QLineEdit()
        template_layout.addWidget(self.template_name)
        save_template_btn = DarkButton("Save Template")
        save_template_btn.clicked.connect(self._save_template)
        template_layout.addWidget(save_template_btn)
        layout.addLayout(template_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = DarkButton("Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        cancel_btn = DarkButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _browse_video(self):
        """Browse for video file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*.*)"
        )
        if file_path:
            self.video_path.setText(file_path)
            if not self.name_input.text():
                self.name_input.setText(Path(file_path).stem)
    
    def _browse_output(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if dir_path:
            self.output_dir.setText(dir_path)
    
    def _save_template(self):
        """Save current settings as a template."""
        name = self.template_name.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Warning", 
                "Please enter a template name"
            )
            return
            
        settings = self._get_settings()
        try:
            self.project_manager.create_template(name, settings)
            QMessageBox.information(
                self, "Success",
                f"Template '{name}' saved successfully"
            )
            self.template_name.clear()
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to save template: {str(e)}"
            )
    
    def _load_project(self, path: str):
        """Load project settings from file."""
        try:
            project = self.project_manager.load_project(path)
            settings = project.settings
            
            self.name_input.setText(settings.name)
            self.video_path.setText(settings.video_path)
            self.output_dir.setText(settings.output_directory)
            self.format_combo.setCurrentText(settings.output_format)
            self.quality_spin.setValue(settings.output_quality)
            self.preserve_audio.setChecked(settings.preserve_audio)
            self.auto_scene.setChecked(settings.auto_scene_detection)
            self.auto_subtitle.setChecked(settings.auto_subtitle_generation)
            self.highlight_duration.setValue(settings.auto_highlight_duration)
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to load project: {str(e)}"
            )
    
    def _get_settings(self):
        """Get project settings from dialog inputs."""
        from models.project import ProjectSettings
        
        return ProjectSettings(
            name=self.name_input.text(),
            video_path=self.video_path.text(),
            output_directory=self.output_dir.text(),
            output_format=self.format_combo.currentText(),
            output_quality=self.quality_spin.value(),
            preserve_audio=self.preserve_audio.isChecked(),
            auto_scene_detection=self.auto_scene.isChecked(),
            auto_subtitle_generation=self.auto_subtitle.isChecked(),
            auto_highlight_duration=self.highlight_duration.value()
        )
    
    def accept(self):
        """Save project settings."""
        if not self.video_path.text():
            QMessageBox.warning(
                self, "Warning",
                "Please select a video file"
            )
            return
            
        if not self.output_dir.text():
            QMessageBox.warning(
                self, "Warning",
                "Please select an output directory"
            )
            return
            
        try:
            settings = self._get_settings()
            if self.project_path:
                project = self.project_manager.load_project(self.project_path)
                project.settings = settings
            else:
                project = self.project_manager.new_project(settings.video_path)
                project.settings = settings
                
            self.project_manager.save_project()
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to save project: {str(e)}"
            )