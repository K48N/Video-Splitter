from typing import List, Optional
import logging
from pathlib import Path
import tempfile
import os
import json
from datetime import timedelta
from pathlib import Path

from models.subtitle import Subtitle
from models.scene import Scene
from models.chapter import Chapter
from models.export_job import JobType
from .base_service import Service
from .background_job_manager import BackgroundJobManager
from .service_registry import ServiceRegistry
from .ai.speech_to_text_provider import SpeechToTextProvider
from .ai.scene_classifier import SceneClassifier
from .ai.content_summarizer import ContentSummarizer
from .ai.whisper_provider import WhisperProvider
from .ai.cv_scene_classifier import CVSceneClassifier
from .ai.content_summarizer import ContentSummarizer

logger = logging.getLogger(__name__)

class AIService(Service):
    """Coordinates AI-powered features and background processing."""
    
    def __init__(self):
        super().__init__()
        self.job_manager = ServiceRegistry().get_service(BackgroundJobManager)
        self.speech_to_text: Optional[SpeechToTextProvider] = None
        self.scene_classifier: Optional[SceneClassifier] = None
        self.content_summarizer: Optional[ContentSummarizer] = None
    
    def start(self) -> None:
        """Initialize AI providers."""
        super().start()
        # Initialize providers
        self.speech_to_text = WhisperProvider("base")
        self.scene_classifier = CVSceneClassifier()
        self.content_summarizer = ContentSummarizer()
    
    def stop(self) -> None:
        """Clean up AI providers."""
        super().stop()
        self.speech_to_text = None
        self.scene_classifier = None
        self.content_summarizer = None
    
    def generate_subtitles(self, video_path: str, 
                          auto_translate: bool = False,
                          speaker_diarization: bool = False,
                          progress_callback=None) -> str:
        """Queue subtitle generation for a video."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        def work_fn(progress_callback):
            try:
                # Extract audio to temp file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
                    audio_path = temp_audio.name
                    if progress_callback:
                        progress_callback(0.1, "Extracting audio...")
                    
                    # TODO: Use ffmpeg_wrapper to extract audio
                    # For now we'll assume audio extraction works
                    
                    if progress_callback:
                        progress_callback(0.2, "Audio extraction complete")
                
                try:
                    # Generate subtitles
                    if progress_callback:
                        progress_callback(0.3, "Generating transcription...")
                        
                    subtitles = self.speech_to_text.transcribe(audio_path)
                    
                    if progress_callback:
                        progress_callback(0.7, "Transcription complete")
                    
                    if auto_translate:
                        if progress_callback:
                            progress_callback(0.8, "Translating subtitles...")
                        # TODO: Implement translation
                    
                    if speaker_diarization:
                        if progress_callback:
                            progress_callback(0.9, "Identifying speakers...")
                        # TODO: Implement speaker diarization
                    
                    # Save subtitles to file
                    output_path = str(Path(video_path).with_suffix(".srt"))
                    self._save_subtitles(subtitles, output_path)
                    
                    if progress_callback:
                        progress_callback(1.0, "Subtitle generation complete")
                    
                    return output_path
                    
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(audio_path)
                    except OSError as e:
                        logger.warning(f"Failed to cleanup temp file: {e}")
                        
            except Exception as e:
                logger.error(f"Subtitle generation failed: {e}")
                raise RuntimeError(f"Failed to generate subtitles: {str(e)}")
        
        return self.job_manager.submit_job(
            job_type=JobType.SPEECH_TO_TEXT,
            work_fn=work_fn,
            progress_callback=progress_callback
        )
    
    def classify_scenes(self, video_path: str) -> str:
        """Queue scene classification for a video."""
        if not self.scene_classifier:
            raise RuntimeError("No scene classifier configured")
            
        def work_fn():
            scenes = self.scene_classifier.classify_scenes(video_path)
            # TODO: Save scene data
            return scenes
            
        return self.job_manager.submit_job(
            job_type=JobType.SCENE_DETECTION,
            work_fn=work_fn
        )
    
    def generate_highlights(self, video_path: str, 
                          target_duration: float) -> str:
        """Queue highlight generation for a video."""
        if not self.content_summarizer:
            raise RuntimeError("No content summarizer configured")
            
        def work_fn():
            # Load existing subtitles and scenes
            subtitles = self._load_subtitles(video_path)
            scenes = self._load_scenes(video_path)
            
            highlight_scenes = self.content_summarizer.generate_highlight(
                video_path, subtitles, scenes, target_duration
            )
            
            # TODO: Create highlight video using scenes
            return highlight_scenes
            
        return self.job_manager.submit_job(
            job_type=JobType.AUTO_SUMMARIZE,
            work_fn=work_fn
        )
    
    def _save_subtitles(self, subtitles: List[Subtitle], output_path: str) -> None:
        """Save subtitles in SRT format."""
        with open(output_path, "w", encoding="utf-8") as f:
            for i, subtitle in enumerate(subtitles, 1):
                # Write subtitle index
                f.write(f"{i}\n")
                
                # Write timestamp
                start = self._format_timedelta(subtitle.start_time)
                end = self._format_timedelta(subtitle.end_time)
                f.write(f"{start} --> {end}\n")
                
                # Write text
                f.write(f"{subtitle.text}\n")
                
                # Write blank line between subtitles
                f.write("\n")
    
    def _format_timedelta(self, td: timedelta) -> str:
        """Format timedelta for SRT timestamp."""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = td.microseconds // 1000
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def _load_subtitles(self, video_path: str) -> List[Subtitle]:
        """Load subtitles associated with a video."""
        srt_path = str(Path(video_path).with_suffix('.srt'))
        if not Path(srt_path).exists():
            return []
            
        subtitles = []
        with open(srt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                try:
                    # Skip empty lines
                    while i < len(lines) and not lines[i].strip():
                        i += 1
                    if i >= len(lines):
                        break
                        
                    # Parse subtitle index
                    index = int(lines[i].strip())
                    i += 1
                    
                    # Parse timestamps
                    timestamps = lines[i].strip().split(' --> ')
                    start_time = self._parse_srt_timestamp(timestamps[0])
                    end_time = self._parse_srt_timestamp(timestamps[1])
                    i += 1
                    
                    # Parse text
                    text = []
                    while i < len(lines) and lines[i].strip():
                        text.append(lines[i].strip())
                        i += 1
                    
                    subtitle = Subtitle(
                        start_time=start_time,
                        end_time=end_time,
                        text='\n'.join(text),
                        confidence_score=1.0  # Default for loaded subtitles
                    )
                    subtitles.append(subtitle)
                    
                except Exception as e:
                    logger.error(f'Error parsing subtitle at line {i}: {e}')
                    i += 1
                    
        return subtitles
    
    def _parse_srt_timestamp(self, timestamp: str) -> timedelta:
        """Parse SRT timestamp into timedelta."""
        # Format: HH:MM:SS,mmm
        hours, minutes, seconds = timestamp.replace(',', '.').split(':')
        return timedelta(
            hours=int(hours),
            minutes=int(minutes),
            seconds=float(seconds)
        )
    
    def _load_scenes(self, video_path: str) -> List[Scene]:
        """Load scene data associated with a video."""
        json_path = str(Path(video_path).with_suffix('.scenes.json'))
        if not Path(json_path).exists():
            return []
            
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        scenes = []
        for scene_data in data:
            scene = Scene(
                start_time=timedelta(seconds=scene_data['start_time']),
                end_time=timedelta(seconds=scene_data['end_time']),
                label=scene_data['label'],
                confidence_score=scene_data['confidence_score'],
                keywords=scene_data['keywords'],
                importance_score=scene_data['importance_score']
            )
            scenes.append(scene)
            
        return scenes