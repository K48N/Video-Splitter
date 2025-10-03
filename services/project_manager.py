import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict
import json
import shutil

from .base_service import Service
from models.project import Project, ProjectSettings

logger = logging.getLogger(__name__)

class ProjectManager(Service):
    """Manages video editing projects and their settings."""
    
    def __init__(self):
        super().__init__()
        self.current_project: Optional[Project] = None
        self.recent_projects: List[str] = []
        self.max_recent_projects = 10
        self.templates: Dict[str, ProjectSettings] = {}
        self.config_dir = Path.home() / ".video-splitter"
        self.backup_dir = self.config_dir / "backups"
        self.templates_dir = self.config_dir / "templates"
    
    def start(self) -> None:
        """Initialize the project manager."""
        super().start()
        
        # Create necessary directories
        self.config_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        
        # Load recent projects
        self._load_recent_projects()
        
        # Load project templates
        self._load_templates()
    
    def stop(self) -> None:
        """Clean up project manager."""
        super().stop()
        
        # Save current project if exists
        if self.current_project:
            self.save_project()
            
        # Save recent projects list
        self._save_recent_projects()
    
    def new_project(self, video_path: str, template_name: str = None) -> Project:
        """Create a new project."""
        if template_name and template_name in self.templates:
            project = Project.create_from_template(template_name, video_path)
        else:
            settings = ProjectSettings(
                name=Path(video_path).stem,
                video_path=video_path,
                output_directory=str(Path(video_path).parent)
            )
            project = Project(settings=settings)
        
        project.backup_path = str(self.backup_dir)
        self.current_project = project
        self._add_to_recent_projects(video_path)
        return project
    
    def save_project(self, path: str = None) -> None:
        """Save the current project."""
        if not self.current_project:
            raise RuntimeError("No active project to save")
            
        self.current_project.save(path)
        if path:
            self._add_to_recent_projects(path)
    
    def load_project(self, path: str) -> Project:
        """Load a project from file."""
        project = Project(ProjectSettings.load(path))
        project.backup_path = str(self.backup_dir)
        self.current_project = project
        self._add_to_recent_projects(path)
        return project
    
    def create_template(self, name: str, settings: ProjectSettings) -> None:
        """Save current settings as a project template."""
        template_path = self.templates_dir / f"{name}.json"
        settings.save(str(template_path))
        self.templates[name] = settings
    
    def delete_template(self, name: str) -> None:
        """Delete a project template."""
        if name in self.templates:
            template_path = self.templates_dir / f"{name}.json"
            template_path.unlink(missing_ok=True)
            del self.templates[name]
    
    def get_recent_projects(self) -> List[str]:
        """Get list of recent projects."""
        # Filter out non-existent files
        self.recent_projects = [p for p in self.recent_projects if Path(p).exists()]
        return self.recent_projects
    
    def get_available_templates(self) -> List[str]:
        """Get list of available project templates."""
        return list(self.templates.keys())
    
    def clean_old_backups(self, days: int = 30) -> None:
        """Remove backup files older than specified days."""
        now = datetime.now()
        for backup_file in self.backup_dir.glob("*.vproj"):
            file_age = now - datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_age.days > days:
                backup_file.unlink()
    
    def _load_recent_projects(self) -> None:
        """Load recent projects list from config."""
        recent_file = self.config_dir / "recent.json"
        if recent_file.exists():
            try:
                with open(recent_file) as f:
                    self.recent_projects = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load recent projects: {e}")
                self.recent_projects = []
    
    def _save_recent_projects(self) -> None:
        """Save recent projects list to config."""
        recent_file = self.config_dir / "recent.json"
        try:
            with open(recent_file, 'w') as f:
                json.dump(self.recent_projects, f)
        except Exception as e:
            logger.error(f"Failed to save recent projects: {e}")
    
    def _add_to_recent_projects(self, path: str) -> None:
        """Add a project to recent projects list."""
        if path in self.recent_projects:
            self.recent_projects.remove(path)
        self.recent_projects.insert(0, path)
        
        # Keep list size in check
        if len(self.recent_projects) > self.max_recent_projects:
            self.recent_projects.pop()
    
    def _load_templates(self) -> None:
        """Load available project templates."""
        for template_file in self.templates_dir.glob("*.json"):
            try:
                settings = ProjectSettings.load(str(template_file))
                self.templates[template_file.stem] = settings
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")

    def import_project(self, path: str, new_path: str = None) -> Project:
        """Import a project file, optionally to a new location."""
        if new_path:
            shutil.copy2(path, new_path)
            path = new_path
        return self.load_project(path)
    
    def export_project(self, path: str, include_resources: bool = False) -> None:
        """Export current project to a file, optionally including resources."""
        if not self.current_project:
            raise RuntimeError("No active project to export")
            
        self.save_project(path)
        
        if include_resources:
            # Create a directory for the exported project
            export_dir = Path(path).parent / Path(path).stem
            export_dir.mkdir(exist_ok=True)
            
            # Copy project file
            shutil.copy2(path, export_dir / Path(path).name)
            
            # Copy video file
            video_path = Path(self.current_project.settings.video_path)
            if video_path.exists():
                shutil.copy2(video_path, export_dir / video_path.name)
            
            # Copy related files (subtitles, scenes, etc.)
            for related in video_path.parent.glob(f"{video_path.stem}.*"):
                if related != video_path:
                    shutil.copy2(related, export_dir / related.name)