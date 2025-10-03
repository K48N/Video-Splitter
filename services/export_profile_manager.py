from pathlib import Path
import json
import os
from typing import Dict, List, Optional
from models.export_profile import ExportProfile

class ExportProfileManager:
    """Manages video export profiles."""
    
    def __init__(self, profiles_dir: Optional[str] = None):
        """Initialize the profile manager.
        
        Args:
            profiles_dir: Directory to store profiles. If None, uses default location.
        """
        if profiles_dir is None:
            # Use default location in user's home directory
            home = Path.home()
            self.profiles_dir = home / '.video_splitter' / 'export_profiles'
        else:
            self.profiles_dir = Path(profiles_dir)
            
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: Dict[str, ExportProfile] = {}
        self._load_profiles()
    
    def _load_profiles(self):
        """Load all profiles from the profiles directory."""
        for file in self.profiles_dir.glob("*.json"):
            try:
                profile = ExportProfile.load(str(file))
                self._profiles[profile.name] = profile
            except Exception as e:
                print(f"Error loading profile {file}: {e}")
    
    def save_profile(self, profile: ExportProfile) -> None:
        """Save a profile to disk."""
        if not profile.name:
            raise ValueError("Profile must have a name")
            
        # Sanitize filename
        filename = "".join(c for c in profile.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filepath = self.profiles_dir / f"{filename}.json"
        
        profile.save(str(filepath))
        self._profiles[profile.name] = profile
    
    def get_profile(self, name: str) -> ExportProfile:
        """Get a profile by name."""
        if name not in self._profiles:
            raise KeyError(f"Profile not found: {name}")
        return self._profiles[name]
    
    def delete_profile(self, name: str) -> None:
        """Delete a profile."""
        if name not in self._profiles:
            raise KeyError(f"Profile not found: {name}")
            
        profile_path = self.profiles_dir / f"{name}.json"
        if profile_path.exists():
            profile_path.unlink()
        
        del self._profiles[name]
    
    def list_profiles(self) -> List[str]:
        """Get list of all profile names."""
        return list(self._profiles.keys())
    
    def create_preset(self, preset_name: str) -> ExportProfile:
        """Create a new profile from a preset."""
        profile = ExportProfile.create_preset(preset_name)
        self.save_profile(profile)
        return profile
    
    def import_profile(self, filepath: str) -> ExportProfile:
        """Import a profile from a file."""
        profile = ExportProfile.load(filepath)
        self.save_profile(profile)
        return profile
    
    def export_profile(self, name: str, filepath: str) -> None:
        """Export a profile to a file."""
        profile = self.get_profile(name)
        profile.save(filepath)