"""
Low-level FFmpeg wrapper with GPU acceleration support
"""
import subprocess
import json
import os
from typing import Optional, Dict, Any, List
from pathlib import Path


class FFmpegWrapper:
    """Professional FFmpeg wrapper with GPU support"""
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
        self.gpu_available = self._check_gpu_support()
    
    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                return 'ffmpeg'
        except:
            pass
        raise FileNotFoundError("FFmpeg not found in system PATH")
    
    def _find_ffprobe(self) -> str:
        """Find FFprobe executable"""
        try:
            result = subprocess.run(['ffprobe', '-version'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                return 'ffprobe'
        except:
            pass
        return None
    
    def _check_gpu_support(self) -> Dict[str, bool]:
        """Check available GPU encoders"""
        gpu_support = {
            'nvenc': False,  # NVIDIA
            'qsv': False,    # Intel Quick Sync
            'videotoolbox': False,  # Apple
            'amf': False     # AMD
        }
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )
            output = result.stdout.lower()
            
            if 'h264_nvenc' in output:
                gpu_support['nvenc'] = True
            if 'h264_qsv' in output:
                gpu_support['qsv'] = True
            if 'h264_videotoolbox' in output:
                gpu_support['videotoolbox'] = True
            if 'h264_amf' in output:
                gpu_support['amf'] = True
        except:
            pass
        
        return gpu_support
    
    def get_video_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive video information using ffprobe"""
        if not self.ffprobe_path:
            raise RuntimeError("FFprobe not available")
        
        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  timeout=10, check=True)
            data = json.loads(result.stdout)
            
            # Extract useful information
            info = {
                'duration': float(data['format'].get('duration', 0)),
                'size': int(data['format'].get('size', 0)),
                'bitrate': int(data['format'].get('bit_rate', 0)),
                'format': data['format'].get('format_name', 'unknown'),
                'streams': []
            }
            
            for stream in data.get('streams', []):
                stream_info = {
                    'type': stream.get('codec_type'),
                    'codec': stream.get('codec_name'),
                    'index': stream.get('index')
                }
                
                if stream['codec_type'] == 'video':
                    stream_info.update({
                        'width': stream.get('width'),
                        'height': stream.get('height'),
                        'fps': eval(stream.get('r_frame_rate', '0/1')),
                        'pix_fmt': stream.get('pix_fmt')
                    })
                elif stream['codec_type'] == 'audio':
                    stream_info.update({
                        'channels': stream.get('channels'),
                        'sample_rate': stream.get('sample_rate'),
                        'channel_layout': stream.get('channel_layout')
                    })
                
                info['streams'].append(stream_info)
            
            return info
            
        except Exception as e:
            raise RuntimeError(f"Failed to get video info: {str(e)}")
    
    def extract_clip(
        self,
        input_path: str,
        output_path: str,
        start: float,
        end: float,
        audio_channels: Optional[str] = None,
        use_gpu: bool = True,
        codec_copy: bool = True
    ) -> None:
        """
        Extract video clip with optimizations
        
        Args:
            input_path: Source video file
            output_path: Output file path
            start: Start time in seconds
            end: End time in seconds
            audio_channels: 'mono', 'stereo', or None
            use_gpu: Use GPU acceleration if available
            codec_copy: Use codec copy (faster but less precise)
        """
        duration = end - start
        
        cmd = [
            self.ffmpeg_path,
            '-y',  # Overwrite
            '-ss', str(start),  # Seek to start
            '-i', input_path,
            '-t', str(duration),  # Duration
        ]
        
        # Video encoding
        if codec_copy:
            cmd.extend(['-c:v', 'copy'])
        elif use_gpu and self.gpu_available['nvenc']:
            cmd.extend(['-c:v', 'h264_nvenc', '-preset', 'fast'])
        elif use_gpu and self.gpu_available['qsv']:
            cmd.extend(['-c:v', 'h264_qsv', '-preset', 'fast'])
        elif use_gpu and self.gpu_available['videotoolbox']:
            cmd.extend(['-c:v', 'h264_videotoolbox'])
        else:
            cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '23'])
        
        # Audio encoding
        if audio_channels == 'mono':
            cmd.extend(['-ac', '1', '-c:a', 'aac', '-b:a', '128k'])
        elif audio_channels == 'stereo':
            cmd.extend(['-ac', '2', '-c:a', 'aac', '-b:a', '192k'])
        elif codec_copy:
            cmd.extend(['-c:a', 'copy'])
        else:
            cmd.extend(['-c:a', 'aac', '-b:a', '192k'])
        
        # Additional options
        cmd.extend([
            '-avoid_negative_ts', '1',
            '-max_muxing_queue_size', '1024',
            output_path
        ])
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Extraction timed out (600s limit)")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed: {e.stderr.decode()}")
    
    def extract_audio(
        self,
        input_path: str,
        output_path: str,
        start: float,
        end: float,
        audio_channels: Optional[str] = None,
        quality: int = 2
    ) -> None:
        """Extract audio as MP3"""
        duration = end - start
        
        cmd = [
            self.ffmpeg_path,
            '-y',
            '-ss', str(start),
            '-i', input_path,
            '-t', str(duration),
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-q:a', str(quality)  # 0-9, lower is better
        ]
        
        if audio_channels == 'mono':
            cmd.extend(['-ac', '1'])
        elif audio_channels == 'stereo':
            cmd.extend(['-ac', '2'])
        
        cmd.append(output_path)
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}")
    
    def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        time_position: float,
        width: int = 320,
        height: int = 180
    ) -> bool:
        """Generate thumbnail at specific timestamp"""
        cmd = [
            self.ffmpeg_path,
            '-y',
            '-ss', str(time_position),
            '-i', video_path,
            '-vframes', '1',
            '-s', f'{width}x{height}',
            '-f', 'image2',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            return True
        except:
            return False
    
    def generate_waveform(
        self,
        video_path: str,
        output_path: str,
        width: int = 1200,
        height: int = 100
    ) -> bool:
        """Generate waveform visualization"""
        cmd = [
            self.ffmpeg_path,
            '-i', video_path,
            '-filter_complex',
            f'showwavespic=s={width}x{height}:colors=009682',
            '-frames:v', '1',
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return True
        except:
            return False