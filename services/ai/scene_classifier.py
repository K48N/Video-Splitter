from abc import ABC, abstractmethod
from typing import List

from models.scene import Scene

class SceneClassifier(ABC):
    """Base class for scene classification providers."""
    
    @abstractmethod
    def classify_scenes(self, video_path: str) -> List[Scene]:
        """Analyze and label scenes in a video."""
        pass
    
    @abstractmethod
    def get_supported_labels(self) -> List[str]:
        """Get the list of scene labels this classifier can detect."""
        pass