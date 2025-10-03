from dataclasses import dataclass
from typing import Optional
from datetime import timedelta

@dataclass
class Subtitle:
    """Represents a subtitle entry with timing, text, and metadata."""
    start_time: timedelta
    end_time: timedelta
    text: str
    speaker_id: Optional[str] = None
    confidence_score: float = 1.0
    is_corrected: bool = False

    def duration(self) -> timedelta:
        """Calculate the duration of this subtitle."""
        return self.end_time - self.start_time

    def overlaps_with(self, other: 'Subtitle') -> bool:
        """Check if this subtitle overlaps in time with another subtitle."""
        return (self.start_time < other.end_time and 
                self.end_time > other.start_time)