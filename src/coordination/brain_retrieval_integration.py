"""
Brain-Inspired Retrieval Integration
脑仿生检索整合模块

整合所有已实现但未使用的脑仿生特性:
1. FastPathDetector - 快慢路径分离 (基底节 + 海马体)
2. HippocampalPrefrontalLoop - 海马-前额叶迭代检索
3. GapDetector/MultiRoundRetrieval - 缺口检测与多轮检索
4. Hybrid Retrieval - BM25 + 向量 + 重排序
5. 🔥 NEW: PrefrontalFeedback - 前额叶反馈机制（奖励/惩罚调整检索策略）

神经科学原理:
- 基底节: 处理自动化/程序化任务 (快速路径)
- 海马体: 情景记忆检索
- 前额叶: 工作记忆、缺口分析、反馈与奖励机制
- 颞叶: 语义记忆/概念管理
- 迭代循环: 检索→分析→反馈→策略调整→再检索

Author: BMAM Team
"""

import logging
import asyncio
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import brain-inspired modules
from ..optimization.fast_path import FastPathDetector, get_fast_path_detector
from ..brain.hippocampal_loop import HippocampalPrefrontalLoop
from ..agents.core.multi_round_retrieval import (
    GapDetector,
    MultiRoundRetrievalScheduler,
    retrieve_with_multi_round
)
from ..brain.emotion_modulator import EmotionModulator  # FIX-007: 情绪调节器
from ..config.ablation_config import is_component_enabled  # 🔥 FIX: 消融实验支持
from ..core.config import get_config  # 🔥 Task 1.5: Centralized config

# Task 3.3: Adaptive semantic/episodic weights for memory fusion
try:
    from src.coordination.adaptive_config import (
        get_adaptive_config_manager,
    )
    _ADAPTIVE_CONFIG_AVAILABLE = True
except ImportError:
    _ADAPTIVE_CONFIG_AVAILABLE = False

logger = logging.getLogger(__name__)

# Task 3.2: Emotion keyword patterns for query-level emotion detection
# Only apply emotion modulation when query actually contains emotional content
EMOTION_KEYWORDS = {
    'en': [
        r'\b(happy|sad|angry|afraid|scared|excited|nervous|anxious)\b',
        r'\b(love|hate|fear|joy|grief|rage|panic|thrill)\b',
        r'\b(worried|stressed|delighted|frustrated|disappointed)\b',
        r'\b(feel|feeling|felt|emotion|emotional|mood)\b',
    ],
    'zh': [
        r'(开心|难过|生气|害怕|兴奋|紧张|焦虑)',
        r'(爱|恨|恐惧|喜悦|悲伤|愤怒|恐慌)',
        r'(担心|压力|高兴|沮丧|失望)',
        r'(感觉|感到|情绪|心情)',
    ]
}


@dataclass
class BrainRetrievalResult:
    """脑仿生检索结果"""
    memories: List[Dict[str, Any]]
    path_type: str  # 'fast' or 'slow'
    iterations: int
    gaps_detected: List[Dict]
    confidence: float
    retrieval_time_ms: float
    debug_info: Dict[str, Any]


