"""
Data models for Temporal Lobe Agent
颞叶智能体数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple


class MemoryType(Enum):
    """
    阶段1: 五类语义记忆类型
    用于模拟人脑多层记忆加工（而非单纯存原文）
    """
    FACTUAL = "factual"           # 客观事实陈述: "Person attended a support group"
    RELATIONAL = "relational"     # 实体关系: "Person -> interested_in -> topic"
    TEMPORAL = "temporal"         # 时间线事件: "2023-05-08: Person visited an event"
    PROCEDURAL = "procedural"     # 过程/行动: "How Person researched a process"
    SUMMARY = "summary"           # 高层摘要: "Person's journey through events"


@dataclass
class SemanticMemory:
    """语义记忆项"""
    id: str
    content: str
    memory_subtype: str  # 'semantic' or 'common_sense'
    timestamp: datetime  # 学习时间 (when I learned this)
    entities: List[str] = field(default_factory=list)
    relations: List[Tuple[str, str, str]] = field(default_factory=list)  # [(source, relation, target)]
    importance: float = 0.5
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    consolidation_level: int = 1  # 巩固级别 (越高越不容易忘记)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 🔥 NEW: 区分学习时间 vs 事件时间
    event_time: Optional[datetime] = None  # 事件发生时间 (when the event happened)
    # 🔥 优先级2: Embedding缓存（避免重复调用远程服务）
    embedding: Optional[List[float]] = None  # 缓存的embedding向量
    # 🔥 阶段1: 记忆类型分类（factual/relational/temporal/procedural/summary）
    memory_type: Optional[MemoryType] = None  # 记忆类型，用于类型过滤检索
