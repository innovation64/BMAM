"""
Reflection Data Models
反思数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional

@dataclass
class ReflectionTrigger:
    """反思触发器"""
    trigger_type: str  # 'error', 'milestone', 'scheduled', 'threshold'
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    priority: float = 0.5

@dataclass
class PerformanceMetrics:
    """性能指标"""
    accuracy: float = 0.0
    response_time: float = 0.0
    error_rate: float = 0.0
    user_satisfaction: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Insight:
    """洞察"""
    insight_id: str
    insight_type: str  # 'pattern', 'bias', 'opportunity', 'risk'
    content: str
    confidence: float
    actionable: bool
    recommendations: List[str] = field(default_factory=list)
    evidence: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ReflectionCycle:
    """反思周期"""
    cycle_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    triggers: List[ReflectionTrigger] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)

# 反思配置
REFLECTION_CONFIG = {
    'frequency': {
        'error_threshold': 3,      # 错误达到3次触发反思
        'time_interval': 3600,     # 每小时定期反思
        'milestone_tasks': 10      # 每完成10个任务反思
    },
    'depth': {
        'shallow': 0.3,  # 快速反思
        'medium': 0.6,   # 中等深度
        'deep': 1.0      # 深度反思
    },
    'reflection_levels': {
        'surface': 'Immediate observations and facts',
        'analytical': 'Relationships and connections',
        'critical': 'Evaluation and judgment',
        'metacognitive': 'Thinking about thinking',
        'transformative': 'Paradigm shifts and deep insights'
    }
}
