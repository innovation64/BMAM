"""
Data Models for Prefrontal Agent
工作记忆数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class WorkingMemoryItem:
    """工作记忆项"""
    id: str
    content: str
    timestamp: datetime
    task_type: str = "general"  # task type: 'reasoning', 'conversation', 'calculation', etc.
    priority: int = 0  # 优先级 (0-10)
    metadata: Dict[str, Any] = field(default_factory=dict)
