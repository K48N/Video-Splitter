from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class AudioProfile:
    """Represents audio characteristics and enhancement settings."""
    loudness: float  # in LUFS
    dynamic_range: float
    eq_settings: Dict[str, float]  # frequency: gain
    noise_reduction_amount: float = 0.0
    clarity_boost: float = 0.0
    music_ducking_threshold: Optional[float] = None
    music_ducking_amount: Optional[float] = None
    
    def to_ffmpeg_filters(self) -> str:
        """Convert the audio profile to FFmpeg filter string."""
        filters = []
        
        # Add loudness normalization
        filters.append(f"loudnorm=I={self.loudness}")
        
        # Add EQ filters if any
        if self.eq_settings:
            eq_parts = []
            for freq, gain in self.eq_settings.items():
                eq_parts.append(f"equalizer=f={freq}:t=q:w=1:g={gain}")
            filters.extend(eq_parts)
            
        # Add noise reduction if enabled
        if self.noise_reduction_amount > 0:
            filters.append(f"afftdn=nr={self.noise_reduction_amount}")
            
        return ",".join(filters)