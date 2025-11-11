"""
Confidence Calculator
置信度计算器 - 统一的检索结果置信度计算
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import math
import logging

logger = logging.getLogger(__name__)


class ConfidenceCalculator:
    """
    置信度计算器

    功能:
    - 统一计算检索结果的置信度
    - 考虑多维因素: 相似度、时效性、重要性、访问频率
    - 支持不同策略的置信度标准化
    - 提供置信度分解和解释

    置信度计算公式:
    confidence = base_score * recency_factor * importance_factor * access_factor
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化置信度计算器

        Args:
            config: 配置参数
                {
                    'recency_decay': 0.001,  # 时间衰减因子
                    'min_confidence': 0.1,   # 最小置信度阈值
                    'importance_weight': 0.3 # 重要性权重
                }
        """
        self.config = config or {}
        self.recency_decay = self.config.get('recency_decay', 0.001)
        self.min_confidence = self.config.get('min_confidence', 0.1)
        self.importance_weight = self.config.get('importance_weight', 0.3)

    def calculate(
        self,
        memory: Dict[str, Any],
        base_score: float,
        strategy: str,
        **factors
    ) -> Dict[str, Any]:
        """
        计算综合置信度

        Args:
            memory: 记忆对象 (字典形式)
            base_score: 基础分数 (来自策略的相似度/匹配度)
            strategy: 检索策略名称
            **factors: 额外因素 (time_range, query_context等)

        Returns:
            {
                'confidence': 0.85,
                'components': {
                    'base_score': 0.9,
                    'recency_factor': 0.95,
                    'importance_factor': 1.0,
                    'access_factor': 1.0
                },
                'explanation': '高置信度: 语义相似度高, 最近访问'
            }
        """
        # 1. 获取记忆属性
        timestamp = self._extract_timestamp(memory)
        importance = memory.get('importance', 0.5)
        access_count = memory.get('access_count', 1)

        # 2. 计算各个因子
        recency_factor = self._calculate_recency_factor(timestamp)
        importance_factor = self._calculate_importance_factor(importance)
        access_factor = self._calculate_access_factor(access_count)

        # 3. 综合置信度
        confidence = base_score * recency_factor * importance_factor * access_factor

        # 4. 策略特定调整
        confidence = self._adjust_by_strategy(
            confidence,
            strategy,
            memory,
            **factors
        )

        # 5. 截断到合理范围
        confidence = max(self.min_confidence, min(1.0, confidence))

        # 6. 生成解释
        explanation = self._generate_explanation(
            confidence,
            base_score,
            recency_factor,
            importance_factor,
            access_factor,
            strategy
        )

        return {
            'confidence': confidence,
            'components': {
                'base_score': base_score,
                'recency_factor': recency_factor,
                'importance_factor': importance_factor,
                'access_factor': access_factor
            },
            'explanation': explanation
        }

    def _calculate_recency_factor(self, timestamp: Optional[datetime]) -> float:
        """
        计算时效性因子

        使用指数衰减: factor = exp(-decay * days_ago)

        Args:
            timestamp: 记忆创建时间

        Returns:
            时效性因子 [0.5, 1.0]
        """
        if not timestamp:
            return 0.8  # 未知时间, 默认中等

        now = datetime.now()
        days_ago = (now - timestamp).total_seconds() / 86400

        # 指数衰减, 但不低于0.5
        factor = math.exp(-self.recency_decay * days_ago)
        return max(0.5, factor)

    def _calculate_importance_factor(self, importance: float) -> float:
        """
        计算重要性因子

        Args:
            importance: 记忆重要性 [0.0, 1.0]

        Returns:
            重要性因子 [0.7, 1.3]
        """
        # 重要性加成: 范围从0.7到1.3
        factor = 0.7 + 0.6 * importance
        return factor

    def _calculate_access_factor(self, access_count: int) -> float:
        """
        计算访问频率因子

        Args:
            access_count: 访问次数

        Returns:
            访问因子 [1.0, 1.2]
        """
        # 访问次数带来小幅加成, 使用对数避免过大
        if access_count <= 1:
            return 1.0

        # log(access_count + 1) / 10, 最大1.2
        factor = 1.0 + min(0.2, math.log(access_count + 1) / 10)
        return factor

    def _adjust_by_strategy(
        self,
        confidence: float,
        strategy: str,
        memory: Dict[str, Any],
        **factors
    ) -> float:
        """
        根据策略类型调整置信度

        不同策略有不同的特点和可靠性
        """
        # 策略可靠性系数
        strategy_reliability = {
            'semantic': 1.0,      # 语义检索: 基准
            'temporal': 0.95,     # 时间检索: 稍低
            'episodic': 0.9,      # 情节检索: 较低
            'associative': 0.85,  # 关联检索: 更低
            'pattern': 0.8,       # 模式补全: 不太可靠
            'contextual': 0.9,    # 上下文检索: 较可靠
            'multi': 1.05,        # 多策略: 更可靠
        }

        reliability = strategy_reliability.get(strategy, 1.0)
        return confidence * reliability

    def _extract_timestamp(self, memory: Dict[str, Any]) -> Optional[datetime]:
        """
        从记忆中提取时间戳

        尝试多个可能的字段
        """
        # 尝试多个字段
        for field in ['created_at', 'timestamp', 'time', 'date']:
            value = memory.get(field)
            if value:
                if isinstance(value, datetime):
                    return value
                elif isinstance(value, (int, float)):
                    return datetime.fromtimestamp(value)
                elif isinstance(value, str):
                    try:
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        continue

        return None

    def _generate_explanation(
        self,
        confidence: float,
        base_score: float,
        recency_factor: float,
        importance_factor: float,
        access_factor: float,
        strategy: str
    ) -> str:
        """
        生成置信度解释

        Args:
            confidence: 最终置信度
            base_score: 基础分数
            recency_factor: 时效性因子
            importance_factor: 重要性因子
            access_factor: 访问因子
            strategy: 策略名称

        Returns:
            置信度解释文本
        """
        reasons = []

        # 置信度等级
        if confidence >= 0.8:
            level = "高置信度"
        elif confidence >= 0.6:
            level = "中等置信度"
        else:
            level = "低置信度"

        # 基础分数
        if base_score >= 0.8:
            reasons.append("匹配度高")
        elif base_score >= 0.6:
            reasons.append("匹配度中等")
        else:
            reasons.append("匹配度较低")

        # 时效性
        if recency_factor >= 0.9:
            reasons.append("最近创建")
        elif recency_factor < 0.7:
            reasons.append("时间较久")

        # 重要性
        if importance_factor >= 1.1:
            reasons.append("重要记忆")

        # 访问频率
        if access_factor > 1.1:
            reasons.append("经常访问")

        # 组合解释
        explanation = f"{level}: {', '.join(reasons)}"

        return explanation

    def batch_calculate(
        self,
        memories: List[Dict[str, Any]],
        strategy: str,
        **factors
    ) -> List[Dict[str, Any]]:
        """
        批量计算置信度

        Args:
            memories: 记忆列表 (每个记忆应包含base_score字段)
            strategy: 策略名称
            **factors: 额外因素

        Returns:
            添加了置信度信息的记忆列表
        """
        results = []

        for mem_item in memories:
            memory = mem_item.get('memory', {})
            base_score = mem_item.get('retrieval_confidence', 0.5)

            # 计算置信度
            confidence_info = self.calculate(
                memory,
                base_score,
                strategy,
                **factors
            )

            # 更新记忆项
            mem_item['retrieval_confidence'] = confidence_info['confidence']
            mem_item['confidence_components'] = confidence_info['components']
            mem_item['confidence_explanation'] = confidence_info['explanation']

            results.append(mem_item)

        return results