class PrefrontalFeedbackSystem:
    """
    🔥 前额叶反馈系统 - 模拟前额叶的奖励/惩罚机制

    神经科学基础:
    - 前额叶皮层 (PFC) 负责执行控制和反馈学习
    - 多巴胺信号提供奖励/惩罚反馈
    - 基于结果调整未来行为策略

    功能:
    1. 评估检索质量 (Quality Assessment)
    2. 奖励/惩罚信号 (Reward Signal)
    3. 策略调整 (Strategy Adaptation)
    4. 权重持久化 (跨会话保留学习成果)
    """

    _WEIGHTS_PATH = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'data', 'state', 'prefrontal_weights.json'
    )

    def __init__(self):
        # 策略权重 (会根据反馈动态调整)
        default_weights = {
            'bm25_weight': 0.35,      # BM25关键词权重
            'vector_weight': 0.35,    # 向量检索权重
            'entity_weight': 0.20,    # 实体检索权重
            'temporal_weight': 0.10,  # 时间过滤权重
        }
        self.strategy_weights = self._load_weights(default_weights)

        # 学习率
        self.learning_rate = get_config().retrieval.learning_rate

        # 反馈历史 (用于策略调整)
        self.feedback_history = []
        self.max_history = 100

        # 查询类型→成功策略映射
        self.query_strategy_map = {
            'temporal': {'bm25_weight': 0.4, 'temporal_weight': 0.3},
            'entity': {'entity_weight': 0.4, 'vector_weight': 0.3},
            'semantic': {'vector_weight': 0.5, 'bm25_weight': 0.25},
            'factual': {'bm25_weight': 0.5, 'entity_weight': 0.3}
        }

    def _load_weights(self, defaults: dict) -> dict:
        """Load persisted strategy weights from disk, fallback to defaults."""
        import json as _json
        try:
            path = os.path.normpath(self._WEIGHTS_PATH)
            if os.path.exists(path):
                with open(path, 'r') as f:
                    loaded = _json.load(f)
                if set(loaded.keys()) == set(defaults.keys()):
                    logger.debug(f"Loaded prefrontal weights from {path}")
                    return loaded
        except Exception as e:
            logger.debug(f"Could not load prefrontal weights: {e}")
        return defaults.copy()

    def _save_weights(self):
        """Persist current strategy weights to disk."""
        import json as _json
        try:
            path = os.path.normpath(self._WEIGHTS_PATH)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                _json.dump(self.strategy_weights, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save prefrontal weights: {e}")

    def evaluate_retrieval_quality(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        query_type: str = 'general'
    ) -> Dict[str, Any]:
        """
        评估检索结果质量 - 前额叶质量评估功能

        Returns:
            {
                'quality_score': 0-1,
                'reward_signal': -1 to 1 (负=惩罚, 正=奖励),
                'suggested_adjustments': Dict
            }
        """
        if not memories:
            return {
                'quality_score': 0.0,
                'reward_signal': -0.5,
                'issues': ['no_memories_found'],
                'suggested_adjustments': {'expand_search': True}
            }

        # 1. 覆盖度评估: 查询关键词在结果中的覆盖率
        query_words = set(query.lower().split())
        stopwords = {'what', 'when', 'where', 'who', 'how', 'why', 'is', 'are', 'the', 'a', 'an', 'did', 'does'}
        query_keywords = query_words - stopwords

        covered_keywords = set()
        for mem in memories[:5]:  # 只看top5
            content = (mem.get('content', '') or '').lower()
            for kw in query_keywords:
                if kw in content:
                    covered_keywords.add(kw)

        coverage = len(covered_keywords) / len(query_keywords) if query_keywords else 0.5

        # 2. 多样性评估: 结果不应都来自同一来源
        sources = set(mem.get('source', mem.get('retrieval_strategy', 'unknown')) for mem in memories[:10])
        diversity = len(sources) / 3.0  # 理想是3种来源

        # 3. 置信度评估: 检索分数分布
        scores = [mem.get('relevance', mem.get('score', 0.5)) for mem in memories[:5]]
        avg_score = sum(scores) / len(scores) if scores else 0.5
        score_spread = max(scores) - min(scores) if len(scores) > 1 else 0

        # 综合质量分数
        quality_score = (
            0.4 * coverage +
            0.2 * diversity +
            0.3 * avg_score +
            0.1 * (1 - score_spread)  # 分数应该比较集中
        )

        # 计算奖励信号
        reward_signal = (quality_score - 0.5) * 2  # 映射到[-1, 1]

        # 识别问题和建议
        issues = []
        adjustments = {}

        _rcfg = get_config().retrieval
        if coverage < _rcfg.quality_threshold:
            issues.append('low_coverage')
            adjustments['increase_bm25'] = True
        if diversity < _rcfg.kg_coverage_threshold:
            issues.append('low_diversity')
            adjustments['expand_sources'] = True
        if avg_score < 0.4:
            issues.append('low_relevance')
            adjustments['increase_k'] = True

        return {
            'quality_score': round(quality_score, 3),
            'reward_signal': round(reward_signal, 3),
            'issues': issues,
            'suggested_adjustments': adjustments,
            'details': {
                'coverage': round(coverage, 3),
                'diversity': round(diversity, 3),
                'avg_score': round(avg_score, 3)
            }
        }

    def apply_feedback(self, query_type: str, reward_signal: float):
        """
        应用反馈调整策略权重 - 强化学习式更新

        Args:
            query_type: 查询类型
            reward_signal: 奖励信号 (-1 to 1)
        """
        # 记录反馈历史
        self.feedback_history.append({
            'query_type': query_type,
            'reward': reward_signal,
            'timestamp': datetime.now().isoformat()
        })

        # 限制历史长度
        if len(self.feedback_history) > self.max_history:
            self.feedback_history = self.feedback_history[-self.max_history:]

        # 根据奖励信号调整策略
        if query_type in self.query_strategy_map:
            target_weights = self.query_strategy_map[query_type]

            if reward_signal > 0:
                # 正反馈: 朝目标策略方向调整
                for key, target in target_weights.items():
                    current = self.strategy_weights.get(key, 0.25)
                    self.strategy_weights[key] = current + self.learning_rate * reward_signal * (target - current)
            else:
                # 负反馈: 远离当前策略
                for key in self.strategy_weights:
                    current = self.strategy_weights.get(key, 0.25)
                    # 均匀化权重
                    self.strategy_weights[key] = current + self.learning_rate * abs(reward_signal) * (0.25 - current)

        # 归一化权重
        total = sum(self.strategy_weights.values())
        if total > 0:
            self.strategy_weights = {k: v/total for k, v in self.strategy_weights.items()}

        logger.debug(f"🧠 Prefrontal feedback applied: reward={reward_signal:.2f}, new_weights={self.strategy_weights}")

        # Persist every 10 feedback cycles to avoid excessive I/O
        if len(self.feedback_history) % 10 == 0:
            self._save_weights()

    def get_recommended_strategy(self, query: str) -> Dict[str, float]:
        """
        根据查询特征推荐检索策略

        Returns:
            策略权重字典
        """
        query_lower = query.lower()

        # 检测查询类型
        if any(kw in query_lower for kw in ['when', 'what date', 'what time', 'how long']):
            query_type = 'temporal'
        elif any(kw in query_lower for kw in ['who', 'what is', 'name']):
            query_type = 'entity'
        elif any(kw in query_lower for kw in ['why', 'how', 'explain', 'describe']):
            query_type = 'semantic'
        else:
            query_type = 'factual'

        # 返回推荐策略（基于学习到的权重和查询类型映射）
        base_weights = self.strategy_weights.copy()

        if query_type in self.query_strategy_map:
            type_weights = self.query_strategy_map[query_type]
            # 融合通用权重和类型特定权重
            for key, type_val in type_weights.items():
                if key in base_weights:
                    base_weights[key] = 0.6 * type_val + 0.4 * base_weights[key]

        return {
            'query_type': query_type,
            'weights': base_weights
        }


class BrainRegionCollaboration:
    """
    🔥 真正的脑区协作机制 - 动态循环记忆框架核心

    不是单线的 Query → 检索 → 返回
    而是循环的：

    ┌────────────────────────────────────────────────────────────┐
    │                    🧠 脑区协作循环                          │
    │                                                            │
    │  Query ──→ [前额叶: 策略决定] ──→ [海马体: 情节检索]         │
    │              ↑                         ↓                   │
    │              │    ┌──────────────────────────────┐         │
    │              │    ↓                              │         │
    │              │  [前额叶: 质量评估]               │         │
    │              │    ↓                              │         │
    │              │  足够? ──Yes──→ [输出结果]        │         │
    │              │    │                              │         │
    │              │   No                              │         │
    │              │    ↓                              │         │
    │              │  [杏仁核: 情绪注意力调节]          │         │
    │              │    ↓                              │         │
    │              │  [颞叶: 语义知识补充]              │         │
    │              │    ↓                              │         │
    │              └──[生成新查询策略]────→ 循环回前额叶          │
    │                                                            │
    └────────────────────────────────────────────────────────────┘

    神经科学依据:
    - 海马体 ↔ 前额叶 θ波同步: 记忆检索需要两区域协同
    - 杏仁核调节注意力: 情绪相关记忆优先级更高
    - 颞叶语义支持: 概念层面的知识补充
    """

    def __init__(self, memory_coordinator, llm_client=None):
        self.memory_coordinator = memory_coordinator
        self.llm_client = llm_client
        self.prefrontal = PrefrontalFeedbackSystem()
        self.gap_detector = GapDetector()
        self.emotion_modulator = EmotionModulator()  # FIX-007: 情绪调节器

        # 杏仁核情绪权重映射
        self.amygdala_emotion_weights = {
            'fear': 1.5,      # 恐惧记忆优先（生存本能）
            'joy': 1.3,       # 快乐记忆重要
            'sadness': 1.2,   # 悲伤记忆印象深
            'anger': 1.2,     # 愤怒记忆
            'surprise': 1.1,  # 惊讶记忆
            'love': 1.4,      # 🔥 爱/亲密关系记忆
            'anxiety': 1.3,   # 🔥 焦虑
            'excitement': 1.2,  # 🔥 兴奋
            'neutral': 1.0    # 中性
        }

        # 🔥 2026-03-31: 情绪关键词从共享 emotion_utils 加载
        from ..utils.emotion_utils import get_emotion_keywords
        self.emotion_keywords = get_emotion_keywords()

        # 协作统计
        self.stats = {
            'total_collaborations': 0,
            'avg_loops': 0.0,
            'amygdala_boosts': 0,
            'temporal_supplements': 0
        }

    def _load_emotion_keywords(self) -> Dict[str, List[str]]:
        """
        🔥 从配置加载情绪关键词，避免硬编码

        优先使用 SoulConfigLoader，fallback 到默认值
        """
        # 尝试从 SoulConfigLoader 加载
        try:
            from .soul_config_loader import SoulConfigLoader
            config = SoulConfigLoader()
            keywords = config.get_all_emotion_keywords('en')
            if keywords:
                logger.debug(f"Loaded emotion keywords from config: {list(keywords.keys())}")
                return keywords
        except Exception as e:
            logger.debug(f"SoulConfigLoader not available: {e}")

        # Fallback: 默认情绪关键词 (符合 Ekman 基本情绪模型)
        return {
            'fear': ['afraid', 'scared', 'terrified', 'worry', 'worried', 'anxious', 'panic', 'horror'],
            'joy': ['happy', 'glad', 'delighted', 'pleased', 'joyful', 'excited', 'thrilled', 'wonderful'],
            'sadness': ['sad', 'unhappy', 'depressed', 'disappointed', 'upset', 'crying', 'tears', 'grief'],
            'anger': ['angry', 'mad', 'furious', 'annoyed', 'frustrated', 'irritated', 'rage'],
            'surprise': ['surprised', 'amazed', 'astonished', 'shocked', 'unexpected', 'stunning'],
            'love': ['love', 'beloved', 'adore', 'affection', 'romantic', 'relationship', 'partner'],
            'anxiety': ['nervous', 'stressed', 'tense', 'uneasy', 'concern'],
            'excitement': ['excited', 'thrilled', 'eager', 'enthusiastic']
        }

    async def collaborative_retrieval(
        self,
        query: str,
        k: int = 10,
        max_loops: int = 3,
        quality_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        🔥 协作式检索 - 脑区循环协作

        Args:
            query: 查询
            k: 返回结果数
            max_loops: 最大循环次数
            quality_threshold: 质量阈值（达到则停止循环）

        Returns:
            检索结果 + 协作过程信息
        """
        self.stats['total_collaborations'] += 1
        loop_count = 0
        all_memories = []
        seen_ids = set()
        collaboration_trace = []

        # 初始策略由前额叶决定
        strategy = self.prefrontal.get_recommended_strategy(query)
        current_query = query

        logger.info(f"🧠 Starting brain region collaboration for: '{query[:50]}...'")
        logger.info(f"   Initial strategy: {strategy['query_type']}, weights: {strategy['weights']}")

        while loop_count < max_loops:
            loop_count += 1
            loop_info = {'loop': loop_count, 'query': current_query}

            # ===== Step 1: 海马体情节记忆检索 =====
            hippocampus_memories = await self._hippocampus_retrieve(current_query, k * 2)
            loop_info['hippocampus_count'] = len(hippocampus_memories)

            # ===== Step 2: 杏仁核情绪注意力调节 =====
            # Task 3.2: Only apply emotion modulation when feature flag is
            # enabled AND the query actually contains emotional content.
            # This prevents the -1.01% regression caused by indiscriminate
            # emotion modulation on all queries (FIX-007).
            emotion_modulation_enabled = os.getenv(
                "BMAM_ENABLE_EMOTION_MODULATION", "true"
            ).lower() != "false"

            current_mood = None
            if emotion_modulation_enabled:
                is_emotional, emotion_confidence = self._detect_emotion_in_query(
                    current_query
                )
                if is_emotional and emotion_confidence > 0.5:
                    current_mood = self._infer_user_mood(current_query)
                    logger.debug(
                        f"Task 3.2: Emotion detected in query "
                        f"(confidence={emotion_confidence:.2f}), "
                        f"applying modulation with mood={current_mood}"
                    )
                else:
                    logger.debug(
                        f"Task 3.2: No significant emotion in query "
                        f"(confidence={emotion_confidence:.2f}), "
                        f"skipping modulation"
                    )

            adjusted_memories = self._amygdala_attention_boost(
                hippocampus_memories, current_mood=current_mood
            )
            loop_info['amygdala_boosts'] = sum(
                1 for m in adjusted_memories if m.get('_amygdala_boosted')
            )
            loop_info['inferred_mood'] = current_mood

            # ===== Step 3: 颞叶语义补充 =====
            semantic_supplement = await self._temporal_lobe_supplement(current_query, adjusted_memories)
            loop_info['temporal_supplement'] = len(semantic_supplement)

            # 合并结果（去重）
            for mem in adjusted_memories + semantic_supplement:
                mem_id = mem.get('id', id(mem))
                if mem_id not in seen_ids:
                    all_memories.append(mem)
                    seen_ids.add(mem_id)

            # ===== Step 4: 前额叶质量评估 =====
            # 🔥 FIX: 消融检查 - 禁用 prefrontal 时跳过反馈评估
            if is_component_enabled('prefrontal'):
                quality = self.prefrontal.evaluate_retrieval_quality(
                    query=query,  # 原始query，不是current_query
                    memories=all_memories,
                    query_type=strategy['query_type']
                )
            else:
                # 消融模式：使用默认质量分数，不进行反馈调整
                quality = {'quality_score': 0.7, 'issues': [], 'reward_signal': 0.5}
            loop_info['quality'] = quality

            collaboration_trace.append(loop_info)

            logger.info(f"   Loop {loop_count}: hippocampus={len(hippocampus_memories)}, "
                       f"quality={quality['quality_score']:.2f}, issues={quality['issues']}")

            # ===== Step 5: 判断是否继续循环 =====
            if quality['quality_score'] >= quality_threshold:
                logger.info(f"   ✅ Quality threshold met ({quality['quality_score']:.2f} >= {quality_threshold})")
                break

            if not quality['issues']:
                logger.info(f"   ✅ No issues detected, stopping")
                break

            # ===== Step 6: 前额叶生成新策略 =====
            # 检测缺口并生成补充查询
            gaps = self.gap_detector.detect_gaps(query, all_memories)

            if gaps['has_gaps'] and gaps['suggested_queries']:
                current_query = gaps['suggested_queries'][0]
                logger.info(f"   🔄 Gap detected: {gaps['gap_types']}, new query: '{current_query[:50]}...'")
            else:
                # 尝试query expansion
                current_query = self._expand_query(query, quality['issues'])
                logger.info(f"   🔄 Query expanded: '{current_query[:50]}...'")

            # 应用反馈调整策略权重
            # 🔥 FIX: 消融检查 - 禁用 prefrontal 时跳过反馈
            if is_component_enabled('prefrontal'):
                self.prefrontal.apply_feedback(strategy['query_type'], quality['reward_signal'])

        # 更新统计
        n = self.stats['total_collaborations']
        self.stats['avg_loops'] = (self.stats['avg_loops'] * (n-1) + loop_count) / n

        # 最终排序
        final_memories = sorted(
            all_memories,
            key=lambda m: m.get('_final_score', m.get('relevance', 0)),
            reverse=True
        )[:k]

        return {
            'memories': final_memories,
            'loops': loop_count,
            'collaboration_trace': collaboration_trace,
            'final_quality': quality,
            'strategy_used': strategy
        }

    async def _hippocampus_retrieve(self, query: str, k: int) -> List[Dict]:
        """海马体情节记忆检索"""
        if not self.memory_coordinator or not hasattr(self.memory_coordinator, 'hippocampus'):
            return []

        try:
            result = await self.memory_coordinator.hippocampus.search_memories(query, k=k)
            return result.get('memories', [])
        except Exception as e:
            logger.warning(f"Hippocampus retrieval failed: {e}")
            return []

    def _amygdala_attention_boost(self, memories: List[Dict], current_mood: Optional[str] = None) -> List[Dict]:
        """
        杏仁核情绪注意力调节

        根据记忆的情绪标签调整其权重
        🔥 2025-12-16 修复: 如果没有 emotion_tags，从内容中动态检测情绪
        🔥 FIX-007: 增加情绪一致性效应 (Mood Congruency Effect)
        """
        for mem in memories:
            emotion_tags = mem.get('emotion_tags', [])
            if not emotion_tags:
                emotion_tags = mem.get('metadata', {}).get('emotion_tags', [])

            # 🔥 动态情绪检测: 如果没有标签，从内容中推断
            if not emotion_tags:
                content = mem.get('content', mem.get('text', ''))
                if content:
                    detected_emotions = self._detect_emotions_from_content(content)
                    if detected_emotions:
                        emotion_tags = detected_emotions
                        mem['_detected_emotions'] = detected_emotions  # 标记为动态检测

            # 固定情绪权重
            max_boost = 1.0
            primary_memory_emotion = None  # FIX-007: 记忆的主要情绪
            for tag in emotion_tags:
                tag_lower = tag.lower() if isinstance(tag, str) else str(tag).lower()
                boost = self.amygdala_emotion_weights.get(tag_lower, 1.0)
                if boost > max_boost:
                    max_boost = boost
                    primary_memory_emotion = tag_lower

            # FIX-007: 情绪一致性效应 (Mood Congruency Effect)
            congruency_boost = 0.0
            if current_mood and primary_memory_emotion:
                emotion_intensity = mem.get('emotion_intensity', 0.5)
                modulated_score = self.emotion_modulator.modulate_retrieval_score(
                    base_score=1.0,  # 只计算boost比例
                    emotion_intensity=emotion_intensity,
                    current_mood=current_mood,
                    memory_emotion=primary_memory_emotion
                )
                congruency_boost = modulated_score - 1.0  # 提取额外boost
                if congruency_boost > 0:
                    mem['_mood_congruency_boost'] = congruency_boost
                    logger.debug(f"FIX-007: Mood congruency {current_mood}↔{primary_memory_emotion} = +{congruency_boost:.2f}")

            # 应用总boost (固定权重 + 情绪一致性)
            total_boost = max_boost + congruency_boost
            if total_boost > 1.0:
                original_score = mem.get('relevance', mem.get('score', 0.5))
                mem['_original_score'] = original_score
                mem['relevance'] = min(1.0, original_score * total_boost)
                mem['_amygdala_boosted'] = True
                mem['_amygdala_boost'] = total_boost
                self.stats['amygdala_boosts'] += 1

        return memories

    def _detect_emotions_from_content(self, content: str) -> List[str]:
        """
        🔥 从内容中检测情绪标签

        基于关键词匹配进行简单情绪检测
        """
        content_lower = content.lower()
        detected = []

        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    detected.append(emotion)
                    break  # 每种情绪只检测一次

        return detected if detected else ['neutral']

    def _infer_user_mood(self, query: str) -> Optional[str]:
        """
        FIX-007: 从查询文本推断用户当前情绪

        基于情绪关键词匹配推断用户可能的情绪状态
        用于情绪一致性效应 (Mood Congruency Effect) 计算

        Returns:
            推断的情绪标签 (如 'sadness', 'joy') 或 None
        """
        query_lower = query.lower()

        # 按情绪强度排序检测（高valence情绪优先）
        mood_priority = ['fear', 'sadness', 'anger', 'joy', 'love', 'anxiety', 'excitement', 'surprise']

        for mood in mood_priority:
            keywords = self.emotion_keywords.get(mood, [])
            for keyword in keywords:
                if keyword in query_lower:
                    logger.debug(f"FIX-007: Inferred user mood '{mood}' from query")
                    return mood

        return None  # 无法推断时返回None

    def _detect_emotion_in_query(self, query: str) -> Tuple[bool, float]:
        """
        Task 3.2: Detect if query contains emotional content.

        Uses regex-based keyword matching against EMOTION_KEYWORDS patterns
        for both English and Chinese. Only when confidence > 0.8 (i.e., 3+
        pattern matches) should emotion modulation be applied.

        Returns:
            (is_emotional, confidence) where is_emotional is True only when
            confidence exceeds the 0.8 threshold.
        """
        match_count = 0
        total_patterns = 0
        for lang_patterns in EMOTION_KEYWORDS.values():
            for pattern in lang_patterns:
                total_patterns += 1
                if re.search(pattern, query, re.IGNORECASE):
                    match_count += 1

        if match_count == 0:
            return False, 0.0
        confidence = min(1.0, match_count / 2.0)  # 2+ matches = full confidence
        return confidence > 0.5, confidence

    async def _temporal_lobe_supplement(
        self,
        query: str,
        current_memories: List[Dict]
    ) -> List[Dict]:
        """
        颞叶语义知识补充

        🔥 修复: 不再只在记忆不足时补充，而是总是尝试获取语义知识
        因为语义知识可以提供不同视角的信息（概念、关系等）
        """
        if not self.memory_coordinator or not hasattr(self.memory_coordinator, 'temporal_lobe'):
            return []

        try:
            # 🔥 总是尝试获取语义记忆，作为情节记忆的补充
            result = await self.memory_coordinator.temporal_lobe.search_memories(query, k=5)
            semantic_memories = result.get('memories', [])

            # 去重：不要返回已经在 current_memories 中的记忆
            current_ids = {m.get('id') for m in current_memories if m.get('id')}
            unique_semantic = []
            for mem in semantic_memories:
                mem_id = mem.get('id')
                if mem_id and mem_id not in current_ids:
                    mem['source'] = 'temporal_lobe_supplement'
                    mem['_temporal_supplement'] = True
                    unique_semantic.append(mem)

            if unique_semantic:
                self.stats['temporal_supplements'] += len(unique_semantic)
                logger.debug(f"Temporal lobe supplemented {len(unique_semantic)} unique memories")

            return unique_semantic
        except Exception as e:
            logger.warning(f"Temporal lobe supplement failed: {e}")
            return []

    def _expand_query(self, original_query: str, issues: List[str]) -> str:
        """
        基于前额叶反馈的问题扩展查询
        """
        expanded = original_query

        if 'low_coverage' in issues:
            # 提取关键词并添加同义词
            keywords = self._extract_keywords(original_query)
            if keywords:
                expanded = f"{original_query} {' '.join(keywords[:3])}"

        if 'low_diversity' in issues:
            # 添加"related to"等扩展词
            expanded = f"{expanded} related details"

        return expanded

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        stopwords = {
            'what', 'when', 'where', 'who', 'how', 'why', 'is', 'are', 'was', 'were',
            'the', 'a', 'an', 'did', 'does', 'do', 'to', 'of', 'in', 'for', 'on'
        }
        words = query.lower().split()
        return [w.strip('?.,!') for w in words if w.lower() not in stopwords and len(w) > 2]


class BrainInspiredRetrieval:
    """
    脑仿生检索系统

    整合快慢路径、迭代检索、缺口检测的完整检索管道

    流程:
    1. 快速路径检测 (FastPathDetector)
       - 简单事实查询 → 直接返回
       - 复杂查询 → 进入慢速路径

    2. 慢速路径 (HippocampalPrefrontalLoop + GapDetector)
       - 初始检索
       - 前额叶缺口分析
       - 迭代补充检索
       - 结果融合
    """

    def __init__(
        self,
        memory_coordinator=None,
        llm_client=None,
        enable_fast_path: bool = False,  # 🔥 FIX: 关闭快速路径，强制深度检索
        enable_iterative: bool = True,
        max_iterations: int = 5  # 🔥 FIX: 增加迭代次数支持复杂推理
    ):
        """
        Args:
            memory_coordinator: 记忆协调器 (用于检索)
            llm_client: LLM客户端 (用于缺口分析)
            enable_fast_path: 是否启用快速路径 (默认开启，让系统智能判断)
            enable_iterative: 是否启用迭代检索
            max_iterations: 最大迭代次数 (默认3次)
        """
        self.memory_coordinator = memory_coordinator
        self.llm_client = llm_client
        self.enable_fast_path = enable_fast_path
        self.enable_iterative = enable_iterative
        self.max_iterations = max_iterations

        # Initialize brain-inspired components
        self.fast_path_detector = get_fast_path_detector()
        self.gap_detector = GapDetector()
        self.multi_round_scheduler = MultiRoundRetrievalScheduler(max_rounds=max_iterations)
        self.hippocampal_loop = None  # Lazy init

        # 🔥 NEW: 前额叶反馈系统
        self.prefrontal_feedback = PrefrontalFeedbackSystem()

        # 🔥 NEW: 脑区协作系统 (真正的循环协作，不是单线pipeline)
        self.brain_collaboration = None  # Lazy init with memory_coordinator

        # Statistics
        self.stats = {
            'total_queries': 0,
            'fast_path_queries': 0,
            'slow_path_queries': 0,
            'avg_iterations': 0.0,
            'avg_confidence': 0.0,
            'feedback_applied': 0  # 🔥 NEW: 反馈应用次数
        }

        logger.info("BrainInspiredRetrieval initialized with:")
        logger.info(f"  - Fast path: {enable_fast_path}")
        logger.info(f"  - Iterative retrieval: {enable_iterative}")
        logger.info(f"  - Max iterations: {max_iterations}")
        logger.info(f"  - Prefrontal feedback: enabled")

    def _init_hippocampal_loop(self):
        """懒初始化海马-前额叶循环"""
        if self.hippocampal_loop is None and self.memory_coordinator:
            self.hippocampal_loop = HippocampalPrefrontalLoop(
                memory_system=self.memory_coordinator,
                llm_client=self.llm_client
            )

    def _init_brain_collaboration(self):
        """🔥 懒初始化脑区协作系统"""
        if self.brain_collaboration is None and self.memory_coordinator:
            self.brain_collaboration = BrainRegionCollaboration(
                memory_coordinator=self.memory_coordinator,
                llm_client=self.llm_client
            )

    async def retrieve(
        self,
        query: str,
        k: int = 10,
        context: Optional[Dict[str, Any]] = None,
        activation_plan: Optional[Dict[str, bool]] = None,
        force_slow_path: bool = False
    ) -> BrainRetrievalResult:
        """
        脑仿生检索主入口

        Args:
            query: 查询文本
            k: 返回结果数量
            context: 上下文信息
            activation_plan: 脑区激活计划 (来自丘脑动态门控)
            force_slow_path: 强制使用慢速路径

        Returns:
            BrainRetrievalResult: 检索结果
        """
        start_time = datetime.now()
        self.stats['total_queries'] += 1

        if context is None:
            context = {}

        logger.info(f"🧠 Brain-inspired retrieval: '{query[:50]}...'")

        # Step 1: Fast Path Detection (基底节自动化检测)
        if self.enable_fast_path and not force_slow_path:
            fast_result = await self._try_fast_path(query, k, context, activation_plan)
            if fast_result:
                elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
                self.stats['fast_path_queries'] += 1
                logger.info(f"⚡ Fast path success: {len(fast_result.memories)} memories in {elapsed_ms:.1f}ms")
                fast_result.retrieval_time_ms = elapsed_ms
                return fast_result

        # Step 2: Slow Path (海马-前额叶迭代检索)
        self.stats['slow_path_queries'] += 1
        logger.info("🐢 Entering slow path (iterative retrieval)")

        slow_result = await self._slow_path_retrieval(
            query=query,
            k=k,
            context=context,
            activation_plan=activation_plan
        )

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        slow_result.retrieval_time_ms = elapsed_ms

        # Update statistics
        self._update_stats(slow_result)

        logger.info(f"🧠 Slow path complete: {len(slow_result.memories)} memories, "
                   f"{slow_result.iterations} iterations, {elapsed_ms:.1f}ms")

        return slow_result

    async def _try_fast_path(
        self,
        query: str,
        k: int,
        context: Dict[str, Any],
        activation_plan: Optional[Dict[str, bool]]
    ) -> Optional[BrainRetrievalResult]:
        """
        尝试快速路径

        检测条件:
        1. 简单事实查询 (When, Who, What is)
        2. 高置信度直接匹配
        """
        # First, get initial memories for fast path detection
        initial_memories = await self._initial_retrieval(
            query=query,
            k=k,
            activation_plan=activation_plan
        )

        if not initial_memories:
            logger.debug("No memories for fast path detection")
            return None

        # Try fast path detection
        fast_path_result = self.fast_path_detector.detect_fast_path(
            query=query,
            retrieved_memories=initial_memories
        )

        if fast_path_result and fast_path_result.get('can_use_fast_path'):
            # Fast path success!
            logger.info(f"⚡ Fast path detected: {fast_path_result.get('path_type')}")
            logger.info(f"   Confidence: {fast_path_result.get('confidence', 0):.2f}")

            return BrainRetrievalResult(
                memories=initial_memories[:k],
                path_type='fast',
                iterations=1,
                gaps_detected=[],
                confidence=fast_path_result.get('confidence', 0.8),
                retrieval_time_ms=0,  # Will be set by caller
                debug_info={
                    'fast_path_type': fast_path_result.get('path_type'),
                    'direct_answer': fast_path_result.get('direct_answer'),
                    'reasoning': fast_path_result.get('reasoning')
                }
            )

        return None

    async def _slow_path_retrieval(
        self,
        query: str,
        k: int,
        context: Dict[str, Any],
        activation_plan: Optional[Dict[str, bool]]
    ) -> BrainRetrievalResult:
        """
        🔥 慢速路径检索 - 使用脑区协作循环

        不再是单线pipeline，而是真正的脑区循环协作：
        前额叶策略 → 海马体检索 → 杏仁核注意力 → 颞叶补充 → 前额叶评估 → 循环

        流程:
        1. 脑区协作循环检索
        2. LLM精排
        3. 前额叶反馈学习
        """
        self._init_hippocampal_loop()
        self._init_brain_collaboration()  # 🔥 初始化协作系统

        # ═══════════════════════════════════════════════════════════════
        # 🔥 Step 1: 脑区协作循环检索 (替代原来的单线pipeline)
        # ═══════════════════════════════════════════════════════════════
        logger.info("🧠 Step 1: Brain Region Collaborative Retrieval")

        collab_result = await self.brain_collaboration.collaborative_retrieval(
            query=query,
            k=k * 2,  # 获取更多用于后续精排
            max_loops=self.max_iterations,
            quality_threshold=0.6
        )

        all_memories = collab_result['memories']
        loops_used = collab_result['loops']
        collaboration_trace = collab_result['collaboration_trace']

        logger.info(f"   Collaboration complete: {len(all_memories)} memories in {loops_used} loops")
        logger.info(f"   Amygdala boosts: {self.brain_collaboration.stats['amygdala_boosts']}")
        logger.info(f"   Temporal supplements: {self.brain_collaboration.stats['temporal_supplements']}")

        # 构建gaps_history用于后续兼容
        gaps_history = [
            {'iteration': t['loop'], 'gaps': t.get('quality', {})}
            for t in collaboration_trace
        ]

        # ═══════════════════════════════════════════════════════════════
        # 🔥 Step 2: BM25+Vector多因子排序
        # ═══════════════════════════════════════════════════════════════
        logger.info("📊 Step 2: BM25+Vector ranking")
        ranked_memories = self._rank_memories(all_memories, query)

        # ═══════════════════════════════════════════════════════════════
        # 🔥 Step 3: LLM Reranker精排
        # ═══════════════════════════════════════════════════════════════
        logger.info("🎯 Step 3: LLM Reranker精排")
        final_memories = await self._llm_rerank(ranked_memories, query, top_k=k)

        # Calculate overall confidence
        confidence = self._calculate_confidence(final_memories, gaps_history)

        # ═══════════════════════════════════════════════════════════════
        # 🔥 Step 4: 前额叶最终反馈 (用于持续学习)
        # ═══════════════════════════════════════════════════════════════
        strategy_info = self.prefrontal_feedback.get_recommended_strategy(query)
        feedback = self.prefrontal_feedback.evaluate_retrieval_quality(
            query=query,
            memories=final_memories,
            query_type=strategy_info['query_type']
        )
        # 应用反馈学习
        self.prefrontal_feedback.apply_feedback(
            query_type=strategy_info['query_type'],
            reward_signal=feedback['reward_signal']
        )
        self.stats['feedback_applied'] += 1
        logger.info(f"🧠 Prefrontal feedback: quality={feedback['quality_score']:.2f}, issues={feedback['issues']}")

        return BrainRetrievalResult(
            memories=final_memories,
            path_type='slow',
            iterations=loops_used,  # 🔥 使用协作循环次数
            gaps_detected=gaps_history,
            confidence=confidence,
            retrieval_time_ms=0,  # Will be set by caller
            debug_info={
                'total_memories_found': len(all_memories),
                'collaboration_loops': loops_used,
                'amygdala_boosts': self.brain_collaboration.stats['amygdala_boosts'],
                'temporal_supplements': self.brain_collaboration.stats['temporal_supplements'],
                'collaboration_trace': collaboration_trace,
                'prefrontal_feedback': feedback,
                'strategy_weights': self.prefrontal_feedback.strategy_weights.copy()
            }
        )

    async def _initial_retrieval(
        self,
        query: str,
        k: int,
        activation_plan: Optional[Dict[str, bool]]
    ) -> List[Dict[str, Any]]:
        """
        初始检索 - 调用 cross_region_retrieval
        """
        if not self.memory_coordinator:
            logger.warning("No memory_coordinator available")
            return []

        try:
            memories = await self.memory_coordinator.cross_region_retrieval(
                query=query,
                top_k=k,
                activation_plan=activation_plan
            )
            return memories if memories else []
        except Exception as e:
            logger.error(f"Initial retrieval failed: {e}")
            return []

    async def _enhanced_initial_retrieval(
        self,
        query: str,
        k: int,
        activation_plan: Optional[Dict[str, bool]]
    ) -> List[Dict[str, Any]]:
        """
        增强初始检索 - 多策略组合

        策略:
        1. 语义检索 (cross_region_retrieval)
        2. 关键词检索 (BM25-like)
        3. 时间范围检索 (如果query包含时间相关词)
        """
        all_memories = []
        seen_ids = set()

        # Strategy 1: Semantic retrieval (main)
        semantic_mems = await self._initial_retrieval(query, k, activation_plan)
        for mem in semantic_mems:
            mem_id = mem.get('id', id(mem))
            if mem_id not in seen_ids:
                mem['retrieval_strategy'] = 'semantic'
                all_memories.append(mem)
                seen_ids.add(mem_id)

        # Strategy 2: Keyword extraction and retrieval
        keywords = self._extract_keywords(query)
        if keywords:
            keyword_query = ' '.join(keywords)
            try:
                keyword_mems = await self._initial_retrieval(keyword_query, k // 2, activation_plan)
                for mem in keyword_mems:
                    mem_id = mem.get('id', id(mem))
                    if mem_id not in seen_ids:
                        mem['retrieval_strategy'] = 'keyword'
                        all_memories.append(mem)
                        seen_ids.add(mem_id)
            except Exception as e:
                logger.debug(f"Keyword retrieval failed: {e}")

        # Strategy 3: Entity-focused retrieval
        entities = self._extract_entities(query)
        if entities:
            for entity in entities[:2]:  # Max 2 entities
                try:
                    entity_mems = await self._initial_retrieval(entity, k // 3, activation_plan)
                    for mem in entity_mems:
                        mem_id = mem.get('id', id(mem))
                        if mem_id not in seen_ids:
                            mem['retrieval_strategy'] = 'entity'
                            mem['target_entity'] = entity
                            all_memories.append(mem)
                            seen_ids.add(mem_id)
                except Exception as e:
                    logger.debug(f"Entity retrieval for '{entity}' failed: {e}")

        logger.info(f"Enhanced retrieval: {len(all_memories)} unique memories "
                   f"(semantic: {len([m for m in all_memories if m.get('retrieval_strategy') == 'semantic'])}, "
                   f"keyword: {len([m for m in all_memories if m.get('retrieval_strategy') == 'keyword'])}, "
                   f"entity: {len([m for m in all_memories if m.get('retrieval_strategy') == 'entity'])})")

        return all_memories

    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        stopwords = {
            'what', 'when', 'where', 'who', 'how', 'why', 'is', 'are', 'was', 'were',
            'the', 'a', 'an', 'did', 'does', 'do', 'would', 'could', 'should', 'can',
            'will', 'has', 'have', 'had', 'be', 'been', 'being', 'to', 'of', 'in',
            'for', 'on', 'with', 'at', 'by', 'from', 'about', 'into', 'through'
        }

        words = query.lower().split()
        keywords = [w.strip('?.,!\'\"') for w in words if w.lower() not in stopwords]
        return [kw for kw in keywords if len(kw) > 2]

    def _extract_entities(self, query: str) -> List[str]:
        """提取实体 (简单的大写词检测)"""
        import re
        # Find capitalized words (likely proper nouns/entities)
        entities = re.findall(r'\b[A-Z][a-z]+\b', query)
        # Filter out common words that might be capitalized
        common_starts = {'What', 'When', 'Where', 'Who', 'How', 'Why', 'Is', 'Are', 'Did', 'Does'}
        entities = [e for e in entities if e not in common_starts]
        return entities

    def _rank_memories(self, memories: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        对记忆进行重排序 (BM25 + Vector + 多因子融合)

        排序因子:
        1. BM25关键词匹配分数
        2. 向量相关性分数 (relevance/score)
        3. 重要性 (importance)
        4. 共振分数 (resonance_score)
        5. 实体匹配加成
        6. Task 3.3: Adaptive semantic/episodic weight
        """
        query_lower = query.lower()
        query_words = set(self._extract_keywords(query))
        entities = set(self._extract_entities(query))

        # Task 3.3: Get adaptive weights for this query
        adaptive_semantic_w = 1.0
        adaptive_episodic_w = 1.0
        if _ADAPTIVE_CONFIG_AVAILABLE:
            try:
                _acm = get_adaptive_config_manager()
                _aw = _acm.get_adaptive_weights(query)
                adaptive_semantic_w = _aw.semantic_weight
                adaptive_episodic_w = _aw.episodic_weight
                logger.debug(
                    "Task 3.3 QADW rank weights: "
                    f"semantic={adaptive_semantic_w:.2f}, "
                    f"episodic={adaptive_episodic_w:.2f}"
                )
            except Exception as e:
                logger.debug(
                    f"Task 3.3 adaptive weights "
                    f"fallback (1.0): {e}"
                )

        # 计算IDF权重 (文档频率倒数)
        word_doc_freq = {}
        for mem in memories:
            content = (mem.get('content', '') or '').lower()
            content_words = set(content.split())
            for word in query_words:
                if word in content_words:
                    word_doc_freq[word] = word_doc_freq.get(word, 0) + 1

        num_docs = len(memories) if memories else 1

        def compute_bm25_score(mem: Dict) -> float:
            """计算BM25分数"""
            content = (mem.get('content', '') or '').lower()
            content_words = content.split()

            if not content_words or not query_words:
                return 0.0

            # BM25 参数
            _bm25_cfg = get_config().retrieval
            k1 = _bm25_cfg.bm25_k1
            b = _bm25_cfg.bm25_b
            avg_doc_len = sum(len((m.get('content', '') or '').split()) for m in memories) / max(len(memories), 1)
            doc_len = len(content_words)

            bm25_score = 0.0
            for word in query_words:
                if word not in content:
                    continue

                # TF (词频)
                tf = content_words.count(word) if isinstance(content_words, list) else content.count(word)

                # IDF (逆文档频率)
                df = word_doc_freq.get(word, 0)
                idf = max(0, (num_docs - df + 0.5) / (df + 0.5))
                import math
                idf = math.log(1 + idf)

                # BM25公式
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * (doc_len / max(avg_doc_len, 1)))
                bm25_score += idf * (numerator / max(denominator, 0.001))

            # 归一化到 [0, 1]
            return min(bm25_score / 10.0, 1.0)

        def _get_region_weight(mem: Dict) -> float:
            """
            Task 3.3: Determine adaptive weight based on
            memory brain-region origin.

            Sources checked (in priority order):
            1. _meta.regions from cross-region fusion
            2. source field (e.g. 'temporal_lobe_supplement')
            3. retrieval_strategy tag

            Returns adaptive weight multiplier (>= 0.6).
            """
            regions = set()
            meta = mem.get('_meta', {})
            if meta and 'regions' in meta:
                regions = set(meta['regions'])

            src = mem.get('source', '')

            # Identify episodic (hippocampus) origin
            if 'hippocampus' in regions:
                return adaptive_episodic_w

            # Identify semantic (temporal lobe) origin
            if 'temporal_lobe' in regions:
                return adaptive_semantic_w
            if 'temporal_lobe' in src:
                return adaptive_semantic_w

            # Fallback: retrieval_strategy hints
            strategy = mem.get('retrieval_strategy', '')
            if strategy == 'semantic':
                return adaptive_semantic_w

            # No region info -> neutral weight
            return 1.0

        def score_memory(mem: Dict) -> float:
            # 1. BM25 关键词分数 (30%)
            bm25 = compute_bm25_score(mem)

            # 2. 向量相关性分数 (30%)
            relevance = mem.get(
                'relevance', mem.get('score', 0.5)
            )

            # 3. 重要性 (15%)
            importance = mem.get('importance', 0.5)

            # 4. 共振分数 (15%)
            resonance = mem.get('resonance_score', 0.0)

            # 5. 实体匹配加成 (10%)
            content = (
                (mem.get('content', '') or '').lower()
            )
            entity_bonus = 0.0
            for entity in entities:
                if entity.lower() in content:
                    entity_bonus += 0.5
            entity_bonus = min(entity_bonus, 1.0)

            # 融合分数
            score = (
                bm25 * 0.30 +
                relevance * 0.30 +
                importance * 0.15 +
                resonance * 0.15 +
                entity_bonus * 0.10
            )

            # 策略加成
            if mem.get('retrieval_strategy') == 'semantic':
                score *= 1.05
            elif mem.get('retrieval_strategy') == 'entity':
                score *= 1.08

            # Task 3.3: Apply adaptive region weight
            region_w = _get_region_weight(mem)
            score *= region_w

            # 存储分数用于调试
            mem['_rerank_score'] = round(score, 4)
            mem['_bm25_score'] = round(bm25, 4)
            mem['_adaptive_region_w'] = round(
                region_w, 4
            )

            return score

        ranked = sorted(memories, key=score_memory, reverse=True)

        # 记录重排序结果
        if ranked:
            top_scores = [m.get('_rerank_score', 0) for m in ranked[:5]]
            logger.debug(f"Reranking complete: top 5 scores = {top_scores}")

        return ranked

    async def _llm_rerank(
        self,
        memories: List[Dict[str, Any]],
        query: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        🔥 LLM-based Reranker - 使用LLM进行精排

        这是真正的reranker，不是简单的分数排序。
        使用LLM判断每个记忆与查询的相关性。

        Args:
            memories: 候选记忆列表
            query: 用户查询
            top_k: 返回top k个结果

        Returns:
            重排序后的记忆列表
        """
        if not self.llm_client or not memories:
            return memories[:top_k]

        # 限制送入LLM的数量（成本控制）
        candidates = memories[:min(20, len(memories))]

        # 构建rerank prompt
        memory_texts = []
        for i, mem in enumerate(candidates):
            content = mem.get('content', '')[:300]  # 截断长文本
            memory_texts.append(f"[{i}] {content}")

        prompt = f"""Rate how directly each memory answers the question. Output JSON only.

Question: {query}

Memories:
{chr(10).join(memory_texts)}

Scoring criteria (be strict):
- 10: Contains the EXACT answer to the question
- 7-9: Contains information that directly helps answer (dates, names, facts)
- 4-6: Related topic but doesn't answer the question
- 1-3: Tangentially related
- 0: Completely unrelated

IMPORTANT: For "When" questions, only memories with dates/times should score 7+.
For "Who" questions, only memories with names should score 7+.

Output: {{"scores": [s0, s1, ...]}}"""

        try:
            from ..core.constants import DEFAULT_LLM_MODEL
            response = await self.llm_client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,  # 使用配置的模型
                messages=[
                    {"role": "system", "content": "You are a relevance scoring expert. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=200
            )

            import json
            result = json.loads(response.choices[0].message.content)
            scores = result.get('scores', [])

            # 应用LLM分数
            for i, mem in enumerate(candidates):
                if i < len(scores):
                    mem['_llm_rerank_score'] = scores[i] / 10.0  # 归一化到0-1
                    # 融合LLM分数和原有分数
                    original_score = mem.get('_rerank_score', 0.5)
                    mem['_final_score'] = 0.6 * (scores[i] / 10.0) + 0.4 * original_score
                else:
                    mem['_final_score'] = mem.get('_rerank_score', 0.5)

            # 按最终分数排序
            candidates.sort(key=lambda x: x.get('_final_score', 0), reverse=True)

            logger.info(f"🎯 LLM Rerank: top scores = {[round(m.get('_final_score', 0), 2) for m in candidates[:5]]}")

            return candidates[:top_k]

        except Exception as e:
            logger.warning(f"LLM rerank failed: {e}, using original ranking")
            return memories[:top_k]

    def _calculate_confidence(
        self,
        memories: List[Dict[str, Any]],
        gaps_history: List[Dict]
    ) -> float:
        """计算整体置信度"""
        if not memories:
            return 0.0

        # Base: average relevance
        avg_relevance = sum(m.get('relevance', m.get('score', 0.5)) for m in memories) / len(memories)

        # Penalty for remaining gaps or quality issues
        gap_penalty = 0.0
        if gaps_history:
            last_entry = gaps_history[-1]
            # 🔥 FIX: gaps_history may contain 'gaps' (from GapDetector) or 'quality' (from PrefrontalFeedback)
            last_gap = last_entry.get('gaps', {})

            # Handle GapDetector format: {'has_gaps': bool, 'gap_types': [...]}
            if 'has_gaps' in last_gap and last_gap['has_gaps']:
                gap_penalty = 0.1 * len(last_gap.get('gap_types', []))
            # Handle PrefrontalFeedback format: {'quality_score': float, 'issues': [...]}
            elif 'quality_score' in last_gap:
                quality_score = last_gap.get('quality_score', 1.0)
                issues = last_gap.get('issues', [])
                # Lower quality score = higher penalty
                gap_penalty = max(0, (1.0 - quality_score) * 0.3)
                # Additional penalty for each issue
                gap_penalty += 0.05 * len(issues)

        confidence = avg_relevance - gap_penalty
        return max(0.0, min(1.0, confidence))

    def _update_stats(self, result: BrainRetrievalResult):
        """更新统计信息"""
        n = self.stats['total_queries']
        if n > 0:
            # Running average for iterations
            self.stats['avg_iterations'] = (
                self.stats['avg_iterations'] * (n - 1) + result.iterations
            ) / n
            # Running average for confidence
            self.stats['avg_confidence'] = (
                self.stats['avg_confidence'] * (n - 1) + result.confidence
            ) / n

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'fast_path_rate': (
                self.stats['fast_path_queries'] / self.stats['total_queries'] * 100
                if self.stats['total_queries'] > 0 else 0
            ),
            'fast_path_detector_stats': self.fast_path_detector.get_stats()
        }


# Singleton instance
_brain_retrieval = None


def get_brain_retrieval(memory_coordinator=None, **kwargs) -> BrainInspiredRetrieval:
    """获取脑仿生检索系统单例"""
    global _brain_retrieval
    if _brain_retrieval is None:
        _brain_retrieval = BrainInspiredRetrieval(
            memory_coordinator=memory_coordinator,
            **kwargs
        )
    elif memory_coordinator is not None:
        _brain_retrieval.memory_coordinator = memory_coordinator
    return _brain_retrieval


def reset_brain_retrieval():
    """重置单例 (主要用于测试)"""
    global _brain_retrieval
    _brain_retrieval = None
