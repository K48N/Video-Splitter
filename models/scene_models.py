"""Models for scene detection and classification"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SceneMetadata:
    """Metadata for detected scene"""
    start_time: float
    end_time: float
    confidence: float
    labels: List[str]  # Scene content labels
    shot_type: str     # e.g. 'wide', 'medium', 'close-up'
    action_score: float  # 0-1 score for action content
    dialog_score: float  # 0-1 score for dialog content
    
    @property
    def duration(self) -> float:
        """Scene duration in seconds"""
        return self.end_time - self.start_time
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'confidence': self.confidence,
            'labels': self.labels,
            'shot_type': self.shot_type,
            'action_score': self.action_score,
            'dialog_score': self.dialog_score
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SceneMetadata':
        """Create from dictionary"""
        return cls(
            start_time=data['start_time'],
            end_time=data['end_time'],
            confidence=data['confidence'],
            labels=data['labels'],
            shot_type=data['shot_type'],
            action_score=data['action_score'],
            dialog_score=data['dialog_score']
        )