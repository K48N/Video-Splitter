import pytest
import tempfile
import shutil
from pathlib import Path

from services.service_registry import ServiceRegistry
from services.ai_service import AIService
from services.audio_enhancement_service import AudioEnhancementService
from services.media_cache_service import MediaCacheService
from services.export_queue_service import ExportQueueService
from services.background_job_manager import BackgroundJobManager
from models.subtitle import Subtitle
from models.scene import Scene
from models.chapter import Chapter
from models.audio_profile import AudioProfile
from models.export_job import ExportJob, JobStatus, JobType
from utils.exceptions import VideoSplitterError
from .base_test import BaseServiceTest

class TestAIFeatures(BaseServiceTest):
    """Test cases for AI-powered features."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_video = Path(self.test_dir) / "test.mp4"
        self.test_video.touch()
    
    def test_subtitle_generation(self):
        """Test subtitle generation workflow."""
        ai_service = self.registry.get_service(AIService)
        
        # Queue subtitle generation
        job_id = ai_service.generate_subtitles(str(self.test_video))
        self.assertIsNotNone(job_id)
        
        # Check job was created
        job_manager = self.registry.get_service(BackgroundJobManager)
        job = job_manager.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.job_type, JobType.SPEECH_TO_TEXT)

class TestAudioEnhancement(BaseServiceTest):
    """Test cases for audio enhancement features."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_audio = Path(self.test_dir) / "test.wav"
        self.test_audio.touch()
    
    def test_voice_clarity_enhancement(self):
        """Test voice clarity enhancement."""
        audio_service = self.registry.get_service(AudioEnhancementService)
        
        # Test with various strength values
        job_id = audio_service.enhance_voice_clarity(
            str(self.test_audio),
            strength=0.5
        )
        self.assertIsNotNone(job_id)
        
        # Check job was created
        job_manager = self.registry.get_service(BackgroundJobManager)
        job = job_manager.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.job_type, JobType.AUDIO_ENHANCEMENT)

class TestMediaCache(BaseServiceTest):
    """Test cases for media caching."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.test_media = Path(self.test_dir) / "test.mp4"
        self.test_media.touch()
    
    def test_proxy_generation(self):
        """Test proxy file generation."""
        cache_service = self.registry.get_service(MediaCacheService)
        
        # Generate proxy
        job_id = cache_service.generate_proxy(str(self.test_media))
        self.assertIsNotNone(job_id)
        
        # Check cached path
        cached_path = cache_service.get_cached_path(str(self.test_media), "proxy")
        self.assertIsNone(cached_path)  # Should be None until job completes
        
        # Check job was created
        job_manager = self.registry.get_service(BackgroundJobManager)
        job = job_manager.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.job_type, JobType.CACHE_GENERATION)
    
    def test_waveform_generation(self):
        """Test waveform data generation."""
        cache_service = self.registry.get_service(MediaCacheService)
        
        # Generate waveform
        job_id = cache_service.generate_waveform(str(self.test_media))
        self.assertIsNotNone(job_id)
        
        # Check job was created
        job_manager = self.registry.get_service(BackgroundJobManager)
        job = job_manager.get_job(job_id)
        self.assertIsNotNone(job)
        self.assertEqual(job.job_type, JobType.CACHE_GENERATION)
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        cache_service = self.registry.get_service(MediaCacheService)
        
        # Generate some cache entries
        cache_service.generate_proxy(str(self.test_media))
        cache_service.generate_waveform(str(self.test_media))
        
        # Clear specific cache
        cache_service.clear_cache(str(self.test_media), "proxy")
        self.assertIsNone(
            cache_service.get_cached_path(str(self.test_media), "proxy")
        )
        
        # Clear all cache for media
        cache_service.clear_cache(str(self.test_media))
        self.assertIsNone(
            cache_service.get_cached_path(str(self.test_media), "waveform")
        )