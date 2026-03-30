"""
Routing Manager Module
Handles intelligent routing decisions, query analysis, and strategy selection
"""

from typing import Dict, Any, List, Optional, Iterable
from ..utils.config import get_logger

logger = get_logger(__name__)


class RoutingManager:
    """Manages routing decisions and query feature analysis"""

    def __init__(self, memory_signal_config: Dict[str, Any],
                 pattern_getter_fn, phrases_checker_fn,
                 task_type_keywords_fn, kg_patterns_fn):
        """
        Initialize Routing Manager

        Args:
            memory_signal_config: Memory signal configuration
            pattern_getter_fn: Function to get query patterns
            phrases_checker_fn: Function to check phrases in text
            task_type_keywords_fn: Function to get task type keywords
            kg_patterns_fn: Function to get KG patterns
        """
        self.memory_signal_config = memory_signal_config
        self._get_query_patterns = pattern_getter_fn
        self._phrases_in_text = phrases_checker_fn
        self._get_task_type_keywords = task_type_keywords_fn
        self._get_kg_patterns = kg_patterns_fn

        # 🔥 NEW: Learnable strategy weights (can be updated by LearningManager)
        # These weights are multiplied with strategy scores to bias selection
        self.strategy_weights = {
            'keyword_search': 1.0,
            'semantic_search': 1.0,
            'episodic_search': 1.0,
            'associative_search': 1.0,
            'multi_strategy_search': 1.0,
            'episodic': 1.0,
            'semantic': 1.0,
            'temporal': 1.0,
            'hybrid': 1.0,
            'kg_joint': 1.0
        }

        # 🔥 NEW: Performance history for learning
        self.strategy_performance = {
            strategy: {'success': 0, 'failure': 0, 'total_confidence': 0.0}
            for strategy in self.strategy_weights.keys()
        }

        # 🔥 NEW: Learning rate for weight updates
        self.learning_rate = 0.1

        # 🔥 2026-03-30: 持久化权重
        self._weights_path = None
        try:
            from ..utils.paths import BMAMPaths
            self._weights_path = BMAMPaths.DATA_DIR / 'state' / 'routing_weights.json'
            self._load_persisted_weights()
        except Exception:
            pass

    def _load_persisted_weights(self):
        """Load strategy weights from disk."""
        import json
        if self._weights_path and self._weights_path.exists():
            try:
                with open(self._weights_path, 'r') as f:
                    saved = json.load(f)
                self.strategy_weights.update(saved.get('weights', {}))
                self.strategy_performance.update(saved.get('performance', {}))
                logger.debug(f"Loaded routing weights from {self._weights_path}")
            except Exception as e:
                logger.debug(f"Could not load routing weights: {e}")

    def _save_persisted_weights(self):
        """Save strategy weights to disk."""
        import json
        if not self._weights_path:
            return
        try:
            self._weights_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._weights_path, 'w') as f:
                json.dump({
                    'weights': self.strategy_weights,
                    'performance': self.strategy_performance,
                }, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save routing weights: {e}")

    def update_strategy_weight(self, strategy: str, delta: float) -> None:
        """
        Update a strategy's weight based on learning feedback
        基于学习反馈更新策略权重

        Args:
            strategy: Strategy name
            delta: Weight change (+/-)
        """
        if strategy in self.strategy_weights:
            old_weight = self.strategy_weights[strategy]
            # Clamp weight between 0.5 and 2.0 to prevent extreme bias
            new_weight = max(0.5, min(2.0, old_weight + delta * self.learning_rate))
            self.strategy_weights[strategy] = new_weight
            self._save_persisted_weights()
            logger.info(f"📊 Strategy weight updated: {strategy} {old_weight:.3f} → {new_weight:.3f}")

    def record_strategy_outcome(
        self,
        strategy: str,
        success: bool,
        confidence: float = 0.0
    ) -> None:
        """
        Record the outcome of a retrieval strategy for learning
        记录检索策略的结果用于学习

        Args:
            strategy: Strategy used
            success: Whether retrieval was successful
            confidence: Confidence score of the result
        """
        if strategy not in self.strategy_performance:
            self.strategy_performance[strategy] = {'success': 0, 'failure': 0, 'total_confidence': 0.0}

        if success:
            self.strategy_performance[strategy]['success'] += 1
        else:
            self.strategy_performance[strategy]['failure'] += 1
        self.strategy_performance[strategy]['total_confidence'] += confidence

        self._save_persisted_weights()
        logger.debug(f"📈 Strategy outcome recorded: {strategy} success={success} conf={confidence:.2f}")

    def get_strategy_success_rate(self, strategy: str) -> float:
        """Get success rate for a strategy"""
        if strategy not in self.strategy_performance:
            return 0.5  # Default neutral

        perf = self.strategy_performance[strategy]
        total = perf['success'] + perf['failure']
        if total == 0:
            return 0.5
        return perf['success'] / total

    def get_learnable_weights(self) -> Dict[str, float]:
        """Get current learnable weights"""
        return self.strategy_weights.copy()

    def set_learnable_weights(self, weights: Dict[str, float]) -> None:
        """Set learnable weights (for loading from checkpoint)"""
        for strategy, weight in weights.items():
            if strategy in self.strategy_weights:
                self.strategy_weights[strategy] = max(0.5, min(2.0, weight))


    async def select_optimal_retrieval_strategy(self, query: str, context: Dict[str, Any]) -> str:
        """
        智能检索策略选择 - 模拟人脑的自适应检索机制

        人脑检索策略选择原理:
        1. 模式识别 - 识别查询的认知模式
        2. 上下文感知 - 基于当前上下文调整策略
        3. 经验学习 - 从成功检索中学习最优策略
        4. 动态适应 - 根据检索结果动态调整

        Args:
            query: Query text
            context: Context dict

        Returns:
            Strategy name (str)
        """
        # 分析查询的认知特征
        query_features = await self.analyze_query_features(query, context)

        # 基于记忆激活和认知负荷选择策略
        raw_scores = {
            'keyword_search': self.evaluate_keyword_search_suitability(query_features),
            'semantic_search': self.evaluate_semantic_search_suitability(query_features),
            'episodic_search': self.evaluate_episodic_search_suitability(query_features),
            'associative_search': self.evaluate_associative_search_suitability(query_features),
            'multi_strategy_search': self.evaluate_multi_strategy_suitability(query_features)
        }

        # 🔥 FIX: Apply learnable weights to bias strategy selection
        strategy_scores = {
            strategy: score * self.strategy_weights.get(strategy, 1.0)
            for strategy, score in raw_scores.items()
        }

        # 选择最高分的策略
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
        strategy_name = best_strategy[0]
        confidence = best_strategy[1]

        logger.debug(f"Strategy selection: {strategy_name} (weighted_score={confidence:.3f})")

        return strategy_name

    async def analyze_query_features(self, query: str, context: Dict[str, Any],
                                    language: str = 'en') -> Dict[str, Any]:
        """
        分析查询的认知特征 - 模拟人脑对信息的特征提取

        Args:
            query: Query text
            context: Context dict
            language: Language code

        Returns:
            Features dict with extracted cognitive features
        """
        query_lower = query.lower()

        features = {
            'length': len(query),
            'word_count': len(query.split()),
            'question_words': [],
            'time_indicators': [],
            'entities': [],
            'has_numerical_data': False,
            'complexity_score': 0.0,
            'specificity_score': 0.0,
            'temporal_nature': False,
            'relational_nature': False,
            'query_lower': query_lower,
            'language': language
        }

        # 识别疑问词 (模式识别)
        question_patterns = {
            'what': 'fact_finding', 'which': 'selection', 'who': 'identity',
            'when': 'temporal', 'where': 'spatial', 'why': 'causal',
            'how': 'procedural', 'how many': 'quantitative'
        }
        for pattern, qtype in question_patterns.items():
            if pattern in query_lower:
                features['question_words'].append((pattern, qtype))

        # 识别时间指示器
        time_patterns = self._get_query_patterns('temporal_keywords', language)
        features['temporal_nature'] = self._phrases_in_text(time_patterns, query_lower)

        # 识别关系性词汇
        relational_patterns = self._get_query_patterns('relational_keywords', language)
        features['relational_nature'] = self._phrases_in_text(relational_patterns, query_lower)

        # 识别数值数据
        import re
        numerical_patterns = re.findall(r'\d+', query)
        features['has_numerical_data'] = len(numerical_patterns) > 0

        # 从上下文中提取实体
        features['entities'] = context.get('entities', [])

        # 计算复杂度分数
        features['complexity_score'] = self.calculate_complexity_score(features)

        # 计算特指性分数
        features['specificity_score'] = self.calculate_specificity_score(features)

        return features

    def calculate_complexity_score(self, features: Dict[str, Any]) -> float:
        """
        计算查询复杂度分数

        Args:
            features: Query features

        Returns:
            Complexity score (0.0-1.0)
        """
        score = 0.0

        # 词数多 → 复杂
        word_count = features.get('word_count', 0)
        if word_count > 10:
            score += 0.3
        elif word_count > 5:
            score += 0.15

        # 有关系性词汇 → 复杂
        if features.get('relational_nature', False):
            score += 0.3

        # 有疑问词 → 适度增加复杂度
        question_count = len(features.get('question_words', []))
        score += min(question_count * 0.1, 0.2)

        # 有多个实体 → 复杂
        entity_count = len(features.get('entities', []))
        if entity_count > 2:
            score += 0.2

        return min(score, 1.0)

    def calculate_specificity_score(self, features: Dict[str, Any]) -> float:
        """
        计算查询特指性分数

        Args:
            features: Query features

        Returns:
            Specificity score (0.0-1.0)
        """
        score = 0.0

        # 有实体 → 特指性高
        entity_count = len(features.get('entities', []))
        score += min(entity_count * 0.25, 0.5)

        # 有时间指示 → 特指性高
        if features.get('temporal_nature', False):
            score += 0.3

        # 有数值数据 → 特指性高
        if features.get('has_numerical_data', False):
            score += 0.2

        return min(score, 1.0)

    def evaluate_keyword_search_suitability(self, features: Dict[str, Any]) -> float:
        """评估关键词检索适合度"""
        score = 0.0

        # 特指性高 → 适合关键词检索
        score += features.get('specificity_score', 0) * 0.5

        # 词数少 → 适合关键词检索
        word_count = features.get('word_count', 0)
        if word_count <= 5:
            score += 0.3

        # 有数值数据 → 适合关键词检索
        if features.get('has_numerical_data', False):
            score += 0.2

        return min(score, 1.0)

    def evaluate_semantic_search_suitability(self, features: Dict[str, Any]) -> float:
        """评估语义检索适合度"""
        score = 0.0

        # 复杂度高 → 适合语义检索
        score += features.get('complexity_score', 0) * 0.5

        # 词数多 → 适合语义检索
        word_count = features.get('word_count', 0)
        if word_count > 10:
            score += 0.3

        # 关系性查询 → 适合语义检索
        if features.get('relational_nature', False):
            score += 0.2

        return min(score, 1.0)

    def evaluate_episodic_search_suitability(self, features: Dict[str, Any]) -> float:
        """评估情节检索适合度"""
        score = 0.0

        # 有时间指示 → 适合情节检索
        if features.get('temporal_nature', False):
            score += 0.5

        # 有疑问词 "when", "where" → 适合情节检索
        question_words = features.get('question_words', [])
        episodic_types = ['temporal', 'spatial']
        has_episodic = any(qtype in episodic_types for _, qtype in question_words)
        if has_episodic:
            score += 0.3

        # 有实体 → 适合情节检索
        if len(features.get('entities', [])) > 0:
            score += 0.2

        return min(score, 1.0)

    def evaluate_associative_search_suitability(self, features: Dict[str, Any]) -> float:
        """评估联想检索适合度"""
        score = 0.0

        # 关系性查询 → 适合联想检索
        if features.get('relational_nature', False):
            score += 0.6

        # 复杂度适中 → 适合联想检索
        complexity = features.get('complexity_score', 0)
        if 0.3 <= complexity <= 0.7:
            score += 0.4

        return min(score, 1.0)

    def evaluate_multi_strategy_suitability(self, features: Dict[str, Any]) -> float:
        """评估多策略检索适合度"""
        score = 0.0

        # 特征多样性高 → 适合多策略检索
        feature_diversity = sum([
            features.get('temporal_nature', False),
            features.get('relational_nature', False),
            features.get('has_numerical_data', False),
            len(features.get('entities', [])) > 0
        ])

        score += feature_diversity * 0.2

        # 复杂度和特指性都中等 → 适合多策略检索
        complexity = features.get('complexity_score', 0)
        specificity = features.get('specificity_score', 0)
        if 0.3 <= complexity <= 0.7 and 0.3 <= specificity <= 0.7:
            score += 0.4

        return min(score, 1.0)

    async def decide_retrieval_route(
        self,
        query_features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        前额叶路由决策：无硬编码，基于特征动态决策

        类脑原理:
        - 前额叶执行控制：分析、决策、选择
        - 基于查询特征和上下文动态决策
        - 多维度评分，选择最优策略

        Args:
            query_features: 查询特征
            context: 上下文

        Returns:
            {
                'recommended_strategy': str,
                'confidence': float,
                'reasoning': str,
                'alpha': float (for hybrid)
            }
        """
        # 计算各策略的适合度分数（基于特征，无硬编码）
        raw_scores = {}

        # 1. 情节记忆适合度
        episodic_score = self.calculate_episodic_suitability(query_features, context)
        raw_scores['episodic'] = episodic_score

        # 2. 语义记忆适合度
        semantic_score = self.calculate_semantic_suitability(query_features, context)
        raw_scores['semantic'] = semantic_score

        # 3. 时间线检索适合度
        temporal_score = self.calculate_temporal_suitability(query_features, context)
        raw_scores['temporal'] = temporal_score

        # 4. 混合检索适合度
        hybrid_score = self.calculate_hybrid_suitability(query_features, context)
        raw_scores['hybrid'] = hybrid_score

        # 5. KG联合检索适合度
        kg_score = self.calculate_kg_suitability(query_features, context)
        raw_scores['kg_joint'] = kg_score

        # 🔥 FIX: Apply learnable weights to bias strategy selection
        scores = {
            strategy: score * self.strategy_weights.get(strategy, 1.0)
            for strategy, score in raw_scores.items()
        }

        # 选择分数最高的策略
        best_strategy = max(scores, key=scores.get)
        best_score = scores[best_strategy]

        # 生成推理说明
        reasoning = self.generate_route_reasoning(best_strategy, query_features, scores)

        # 如果是混合检索，动态计算alpha（基于特征，无硬编码）
        alpha = self.calculate_dynamic_alpha(query_features) if best_strategy == 'hybrid' else 0.5

        return {
            'recommended_strategy': best_strategy,
            'confidence': best_score,
            'reasoning': reasoning,
            'scores': scores,
            'alpha': alpha
        }

    def calculate_episodic_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算情节记忆检索适合度（无硬编码阈值）"""
        score = 0.0

        # 特指性高 → 适合情节记忆
        score += features.get('specificity_score', 0) * 0.4

        # 有时间指示 → 适合情节记忆
        if features.get('temporal_nature', False):
            score += 0.3

        # 有实体 → 适合情节记忆
        entity_count = len(features.get('entities', []))
        score += min(entity_count * 0.1, 0.3)

        return min(score, 1.0)

    def calculate_semantic_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算语义记忆检索适合度（无硬编码阈值）"""
        score = 0.0

        # 复杂度高 → 适合语义记忆
        score += features.get('complexity_score', 0) * 0.4

        # 概念性问题 → 适合语义记忆
        question_words = features.get('question_words', [])
        conceptual_types = ['causal', 'procedural']
        has_conceptual = any(qtype in conceptual_types for _, qtype in question_words)
        if has_conceptual:
            score += 0.3

        # 关系性查询 → 适合语义记忆
        if features.get('relational_nature', False):
            score += 0.3

        return min(score, 1.0)

    def calculate_temporal_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算时间线检索适合度（无硬编码阈值）"""
        score = 0.0

        # 强时间性 → 适合时间线检索
        if features.get('temporal_nature', False):
            score += 0.6

        # 时间相关问题词
        question_words = features.get('question_words', [])
        has_temporal_question = any(qtype == 'temporal' for _, qtype in question_words)
        if has_temporal_question:
            score += 0.4

        return min(score, 1.0)

    def calculate_hybrid_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算混合检索适合度（无硬编码阈值）"""
        score = 0.0

        # 复杂度和特指性都中等 → 适合混合检索
        complexity = features.get('complexity_score', 0)
        specificity = features.get('specificity_score', 0)

        # 两者平衡时适合混合检索
        balance = 1.0 - abs(complexity - specificity)
        score += balance * 0.5

        # 词数适中 → 适合混合检索
        word_count = features.get('word_count', 0)
        if 5 <= word_count <= 15:
            score += 0.3

        # 有多种特征 → 适合混合检索
        feature_diversity = sum([
            features.get('temporal_nature', False),
            features.get('relational_nature', False),
            len(features.get('entities', [])) > 0,
            features.get('has_numerical_data', False)
        ])
        score += feature_diversity * 0.05

        return min(score, 1.0)

    def calculate_kg_suitability(
        self,
        features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> float:
        """计算KG联合检索适合度（无硬编码阈值）"""
        score = 0.0

        # 有实体 → 适合KG检索
        entity_count = len(features.get('entities', []))
        score += min(entity_count * 0.3, 0.6)

        # 关系性查询 → 适合KG检索
        if features.get('relational_nature', False):
            score += 0.4

        return min(score, 1.0)

    def calculate_dynamic_alpha(self, features: Dict[str, Any]) -> float:
        """
        动态计算混合检索的alpha（无硬编码）

        基于查询特征自动调整BM25和Vector权重

        Args:
            features: Query features

        Returns:
            Alpha value (0.0-1.0)
        """
        from ..utils.memory_signal_config import DEFAULT_MEMORY_SIGNAL_CONFIG

        # 特指性高 → alpha高（偏重BM25精确匹配）
        specificity = features.get('specificity_score', 0.5)

        # 复杂度高 → alpha低（偏重Vector语义理解）
        complexity = features.get('complexity_score', 0.5)

        retrieval_cfg = self.memory_signal_config.get('retrieval', DEFAULT_MEMORY_SIGNAL_CONFIG['retrieval'])
        query_lower = features.get('query_lower', '')
        factual_keywords = retrieval_cfg.get(
            'factual_keywords',
            DEFAULT_MEMORY_SIGNAL_CONFIG['retrieval']['factual_keywords']
        )

        # 使用简单子串匹配
        has_factual_keyword = any(kw in query_lower for kw in factual_keywords)

        # 动态平衡
        alpha = specificity * 0.6 + (1 - complexity) * 0.4

        # 如果包含事实型关键词，提升BM25权重
        if has_factual_keyword:
            alpha_boost = retrieval_cfg.get('alpha_boost', 0.15)
            alpha_cap = retrieval_cfg.get('alpha_cap', 0.7)
            alpha += alpha_boost
            alpha = min(alpha, alpha_cap)

        # 限制在合理范围
        alpha_floor = retrieval_cfg.get('alpha_floor', 0.3)
        alpha_cap = retrieval_cfg.get('alpha_cap', 0.7)
        alpha = max(alpha_floor, min(alpha_cap, alpha))

        return alpha

    def generate_route_reasoning(
        self,
        strategy: str,
        features: Dict[str, Any],
        scores: Dict[str, float]
    ) -> str:
        """生成路由决策推理说明"""
        reasoning_templates = {
            'episodic': f"具体事件查询（特指性={features.get('specificity_score', 0):.2f}）",
            'semantic': f"概念性查询（复杂度={features.get('complexity_score', 0):.2f}）",
            'temporal': "时间相关查询",
            'hybrid': f"平衡查询（复杂度={features.get('complexity_score', 0):.2f}, 特指性={features.get('specificity_score', 0):.2f}）",
            'kg_joint': f"知识图谱增强查询（实体数={len(features.get('entities', []))}）"
        }

        base_reason = reasoning_templates.get(strategy, "默认策略")
        top_3_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        score_info = ", ".join([f"{s}={sc:.2f}" for s, sc in top_3_scores])

        return f"{base_reason} | 分数: {score_info}"

    def looks_temporal_query(self, query: str) -> bool:
        """检测查询是否具有时间性特征"""
        temporal_patterns = self._get_query_patterns('temporal_keywords', 'en')
        return self._phrases_in_text(temporal_patterns, query.lower())

    def looks_research_event_query(self, query: str) -> bool:
        """检测查询是否为研究事件查询"""
        event_patterns = self._get_query_patterns('event_keywords', 'en')
        return self._phrases_in_text(event_patterns, query.lower())

