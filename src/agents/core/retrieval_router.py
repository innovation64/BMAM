"""
Retrieval Strategy Router
检索策略路由器 - 对应前额叶执行控制

神经科学依据:
- DLPFC (背外侧前额叶) 根据任务需求选择检索策略
- 策略类型: 直接检索、生成检索、联想检索、情景检索

文献:
- Badre & D'Esposito (2009) "Prefrontal cortex and cognitive control"
- Moscovitch & Winocur (2002) "Prefrontal retrieval control"
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import re

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...utils.config import get_logger

logger = get_logger(__name__)


class RetrievalStrategy(Enum):
    """检索策略类型"""
    SEMANTIC = "semantic"        # 语义向量检索
    EPISODIC = "episodic"        # 情景记忆检索 (时序线索)
    ASSOCIATIVE = "associative"  # 关联检索 (记忆链)
    KEYWORD = "keyword"          # 关键词检索 (BM25)
    MULTI_STRATEGY = "multi_strategy"  # 混合策略


@dataclass
class QueryFeatures:
    """查询特征提取结果"""
    has_temporal_markers: bool = False  # "上周", "昨天"
    entities: List[str] = None          # ["Alice", "Bob"]
    has_relation_words: bool = False    # "和", "之间"
    is_factual_question: bool = False   # "什么", "哪个"
    is_why_question: bool = False       # "为什么"
    is_when_question: bool = False      # "什么时候"
    query_length: int = 0
    complexity: str = "medium"          # "low", "medium", "high"

    def to_dict(self) -> Dict:
        return {
            'has_temporal_markers': self.has_temporal_markers,
            'entities': self.entities or [],
            'has_relation_words': self.has_relation_words,
            'is_factual_question': self.is_factual_question,
            'is_why_question': self.is_why_question,
            'is_when_question': self.is_when_question,
            'query_length': self.query_length,
            'complexity': self.complexity
        }


class RetrievalStrategyRouter(BrainAgent):
    """
    检索策略路由器

    对应脑区: 前额叶背外侧 (DLPFC)
    功能:
    1. 分析查询特征
    2. 选择最优检索策略
    3. 动态调整策略权重
    """

    def __init__(self):
        super().__init__(
            agent_id="retrieval_router",
            brain_region=BrainRegion.PREFRONTAL,
            system_prompt="""你是检索策略路由器，负责根据查询类型选择最优检索策略。

策略类型:
- semantic: 语义概念查询 ("关于咖啡的记忆")
- episodic: 时序情景查询 ("上周发生了什么")
- associative: 关联记忆查询 ("Alice相关的内容")
- keyword: 精确事实查询 ("Alice买了什么咖啡机")
- multi_strategy: 混合策略查询 (复杂查询)

