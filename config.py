"""
Global configuration for the Video Splitter application.
Contains settings for AI services, audio processing, and caching.
"""

import os
from pathlib import Path
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

# Default Paths
APP_DATA = os.getenv("APPDATA") or os.path.expanduser("~/.local/share")
APP_CONFIG_DIR = os.path.join(APP_DATA, "VideoSplitter")
CACHE_DIR = os.path.join(APP_CONFIG_DIR, "cache")
CONFIG_FILE = os.path.join(APP_CONFIG_DIR, "config.json")

# Default Configuration
DEFAULT_CONFIG = {
    # AI Service Settings
    "ai": {
        "whisper_model": "base",  # Options: tiny, base, small, medium, large
        "enable_scene_detection": True,
        "enable_speaker_diarization": True,
        "auto_summarize_length": 60,  # seconds
        "confidence_threshold": 0.7
    },
    
    # Audio Enhancement Settings
    "audio": {
        "voice_clarity": {
            "default_strength": 0.5,
            "enable_noise_reduction": True
        },
        "music_ducking": {
            "threshold": -20,  # dB
            "reduction": -10   # dB
        },
        "style_matching": {
            "target_loudness": -18,  # LUFS
            "enable_eq_matching": True
        }
    },
    
    # Cache Settings
    "cache": {
        "max_size_gb": 10,
        "max_age_days": 30,
        "generate_on_import": True,
        "proxy_resolution": "720p",
        "thumbnail_interval": 1.0  # seconds
    },
    
    # Export Settings
    "export": {
        "max_concurrent_jobs": 2,
        "default_format": "mp4",
        "temp_directory": None  # Will be set during initialization
    }
}

class Config:
    """Global configuration manager."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the configuration system."""
        self._config = DEFAULT_CONFIG.copy()
        
        # Create config directory if it doesn't exist
        os.makedirs(APP_CONFIG_DIR, exist_ok=True)
        
        # Load existing config if available
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    stored_config = json.load(f)
                    self._update_recursive(self._config, stored_config)
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        # Set dynamic defaults
        if not self._config["export"]["temp_directory"]:
            self._config["export"]["temp_directory"] = os.path.join(APP_CONFIG_DIR, "temp")
        
        # Create required directories
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(self._config["export"]["temp_directory"], exist_ok=True)
        
        # Save config to ensure all defaults are written
        self.save()
    
    def _update_recursive(self, base: Dict[str, Any], update: Dict[str, Any]):
        """Recursively update configuration while preserving structure."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._update_recursive(base[key], value)
            else:
                base[key] = value
    
    def get(self, section: str, key: str = None):
        """Get a configuration value."""
        if key is None:
            return self._config.get(section, {})
        return self._config.get(section, {}).get(key)
    
    def set(self, section: str, key: str, value: Any):
        """Set a configuration value."""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
        self.save()
    
    def save(self):
        """Save the current configuration to disk."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

# Global configuration instance
config = Config()

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