from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

@dataclass
class Chapter:
    """Represents a chapter marker with title and timing information."""
    title: str
    start_time: timedelta
    end_time: timedelta
    description: Optional[str] = None
    auto_generated: bool = False
    
    def duration(self) -> timedelta:
        """Calculate the duration of this chapter."""
        return self.end_time - self.start_time