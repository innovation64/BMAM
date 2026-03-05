"""
Memory Item Data Structure
记忆项数据结构
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np
import uuid


@dataclass
class MemoryItem:
    """Enhanced memory item with brain-inspired attributes"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    memory_type: str = "episodic"  # episodic, semantic, procedural, working
    importance: float = 0.5
    emotion_tags: List[str] = field(default_factory=list)
    emotion_intensity: float = 0.5
    
    # Brain-inspired attributes
    brain_region: str = "hippocampus"  # hippocampus, neocortex, amygdala, prefrontal
    consolidation_level: int = 0  # 0=new, 1=weak, 2=strong, 3=permanent
    access_frequency: int = 0
    decay_rate: float = 0.1
    stress_marker: bool = False
    
    # Temporal attributes
    timestamp: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    last_consolidated: Optional[datetime] = None
    
    # Network attributes
    associations: List[str] = field(default_factory=list)  # IDs of associated memories
    source_reliability: float = 1.0  # For memory distortion tracking
    
    # Context
    context_tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Vector representation
    embedding: Optional[np.ndarray] = None
    embedding_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Handle numpy array
        if self.embedding is not None:
            data['embedding'] = self.embedding.tolist()
        # Handle datetime objects
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        if self.last_accessed:
            data['last_accessed'] = self.last_accessed.isoformat()
        if self.last_consolidated:
            data['last_consolidated'] = self.last_consolidated.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryItem':
        if 'timestamp' in data and isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if 'last_accessed' in data and data['last_accessed'] and isinstance(data['last_accessed'], str):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        if 'last_consolidated' in data and data['last_consolidated'] and isinstance(data['last_consolidated'], str):
            data['last_consolidated'] = datetime.fromisoformat(data['last_consolidated'])
        if 'embedding' in data and isinstance(data['embedding'], list):
            data['embedding'] = np.array(data['embedding'])
        return cls(**data)