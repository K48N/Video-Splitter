from typing import List, Dict
import logging
import cv2
import numpy as np
from pathlib import Path
import json
from datetime import timedelta

from models.scene import Scene
from .scene_classifier import SceneClassifier

logger = logging.getLogger(__name__)

class CVSceneClassifier(SceneClassifier):
    """Computer vision-based scene classifier implementation."""
    
    def __init__(self):
        """Initialize the scene classifier."""
        self.scene_categories = [
            "interview", "action", "b-roll", "dialogue", 
            "transition", "montage", "establishing_shot"
        ]
    
    def classify_scenes(self, video_path: str) -> List[Scene]:
        """Detect and classify scenes in a video."""
        scenes = []
        video = cv2.VideoCapture(video_path)
        
        if not video.isOpened():
            raise RuntimeError(f"Could not open video file: {video_path}")
        
        try:
            fps = video.get(cv2.CAP_PROP_FPS)
            total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Scene detection parameters
            min_scene_duration = int(fps * 2)  # 2 seconds minimum
            threshold = 30.0  # Difference threshold for scene changes
            
            prev_frame = None
            scene_start_frame = 0
            frame_count = 0
            
            while True:
                ret, frame = video.read()
                if not ret:
                    break
                
                frame_count += 1
                
                if prev_frame is None:
                    prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    continue
                
                # Convert current frame to grayscale
                curr_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # Calculate frame difference
                diff = cv2.absdiff(curr_frame, prev_frame)
                mean_diff = np.mean(diff)
                
                # Detect scene change
                if (mean_diff > threshold and 
                    frame_count - scene_start_frame > min_scene_duration):
                    
                    # Analyze the scene content
                    scene_label, confidence = self._analyze_scene_content(
                        video_path, scene_start_frame, frame_count, fps
                    )
                    
                    # Create scene object
                    scene = Scene(
                        start_time=timedelta(seconds=scene_start_frame/fps),
                        end_time=timedelta(seconds=frame_count/fps),
                        label=scene_label,
                        confidence_score=confidence,
                        keywords=self._extract_keywords(scene_label),
                        importance_score=self._calculate_importance(
                            scene_label, confidence
                        )
                    )
                    scenes.append(scene)
                    
                    # Start new scene
                    scene_start_frame = frame_count
                
                prev_frame = curr_frame
            
            # Add final scene if needed
            if frame_count - scene_start_frame > min_scene_duration:
                scene_label, confidence = self._analyze_scene_content(
                    video_path, scene_start_frame, frame_count, fps
                )
                scene = Scene(
                    start_time=timedelta(seconds=scene_start_frame/fps),
                    end_time=timedelta(seconds=frame_count/fps),
                    label=scene_label,
                    confidence_score=confidence,
                    keywords=self._extract_keywords(scene_label),
                    importance_score=self._calculate_importance(
                        scene_label, confidence
                    )
                )
                scenes.append(scene)
        
        finally:
            video.release()
        
        return scenes
    
    def get_supported_labels(self) -> List[str]:
        """Get the list of scene labels this classifier can detect."""
        return self.scene_categories
        
    def _analyze_scene_content(self, video_path: str, 
                             start_frame: int, end_frame: int, 
                             fps: float) -> tuple[str, float]:
        """Analyze the content of a scene segment."""
        # TODO: Implement proper scene content analysis using a trained model
        # For now, return a placeholder classification
        return "b-roll", 0.8
    
    def _extract_keywords(self, scene_label: str) -> List[str]:
        """Extract relevant keywords for a scene type."""
        keywords_map = {
            "interview": ["person", "talking", "conversation"],
            "action": ["movement", "dynamic", "fast-paced"],
            "b-roll": ["background", "establishing", "context"],
            "dialogue": ["conversation", "interaction", "people"],
            "transition": ["change", "effect", "bridge"],
            "montage": ["sequence", "collection", "highlights"],
            "establishing_shot": ["location", "setting", "context"]
        }
        return keywords_map.get(scene_label, [])
    
    def _calculate_importance(self, scene_label: str, 
                            confidence: float) -> float:
        """Calculate an importance score for the scene."""
        importance_weights = {
            "interview": 0.8,
            "action": 0.7,
            "dialogue": 0.75,
            "b-roll": 0.4,
            "transition": 0.2,
            "montage": 0.6,
            "establishing_shot": 0.5
        }
        
        base_importance = importance_weights.get(scene_label, 0.5)
        return base_importance * confidence