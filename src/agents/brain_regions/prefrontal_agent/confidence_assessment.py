"""
Confidence Assessment for Prefrontal Agent
置信度评估模块
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfidenceAssessmentMixin:
    """Confidence assessment mixin for PrefrontalAgent"""

    async def assess_confidence(
        self,
        query: str,
        internal_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        元认知评估: 评估内部记忆的置信度

        理论依据:
        - Koriat et al. (2006) - Feeling of Knowing (FOK)
        - Fleming & Dolan (2012) - Metacognitive accuracy in DLPFC
        - Metcalfe (2009) - Judgment of Learning (JOL)

        实现策略:
        1. 信息完整性检查: 是否有足够的记忆支持回答?
        2. 一致性检查: 检索到的记忆是否相互一致?
        3. 时效性检查: 记忆是否太旧? (对时间敏感的问题)
        4. 覆盖度检查: 问题的关键要素是否都被覆盖?

        Args:
            query: 用户问题
            internal_results: 内部检索结果 (来自Hippocampus + TemporalLobe)

        Returns:
            {
                'confidence': float (0-1),
                'should_use_external': bool,
                'reasoning': str,
                'missing_info': List[str],
                'consistency_score': float
            }
        """

        # Step 1: 信息覆盖度分析
        query_keywords = self._extract_key_concepts(query)
        covered_keywords = self._check_coverage(query_keywords, internal_results)
        coverage_ratio = len(covered_keywords) / len(query_keywords) if query_keywords else 0

        # Step 2: 一致性分析
        consistency_score = self._check_consistency(internal_results)

        # Step 3: 时效性分析 (针对"最近"、"昨天"等时间敏感问题)
        recency_score = self._check_recency(query, internal_results)

        # Step 4: 综合置信度计算
        confidence = (
            0.4 * coverage_ratio +
            0.3 * consistency_score +
            0.3 * recency_score
        )

        # Step 5: 决策是否需要外部搜索
        should_use_external = (
            confidence < 0.6 or  # 置信度低
            coverage_ratio < 0.5 or  # 覆盖不足
            consistency_score < 0.7  # 一致性差
        )


        return {
            'confidence': confidence,
            'should_use_external': should_use_external,
            'reasoning': self._generate_reasoning(confidence, coverage_ratio, consistency_score),
            'missing_info': [k for k in query_keywords if k not in covered_keywords],
            'consistency_score': consistency_score,
            'coverage_ratio': coverage_ratio,
            'recency_score': recency_score
        }

    def _extract_key_concepts(self, query: str) -> List[str]:
        """从问题中提取关键概念"""
        # 简化实现: 提取问题中的名词和动词
        import re

        # 移除停用词
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                     'can', 'could', 'may', 'might', 'must', 'what', 'when', 'where', 'who',
                     'which', 'how', 'why', 'that', 'this', 'these', 'those'}

        # 提取单词
        words = re.findall(r'\b[a-z]+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return list(set(keywords))[:10]  # 限制最多10个关键词

    def _check_coverage(self, keywords: List[str], results: List[Dict]) -> List[str]:
        """检查关键词在结果中的覆盖情况"""
        covered = []
        for keyword in keywords:
            for result in results:
                content = result.get('content', '')
                if isinstance(content, dict):
                    content = str(content)

                if keyword.lower() in content.lower():
                    covered.append(keyword)
                    break

        return list(set(covered))

    def _check_consistency(self, results: List[Dict]) -> float:
        """检查结果的一致性 (是否有矛盾)"""
        if len(results) < 2:
            return 1.0

        # 简化版: 检查时间戳一致性和内容相似性
        # 完整版应该使用LLM检测语义矛盾

        # 检查是否有明显的否定词冲突
        negation_words = ['not', 'no', 'never', 'neither', 'none', 'nobody', 'nothing']
        contents = [str(r.get('content', '')) for r in results]

        # 如果结果中既有肯定又有否定的陈述,降低一致性分数
        has_negation = any(any(neg in content.lower() for neg in negation_words) for content in contents)
        has_positive = any(not any(neg in content.lower() for neg in negation_words) for content in contents)

        if has_negation and has_positive:
            return 0.6  # 可能有冲突

        return 0.85  # 默认较高一致性

    def _check_recency(self, query: str, results: List[Dict]) -> float:
        """检查时效性"""
        time_keywords = ['yesterday', 'recently', 'last week', 'today', 'now',
                        'latest', 'current', '昨天', '最近', '今天', '现在']
        needs_recent = any(kw in query.lower() for kw in time_keywords)

        if not needs_recent:
            return 1.0  # 不需要时效性

        # 检查结果中最新记忆的时间
        if not results:
            return 0.0

        # 提取时间戳
        timestamps = []
        for r in results:
            ts = r.get('timestamp')
            if ts:
                try:
                    if isinstance(ts, str):
                        from datetime import datetime
                        timestamps.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
                    elif isinstance(ts, datetime):
                        timestamps.append(ts)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse timestamp: {e}")

        if not timestamps:
            return 0.5  # 无时间戳,中等分数

        # 计算最新记忆距离现在的时间
        latest_time = max(timestamps)
        age_hours = (datetime.now() - latest_time.replace(tzinfo=None)).total_seconds() / 3600

        # 时效性评分: < 24小时 = 1.0, > 7天 = 0.3
        if age_hours < 24:
            return 1.0
        elif age_hours < 168:  # 7天
            return 0.7
        else:
            return 0.3

    def _generate_reasoning(self, confidence: float, coverage: float, consistency: float) -> str:
        """生成可解释的推理"""
        if confidence > 0.8:
            return f"High confidence ({confidence:.2f}). Good coverage ({coverage:.2f}) and consistency ({consistency:.2f})."
        elif confidence > 0.6:
            return f"Medium confidence ({confidence:.2f}). Acceptable but may benefit from external sources."
        else:
            return f"Low confidence ({confidence:.2f}). Coverage ({coverage:.2f}) or consistency ({consistency:.2f}) insufficient. External search recommended."

