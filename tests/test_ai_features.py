import pytest
from pathlib import Path
import tempfile
from datetime import timedelta
import json

from models.scene import Scene
from models.subtitle import Subtitle
from services.ai_service import AIService
from services.ai.whisper_provider import WhisperProvider
from services.ai.cv_scene_classifier import CVSceneClassifier

@pytest.fixture
def temp_video():
    """Create a temporary video file."""
    with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp:
        yield tmp.name

@pytest.fixture
def sample_scenes():
    """Create sample scene data."""
    return [
        Scene(
            start_time=timedelta(seconds=0),
            end_time=timedelta(seconds=10),
            label="interview",
            confidence_score=0.8,
            keywords=["person", "talking"],
            importance_score=0.7
        ),
        Scene(
            start_time=timedelta(seconds=10),
            end_time=timedelta(seconds=20),
            label="b-roll",
            confidence_score=0.9,
            keywords=["background"],
            importance_score=0.4
        )
    ]

@pytest.fixture
def sample_subtitles():
    """Create sample subtitle data."""
    return [
        Subtitle(
            start_time=timedelta(seconds=1),
            end_time=timedelta(seconds=5),
            text="Hello, welcome to the video",
            confidence_score=0.95
        ),
        Subtitle(
            start_time=timedelta(seconds=6),
            end_time=timedelta(seconds=10),
            text="This is a test subtitle",
            confidence_score=0.90
        )
    ]

def test_scene_serialization(sample_scenes, temp_video):
    """Test scene data can be saved and loaded."""
    ai_service = AIService()
    
    # Save scenes
    scenes_path = Path(temp_video).with_suffix('.scenes.json')
    ai_service._save_scenes(sample_scenes, temp_video)
    
    # Load scenes
    loaded_scenes = ai_service._load_scenes(temp_video)
    
    # Compare
    assert len(loaded_scenes) == len(sample_scenes)
    for orig, loaded in zip(sample_scenes, loaded_scenes):
        assert loaded.start_time == orig.start_time
        assert loaded.end_time == orig.end_time
        assert loaded.label == orig.label
        assert loaded.confidence_score == orig.confidence_score
        assert loaded.keywords == orig.keywords
        assert loaded.importance_score == orig.importance_score

def test_subtitle_serialization(sample_subtitles, temp_video):
    """Test subtitle data can be saved and loaded."""
    ai_service = AIService()
    
    # Save subtitles
    srt_path = Path(temp_video).with_suffix('.srt')
    ai_service._save_subtitles(sample_subtitles, str(srt_path))
    
    # Load subtitles
    loaded_subtitles = ai_service._load_subtitles(temp_video)
    
    # Compare
    assert len(loaded_subtitles) == len(sample_subtitles)
    for orig, loaded in zip(sample_subtitles, loaded_subtitles):
        assert loaded.start_time == orig.start_time
        assert loaded.end_time == orig.end_time
        assert loaded.text == orig.text

def test_scene_classifier():
    """Test scene classifier functionality."""
    classifier = CVSceneClassifier()
    
    # Check supported labels
    labels = classifier.get_supported_labels()
    assert len(labels) > 0
    assert "interview" in labels
    assert "b-roll" in labels
    
    # Test importance calculation
    score = classifier._calculate_importance("interview", 0.8)
    assert 0 <= score <= 1
    
    # Test keyword extraction
    keywords = classifier._extract_keywords("interview")
    assert len(keywords) > 0
    assert "person" in keywords
    assert "talking" in keywords

@pytest.mark.slow
def test_whisper_provider():
    """Test Whisper transcription."""
    provider = WhisperProvider("base")
    
    # Create a simple test audio file
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        # TODO: Generate test audio
        # For now, just test initialization
        assert provider.model is not None
        assert not provider.supports_speaker_diarization()