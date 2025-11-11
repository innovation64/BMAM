"""
Consolidation Data Models
记忆巩固数据模型和配置
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any
from enum import Enum


class ConsolidationStage(Enum):
    """巩固阶段"""
    INITIAL = "initial"           # 初始编码
    EARLY = "early"               # 早期巩固 (0-6小时)
    LATE = "late"                 # 晚期巩固 (6-24小时)
    SYSTEMS = "systems"           # 系统巩固 (>24小时)


@dataclass
class ConsolidationJob:
    """巩固任务"""
    memory_id: str
    memory_type: str
    priority: float
    stage: ConsolidationStage
    rehearsal_count: int = 0
    interference_score: float = 0.0
    last_consolidated: datetime = field(default_factory=datetime.now)


@dataclass
class ConsolidationResult:
    """巩固结果"""
    memory_id: str
    success: bool
    strength_before: float
    strength_after: float
    operations_performed: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


# 巩固配置
CONSOLIDATION_CONFIG = {
    'rehearsal': {
        'min_interval': 300,      # 最小复述间隔（秒）
        'max_rehearsals': 5,      # 最大复述次数
        'spacing_factor': 2.0     # 间隔递增因子
    },
    'strength': {
        'initial': 0.3,           # 初始强度
        'rehearsal_boost': 0.15,  # 每次复述增加
        'decay_rate': 0.05        # 衰减率
    },
    'consolidation': {
        'threshold': 0.6,         # 巩固阈值
        'replay_capacity': 50,    # 重播缓冲区容量
        'batch_size': 10          # 批处理大小
    }
}
