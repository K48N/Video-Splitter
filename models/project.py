from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path

@dataclass
class ProjectSettings:
    """Settings for a video editing project."""
    name: str
    video_path: str
    output_directory: str
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    
    # Video settings
    output_format: str = "mp4"
    output_quality: int = 90  # 1-100
    preserve_audio: bool = True
    
    # Timeline settings
    timeline_zoom: float = 1.0
    show_waveform: bool = True
    snap_to_grid: bool = True
    grid_size: float = 1.0  # seconds
    
    # AI feature settings
    auto_scene_detection: bool = True
    auto_subtitle_generation: bool = False
    auto_highlight_duration: int = 60  # seconds
    
    # Export settings
    export_profile: str = "default"
    custom_export_settings: Dict = field(default_factory=dict)
    
    # Effect presets
    effect_presets: Dict = field(default_factory=dict)
    
    # Recent changes for undo/redo
    history: List[Dict] = field(default_factory=list)
    history_max_size: int = 50
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary for serialization."""
        return {
            "name": self.name,
            "video_path": self.video_path,
            "output_directory": self.output_directory,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "version": self.version,
            "output_format": self.output_format,
            "output_quality": self.output_quality,
            "preserve_audio": self.preserve_audio,
            "timeline_zoom": self.timeline_zoom,
            "show_waveform": self.show_waveform,
            "snap_to_grid": self.snap_to_grid,
            "grid_size": self.grid_size,
            "auto_scene_detection": self.auto_scene_detection,
            "auto_subtitle_generation": self.auto_subtitle_generation,
            "auto_highlight_duration": self.auto_highlight_duration,
            "export_profile": self.export_profile,
            "custom_export_settings": self.custom_export_settings,
            "effect_presets": self.effect_presets
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectSettings':
        """Create settings from dictionary."""
        # Convert ISO format strings back to datetime
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["modified_at"] = datetime.fromisoformat(data["modified_at"])
        return cls(**data)
    
    def save(self, path: str):
        """Save settings to file."""
        self.modified_at = datetime.now()
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)
    
    @classmethod
    def load(cls, path: str) -> 'ProjectSettings':
        """Load settings from file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def add_to_history(self, action: str, data: dict):
        """Add an action to the history for undo/redo."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "data": data
        })
        
        # Keep history size in check
        if len(self.history) > self.history_max_size:
            self.history.pop(0)

@dataclass
class Project:
    """Represents a video editing project."""
    settings: ProjectSettings
    backup_path: Optional[str] = None
    auto_backup_interval: int = 300  # seconds
    _last_backup: datetime = field(default_factory=datetime.now)
    
    def save(self, path: str = None):
        """Save the project to file."""
        if path is None and self.settings.video_path:
            # Use video path as base for project file
            path = str(Path(self.settings.video_path).with_suffix('.vproj'))
        
        if path:
            self.settings.save(path)
    
    def load(self, path: str) -> None:
        """Load project from file."""
        self.settings = ProjectSettings.load(path)
    
    def create_backup(self) -> None:
        """Create a backup of the current project state."""
        if not self.backup_path:
            return
            
        now = datetime.now()
        if (now - self._last_backup).total_seconds() >= self.auto_backup_interval:
            backup_file = Path(self.backup_path) / f"{self.settings.name}_{now.strftime('%Y%m%d_%H%M%S')}.vproj"
            self.save(str(backup_file))
            self._last_backup = now
    
    def restore_from_backup(self, backup_path: str) -> None:
        """Restore project from a backup file."""
        self.load(backup_path)
    
    @staticmethod
    def list_backups(backup_dir: str) -> List[str]:
        """List available backup files in the backup directory."""
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return []
            
        return [str(f) for f in backup_path.glob("*.vproj")]
    
    @classmethod
    def create_from_template(cls, template_name: str, video_path: str) -> 'Project':
        """Create a new project from a template."""
        # TODO: Implement template system
        settings = ProjectSettings(
            name=Path(video_path).stem,
            video_path=video_path,
            output_directory=str(Path(video_path).parent)
        )
        return cls(settings=settings)