"""
Scene detection with ML-based classification
"""
import subprocess
import json
import os
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np
import torch
from pathlib import Path
import logging

from core.segment import Segment
from models.scene_models import SceneMetadata
from services.service_registry import ServiceRegistry
from services.ml_service import MLService

logger = logging.getLogger(__name__)


class SceneDetector:
    """Detect scene changes in video"""
    
    SHOT_TYPES = ['extreme-wide', 'wide', 'medium', 'close-up', 'extreme-close-up']
    
    def __init__(self):
        self.ffmpeg_path = 'ffmpeg'
        self.threshold = 0.3  # Scene change threshold (0.0-1.0)
        
        # Initialize ML service
        self.ml_service = ServiceRegistry().get_service(MLService)
        self.scene_model = None
        self.device = None
    
    def detect_scenes(
        self,
        video_path: str,
        threshold: float = 0.3,
        min_scene_length: float = 2.0,
        analyze_content: bool = True
    ) -> List[SceneMetadata]:
        """
        Detect scene changes using FFmpeg
        
        Args:
            video_path: Path to video file
            threshold: Scene change sensitivity (0.0-1.0, lower = more sensitive)
            min_scene_length: Minimum scene length in seconds
        
        Returns:
            List of (start, end) tuples for each scene
        """
        try:
            # Use FFmpeg scene detection filter
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-filter:v', f'select=gt(scene\\,{threshold}),showinfo',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse scene change timestamps from stderr
            timestamps = self._parse_scene_timestamps(result.stderr)
            
            # Convert timestamps to segments
            scenes = self._timestamps_to_scenes(
                timestamps,
                video_path,
                min_scene_length
            )
            
            if analyze_content and scenes:
                # Load ML model if needed
                if not self.scene_model:
                    self.scene_model = self.ml_service.load_scene_model()
                    if not self.scene_model:
                        logger.warning("Failed to load scene classification model")
                        analyze_content = False
                
                if analyze_content:
                    return self._analyze_scenes(video_path, scenes)
            
            # Return basic scenes without analysis
            return [
                SceneMetadata(
                    start_time=start,
                    end_time=end,
                    confidence=1.0,
                    labels=[],
                    shot_type="unknown",
                    action_score=0.0,
                    dialog_score=0.0
                )
                for start, end in scenes
            ]
            
        except Exception as e:
            raise RuntimeError(f"Scene detection failed: {str(e)}")
    
    def _parse_scene_timestamps(self, ffmpeg_output: str) -> List[float]:
        """Parse scene change timestamps from FFmpeg output"""
        timestamps = []
        
        for line in ffmpeg_output.split('\n'):
            if 'pts_time:' in line:
                try:
                    # Extract timestamp
                    parts = line.split('pts_time:')
                    if len(parts) > 1:
                        time_str = parts[1].split()[0]
                        timestamp = float(time_str)
                        timestamps.append(timestamp)
                except:
                    continue
        
        return sorted(set(timestamps))
    
    def _timestamps_to_scenes(
        self,
        timestamps: List[float],
        video_path: str,
        min_scene_length: float
    ) -> List[Tuple[float, float]]:
        """Group timestamps into scene ranges with minimum length"""
        """Convert scene change timestamps to scene ranges"""
        if not timestamps:
            return []
        
        # Get video duration
        duration = self._get_video_duration(video_path)
        
        scenes = []
        start = 0.0
        
        for timestamp in timestamps:
            if timestamp - start >= min_scene_length:
                scenes.append((start, timestamp))
                start = timestamp
        
        # Add final scene
        if duration - start >= min_scene_length:
            scenes.append((start, duration))
        
        return scenes
    
    def _analyze_scenes(
        self,
        video_path: str,
        scenes: List[Tuple[float, float]]
    ) -> List[SceneMetadata]:
        """Analyze scene content using ML models"""
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            analyzed_scenes = []
            
            for start, end in scenes:
                # Sample frames from scene
                frame_times = np.linspace(start, end, num=5)  # 5 frames per scene
                frames = []
                
                for t in frame_times:
                    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                    ret, frame = cap.read()
                    if ret:
                        # Convert to RGB and resize
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame = cv2.resize(frame, (224, 224))
                        frames.append(frame)
                
                if frames:
                    # Convert to tensor
                    frames = torch.tensor(np.array(frames)).permute(0, 3, 1, 2)
                    frames = frames.float() / 255.0
                    frames = frames.to(self.ml_service.model_cache.device)
                    
                    # Get scene predictions
                    with torch.no_grad():
                        outputs = self.scene_model(frames)
                        scene_logits = outputs.logits.mean(dim=0)
                        scene_probs = torch.softmax(scene_logits, dim=-1)
                    
                    # Get top labels
                    top_probs, top_indices = scene_probs.topk(3)
                    labels = [
                        self.scene_model.config.id2label[idx.item()]
                        for idx in top_indices
                    ]
                    confidence = top_probs[0].item()
                    
                    # Analyze shot type
                    shot_type = self._detect_shot_type(frames[len(frames)//2])
                    
                    # Calculate action/dialog scores
                    action_score = self._calculate_motion(frames)
                    dialog_score = self._estimate_dialog_probability(frames)
                    
                    analyzed_scenes.append(SceneMetadata(
                        start_time=start,
                        end_time=end,
                        confidence=confidence,
                        labels=labels,
                        shot_type=shot_type,
                        action_score=action_score,
                        dialog_score=dialog_score
                    ))
                else:
                    # Fallback if frame extraction failed
                    analyzed_scenes.append(SceneMetadata(
                        start_time=start,
                        end_time=end,
                        confidence=0.0,
                        labels=[],
                        shot_type="unknown",
                        action_score=0.0,
                        dialog_score=0.0
                    ))
            
            cap.release()
            return analyzed_scenes
            
        except Exception as e:
            logger.error(f"Scene analysis failed: {e}")
            # Return basic scenes without analysis
            return [
                SceneMetadata(
                    start_time=start,
                    end_time=end,
                    confidence=0.0,
                    labels=[],
                    shot_type="unknown",
                    action_score=0.0,
                    dialog_score=0.0
                )
                for start, end in scenes
            ]
    
    def _detect_shot_type(self, frame: torch.Tensor) -> str:
        """Detect shot type based on face detection and scene composition"""
        try:
            # Convert frame to numpy
            frame = frame.cpu().numpy()
            height, width = frame.shape[:2]
            
            # Run face detection
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            faces = face_cascade.detectMultiScale(frame, 1.1, 4)
            
            if len(faces) > 0:
                # Use largest face for shot type
                largest_face = max(faces, key=lambda x: x[2] * x[3])
                face_width = largest_face[2] / width
                
                # Classify based on face size
                if face_width > 0.5:
                    return "extreme-close-up"
                elif face_width > 0.3:
                    return "close-up"
                elif face_width > 0.15:
                    return "medium"
                else:
                    return "wide"
            else:
                # No faces, estimate based on edge density
                edges = cv2.Canny(frame, 100, 200)
                edge_density = np.mean(edges > 0)
                
                return "wide" if edge_density < 0.1 else "medium"
        except:
            return "unknown"
    
    def _calculate_motion(self, frames: torch.Tensor) -> float:
        """Calculate motion intensity score"""
        try:
            if len(frames) < 2:
                return 0.0
            
            diffs = []
            frames_np = frames.cpu().numpy()
            
            for i in range(len(frames_np) - 1):
                # Calculate frame difference
                diff = np.abs(frames_np[i+1] - frames_np[i]).mean()
                diffs.append(diff)
            
            # Normalize motion score
            motion_score = np.mean(diffs)
            return float(min(motion_score * 5, 1.0))  # Scale up and cap
        except:
            return 0.0
    
    def _estimate_dialog_probability(self, frames: torch.Tensor) -> float:
        """Estimate probability of dialog scene"""
        try:
            # Convert middle frame to numpy
            mid_frame = frames[len(frames)//2].cpu().numpy()
            
            # Run face detection
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            faces = face_cascade.detectMultiScale(mid_frame, 1.1, 4)
            
            # Dialog probability based on:
            # - Number of faces (1-2 faces typical for dialog)
            # - Face sizes (medium shots typical)
            # - Face positions (facing each other)
            
            n_faces = len(faces)
            if n_faces == 0:
                return 0.0
            elif n_faces > 3:
                return 0.3  # Group scene, less likely dialog
            
            # Check face sizes
            face_sizes = [w * h for (x, y, w, h) in faces]
            avg_face_size = np.mean(face_sizes) / (mid_frame.shape[0] * mid_frame.shape[1])
            
            # Medium shot is ideal for dialog
            size_score = 1.0 - abs(avg_face_size - 0.15) * 3
            
            # For 2 faces, check if they're facing each other
            position_score = 1.0
            if n_faces == 2:
                x1, x2 = faces[0][0], faces[1][0]
                w1, w2 = faces[0][2], faces[1][2]
                gap = abs((x1 + w1/2) - (x2 + w2/2))
                position_score = min(gap / mid_frame.shape[1] * 2, 1.0)
            
            return float(min(
                (size_score + position_score) / 2,
                1.0
            ))
        except:
            return 0.0
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            return float(result.stdout.strip())
        except:
            return 3600.0  # Default fallback
    
    def create_segments_from_scenes(
        self,
        scenes: List[SceneMetadata],
        label_prefix: str = "Scene"
    ) -> List[Segment]:
        """Convert scene metadata to Segment objects"""
        segments = []
        
        for i, scene in enumerate(scenes, 1):
            # Create label with scene type and content
            label_parts = [f"{label_prefix} {i}", scene.shot_type]
            if scene.labels:
                label_parts.extend(scene.labels[:2])  # Top 2 labels
            
            segment = Segment(
                start=scene.start_time,
                end=scene.end_time,
                label=" - ".join(label_parts)
            )
            segment.metadata = scene.to_dict()
            segments.append(segment)
        
        return segments
    
    def detect_silence(
        self,
        video_path: str,
        noise_threshold: str = "-30dB",
        min_silence_duration: float = 1.0
    ) -> List[Tuple[float, float]]:
        """
        Detect silent portions in audio
        
        Args:
            video_path: Path to video file
            noise_threshold: Silence threshold (e.g., "-30dB")
            min_silence_duration: Minimum silence length in seconds
        
        Returns:
            List of (start, end) tuples for silent portions
        """
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', video_path,
                '-af', f'silencedetect=noise={noise_threshold}:d={min_silence_duration}',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse silence timestamps
            silences = self._parse_silence_timestamps(result.stderr)
            
            return silences
            
        except Exception as e:
            raise RuntimeError(f"Silence detection failed: {str(e)}")
    
    def _parse_silence_timestamps(self, ffmpeg_output: str) -> List[Tuple[float, float]]:
        """Parse silence start/end timestamps"""
        silences = []
        silence_start = None
        
        for line in ffmpeg_output.split('\n'):
            if 'silence_start:' in line:
                try:
                    parts = line.split('silence_start:')
                    silence_start = float(parts[1].strip())
                except:
                    continue
            
            elif 'silence_end:' in line and silence_start is not None:
                try:
                    parts = line.split('silence_end:')
                    silence_end = float(parts[1].split('|')[0].strip())
                    silences.append((silence_start, silence_end))
                    silence_start = None
                except:
                    continue
        
        return silences
    
    def create_segments_between_silences(
        self,
        video_path: str,
        silences: List[Tuple[float, float]],
        label_prefix: str = "Part"
    ) -> List[Segment]:
        """Create segments for non-silent portions"""
        duration = self._get_video_duration(video_path)
        
        if not silences:
            return [Segment(0, duration, f"{label_prefix} 1")]
        
        segments = []
        current_start = 0.0
        part_num = 1
        
        for silence_start, silence_end in silences:
            # Add segment before silence
            if silence_start > current_start:
                segments.append(Segment(
                    start=current_start,
                    end=silence_start,
                    label=f"{label_prefix} {part_num}"
                ))
                part_num += 1
            
            current_start = silence_end
        
        # Add final segment
        if current_start < duration:
            segments.append(Segment(
                start=current_start,
                end=duration,
                label=f"{label_prefix} {part_num}"
            ))
        
        return segments