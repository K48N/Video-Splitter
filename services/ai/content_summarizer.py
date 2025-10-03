from abc import ABC, abstractmethod
from typing import List

from models.subtitle import Subtitle
from models.scene import Scene

class ContentSummarizer(ABC):
    """Base class for content summarization providers."""
    
    @abstractmethod
    def generate_highlight(self, video_path: str, subtitles: List[Subtitle],
                         scenes: List[Scene], target_duration: float) -> List[Scene]:
        """Generate a highlight reel/trailer from the video content."""
        pass
    
    @abstractmethod
    def generate_chapter_titles(self, subtitles: List[Subtitle],
                              scenes: List[Scene]) -> List[str]:
        """Generate meaningful chapter titles based on content."""
        pass