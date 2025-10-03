"""
Centralized configuration management
All app settings, constants, and configurations in one place
"""
import os
from pathlib import Path
from typing import Dict, Any
import json


class Config:
    """Application configuration manager"""
    
    # Application Info
    APP_NAME = "Video Splitter Pro"
    APP_VERSION = "3.0.0"
    APP_AUTHOR = "Video Tools"
    
    # Paths
    BASE_DIR = Path(__file__).parent
    CONFIG_DIR = Path.home() / ".video-splitter-pro"
    CACHE_DIR = CONFIG_DIR / "cache"
    LOGS_DIR = CONFIG_DIR / "logs"
    PRESETS_DIR = CONFIG_DIR / "presets"
    TEMP_DIR = CONFIG_DIR / "temp"
    
    # Video Processing
    MAX_PARTS = 100
    MIN_PART_DURATION = 0.1  # seconds
    DEFAULT_THUMBNAIL_SIZE = (160, 90)
    WAVEFORM_HEIGHT = 60
    WAVEFORM_SAMPLES = 1000
    MAX_SUBPROCESS_TIMEOUT = 600  # 10 minutes
    
    # Performance
    MAX_THREADS = os.cpu_count() or 4
    ENABLE_GPU = True
    CHUNK_SIZE = 1024 * 1024  # 1MB for file operations
    MAX_CACHE_SIZE_MB = 500
    MAX_UNDO_HISTORY = 50
    
    # UI Settings
    WINDOW_WIDTH = 1600
    WINDOW_HEIGHT = 1000
    MIN_WINDOW_WIDTH = 1200
    MIN_WINDOW_HEIGHT = 700
    ANIMATION_DURATION = 300  # ms
    STATUS_MESSAGE_DURATION = 3000  # ms
    AUTO_SAVE_INTERVAL = 300  # 5 minutes in seconds
    
    # Recent Files
    MAX_RECENT_FILES = 10
    MAX_RECENT_PROJECTS = 10
    
    # Export Defaults
    DEFAULT_NAMING_PATTERN = "{basename}_part{part_number:02d}"
    DEFAULT_AUDIO_FORMAT = "original"
    DEFAULT_VIDEO_CODEC = "copy"
    DEFAULT_AUDIO_CODEC = "libmp3lame"
    DEFAULT_AUDIO_BITRATE = "192k"
    
    # Keyboard Shortcuts
    DEFAULT_SHORTCUTS = {
        "play_pause": "Space",
        "mark_in": "I",
        "mark_out": "O",
        "seek_forward": "Right",
        "seek_backward": "Left",
        "seek_forward_small": "Up",
        "seek_backward_small": "Down",
        "next_frame": "]",
        "prev_frame": "[",
        "delete_part": "Delete",
        "undo": "Ctrl+Z",
        "redo": "Ctrl+Y",
        "save": "Ctrl+S",
        "open": "Ctrl+O",
        "new": "Ctrl+N",
        "export": "Ctrl+E",
        "split_at_cursor": "S",
        "add_part": "A"
    }
    
    # Themes
    DARK_THEME = {
        "name": "Dark",
        "bg_primary": "#0f0f0f",
        "bg_secondary": "#1a1a1a",
        "bg_tertiary": "#222222",
        "bg_elevated": "#2d2d2d",
        "text_primary": "#ffffff",
        "text_secondary": "#999999",
        "text_tertiary": "#666666",
        "accent": "#00d9ff",
        "accent_hover": "#00b8d4",
        "success": "#00c853",
        "warning": "#ffc107",
        "error": "#ff5252",
        "border": "rgba(255, 255, 255, 0.08)",
        "shadow": "rgba(0, 0, 0, 0.5)"
    }
    
    # Export Presets
    EXPORT_PRESETS = {
        "Conference Talk": {
            "audio_channels": "mono",
            "audio_bitrate": "96k",
            "naming": "{basename}_talk{part_number:02d}",
            "description": "Optimized for speech content"
        },
        "Music/Concert": {
            "audio_channels": "stereo",
            "audio_bitrate": "320k",
            "naming": "{basename}_track{part_number:02d}",
            "description": "High-quality stereo audio"
        },
        "Podcast": {
            "audio_channels": "mono",
            "audio_bitrate": "128k",
            "naming": "{basename}_ep{part_number:02d}",
            "description": "Podcast episode format"
        },
        "Interview": {
            "audio_channels": "mono",
            "audio_bitrate": "128k",
            "naming": "{basename}_q{part_number:02d}",
            "description": "Interview Q&A format"
        },
        "Tutorial": {
            "audio_channels": "stereo",
            "audio_bitrate": "192k",
            "naming": "{basename}_lesson{part_number:02d}",
            "description": "Tutorial series format"
        }
    }
    
    # Validation Rules
    SUPPORTED_VIDEO_FORMATS = [
        ".mp4", ".avi", ".mov", ".mkv", ".webm", 
        ".flv", ".wmv", ".m4v", ".mpg", ".mpeg", ".3gp"
    ]
    
    SUPPORTED_AUDIO_FORMATS = [
        ".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac", ".wma"
    ]
    
    # Feature Flags
    ENABLE_SCENE_DETECTION = True
    ENABLE_SILENCE_DETECTION = True
    ENABLE_WAVEFORM = True
    ENABLE_THUMBNAILS = True
    ENABLE_AUTO_SAVE = True
    ENABLE_CLOUD_SYNC = False
    ENABLE_ANALYTICS = False
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories"""
        for dir_path in [cls.CONFIG_DIR, cls.CACHE_DIR, cls.LOGS_DIR, 
                        cls.PRESETS_DIR, cls.TEMP_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def load_user_settings(cls) -> Dict[str, Any]:
        """Load user settings from file"""
        settings_file = cls.CONFIG_DIR / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    @classmethod
    def save_user_settings(cls, settings: Dict[str, Any]):
        """Save user settings to file"""
        settings_file = cls.CONFIG_DIR / "settings.json"
        try:
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")
    
    @classmethod
    def get_ffmpeg_path(cls) -> str:
        """Get FFmpeg executable path"""
        # Try system PATH first
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg
        
        # Try common installation paths
        common_paths = [
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "C:\\ffmpeg\\bin\\ffmpeg.exe",
            "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError("FFmpeg not found. Please install FFmpeg and add it to PATH.")
    
    @classmethod
    def clear_cache(cls):
        """Clear cached data"""
        import shutil
        if cls.CACHE_DIR.exists():
            shutil.rmtree(cls.CACHE_DIR)
            cls.CACHE_DIR.mkdir()
    
    @classmethod
    def clear_temp(cls):
        """Clear temporary files"""
        import shutil
        if cls.TEMP_DIR.exists():
            shutil.rmtree(cls.TEMP_DIR)
            cls.TEMP_DIR.mkdir()
    
    @classmethod
    def get_log_file(cls) -> Path:
        """Get current log file path"""
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        return cls.LOGS_DIR / f"app_{date_str}.log"


# Initialize directories on import
Config.ensure_directories()