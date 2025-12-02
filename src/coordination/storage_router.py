"""
Storage Router - 存储路由层 + 记忆塑造循环
根据内容类型智能分流到对应脑区，支持完整的 CRUD 操作

路由规则:
- 情感/情绪 → Amygdala (跳过 embedding)
- 时序事件/情景 → Hippocampus (走 embedding + FAISS)
- 事实/属性/知识 → Temporal Lobe (直接 KG，可选 embedding)
- 短期上下文/工作记忆 → Prefrontal (跳过 embedding)
- 模式/习惯/技能 → Basal Ganglia (跳过 embedding)

记忆塑造循环:
- Create: store_memory_if_needed (按路由存储)
- Read: retrieve_with_routing (按类型检索)
- Update: reshape_memory (巩固/修改/关联)
- Delete: forget_memory (遗忘/衰减)
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import asyncio

from ..utils.config import get_logger

logger = get_logger(__name__)


class StorageTarget(Enum):
    """存储目标脑区"""
    HIPPOCAMPUS = "hippocampus"      # 情景记忆 - 需要 embedding
    TEMPORAL_LOBE = "temporal_lobe"  # 语义/KG - 结构化存储
    PREFRONTAL = "prefrontal"        # 工作记忆 - 短期缓存
    AMYGDALA = "amygdala"            # 情感标签 - 情绪处理
    BASAL_GANGLIA = "basal_ganglia"  # 习惯/模式 - 程序性记忆


@dataclass
class RoutingDecision:
    """路由决策结果"""
    primary_target: StorageTarget
    secondary_targets: List[StorageTarget]
    should_embed: bool
    should_extract_kg: bool
    confidence: float
    reasoning: str
    content_type: str  # 'episodic', 'semantic', 'emotional', 'procedural', 'working'


class StorageRouter:
    """
    存储路由器 - 在入口处判断内容类型，分流到正确的脑区

    设计原则:
    1. 轻量级规则优先 - 避免为路由引入额外 LLM 调用
    2. 可观测性 - 记录每条消息的路由决策
    3. 可配置 - 支持调整路由规则
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # 情感关键词 (中英文)
        self.emotion_keywords = {
            'positive': ['happy', 'love', 'excited', 'glad', 'joy', 'wonderful',
                        '开心', '高兴', '爱', '喜欢', '兴奋', '快乐', '幸福'],
            'negative': ['sad', 'angry', 'upset', 'hate', 'fear', 'worry', 'anxious',
                        '难过', '伤心', '生气', '愤怒', '害怕', '担心', '焦虑', '讨厌'],
            'neutral': ['feel', 'emotion', 'mood', '感觉', '情绪', '心情']
        }

        # 事实/知识关键词
        self.fact_keywords = [
            'is a', 'are', 'was', 'were', 'born', 'died', 'located', 'capital',
            'founder', 'invented', 'discovered', 'means', 'definition',
            '是', '叫做', '位于', '创始人', '发明', '定义', '意思是'
        ]

        # 时序/事件关键词
        self.temporal_keywords = [
            'yesterday', 'today', 'tomorrow', 'last week', 'next month',
            'remember when', 'that time', 'once', 'happened',
            '昨天', '今天', '明天', '上周', '下个月', '那次', '记得', '发生'
        ]

        # 习惯/模式关键词
        self.habit_keywords = [
            'always', 'usually', 'often', 'never', 'routine', 'habit',
            'prefer', 'like to', 'tend to',
            '总是', '通常', '经常', '从不', '习惯', '喜欢', '倾向'
        ]

        # 短期/上下文关键词
        self.context_keywords = [
            'just said', 'you mentioned', 'earlier', 'just now', 'current',
            '刚才', '你说的', '之前提到', '现在'
        ]

        # 统计
        self.routing_stats = {target: 0 for target in StorageTarget}

    def route(self, content: str, context: Optional[Dict[str, Any]] = None) -> RoutingDecision:
        """
        核心路由方法 - 根据内容特征决定存储目标

        Args:
            content: 要存储的内容
            context: 上下文信息 (可包含 importance, session_turn 等)

        Returns:
            RoutingDecision 包含主目标、次目标、是否需要 embedding 等
        """
        context = context or {}
        content_lower = content.lower()

        scores = {
            StorageTarget.AMYGDALA: 0.0,
            StorageTarget.HIPPOCAMPUS: 0.0,
            StorageTarget.TEMPORAL_LOBE: 0.0,
            StorageTarget.PREFRONTAL: 0.0,
            StorageTarget.BASAL_GANGLIA: 0.0,
        }

        # 0. 语义权重（由 SemanticRouter 提供，可选）
        semantic_weights = (context or {}).get('semantic_weights') or {}
        semantic_map = {
            StorageTarget.AMYGDALA: 'amygdala',
            StorageTarget.PREFRONTAL: 'prefrontal',
            StorageTarget.BASAL_GANGLIA: 'basal_ganglia',
            StorageTarget.HIPPOCAMPUS: 'hippocampus',
            StorageTarget.TEMPORAL_LOBE: 'temporal_lobe'
        }
        semantic_boost = {t: float(semantic_weights.get(name, 0.0)) for t, name in semantic_map.items()}

        # 1. 情感检测
        emotion_score = self._score_emotion(content_lower)
        scores[StorageTarget.AMYGDALA] = emotion_score + semantic_boost[StorageTarget.AMYGDALA] * 0.7

        # 2. 事实/知识检测
        fact_score = self._score_facts(content_lower)
        scores[StorageTarget.TEMPORAL_LOBE] = fact_score + semantic_boost[StorageTarget.TEMPORAL_LOBE] * 0.7

        # 3. 时序/事件检测
        temporal_score = self._score_temporal(content_lower)
        scores[StorageTarget.HIPPOCAMPUS] = temporal_score + semantic_boost[StorageTarget.HIPPOCAMPUS] * 0.7

        # 4. 习惯/模式检测
        habit_score = self._score_habits(content_lower)
        scores[StorageTarget.BASAL_GANGLIA] = habit_score + semantic_boost[StorageTarget.BASAL_GANGLIA] * 0.7

        # 5. 短期上下文检测
        context_score = self._score_context(content_lower, context)
        scores[StorageTarget.PREFRONTAL] = context_score + semantic_boost[StorageTarget.PREFRONTAL] * 0.7

        # 基础分: 默认给 Hippocampus 一个底分 (情景记忆是默认)
        # 🔥 降低底分，让其他脑区有机会成为主目标
        scores[StorageTarget.HIPPOCAMPUS] += 0.15

        # 排序找主目标和次目标
        sorted_targets = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_targets[0][0]
        primary_score = sorted_targets[0][1]

        # 次目标: 分数 > 0.3 的其他目标
        secondary = [t for t, s in sorted_targets[1:] if s > 0.3]

        # 决定是否需要 embedding
        should_embed = primary in [StorageTarget.HIPPOCAMPUS, StorageTarget.TEMPORAL_LOBE]

        # 决定是否需要 KG 抽取
        should_extract_kg = primary == StorageTarget.TEMPORAL_LOBE or fact_score > 0.5

        # 内容类型映射
        content_type_map = {
            StorageTarget.HIPPOCAMPUS: 'episodic',
            StorageTarget.TEMPORAL_LOBE: 'semantic',
            StorageTarget.AMYGDALA: 'emotional',
            StorageTarget.BASAL_GANGLIA: 'procedural',
            StorageTarget.PREFRONTAL: 'working',
        }

        # 生成推理说明
        reasoning = self._generate_reasoning(scores, primary)
        if semantic_weights:
            reasoning = f"{reasoning}; semantic={self._format_semantic_weights(semantic_weights)}"

        # 更新统计
        self.routing_stats[primary] += 1

        decision = RoutingDecision(
            primary_target=primary,
            secondary_targets=secondary,
            should_embed=should_embed,
            should_extract_kg=should_extract_kg,
            confidence=min(primary_score, 1.0),
            reasoning=reasoning,
            content_type=content_type_map[primary]
        )

        logger.info(f"🧭 Storage Router: {primary.value} (conf={decision.confidence:.2f}, embed={should_embed}, kg={should_extract_kg})")

        return decision

    def _score_emotion(self, text: str) -> float:
        """计算情感分数"""
        score = 0.0
        for category, keywords in self.emotion_keywords.items():
            for kw in keywords:
                if kw in text:
                    # 🔥 提高情感关键词权重
                    score += 0.4 if category != 'neutral' else 0.2
        return min(score, 1.0)

    def _score_facts(self, text: str) -> float:
        """计算事实/知识分数"""
        score = 0.0
        for kw in self.fact_keywords:
            if kw in text:
                score += 0.25
        # 包含专有名词 (大写开头) 的句子更可能是事实
        if re.search(r'\b[A-Z][a-z]+\b', text):
            score += 0.2
        return min(score, 1.0)

    def _score_temporal(self, text: str) -> float:
        """计算时序/事件分数"""
        score = 0.0
        for kw in self.temporal_keywords:
            if kw in text:
                score += 0.3
        # 包含日期格式
        if re.search(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}', text):
            score += 0.4
        return min(score, 1.0)

    def _score_habits(self, text: str) -> float:
        """计算习惯/模式分数"""
        score = 0.0
        for kw in self.habit_keywords:
            if kw in text:
                score += 0.35
        return min(score, 1.0)

    def _score_context(self, text: str, context: Dict[str, Any]) -> float:
        """计算短期上下文分数"""
        score = 0.0
        for kw in self.context_keywords:
            if kw in text:
                score += 0.4  # 🔥 提高关键词权重
        # 如果是对话的前几轮，更可能是上下文
        turn = context.get('session_turn', 0)
        if turn < 3:
            score += 0.1  # 🔥 降低轮次加分
        # 🔥 移除短内容加分 - 这会导致事实类被误判
        # if len(text) < 50:
        #     score += 0.15
        return min(score, 1.0)

    def _generate_reasoning(self, scores: Dict[StorageTarget, float], primary: StorageTarget) -> str:
        """生成路由推理说明"""
        parts = []
        for target, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
            if score > 0.1:
                parts.append(f"{target.value}={score:.2f}")
        return f"Selected {primary.value} based on scores: {', '.join(parts[:3])}"

    def _format_semantic_weights(self, weights: Dict[str, Any]) -> str:
        """格式化语义权重，便于日志观测"""
        safe = {k: round(float(v), 2) for k, v in weights.items() if isinstance(v, (int, float, str))}
        return str(safe)

    def get_stats(self) -> Dict[str, int]:
        """获取路由统计"""
        return {k.value: v for k, v in self.routing_stats.items()}

    def reset_stats(self):
        """重置统计"""
        self.routing_stats = {target: 0 for target in StorageTarget}


# 单例
_storage_router: Optional[StorageRouter] = None

def get_storage_router(config: Optional[Dict[str, Any]] = None) -> StorageRouter:
    """获取存储路由器单例"""
    global _storage_router
    if _storage_router is None:
        _storage_router = StorageRouter(config)
    return _storage_router
