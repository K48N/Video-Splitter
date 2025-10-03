from typing import List
import logging
from datetime import timedelta
import whisper  # You'll need to pip install whisper

from models.subtitle import Subtitle
from .speech_to_text_provider import SpeechToTextProvider

logger = logging.getLogger(__name__)

class WhisperProvider(SpeechToTextProvider):
    """OpenAI Whisper-based speech-to-text provider."""
    
    def __init__(self, model_name: str = "base"):
        """Initialize the Whisper model."""
        self.model = whisper.load_model(model_name)
    
    def transcribe(self, audio_path: str) -> List[Subtitle]:
        """Generate subtitles using Whisper."""
        try:
            # Transcribe the audio
            result = self.model.transcribe(audio_path)
            
            # Convert segments to our Subtitle format
            subtitles = []
            for segment in result["segments"]:
                subtitle = Subtitle(
                    start_time=timedelta(seconds=segment["start"]),
                    end_time=timedelta(seconds=segment["end"]),
                    text=segment["text"].strip(),
                    confidence_score=segment.get("confidence", 1.0)
                )
                subtitles.append(subtitle)
            
            return subtitles
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise
    
    def supports_speaker_diarization(self) -> bool:
        """Whisper does not support speaker diarization natively."""
        return False