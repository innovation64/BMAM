"""
Query-Aware Dynamic Weighting (QADW) Configuration Manager
查询感知动态权重配置管理器

核心设计理念:
1. LLM-based Query Classification - 用LLM做语义分类，替代弱正则匹配
2. 软性权重 (0.0-1.0) - 真正的连续控制，无硬阈值
3. 多维度混合 - 查询可以同时具有多种特征
4. 缓存机制 - 避免重复LLM调用

学术贡献:
- Query-Aware: 实时分析每个查询，而非预定义任务类型
- Soft Weighting: 线性映射，无硬阈值截断
- LLM Classification: 比正则匹配更准确的语义理解
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging
import re
import json
import hashlib
import os

from src.core.constants import DEFAULT_LLM_MODEL

logger = logging.getLogger(__name__)


@dataclass
class QueryCharacteristics:
    """查询特征分析结果 - 多维度得分 (0.0-1.0)"""

    temporal_score: float = 0.0      # 时间推理相关性
    preference_score: float = 0.0    # 偏好相关性
    identity_score: float = 0.0      # 身份/个性化相关性
    factual_score: float = 0.0       # 事实性查询相关性

    def get_dominant_characteristic(self) -> str:
        """获取主导特征(仅用于日志)"""
        scores = {
            'temporal': self.temporal_score,
            'preference': self.preference_score,
            'identity': self.identity_score,
            'factual': self.factual_score
        }
        return max(scores.items(), key=lambda x: x[1])[0]

    def max_score(self) -> float:
        """获取最高分数"""
        return max(self.temporal_score, self.preference_score,
                   self.identity_score, self.factual_score)


@dataclass
class AdaptiveWeights:
    """
    自适应权重配置 - QADW核心

    关键原则:
    - 所有权重范围 0.0-1.0
    - 权重直接线性映射到参数，无硬阈值
    - K值范围扩大: 5-20 (而非之前的 5-15)
    """

    # 记忆检索模块权重
    episodic_weight: float = 1.0     # 情景记忆权重
    semantic_weight: float = 1.0     # 语义记忆权重
    persona_weight: float = 0.8      # 用户画像权重

    # 功能模块权重
    preference_extraction_weight: float = 0.5      # 偏好提取权重
    preference_retrieval_boost: float = 0.0        # 偏好检索增强 (0.0-0.5)
    temporal_reasoning_weight: float = 0.7         # 时间推理权重
    identity_reasoning_weight: float = 0.5         # 身份推理权重

    # 🔥 2026-01-20: 权重下限配置（避免硬编码，符合神经可塑性原则）
    # 模拟基底神经节的基线活动 - 即使被抑制也保持最小活跃度
    min_preference_weight: float = 0.15            # 偏好提取最低权重（防止完全跳过）

    # 动态检索参数 - 扩大范围
    persona_retrieval_k: int = 10                  # persona检索top-k (5-20)
    episodic_retrieval_k: int = 10                 # episodic检索top-k (5-20)
    semantic_retrieval_k: int = 5                  # semantic检索top-k

    # 融合权重
    kg_coverage_threshold: float = 0.75            # KG覆盖率阈值

    def scale_by_characteristics(self, chars: QueryCharacteristics):
        """
        根据查询特征动态调整权重 - QADW核心算法

        关键改进 (2025-12-27 FIX):
        1. K值范围扩大: 5-20 (之前 5-15)
        2. 🔥 互斥逻辑: 时间推理高分时压制偏好提取（解决LongMemEval污染问题）
        3. 线性映射，但偏好权重基础值降为0（而非0.3）
        """
        # 🔥 2025-12-28 ROLLBACK: 禁用temporal_suppression（导致LoCoMo从83%→24%）
        # 原逻辑: temporal_suppression = max(0.0, 1.0 - chars.temporal_score * 1.5)
        temporal_suppression = 1.0  # 不压制，保持原有行为

        # 1. 偏好相关权重调整 - 🔥 FIX: 基础值改为0，由preference_score和互斥因子共同决定
        # 当temporal_score=0.8时，temporal_suppression=max(0, 1-1.2)=0，偏好权重接近0
        # 当temporal_score=0.0时，temporal_suppression=1.0，偏好权重由preference_score决定
        raw_pref_weight = 0.1 + 0.7 * chars.preference_score  # 基础0.1（降低自0.3）
        self.preference_extraction_weight = raw_pref_weight * temporal_suppression

        raw_boost = 0.05 + 0.45 * chars.preference_score  # 基础0.05（降低自0.1）
        self.preference_retrieval_boost = raw_boost * temporal_suppression

        # 2. 时间推理权重调整
        self.temporal_reasoning_weight = 0.4 + 0.6 * chars.temporal_score

        # 3. 身份/个性化权重调整
        # 🔥 2025-12-28 ROLLBACK: 禁用identity_suppression（与temporal_suppression一起导致问题）
        # 原逻辑: identity_suppression = max(0.3, 1.0 - chars.temporal_score * 0.7)
        identity_suppression = 1.0  # 不压制
        self.persona_weight = (0.5 + 0.5 * chars.identity_score) * identity_suppression
        self.identity_reasoning_weight = 0.4 + 0.6 * chars.identity_score

        # 4. 动态调整检索K值 - 范围扩大到 5-20
        # 身份查询需要更多persona记忆
        self.persona_retrieval_k = 5 + int(15 * chars.identity_score)  # 5-20

        # 时间查询需要更多情景记忆
        self.episodic_retrieval_k = 5 + int(15 * chars.temporal_score)  # 5-20

        # 5. 事实性查询偏向语义记忆
        self.semantic_weight = 0.6 + 0.4 * chars.factual_score
        self.episodic_weight = 1.0 - 0.2 * chars.factual_score

        logger.debug(f"🎯 QADW权重: pref={self.preference_extraction_weight:.2f}, "
                    f"boost={self.preference_retrieval_boost:.2f}, "
                    f"temporal={self.temporal_reasoning_weight:.2f}, "
                    f"temporal_supp={temporal_suppression:.2f}, "
                    f"persona={self.persona_weight:.2f}, "
                    f"identity={self.identity_reasoning_weight:.2f}, "
                    f"persona_k={self.persona_retrieval_k}, "
                    f"episodic_k={self.episodic_retrieval_k}")


class AdaptiveConfigManager:
    """
    Query-Aware Dynamic Weighting (QADW) 配置管理器

    核心特点:
    1. LLM-based分类 (主方案) + 增强正则 (fallback)
    2. 查询缓存避免重复LLM调用
    3. 多维度得分而非单一分类
    4. 软性权重，无硬阈值
    """

    # 增强版信号检测 - 提高每个匹配的分数贡献
    # 🔥 2025-12-27 FIX: 增强时间信号检测（解决LongMemEval漏检问题）
    TEMPORAL_SIGNALS = [
        (r'\bwhen\b', 0.5),  # 强信号 (提高自0.4)
        (r'\bafter\b', 0.4),  # 提高自0.35
        (r'\bbefore\b', 0.4),  # 提高自0.35
        (r'\bduring\b', 0.3),
        (r'\btimeline\b', 0.5),
        (r'\bsequence\b', 0.4),
        (r'in what order', 0.5),
        (r'what happened', 0.45),  # 提高自0.4
        (r'\bfirst\b.*\bthen\b', 0.5),
        (r'\bfirst\b', 0.35),  # 🔥 新增：单独的first信号
        (r'\blast\b', 0.3),   # 🔥 新增：last信号
        (r'\bearlier\b', 0.35),  # 提高自0.3
        (r'\blater\b', 0.35),    # 提高自0.3
        (r'\bpreviously\b', 0.35),
        (r'\bsubsequently\b', 0.35),
        (r'how long', 0.35),   # 提高自0.3
        (r'how many days', 0.5),  # 🔥 新增：LongMemEval常见模式
        (r'which.*(came|happened|did|was).*first', 0.6),  # 🔥 新增：顺序比较问题
        (r'which.*(came|happened|did|was).*last', 0.5),   # 🔥 新增
        (r'\bmonth\b', 0.2),   # 🔥 新增：时间单位弱信号
        (r'\byear\b', 0.2),
        (r'\bday\b', 0.2),
        (r'\bweek\b', 0.2),
    ]

    PREFERENCE_SIGNALS = [
        (r'\bprefer\b', 0.5),  # 强信号
        (r'\bfavorite\b', 0.5),
        (r'like better', 0.5),
        (r'which do (i|you)', 0.5),
        (r'would (i|you) rather', 0.5),
        (r'\bchoice\b', 0.3),
        (r'between .* and', 0.4),
        (r'\binstead of\b', 0.3),
        (r'\brather than\b', 0.35),
    ]

    IDENTITY_SIGNALS = [
        (r'what is my\b', 0.6),  # 强信号
        (r'what are my\b', 0.6),
        (r'do i (like|prefer|enjoy|have)', 0.5),
        (r'my (favorite|preference|interest|hobby)', 0.6),
        (r'am i (a|an)\b', 0.4),
        (r'who am i', 0.5),
        (r'i told you', 0.5),
        (r'you know (that )?i', 0.4),
        (r'as i mentioned', 0.5),
        (r'remember (that )?i', 0.5),
        (r'about me\b', 0.5),
        (r'my (name|background|job|work|occupation)', 0.6),
        (r"(does|do) .* (like|prefer|enjoy)", 0.5),  # 第三人称身份查询
        (r"what .* (like|prefer|favorite)", 0.5),
    ]

    FACTUAL_SIGNALS = [
        (r'\bwhat\b', 0.15),  # 弱信号，避免干扰其他类型
        (r'\bwhere\b', 0.2),
        (r'\bwho\b', 0.2),
        (r'\bhow\b', 0.15),
        (r'(define|definition|meaning) of', 0.4),
        (r'(tell me|explain) about', 0.3),
    ]

    # LLM分类提示模板
    CLASSIFICATION_PROMPT = """Analyze this query and rate each dimension from 0.0 to 1.0:

Query: "{query}"

Dimensions:
- temporal: Time/sequence reasoning (when, before, after, order of events)
- identity: Personal info recall (my name, my preferences, what I told you)
- preference: Choice/comparison (prefer, favorite, which do I like better)
- factual: General fact lookup (what is X, define, explain)

Return ONLY valid JSON: {{"temporal": 0.X, "identity": 0.X, "preference": 0.X, "factual": 0.X}}"""

    def __init__(self):
        self.current_weights = AdaptiveWeights()
        self._query_history = []
        self._cache: Dict[str, QueryCharacteristics] = {}
        self._llm_client = None
        self._use_llm = True  # 是否使用LLM分类

    def _get_cache_key(self, query: str) -> str:
        """生成查询缓存键"""
        # 规范化查询用于缓存
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    async def _classify_with_llm(self, query: str) -> Optional[QueryCharacteristics]:
        """
        使用LLM进行查询分类 - QADW核心

        Returns:
            QueryCharacteristics if successful, None if failed
        """
        try:
            # 延迟导入避免循环依赖
            if self._llm_client is None:
                try:
                    import openai
                    from dotenv import load_dotenv
                    load_dotenv()
                    api_key = os.getenv('OPENAI_API_KEY')
                    if api_key:
                        self._llm_client = openai.AsyncOpenAI(api_key=api_key)
                    else:
                        logger.warning("OPENAI_API_KEY not found, using regex fallback")
                        self._use_llm = False
                        return None
                except ImportError:
                    logger.warning("openai not installed, using regex fallback")
                    self._use_llm = False
                    return None

            # 调用LLM分类
            prompt = self.CLASSIFICATION_PROMPT.format(query=query[:200])
            response = await self._llm_client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,  # 快速便宜的模型
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100
            )

            # 解析响应
            content = response.choices[0].message.content.strip()
            # 提取JSON部分
            if '{' in content and '}' in content:
                json_str = content[content.index('{'):content.rindex('}')+1]
                scores = json.loads(json_str)

                chars = QueryCharacteristics(
                    temporal_score=min(1.0, max(0.0, float(scores.get('temporal', 0)))),
                    preference_score=min(1.0, max(0.0, float(scores.get('preference', 0)))),
                    identity_score=min(1.0, max(0.0, float(scores.get('identity', 0)))),
                    factual_score=min(1.0, max(0.0, float(scores.get('factual', 0))))
                )

                logger.debug(f"🤖 LLM分类: T={chars.temporal_score:.2f}, "
                            f"I={chars.identity_score:.2f}, "
                            f"P={chars.preference_score:.2f}, "
                            f"F={chars.factual_score:.2f}")
                return chars

        except Exception as e:
            logger.debug(f"LLM classification failed: {e}, using regex fallback")

        return None

    def _classify_with_regex(self, query: str) -> QueryCharacteristics:
        """
        使用增强正则进行查询分类 - Fallback方案

        改进: 每个信号有独立的权重，而非统一的低分数
        """
        if not query:
            return QueryCharacteristics()

        query_lower = query.lower()

        temporal_score = self._calculate_signal_score(query_lower, self.TEMPORAL_SIGNALS)
        preference_score = self._calculate_signal_score(query_lower, self.PREFERENCE_SIGNALS)
        identity_score = self._calculate_signal_score(query_lower, self.IDENTITY_SIGNALS)
        factual_score = self._calculate_signal_score(query_lower, self.FACTUAL_SIGNALS)

        # 归一化 - 确保最高分接近1.0
        max_score = max(temporal_score, preference_score, identity_score, factual_score)
        if max_score > 0:
            # 归一化，但保持相对比例
            if max_score > 1.0:
                temporal_score /= max_score
                preference_score /= max_score
                identity_score /= max_score
                factual_score /= max_score
            else:
                # 如果最高分不到1.0，适度放大主导特征
                boost = min(1.0 / max_score, 1.5)  # 最多放大1.5倍
                temporal_score = min(1.0, temporal_score * boost)
                preference_score = min(1.0, preference_score * boost)
                identity_score = min(1.0, identity_score * boost)
                factual_score = min(1.0, factual_score * boost)

        chars = QueryCharacteristics(
            temporal_score=min(temporal_score, 1.0),
            preference_score=min(preference_score, 1.0),
            identity_score=min(identity_score, 1.0),
            factual_score=min(factual_score, 1.0)
        )

        logger.debug(f"📊 Regex分类: T={chars.temporal_score:.2f}, "
                    f"I={chars.identity_score:.2f}, "
                    f"P={chars.preference_score:.2f}, "
                    f"F={chars.factual_score:.2f}")

        return chars

    def _calculate_signal_score(self, query: str, signals: list) -> float:
        """计算信号强度得分 - 使用独立权重"""
        score = 0.0
        for pattern, weight in signals:
            if re.search(pattern, query):
                score += weight
        return score

    def analyze_query_characteristics(self, query: str) -> QueryCharacteristics:
        """
        分析查询特征 - 同步接口 (使用正则)

        用于不支持async的场景
        """
        cache_key = self._get_cache_key(query)
        if cache_key in self._cache:
            return self._cache[cache_key]

        chars = self._classify_with_regex(query)
        self._cache[cache_key] = chars
        return chars

    async def analyze_query_characteristics_async(self, query: str) -> QueryCharacteristics:
        """
        分析查询特征 - 异步接口 (优先使用LLM)

        用于支持async的场景，提供更准确的分类
        """
        cache_key = self._get_cache_key(query)
        if cache_key in self._cache:
            return self._cache[cache_key]

        chars = None
        if self._use_llm:
            chars = await self._classify_with_llm(query)

        if chars is None:
            chars = self._classify_with_regex(query)

        self._cache[cache_key] = chars
        return chars

    def get_adaptive_weights(self, query: str, context: Dict[str, Any] = None) -> AdaptiveWeights:
        """
        获取自适应权重配置 - 同步接口

        使用增强正则分类
        """
        context = context or {}

        # 1. 分析查询特征
        chars = self.analyze_query_characteristics(query)

        # 2. 创建基础权重
        weights = AdaptiveWeights()

        # 3. 根据特征动态调整权重
        weights.scale_by_characteristics(chars)

        # 4. 记录历史
        self._query_history.append({
            'query_sample': query[:50] if query else '',
            'characteristics': chars,
            'dominant': chars.get_dominant_characteristic()
        })

        self.current_weights = weights
        return weights

    async def get_adaptive_weights_async(self, query: str, context: Dict[str, Any] = None) -> AdaptiveWeights:
        """
        获取自适应权重配置 - 异步接口

        优先使用LLM分类，提供更准确的权重
        """
        context = context or {}

        # 1. 分析查询特征 (使用LLM)
        chars = await self.analyze_query_characteristics_async(query)

        # 2. 创建基础权重
        weights = AdaptiveWeights()

        # 3. 根据特征动态调整权重
        weights.scale_by_characteristics(chars)

        # 4. 记录历史
        self._query_history.append({
            'query_sample': query[:50] if query else '',
            'characteristics': chars,
            'dominant': chars.get_dominant_characteristic()
        })

        self.current_weights = weights
        return weights

    def get_config_summary(self) -> str:
        """获取当前配置摘要"""
        w = self.current_weights
        return (f"QADW[pref={w.preference_extraction_weight:.2f}, "
                f"temp={w.temporal_reasoning_weight:.2f}, "
                f"pers={w.persona_weight:.2f}, "
                f"id={w.identity_reasoning_weight:.2f}, "
                f"pk={w.persona_retrieval_k}, ek={w.episodic_retrieval_k}]")

    def get_feature_flags(self) -> Dict[str, bool]:
        """
        向后兼容接口 - 将权重转换为bool标志

        注意: 阈值降低，确保功能不被禁用
        """
        w = self.current_weights
        return {
            'preference_extraction': w.preference_extraction_weight > 0.25,
            'preference_aware_retrieval': w.preference_retrieval_boost > 0.05,
            'temporal_reasoning': w.temporal_reasoning_weight > 0.3,
            'identity_reasoning': w.identity_reasoning_weight > 0.3,
        }

    def compute_context_aware_k(
        self,
        conversation_turns: int,
        weights: 'AdaptiveWeights' = None
    ) -> Dict[str, int]:
        """
        🔥 2025-12-27: Context-Aware K值分配（解决LoCoMo长对话退化问题）

        根据对话长度动态调整 persona/episodic/semantic 的检索K值分配。

        核心原理：
        - 短对话 (< 5轮): episodic优先，捕获最近交互
        - 中等对话 (5-15轮): 平衡分配
        - 长对话 (> 15轮): persona优先，保持用户身份一致性

        Args:
            conversation_turns: 对话轮数
            weights: 当前的 AdaptiveWeights (可选，用于进一步调整)

        Returns:
            Dict[str, int]: {'persona': k, 'episodic': k, 'semantic': k}
        """
        weights = weights or self.current_weights

        # 计算对话长度比例 (0.0-1.0)
        # 20轮为饱和点
        turn_ratio = min(conversation_turns / 20.0, 1.0)

        if turn_ratio < 0.25:  # 短对话 (< 5轮)
            # episodic 优先 - 捕获最近交互细节
            base_k = {
                'persona': 5,
                'episodic': 12,
                'semantic': 5
            }
        elif turn_ratio < 0.75:  # 中等对话 (5-15轮)
            # 平衡分配
            base_k = {
                'persona': 8,
                'episodic': 10,
                'semantic': 4
            }
        else:  # 长对话 (> 15轮)
            # persona 优先 - 保持用户身份一致性
            base_k = {
                'persona': 12,
                'episodic': 6,
                'semantic': 3
            }

        # 🔥 根据 weights 进一步调整
        # identity_score 高 → persona K 增加
        if weights.identity_reasoning_weight > 0.6:
            base_k['persona'] = min(20, base_k['persona'] + 3)

        # temporal_score 高 → episodic K 增加
        if weights.temporal_reasoning_weight > 0.6:
            base_k['episodic'] = min(15, base_k['episodic'] + 2)

        logger.debug(f"🎯 Context-Aware K: turns={conversation_turns}, "
                    f"ratio={turn_ratio:.2f}, k={base_k}")

        return base_k

    def clear_cache(self):
        """清除查询缓存"""
        self._cache.clear()


# 全局单例
_adaptive_manager = None


def get_adaptive_config_manager() -> AdaptiveConfigManager:
    """获取全局自适应配置管理器"""
    global _adaptive_manager
    if _adaptive_manager is None:
        _adaptive_manager = AdaptiveConfigManager()
    return _adaptive_manager
