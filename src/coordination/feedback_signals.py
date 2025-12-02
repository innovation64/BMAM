"""
Consolidation Feedback Signals - 巩固反馈信号

类脑原理:
- 模拟神经调质信号（如多巴胺、乙酰胆碱）
- 不直接指定"怎么做"，而是传递"什么需要注意"
- 下游 Agent 根据信号自主决策

设计原则:
- 无硬编码：不写死具体的提取规则
- 多智能体协作：通过消息传递，不直接函数调用
- 自适应：紧迫度和阈值根据历史效果调整

Reference: BMAM_FEEDBACK_LOOP_DESIGN.md Section 3.2
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """
    反馈类型枚举

    类脑映射:
    - RECONSOLIDATE: 类似睡眠时的记忆重播，需要重新提取和强化
    - INCREASE_COVERAGE: 类似注意力分配，需要更广泛的编码
    - REFINE_EXTRACTION: 类似精细加工，需要更深入的分析
    - NO_ACTION: 当前状态良好，无需干预
    """
    RECONSOLIDATE = "reconsolidate"      # 需要重新巩固（检索多但质量差）
    INCREASE_COVERAGE = "coverage"        # 需要增加覆盖率（检索少）
    REFINE_EXTRACTION = "refine"          # 需要精细化提取（部分正确）
    NO_ACTION = "none"                    # 无需行动


class UrgencyLevel(Enum):
    """
    紧迫度级别

    类脑映射:
    - CRITICAL: 类似杏仁核的高度警觉状态
    - HIGH: 类似前扣带回的冲突检测
    - MEDIUM: 类似基底神经节的习惯性处理
    - LOW: 类似默认模式网络的背景处理
    """
    CRITICAL = "critical"  # 紧急：反复失败的核心实体
    HIGH = "high"          # 高：单次失败但重要
    MEDIUM = "medium"      # 中：可延迟处理
    LOW = "low"            # 低：后台优化


@dataclass
class ConsolidationFeedbackSignal:
    """
    巩固反馈信号

    类脑原理:
    - 模拟神经调质信号（如多巴胺、乙酰胆碱）
    - 不直接指定"怎么做"，而是传递"什么需要注意"
    - 下游 Agent 根据信号自主决策

    设计要点:
    1. feedback_type: 告诉下游"发生了什么类型的问题"
    2. query_entities: 告诉下游"哪些实体相关"
    3. missing_fact_hints: 提供"可能缺失什么"的提示（由 LLM 推断，不硬编码）
    4. urgency: 告诉下游"有多紧急"（基于历史失败率，不硬编码阈值）

    使用示例:
        signal = ConsolidationFeedbackSignal(
            feedback_type=FeedbackType.RECONSOLIDATE,
            failed_query="What is Person's identity?",
            query_entities=["Person"],
            missing_fact_hints=["identity", "is_a"],
            urgency=0.8
        )
        await consolidation_manager.receive_feedback(signal)
    """

    # === 核心信息 ===
    feedback_type: FeedbackType
    failed_query: str
    query_entities: List[str]

    # === 提示信息（不是硬编码规则，是 hints）===
    missing_fact_hints: List[str] = field(default_factory=list)

    # === 上下文信息 ===
    retrieval_count: int = 0           # 检索到的记忆数量
    acc_confidence: float = 0.0        # ACC 评估的置信度
    quality_gap: float = 0.0           # 质量差距（期望置信度 - 实际置信度）

    # === 紧迫度和时间 ===
    urgency: float = 0.5               # 紧迫度 0-1
    urgency_level: UrgencyLevel = UrgencyLevel.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)

    # === 可选：相关记忆 ID（如果已知）===
    related_memory_ids: List[str] = field(default_factory=list)

    # === 元数据 ===
    source_agent: str = "memory_quality_monitor"  # 信号来源
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理：计算紧迫度级别"""
        if self.urgency >= 0.8:
            self.urgency_level = UrgencyLevel.CRITICAL
        elif self.urgency >= 0.6:
            self.urgency_level = UrgencyLevel.HIGH
        elif self.urgency >= 0.3:
            self.urgency_level = UrgencyLevel.MEDIUM
        else:
            self.urgency_level = UrgencyLevel.LOW

    def to_agent_message(self) -> Dict[str, Any]:
        """
        转换为 Agent 消息格式

        用于多智能体间的消息传递
        """
        return {
            'message_type': 'consolidation_feedback',
            'sender': self.source_agent,
            'content': {
                'feedback_type': self.feedback_type.value,
                'failed_query': self.failed_query,
                'query_entities': self.query_entities,
                'missing_fact_hints': self.missing_fact_hints,
                'urgency': self.urgency,
                'urgency_level': self.urgency_level.value,
                'context': {
                    'retrieval_count': self.retrieval_count,
                    'acc_confidence': self.acc_confidence,
                    'quality_gap': self.quality_gap
                },
                'related_memory_ids': self.related_memory_ids,
                'metadata': self.metadata
            },
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_agent_message(cls, message: Dict[str, Any]) -> 'ConsolidationFeedbackSignal':
        """
        从 Agent 消息格式恢复

        用于接收端解析消息
        """
        content = message.get('content', {})
        context = content.get('context', {})

        return cls(
            feedback_type=FeedbackType(content.get('feedback_type', 'none')),
            failed_query=content.get('failed_query', ''),
            query_entities=content.get('query_entities', []),
            missing_fact_hints=content.get('missing_fact_hints', []),
            urgency=content.get('urgency', 0.5),
            retrieval_count=context.get('retrieval_count', 0),
            acc_confidence=context.get('acc_confidence', 0.0),
            quality_gap=context.get('quality_gap', 0.0),
            related_memory_ids=content.get('related_memory_ids', []),
            source_agent=message.get('sender', 'unknown'),
            metadata=content.get('metadata', {}),
            timestamp=datetime.fromisoformat(message.get('timestamp', datetime.now().isoformat()))
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于日志和持久化）"""
        return {
            'feedback_type': self.feedback_type.value,
            'failed_query': self.failed_query,
            'query_entities': self.query_entities,
            'missing_fact_hints': self.missing_fact_hints,
            'retrieval_count': self.retrieval_count,
            'acc_confidence': self.acc_confidence,
            'quality_gap': self.quality_gap,
            'urgency': self.urgency,
            'urgency_level': self.urgency_level.value,
            'related_memory_ids': self.related_memory_ids,
            'source_agent': self.source_agent,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsolidationFeedbackSignal':
        """从字典格式恢复"""
        return cls(
            feedback_type=FeedbackType(data.get('feedback_type', 'none')),
            failed_query=data.get('failed_query', ''),
            query_entities=data.get('query_entities', []),
            missing_fact_hints=data.get('missing_fact_hints', []),
            retrieval_count=data.get('retrieval_count', 0),
            acc_confidence=data.get('acc_confidence', 0.0),
            quality_gap=data.get('quality_gap', 0.0),
            urgency=data.get('urgency', 0.5),
            related_memory_ids=data.get('related_memory_ids', []),
            source_agent=data.get('source_agent', 'unknown'),
            metadata=data.get('metadata', {}),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.now().isoformat()))
        )

    def __repr__(self) -> str:
        return (
            f"ConsolidationFeedbackSignal("
            f"type={self.feedback_type.value}, "
            f"entities={self.query_entities}, "
            f"urgency={self.urgency:.2f}/{self.urgency_level.value})"
        )


@dataclass
class FeedbackBatch:
    """
    反馈批次

    用于批量处理多个反馈信号，模拟睡眠时的批量记忆巩固
    """
    signals: List[ConsolidationFeedbackSignal] = field(default_factory=list)
    batch_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    created_at: datetime = field(default_factory=datetime.now)

    def add_signal(self, signal: ConsolidationFeedbackSignal):
        """添加信号到批次"""
        self.signals.append(signal)
        # 按紧迫度排序（高优先）
        self.signals.sort(key=lambda s: s.urgency, reverse=True)

    def get_top_urgent(self, n: int = 5) -> List[ConsolidationFeedbackSignal]:
        """获取最紧迫的 N 个信号"""
        return self.signals[:n]

    def get_by_entity(self, entity: str) -> List[ConsolidationFeedbackSignal]:
        """获取与特定实体相关的信号"""
        return [s for s in self.signals if entity in s.query_entities]

    def get_by_type(self, feedback_type: FeedbackType) -> List[ConsolidationFeedbackSignal]:
        """获取特定类型的信号"""
        return [s for s in self.signals if s.feedback_type == feedback_type]

    @property
    def size(self) -> int:
        return len(self.signals)

    @property
    def avg_urgency(self) -> float:
        if not self.signals:
            return 0.0
        return sum(s.urgency for s in self.signals) / len(self.signals)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'batch_id': self.batch_id,
            'created_at': self.created_at.isoformat(),
            'size': self.size,
            'avg_urgency': self.avg_urgency,
            'signals': [s.to_dict() for s in self.signals]
        }


class FeedbackHistory:
    """
    反馈历史记录

    用于：
    1. 自适应阈值调整（根据历史效果）
    2. 重复失败检测（同一实体反复失败 = 高紧迫度）
    3. 效果评估（反馈后准确率是否提升）
    """

    def __init__(self, max_history: int = 1000):
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.entity_failure_count: Dict[str, int] = {}  # 实体失败计数

    def record(self, signal: ConsolidationFeedbackSignal, result: Optional[Dict[str, Any]] = None):
        """
        记录反馈信号和处理结果

        Args:
            signal: 反馈信号
            result: 处理结果（可选，用于效果评估）
        """
        record = {
            'signal': signal.to_dict(),
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        self.history.append(record)

        # 更新实体失败计数
        for entity in signal.query_entities:
            self.entity_failure_count[entity] = self.entity_failure_count.get(entity, 0) + 1

        # 限制历史大小
        if len(self.history) > self.max_history:
            # 移除最旧的记录，同时更新实体计数
            oldest = self.history.pop(0)
            for entity in oldest['signal'].get('query_entities', []):
                if entity in self.entity_failure_count:
                    self.entity_failure_count[entity] = max(0, self.entity_failure_count[entity] - 1)

    def get_entity_failure_rate(self, entity: str, recent_n: int = 50) -> float:
        """
        获取实体的近期失败率

        用于计算紧迫度：反复失败的实体应该有更高的紧迫度
        """
        recent = self.history[-recent_n:] if len(self.history) >= recent_n else self.history
        total = sum(1 for r in recent if entity in r['signal'].get('query_entities', []))
        return total / recent_n if recent_n > 0 else 0.0

    def get_recent_signals(self, n: int = 20) -> List[ConsolidationFeedbackSignal]:
        """获取最近的 N 个信号"""
        recent = self.history[-n:]
        return [ConsolidationFeedbackSignal.from_dict(r['signal']) for r in recent]

    def get_success_rate(self, recent_n: int = 50) -> float:
        """
        获取近期处理成功率

        用于自适应阈值调整：成功率低时应该更敏感
        """
        recent = self.history[-recent_n:] if len(self.history) >= recent_n else self.history
        if not recent:
            return 0.0

        successful = sum(1 for r in recent if r.get('result', {}).get('success', False))
        return successful / len(recent)

    def calculate_adaptive_urgency(self, query_entities: List[str], base_urgency: float) -> float:
        """
        计算自适应紧迫度

        基于历史失败率调整紧迫度，不硬编码

        Args:
            query_entities: 查询涉及的实体
            base_urgency: 基础紧迫度（来自质量差距）

        Returns:
            调整后的紧迫度
        """
        # 检查实体的历史失败次数
        max_failure_boost = 0.0
        for entity in query_entities:
            failure_rate = self.get_entity_failure_rate(entity)
            # 失败率越高，紧迫度提升越大
            failure_boost = min(0.3, failure_rate * 0.5)
            max_failure_boost = max(max_failure_boost, failure_boost)

        # 综合计算
        adjusted_urgency = min(1.0, base_urgency + max_failure_boost)

        logger.debug(f"Adaptive urgency: base={base_urgency:.2f}, "
                    f"failure_boost={max_failure_boost:.2f}, "
                    f"final={adjusted_urgency:.2f}")

        return adjusted_urgency

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于持久化）"""
        return {
            'history': self.history,
            'entity_failure_count': self.entity_failure_count,
            'max_history': self.max_history
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackHistory':
        """从字典格式恢复"""
        instance = cls(max_history=data.get('max_history', 1000))
        instance.history = data.get('history', [])
        instance.entity_failure_count = data.get('entity_failure_count', {})
        return instance
