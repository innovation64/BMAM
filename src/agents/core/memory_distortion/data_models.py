"""
Memory Distortion Data Models
记忆扭曲数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any
from enum import Enum


class DistortionType(Enum):
    """扭曲类型"""
    RECONSTRUCTION = "reconstruction"     # 重构错误
    SOURCE_CONFUSION = "source_confusion" # 来源混淆
    FALSE_MEMORY = "false_memory"         # 虚假记忆
    SCHEMA_DISTORTION = "schema"          # Schema影响
    EMOTIONAL_BIAS = "emotional"          # 情绪偏差
    TEMPORAL_SHIFT = "temporal"           # 时间位移


@dataclass
class DistortionIndicator:
    """扭曲指标"""
    indicator_type: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    severity: float = 0.0  # 0-1


@dataclass
class DistortionReport:
    """扭曲报告"""
    memory_id: str
    distortion_detected: bool
    distortion_types: List[DistortionType] = field(default_factory=list)
    indicators: List[DistortionIndicator] = field(default_factory=list)
    reliability_score: float = 1.0  # 1.0 = 完全可靠
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# 扭曲检测阈值
DISTORTION_THRESHOLDS = {
    'reconstruction_count': 3,     # 重构次数
    'age_days': 30,                # 记忆年龄
    'source_reliability': 0.5,     # 来源可靠性
    'emotional_intensity': 0.7     # 情绪强度
}
