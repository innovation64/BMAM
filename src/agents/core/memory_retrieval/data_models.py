"""
Memory Retrieval Data Models
记忆检索数据模型
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class RetrievalStrategy(Enum):
    """检索策略枚举"""
    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    EPISODIC = "episodic"
    ASSOCIATIVE = "associative"
    PATTERN = "pattern"
    CONTEXTUAL = "contextual"
    MULTI = "multi"


@dataclass
class RetrievalRequest:
    """
    检索请求数据模型

    Attributes:
        query: 查询文本
        strategy: 检索策略
        k: 返回结果数量
        time_range: 时间范围过滤
        filters: 其他过滤条件
    """
    query: str
    strategy: str = "semantic"
    k: int = 10
    time_range: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'query': self.query,
            'strategy': self.strategy,
            'k': self.k,
            'time_range': self.time_range,
            'filters': self.filters
        }


@dataclass
class RetrievalResult:
    """
    检索结果数据模型

    Attributes:
        memories: 检索到的记忆列表
        strategy_used: 使用的检索策略
        total_count: 结果总数
        retrieval_time_ms: 检索耗时(毫秒)
        cache_hit: 是否命中缓存
        fallback_used: 是否使用了后备策略
    """
    memories: List[Dict[str, Any]]
    strategy_used: str
    total_count: int
    retrieval_time_ms: float = 0.0
    cache_hit: bool = False
    fallback_used: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'memories': self.memories,
            'strategy': self.strategy_used,
            'total_count': self.total_count,
            'retrieval_time_ms': self.retrieval_time_ms,
            'cache_hit': self.cache_hit,
            'fallback_used': self.fallback_used,
            'metadata': self.metadata
        }


@dataclass
class CacheKey:
    """
    缓存键数据模型

    用于生成唯一的缓存标识
    """
    strategy: str
    query: str
    params: Dict[str, Any] = field(default_factory=dict)

    def to_string(self) -> str:
        """
        转换为字符串键

        使用MD5哈希确保键的唯一性和长度固定
        """
        import hashlib
        import json

        # 排序参数确保一致性
        params_str = json.dumps(self.params, sort_keys=True)
        content = f"{self.strategy}_{self.query}_{params_str}"

        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class ConfidenceFactors:
    """
    置信度因子数据模型

    用于计算检索置信度的各项因子
    """
    similarity: float = 0.0
    importance: float = 0.0
    access_frequency: int = 0
    recency: float = 0.0
    consolidation_level: int = 0
    matched_cues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'similarity': self.similarity,
            'importance': self.importance,
            'access_frequency': self.access_frequency,
            'recency': self.recency,
            'consolidation_level': self.consolidation_level,
            'matched_cues': self.matched_cues
        }
