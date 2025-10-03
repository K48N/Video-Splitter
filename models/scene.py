from dataclasses import dataclass
from datetime import timedelta
from typing import List

@dataclass
class Scene:
    """Represents a detected scene with metadata and classification."""
    start_time: timedelta
    end_time: timedelta
    label: str  # e.g., "interview", "action", "b-roll"
    confidence_score: float
    keywords: List[str]
    importance_score: float = 0.0  # Used for auto-summarization
    
    def duration(self) -> timedelta:
        """Calculate the duration of this scene."""
        return self.end_time - self.start_time