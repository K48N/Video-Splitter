import pytest
from pathlib import Path
import tempfile
from datetime import timedelta

from models.project import Project, ProjectSettings
from models.scene import Scene
from models.subtitle import Subtitle
from services.project_manager import ProjectManager

@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for project tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_project_settings():
    """Create sample project settings."""
    return ProjectSettings(
        name="Test Project",
        video_path="/path/to/video.mp4",
        output_directory="/path/to/output"
    )

@pytest.fixture
def sample_project(sample_project_settings):
    """Create a sample project."""
    return Project(settings=sample_project_settings)

def test_project_settings_serialization(sample_project_settings, temp_project_dir):
    """Test project settings can be saved and loaded."""
    # Save settings
    settings_path = temp_project_dir / "test_settings.json"
    sample_project_settings.save(str(settings_path))
    
    # Load settings
    loaded_settings = ProjectSettings.load(str(settings_path))
    
    # Compare
    assert loaded_settings.name == sample_project_settings.name
    assert loaded_settings.video_path == sample_project_settings.video_path
    assert loaded_settings.output_directory == sample_project_settings.output_directory

def test_project_backup(sample_project, temp_project_dir):
    """Test project backup functionality."""
    # Set backup path
    sample_project.backup_path = str(temp_project_dir)
    
    # Create backup
    sample_project.create_backup()
    
    # Check backup exists
    backups = sample_project.list_backups(str(temp_project_dir))
    assert len(backups) == 1
    
    # Load from backup
    backup_path = backups[0]
    restored_project = Project(ProjectSettings(
        name="Restored",
        video_path="",
        output_directory=""
    ))
    restored_project.restore_from_backup(backup_path)
    
    # Compare
    assert restored_project.settings.name == sample_project.settings.name
    assert restored_project.settings.video_path == sample_project.settings.video_path