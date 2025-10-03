from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import timedelta

from models.subtitle import Subtitle

class SpeechToTextProvider(ABC):
    """Base class for speech-to-text providers."""
    
    @abstractmethod
    def transcribe(self, audio_path: str) -> List[Subtitle]:
        """Generate subtitles from audio."""
        pass
    
    @abstractmethod
    def supports_speaker_diarization(self) -> bool:
        """Check if this provider supports speaker diarization."""
        pass