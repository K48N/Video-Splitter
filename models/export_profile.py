from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
import json

@dataclass
class VideoCodecSettings:
    """Video codec specific settings."""
    codec: str = "h264"  # h264, h265, vp9, etc.
    bitrate: str = "5M"
    preset: str = "medium"  # ultrafast to veryslow
    crf: int = 23  # 0-51, lower is better quality
    pixel_format: str = "yuv420p"
    max_rate: Optional[str] = None
    buf_size: Optional[str] = None

@dataclass
class AudioCodecSettings:
    """Audio codec specific settings."""
    codec: str = "aac"  # aac, mp3, opus, etc.
    bitrate: str = "192k"
    sample_rate: int = 44100
    channels: int = 2

@dataclass
class ExportProfile:
    """Video export profile settings."""
    name: str
    description: str = ""
    container: str = "mp4"  # mp4, mov, mkv, etc.
    
    # Video settings
    video_codec: VideoCodecSettings = field(default_factory=VideoCodecSettings)
    width: Optional[int] = None  # If None, maintain source
    height: Optional[int] = None
    fps: Optional[float] = None
    maintain_aspect_ratio: bool = True
    
    # Audio settings
    audio_codec: AudioCodecSettings = field(default_factory=AudioCodecSettings)
    normalize_audio: bool = False
    
    # Additional settings
    metadata: Dict[str, str] = field(default_factory=dict)
    extra_ffmpeg_args: str = ""
    
    @classmethod
    def create_preset(cls, preset_name: str) -> 'ExportProfile':
        """Create a profile from a preset."""
        presets = {
            "youtube": cls(
                name="YouTube HD",
                description="Optimized for YouTube upload",
                container="mp4",
                video_codec=VideoCodecSettings(
                    codec="h264",
                    bitrate="5M",
                    preset="medium",
                    crf=18,
                    max_rate="7M",
                    buf_size="10M"
                ),
                audio_codec=AudioCodecSettings(
                    codec="aac",
                    bitrate="192k"
                ),
                normalize_audio=True
            ),
            "vimeo": cls(
                name="Vimeo HD",
                description="Optimized for Vimeo upload",
                container="mp4",
                video_codec=VideoCodecSettings(
                    codec="h264",
                    bitrate="8M",
                    preset="slower",
                    crf=20
                ),
                audio_codec=AudioCodecSettings(
                    codec="aac",
                    bitrate="320k"
                )
            ),
            "device": cls(
                name="Device Playback",
                description="Optimized for mobile devices",
                container="mp4",
                video_codec=VideoCodecSettings(
                    codec="h264",
                    preset="fast",
                    crf=23
                ),
                audio_codec=AudioCodecSettings(
                    codec="aac",
                    bitrate="128k"
                )
            ),
            "archive": cls(
                name="Archive Quality",
                description="High quality archival",
                container="mkv",
                video_codec=VideoCodecSettings(
                    codec="h265",
                    preset="veryslow",
                    crf=18
                ),
                audio_codec=AudioCodecSettings(
                    codec="flac",
                    bitrate="0"  # Lossless
                )
            )
        }
        
        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        return presets[preset_name]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "container": self.container,
            "video_codec": vars(self.video_codec),
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "maintain_aspect_ratio": self.maintain_aspect_ratio,
            "audio_codec": vars(self.audio_codec),
            "normalize_audio": self.normalize_audio,
            "metadata": self.metadata,
            "extra_ffmpeg_args": self.extra_ffmpeg_args
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportProfile':
        """Create profile from dictionary."""
        video_codec_data = data.pop("video_codec")
        audio_codec_data = data.pop("audio_codec")
        
        profile = cls(**data)
        profile.video_codec = VideoCodecSettings(**video_codec_data)
        profile.audio_codec = AudioCodecSettings(**audio_codec_data)
        
        return profile
    
    def save(self, path: str):
        """Save profile to file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)
    
    @classmethod
    def load(cls, path: str) -> 'ExportProfile':
        """Load profile from file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def get_ffmpeg_args(self) -> list:
        """Get FFmpeg arguments for this profile."""
        args = []
        
        # Container format
        args.extend(["-f", self.container])
        
        # Video codec settings
        args.extend(["-c:v", self.video_codec.codec])
        if self.video_codec.bitrate:
            args.extend(["-b:v", self.video_codec.bitrate])
        if self.video_codec.preset:
            args.extend(["-preset", self.video_codec.preset])
        args.extend(["-crf", str(self.video_codec.crf)])
        args.extend(["-pix_fmt", self.video_codec.pixel_format])
        
        # Video dimensions
        if self.width and self.height:
            if self.maintain_aspect_ratio:
                args.extend(["-vf", f"scale={self.width}:{self.height}:force_original_aspect_ratio=decrease"])
            else:
                args.extend(["-vf", f"scale={self.width}:{self.height}"])
        
        # FPS
        if self.fps:
            args.extend(["-r", str(self.fps)])
        
        # Audio codec settings
        args.extend(["-c:a", self.audio_codec.codec])
        if self.audio_codec.bitrate:
            args.extend(["-b:a", self.audio_codec.bitrate])
        args.extend(["-ar", str(self.audio_codec.sample_rate)])
        args.extend(["-ac", str(self.audio_codec.channels)])
        
        # Additional settings
        if self.video_codec.max_rate:
            args.extend(["-maxrate", self.video_codec.max_rate])
        if self.video_codec.buf_size:
            args.extend(["-bufsize", self.video_codec.buf_size])
            
        # Metadata
        for key, value in self.metadata.items():
            args.extend(["-metadata", f"{key}={value}"])
        
        # Extra arguments
        if self.extra_ffmpeg_args:
            args.extend(self.extra_ffmpeg_args.split())
        
        return args