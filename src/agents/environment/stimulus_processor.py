"""
Environment Stimulus Processor
环境刺激处理器

P6: 深度集成环境刺激输入节点

功能:
1. 多模态刺激输入 (文本、图像、音频、触觉)
2. 刺激强度评估
3. 注意力调制 (显著性检测)
4. 情境感知 (Context-aware processing)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class StimulusModality(Enum):
    """刺激模态"""
    TEXT = "text"              # 文本
    IMAGE = "image"            # 图像
    AUDIO = "audio"            # 音频
    TACTILE = "tactile"        # 触觉
    MULTIMODAL = "multimodal"  # 多模态


class StimulusSaliency(Enum):
    """刺激显著性"""
    VERY_HIGH = "very_high"  # 非常显著 (紧急、重要)
    HIGH = "high"            # 高显著性
    MEDIUM = "medium"        # 中等
    LOW = "low"              # 低显著性
    VERY_LOW = "very_low"    # 非常低


@dataclass
class EnvironmentStimulus:
    """环境刺激"""
    stimulus_id: str
    modality: StimulusModality
    content: Any  # 刺激内容 (文本、图像数据等)
    intensity: float  # 强度 (0.0-1.0)
    saliency: StimulusSaliency  # 显著性
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"  # 刺激来源
    metadata: Dict[str, Any] = field(default_factory=dict)


class StimulusProcessor:
    """
    环境刺激处理器

    模拟大脑对环境刺激的处理:
    - Thalamus (丘脑): 初步过滤和路由
    - Attention (注意力): 显著性检测
    - Sensory Cortex (感觉皮层): 模态处理
    """

    def __init__(self):
        self.processed_stimuli = []
        self.attention_threshold = 0.3  # 注意力阈值
        self.saliency_weights = {
            'novelty': 0.3,      # 新颖性
            'intensity': 0.25,   # 强度
            'relevance': 0.25,   # 相关性
            'emotional': 0.2     # 情绪唤醒
        }


    def process_stimulus(
        self,
        content: Any,
        modality: StimulusModality = StimulusModality.TEXT,
        context: Dict[str, Any] = None
    ) -> EnvironmentStimulus:
        """
        处理环境刺激

        Args:
            content: 刺激内容
            modality: 刺激模态
            context: 上下文

        Returns:
            处理后的刺激对象
        """
        import uuid

        # 评估刺激强度
        intensity = self._evaluate_intensity(content, modality, context)

        # 计算显著性
        saliency = self._compute_saliency(content, modality, intensity, context)

        # 创建刺激对象
        stimulus = EnvironmentStimulus(
            stimulus_id=uuid.uuid4().hex[:12],
            modality=modality,
            content=content,
            intensity=intensity,
            saliency=saliency,
            timestamp=datetime.now(),
            context=context or {},
            source=context.get('source', 'unknown') if context else 'unknown'
        )

        # 记录
        self.processed_stimuli.append(stimulus)


        return stimulus

    def _evaluate_intensity(
        self,
        content: Any,
        modality: StimulusModality,
        context: Optional[Dict[str, Any]]
    ) -> float:
        """
        评估刺激强度

        Args:
            content: 刺激内容
            modality: 模态
            context: 上下文

        Returns:
            强度值 (0.0-1.0)
        """
        intensity = 0.5  # 默认中等强度

        if modality == StimulusModality.TEXT:
            # 文本强度: 基于长度、情绪词、紧急关键词
            if isinstance(content, str):
                # 长度因子
                length_factor = min(len(content) / 200.0, 1.0)

                # 紧急关键词
                urgent_keywords = ['urgent', 'important', 'critical', 'emergency', '紧急', '重要']
                has_urgent = any(kw in content.lower() for kw in urgent_keywords)
                urgency_factor = 0.3 if has_urgent else 0

                # 情绪词
                emotional_keywords = ['love', 'hate', 'angry', 'excited', 'sad', '喜欢', '讨厌', '兴奋']
                has_emotion = any(kw in content.lower() for kw in emotional_keywords)
                emotion_factor = 0.2 if has_emotion else 0

                intensity = min(0.3 + length_factor * 0.2 + urgency_factor + emotion_factor, 1.0)

        elif modality == StimulusModality.IMAGE:
            # 图像强度: 基于对比度、颜色饱和度等 (简化实现)
            intensity = context.get('image_intensity', 0.6) if context else 0.6

        elif modality == StimulusModality.AUDIO:
            # 音频强度: 基于音量、音调变化
            intensity = context.get('audio_volume', 0.5) if context else 0.5

        return round(intensity, 3)

    def _compute_saliency(
        self,
        content: Any,
        modality: StimulusModality,
        intensity: float,
        context: Optional[Dict[str, Any]]
    ) -> StimulusSaliency:
        """
        计算刺激显著性

        基于:
        - Novelty (新颖性): 是否是新信息
        - Intensity (强度): 刺激强度
        - Relevance (相关性): 与当前任务的相关性
        - Emotional (情绪): 情绪唤醒程度

        Returns:
            显著性等级
        """
        scores = {}

        # 1. 新颖性 (简化: 基于内容是否重复)
        # 实际实现可以比对历史刺激
        novelty = 0.7  # 默认较新
        if context and context.get('is_repeated', False):
            novelty = 0.3
        scores['novelty'] = novelty

        # 2. 强度
        scores['intensity'] = intensity

        # 3. 相关性 (简化: 基于context中的task_relevant标记)
        relevance = 0.5  # 默认中等相关
        if context:
            if context.get('task_relevant', False):
                relevance = 0.9
            elif context.get('task_irrelevant', False):
                relevance = 0.1
        scores['relevance'] = relevance

        # 4. 情绪唤醒 (基于内容分析)
        emotional = 0.3  # 默认低情绪
        if modality == StimulusModality.TEXT and isinstance(content, str):
            emotional_keywords = ['love', 'hate', 'angry', 'excited', 'sad', 'fear']
            if any(kw in content.lower() for kw in emotional_keywords):
                emotional = 0.8
        scores['emotional'] = emotional

        # 加权综合
        total_saliency = sum(
            scores[key] * self.saliency_weights[key]
            for key in scores
        )

        # 映射到等级
        if total_saliency >= 0.8:
            return StimulusSaliency.VERY_HIGH
        elif total_saliency >= 0.6:
            return StimulusSaliency.HIGH
        elif total_saliency >= 0.4:
            return StimulusSaliency.MEDIUM
        elif total_saliency >= 0.2:
            return StimulusSaliency.LOW
        else:
            return StimulusSaliency.VERY_LOW

    def filter_by_attention(
        self,
        stimuli: List[EnvironmentStimulus]
    ) -> List[EnvironmentStimulus]:
        """
        基于注意力机制过滤刺激

        模拟注意力的选择性：只处理显著性高的刺激

        Args:
            stimuli: 刺激列表

        Returns:
            通过注意力过滤的刺激
        """
        attended = []

        for stimulus in stimuli:
            # 高显著性的刺激自动通过
            if stimulus.saliency in [StimulusSaliency.VERY_HIGH, StimulusSaliency.HIGH]:
                attended.append(stimulus)
            # 中等显著性 + 高强度也通过
            elif stimulus.saliency == StimulusSaliency.MEDIUM and stimulus.intensity >= 0.6:
                attended.append(stimulus)
            # 低显著性但强度极高 (如突然的巨响)
            elif stimulus.intensity >= 0.9:
                attended.append(stimulus)


        return attended

    def get_recent_stimuli(
        self,
        time_window_seconds: int = 60,
        modality: Optional[StimulusModality] = None
    ) -> List[EnvironmentStimulus]:
        """
        获取最近的刺激

        Args:
            time_window_seconds: 时间窗口（秒）
            modality: 模态过滤

        Returns:
            最近的刺激列表
        """
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(seconds=time_window_seconds)

        recent = [
            s for s in self.processed_stimuli
            if s.timestamp >= cutoff_time
        ]

        if modality:
            recent = [s for s in recent if s.modality == modality]

        return recent

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.processed_stimuli:
            return {
                'total_stimuli': 0,
                'by_modality': {},
                'by_saliency': {}
            }

        by_modality = {}
        by_saliency = {}

        for s in self.processed_stimuli:
            by_modality[s.modality.value] = by_modality.get(s.modality.value, 0) + 1
            by_saliency[s.saliency.value] = by_saliency.get(s.saliency.value, 0) + 1

        avg_intensity = sum(s.intensity for s in self.processed_stimuli) / len(self.processed_stimuli)

        return {
            'total_stimuli': len(self.processed_stimuli),
            'by_modality': by_modality,
            'by_saliency': by_saliency,
            'average_intensity': round(avg_intensity, 3)
        }


class ContextualEnvironmentIntegrator:
    """
    情境化环境集成器

    将环境刺激与系统状态结合，生成情境化的输入
    """

    def __init__(self, stimulus_processor: StimulusProcessor):
        self.stimulus_processor = stimulus_processor
        self.current_context = {}

    def update_context(self, context_updates: Dict[str, Any]):
        """更新当前情境"""
        self.current_context.update(context_updates)

    def integrate_stimulus_with_context(
        self,
        stimulus: EnvironmentStimulus
    ) -> Dict[str, Any]:
        """
        将刺激与情境结合

        Args:
            stimulus: 环境刺激

        Returns:
            情境化的输入
        """
        integrated = {
            'stimulus': {
                'id': stimulus.stimulus_id,
                'modality': stimulus.modality.value,
                'content': stimulus.content,
                'intensity': stimulus.intensity,
                'saliency': stimulus.saliency.value,
                'timestamp': stimulus.timestamp.isoformat()
            },
            'context': {
                **self.current_context,
                **stimulus.context
            },
            'integration_metadata': {
                'processing_time': datetime.now().isoformat(),
                'attention_required': stimulus.saliency in [
                    StimulusSaliency.VERY_HIGH,
                    StimulusSaliency.HIGH
                ],
                'priority': self._calculate_priority(stimulus)
            }
        }

        return integrated

    def _calculate_priority(self, stimulus: EnvironmentStimulus) -> str:
        """计算处理优先级"""
        if stimulus.saliency == StimulusSaliency.VERY_HIGH or stimulus.intensity >= 0.9:
            return 'urgent'
        elif stimulus.saliency == StimulusSaliency.HIGH:
            return 'high'
        elif stimulus.saliency == StimulusSaliency.MEDIUM:
            return 'normal'
        else:
            return 'low'


# ============================================================
# Singleton Pattern with Thread Safety
# ============================================================
import threading

class StimulusProcessingSingletons:
    """
    Thread-safe singletons for stimulus processing components

    Pattern: Singleton with lazy initialization and thread safety
    Why: Stateful services that track stimulus history and context
    """
    _stimulus_processor: Optional['StimulusProcessor'] = None
    _contextual_integrator: Optional['ContextualEnvironmentIntegrator'] = None
    _lock = threading.Lock()

    @classmethod
    def get_stimulus_processor(cls) -> 'StimulusProcessor':
        """获取刺激处理器单例 (thread-safe)"""
        if cls._stimulus_processor is None:
            with cls._lock:
                if cls._stimulus_processor is None:
                    cls._stimulus_processor = StimulusProcessor()
        return cls._stimulus_processor

    @classmethod
    def get_contextual_integrator(cls) -> 'ContextualEnvironmentIntegrator':
        """获取情境集成器单例 (thread-safe)"""
        if cls._contextual_integrator is None:
            with cls._lock:
                if cls._contextual_integrator is None:
                    cls._contextual_integrator = ContextualEnvironmentIntegrator(
                        cls.get_stimulus_processor()
                    )
        return cls._contextual_integrator

    @classmethod
    def reset_all(cls):
        """Reset all singletons (mainly for testing)"""
        with cls._lock:
            cls._stimulus_processor = None
            cls._contextual_integrator = None


# Backward-compatible factory functions
def get_stimulus_processor() -> StimulusProcessor:
    """获取刺激处理器单例 (backward compatible)"""
    return StimulusProcessingSingletons.get_stimulus_processor()


def get_contextual_integrator() -> ContextualEnvironmentIntegrator:
    """获取情境集成器单例 (backward compatible)"""
    return StimulusProcessingSingletons.get_contextual_integrator()