你需要分析查询特征并选择最合适的策略。"""
        )

        # 策略选择统计
        self.strategy_stats = {strategy: 0 for strategy in RetrievalStrategy}
        self.strategy_success_rate = {strategy: 0.5 for strategy in RetrievalStrategy}

        # 规则权重 (可学习调整) - 优化后的权重
        self.rule_weights = {
            'temporal_to_episodic': 0.9,
            'entity_relation_to_associative': 0.95,  # 提高关联检索优先级
            'factual_to_keyword': 0.8,
            'complex_to_multi': 0.90  # 提高复杂查询的multi_strategy优先级
        }

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理路由请求"""
        action = message.content.get('action')

        if action == 'select_strategy':
            query = message.content['query']
            context = message.content.get('context', {})
            return await self._select_retrieval_strategy(query, context)

        elif action == 'update_strategy_feedback':
            # 更新策略成功率 (强化学习)
            return await self._update_strategy_feedback(message.content)

        return {'error': f'Unknown action: {action}'}

    async def _select_retrieval_strategy(
        self,
        query: str,
        context: Dict
    ) -> Dict[str, Any]:
        """
        选择检索策略

        决策流程:
        1. 提取查询特征
        2. 应用决策规则
        3. 计算策略分数
        4. 选择最优策略
        """
        # Step 1: 提取查询特征
        features = self._extract_query_features(query)

        # Step 2: 计算各策略的分数
        strategy_scores = {}

        # Episodic策略分数 (时序查询)
        if features.has_temporal_markers or features.is_when_question:
            strategy_scores[RetrievalStrategy.EPISODIC] = (
                0.9 * self.rule_weights['temporal_to_episodic']
            )

        # Associative策略分数 (关联查询)
        if features.entities and features.has_relation_words:
            num_entities = len(features.entities)
            if num_entities >= 2:
                strategy_scores[RetrievalStrategy.ASSOCIATIVE] = (
                    0.85 * self.rule_weights['entity_relation_to_associative']
                )

        # Keyword策略分数 (精确事实查询)
        if features.is_factual_question and features.entities:
            strategy_scores[RetrievalStrategy.KEYWORD] = (
                0.8 * self.rule_weights['factual_to_keyword']
            )

        # Multi-strategy策略分数 (复杂查询)
        if features.complexity == 'high' or features.is_why_question:
            strategy_scores[RetrievalStrategy.MULTI_STRATEGY] = (
                0.75 * self.rule_weights['complex_to_multi']
            )

        # Semantic策略分数 (默认基线)
        strategy_scores[RetrievalStrategy.SEMANTIC] = 0.6

        # Step 3: 调整分数 (基于历史成功率)
        for strategy, score in strategy_scores.items():
            historical_success = self.strategy_success_rate.get(strategy, 0.5)
            strategy_scores[strategy] = score * (0.7 + 0.3 * historical_success)

        # Step 4: 选择最优策略
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
        selected_strategy = best_strategy[0]
        confidence = best_strategy[1]

        # 更新统计
        self.strategy_stats[selected_strategy] += 1

        logger.info(f"📍 Selected strategy: {selected_strategy.value} "
                   f"(confidence={confidence:.2f})")
        logger.debug(f"Query features: {features.to_dict()}")
        logger.debug(f"Strategy scores: {[(s.value, f'{score:.2f}') for s, score in strategy_scores.items()]}")

        return {
            'strategy': selected_strategy.value,
            'confidence': confidence,
            'features': features.to_dict(),
            'alternative_strategies': sorted(
                [(s.value, score) for s, score in strategy_scores.items()],
                key=lambda x: x[1],
                reverse=True
            )[1:3]  # 备选策略
        }

    def _extract_query_features(self, query: str) -> QueryFeatures:
        """
        提取查询特征

        特征工程:
        - 时间标记: "上周", "昨天", "最近"
        - 实体识别: 大写开头词 / 常见名词
        - 关系词: "和", "与", "之间"
        - 问句类型: "什么", "为什么", "什么时候"
        """
        query_lower = query.lower()

        # 时间标记检测
        temporal_markers = [
            '上周', '昨天', '最近', '之前', '今天', '明天', '刚才',
            'yesterday', 'recently', 'last week', 'just now', 'earlier'
        ]
        has_temporal = any(marker in query_lower for marker in temporal_markers)

        # 实体识别 (简化版)
        entities = []
        # 英文大写开头
        english_entities = re.findall(r'\b[A-Z][a-z]+\b', query)
        entities.extend(english_entities)

        # 中文常见实体 (可扩展为NER)
        chinese_entities = [
            '咖啡机', '咖啡豆', '茶', '书', '电影', '音乐',
            '旅行', '东京', '日本', '北京', '上海'
        ]
        entities.extend([e for e in chinese_entities if e in query])

        # 关系词检测
        relation_words = [
            '和', '与', '之间', '共同', '关系', '相关',
            'and', 'with', 'between', 'relationship', 'related'
        ]
        has_relation = any(word in query_lower for word in relation_words)

        # 问句类型检测
        factual_questions = [
            '什么', '哪个', '谁', '多少', '哪里',
            'what', 'which', 'who', 'how many', 'where'
        ]
        is_factual = any(q in query_lower for q in factual_questions)

        is_why = '为什么' in query or 'why' in query_lower
        is_when = '什么时候' in query or 'when' in query_lower or has_temporal

        # 复杂度评估
        query_len = len(query)
        # "为什么"问句通常需要复杂推理，强制标记为high
        if is_why or query_len > 50 or (len(entities) > 1 and has_relation):
            complexity = 'high'
        elif query_len > 20:
            complexity = 'medium'
        else:
            complexity = 'low'

        return QueryFeatures(
            has_temporal_markers=has_temporal,
            entities=entities,
            has_relation_words=has_relation,
            is_factual_question=is_factual,
            is_why_question=is_why,
            is_when_question=is_when,
            query_length=query_len,
            complexity=complexity
        )

    async def _update_strategy_feedback(self, feedback: Dict) -> Dict:
        """
        更新策略成功率 (强化学习)

        Args:
            feedback: {
                'strategy': str,
                'success': bool,
                'user_satisfaction': float  # 0-1
            }
        """
        strategy_name = feedback['strategy']
        strategy = RetrievalStrategy(strategy_name)

        success = feedback.get('success', False)
        satisfaction = feedback.get('user_satisfaction', 0.5)

        # 简单移动平均更新
        current_rate = self.strategy_success_rate[strategy]
        alpha = 0.1  # 学习率

        new_rate = current_rate * (1 - alpha) + satisfaction * alpha
        self.strategy_success_rate[strategy] = new_rate

        logger.info(f"Updated {strategy_name} success rate: "
                   f"{current_rate:.2f} → {new_rate:.2f}")

        return {
            'strategy': strategy_name,
            'old_rate': current_rate,
            'new_rate': new_rate
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        total_queries = sum(self.strategy_stats.values())

        return {
            'total_queries': total_queries,
            'strategy_distribution': {
                s.value: count for s, count in self.strategy_stats.items()
            },
            'strategy_success_rates': {
                s.value: rate for s, rate in self.strategy_success_rate.items()
            }
        }