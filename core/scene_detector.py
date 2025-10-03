"""
Scene detection for automatic segment creation
"""
import subprocess
import json
import os
from typing import List, Tuple, Optional
from core.segment import Segment


class SceneDetector:
    """Detect scene changes in video"""
    
    def __init__(self):
        self.ffmpeg_path = 'ffmpeg'
        self.threshold = 0.3  # Scene change threshold (0.0-1.0)
    
    def detect_scenes(
        self,
        video_path: str,
        threshold: float = 0.3,
        min_scene_length: float = 2.0
    ) -> List[Tuple[float, float]]:
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
            
            return scenes
            
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
        scenes: List[Tuple[float, float]],
        label_prefix: str = "Scene"
    ) -> List[Segment]:
        """Convert scene ranges to Segment objects"""
        segments = []
        
        for i, (start, end) in enumerate(scenes, 1):
            segment = Segment(
                start=start,
                end=end,
                label=f"{label_prefix} {i}"
            )
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