"""
ML Service for model management and inference
"""
import os
import logging
from pathlib import Path
import threading
from typing import Optional, Dict, Any
import torch
from transformers import AutoModel, AutoTokenizer
import numpy as np

from .base_service import Service
from .service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

class ModelCache:
    """Manages loading and caching of ML models"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Model cache
        self._models: Dict[str, Any] = {}
        self._tokenizers: Dict[str, Any] = {}
        self._lock = threading.Lock()
        
        # Configure device
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else
            "mps" if torch.backends.mps.is_available() else
            "cpu"
        )
        logger.info(f"Using device: {self.device}")
    
    def get_model(
        self,
        model_id: str,
        task: str,
        force_reload: bool = False
    ) -> Any:
        """
        Get model for specified task, loading if needed
        
        Args:
            model_id: HuggingFace model ID
            task: Task type (scene, speech, diarization, etc)
            force_reload: Force model reload
        """
        cache_key = f"{task}_{model_id}"
        
        with self._lock:
            if force_reload and cache_key in self._models:
                del self._models[cache_key]
                del self._tokenizers[cache_key]
            
            if cache_key not in self._models:
                logger.info(f"Loading model {model_id} for {task}")
                
                try:
                    # Download and load model
                    model = AutoModel.from_pretrained(
                        model_id,
                        cache_dir=self.cache_dir / task,
                        device_map="auto" if torch.cuda.is_available() else None
                    )
                    tokenizer = AutoTokenizer.from_pretrained(
                        model_id,
                        cache_dir=self.cache_dir / task
                    )
                    
                    # Move to device if needed
                    if not torch.cuda.is_available():
                        model = model.to(self.device)
                    
                    self._models[cache_key] = model
                    self._tokenizers[cache_key] = tokenizer
                except Exception as e:
                    logger.error(f"Failed to load model {model_id}: {e}")
                    return None
            
            return self._models[cache_key]
    
    def get_tokenizer(self, model_id: str, task: str) -> Optional[Any]:
        """Get tokenizer for model"""
        cache_key = f"{task}_{model_id}"
        return self._tokenizers.get(cache_key)
    
    def clear_cache(self, task: Optional[str] = None):
        """Clear model cache"""
        with self._lock:
            if task:
                # Clear specific task
                keys = [k for k in self._models.keys() if k.startswith(f"{task}_")]
                for k in keys:
                    del self._models[k]
                    del self._tokenizers[k]
            else:
                # Clear all
                self._models.clear()
                self._tokenizers.clear()

class MLService(Service):
    """Service for ML model management and inference"""
    
    # Default models
    SCENE_MODEL = "microsoft/resnet-50"  # Scene classification
    SPEECH_MODEL = "openai/whisper-base"  # Speech recognition
    DIARIZATION_MODEL = "pyannote/speaker-diarization"  # Speaker diarization
    
    def __init__(self):
        super().__init__()
        self.model_cache = None
        self._cache_dir = None
    
    def start(self) -> None:
        """Start the ML service"""
        super().start()
        
        # Initialize model cache in user's app data
        app_data = os.getenv("APPDATA") or os.path.expanduser("~/.local/share")
        self._cache_dir = os.path.join(app_data, "VideoSplitter", "ml_models")
        self.model_cache = ModelCache(self._cache_dir)
    
    def stop(self) -> None:
        """Stop the ML service"""
        super().stop()
        if self.model_cache:
            self.model_cache.clear_cache()
            self.model_cache = None
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get ML device information"""
        info = {
            "device": str(self.model_cache.device),
            "gpu_available": torch.cuda.is_available(),
            "gpu_name": None,
            "gpu_memory": None,
            "mps_available": torch.backends.mps.is_available()
        }
        
        if torch.cuda.is_available():
            info.update({
                "gpu_name": torch.cuda.get_device_name(),
                "gpu_memory": torch.cuda.get_device_properties(0).total_memory
            })
        
        return info
    
    def batch_process(
        self,
        inputs: list,
        batch_size: int,
        process_fn: callable,
        *args,
        **kwargs
    ) -> list:
        """
        Process inputs in batches
        
        Args:
            inputs: List of inputs
            batch_size: Batch size
            process_fn: Processing function
            *args, **kwargs: Additional args for process_fn
        """
        results = []
        
        for i in range(0, len(inputs), batch_size):
            batch = inputs[i:i + batch_size]
            try:
                batch_results = process_fn(batch, *args, **kwargs)
                results.extend(batch_results)
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                # Add None results for failed batch
                results.extend([None] * len(batch))
        
        return results
    
    def load_scene_model(
        self,
        model_id: Optional[str] = None,
        force_reload: bool = False
    ) -> Optional[Any]:
        """Load scene classification model"""
        return self.model_cache.get_model(
            model_id or self.SCENE_MODEL,
            "scene",
            force_reload
        )
    
    def load_speech_model(
        self,
        model_id: Optional[str] = None,
        force_reload: bool = False
    ) -> Optional[Any]:
        """Load speech recognition model"""
        return self.model_cache.get_model(
            model_id or self.SPEECH_MODEL,
            "speech",
            force_reload
        )
    
    def load_diarization_model(
        self,
        model_id: Optional[str] = None,
        force_reload: bool = False
    ) -> Optional[Any]:
        """Load speaker diarization model"""
        return self.model_cache.get_model(
            model_id or self.DIARIZATION_MODEL,
            "diarization",
            force_reload
        )