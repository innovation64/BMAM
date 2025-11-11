"""
Result Arbiter - 结果审查机制
检查回答后的缺失/冲突，必要时自动发起补检索或外部探索
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """质量问题描述"""
    type: str  # missing_keywords, contradiction, too_short, too_verbose, low_confidence
    severity: str  # high, medium, low
    details: Dict[str, Any]
    suggested_action: str


@dataclass
class ReviewResult:
    """审查结果"""
    has_issues: bool
    issues: List[QualityIssue]
    should_retry: bool
    retry_strategy: Optional[str]
    confidence_adjustment: float  # 置信度调整系数


class ResultArbiter:
    """
    结果审查机制

    功能:
    1. 检查回答质量（关键词覆盖、矛盾、长度）
    2. 识别缺失信息并建议补检索策略
    3. 冲突检测并标记不一致记忆
    4. 触发自动重试或外部探索
    """

    def __init__(self, prefrontal_agent=None, environment_agent=None):
        self.prefrontal_agent = prefrontal_agent
        self.environment_agent = environment_agent

        # 配置阈值
        self.min_answer_length = 5
        self.max_answer_length = 500
        self.missing_keyword_threshold = 0.5  # 缺失50%以上关键词算高严重性
        self.low_confidence_threshold = 0.3

    async def review_answer(
        self,
        query: str,
        answer: str,
        memories: List[Dict[str, Any]],
        confidence: float,
        query_features: Optional[Dict[str, Any]] = None
    ) -> ReviewResult:
        """
        全面审查回答质量

        Args:
            query: 原始查询
            answer: 生成的回答
            memories: 使用的记忆
            confidence: 置信度
            query_features: 查询特征（包含关键词等）

        Returns:
            ReviewResult: 审查结果
        """
        issues = []

        # 1. 检查关键词覆盖
        keyword_issues = self._check_keyword_coverage(query, answer, query_features)
        issues.extend(keyword_issues)

        # 2. 检查答案长度
        length_issues = self._check_answer_length(answer, query)
        issues.extend(length_issues)

        # 3. 检查置信度
        confidence_issues = self._check_confidence(confidence, memories)
        issues.extend(confidence_issues)

        # 4. 检查记忆冲突（如果有Prefrontal Agent）
        if self.prefrontal_agent:
            conflict_issues = await self._check_conflicts(memories, answer)
            issues.extend(conflict_issues)

        # 5. 检查答案完整性
        completeness_issues = self._check_completeness(query, answer, memories)
        issues.extend(completeness_issues)

        # 6. 判断是否需要重试
        should_retry = any(issue.severity == 'high' for issue in issues)

        # 7. 决定重试策略
        retry_strategy = self._determine_retry_strategy(issues) if should_retry else None

        # 8. 计算置信度调整
        confidence_adjustment = self._calculate_confidence_adjustment(issues)

        # 日志记录
        if issues:
            logger.warning(f"⚠️ Answer quality issues detected: {len(issues)} issues")
            for issue in issues:
                logger.warning(f"   - {issue.type} ({issue.severity}): {issue.details}")

        if should_retry:
            logger.warning(f"⚠️ Recommending retry: {retry_strategy}")

        return ReviewResult(
            has_issues=len(issues) > 0,
            issues=issues,
            should_retry=should_retry,
            retry_strategy=retry_strategy,
            confidence_adjustment=confidence_adjustment
        )

    def _check_keyword_coverage(
        self,
        query: str,
        answer: str,
        query_features: Optional[Dict[str, Any]]
    ) -> List[QualityIssue]:
        """检查关键词覆盖"""
        issues = []

        # 提取关键词
        if query_features and 'keywords' in query_features:
            expected_keywords = query_features['keywords']
        else:
            # 简单提取（去除停用词）
            expected_keywords = self._extract_keywords(query)

        if not expected_keywords:
            return issues

        # 检查哪些关键词缺失
        answer_lower = answer.lower()
        missing_keywords = [kw for kw in expected_keywords if kw.lower() not in answer_lower]

        if missing_keywords:
            missing_ratio = len(missing_keywords) / len(expected_keywords)
            severity = 'high' if missing_ratio >= self.missing_keyword_threshold else 'medium'

            issues.append(QualityIssue(
                type='missing_keywords',
                severity=severity,
                details={
                    'missing': missing_keywords,
                    'expected': expected_keywords,
                    'missing_ratio': missing_ratio
                },
                suggested_action=f'augment_search_with_keywords: {", ".join(missing_keywords[:3])}'
            ))


        return issues

    def _check_answer_length(self, answer: str, query: str) -> List[QualityIssue]:
        """检查答案长度合理性"""
        issues = []
        answer_len = len(answer.strip())

        # 太短
        if answer_len < self.min_answer_length:
            issues.append(QualityIssue(
                type='too_short',
                severity='high',
                details={'length': answer_len, 'min': self.min_answer_length},
                suggested_action='trigger_environment_exploration'
            ))

        # 太长（可能包含不相关信息）
        elif answer_len > self.max_answer_length:
            # 检查查询类型，某些问题（如"Why"）允许长回答
            if not self._is_explanation_query(query):
                issues.append(QualityIssue(
                    type='too_verbose',
                    severity='low',
                    details={'length': answer_len, 'max': self.max_answer_length},
                    suggested_action='enable_reflection_filter'
                ))

        return issues

    def _check_confidence(self, confidence: float, memories: List[Dict]) -> List[QualityIssue]:
        """检查置信度"""
        issues = []

        if confidence < self.low_confidence_threshold:
            issues.append(QualityIssue(
                type='low_confidence',
                severity='high',
                details={
                    'confidence': confidence,
                    'threshold': self.low_confidence_threshold,
                    'memory_count': len(memories)
                },
                suggested_action='trigger_environment_exploration'
            ))

        return issues

    async def _check_conflicts(
        self,
        memories: List[Dict[str, Any]],
        answer: str
    ) -> List[QualityIssue]:
        """检查记忆冲突"""
        issues = []

        try:
            # 调用Prefrontal Agent检测冲突
            conflicts = await self.prefrontal_agent.detect_conflicts(memories)

            if conflicts.get('has_conflict'):
                conflict_details = conflicts.get('conflicts', [])

                issues.append(QualityIssue(
                    type='contradiction',
                    severity='high',
                    details={
                        'conflicts': conflict_details,
                        'conflicting_memory_count': len(conflict_details)
                    },
                    suggested_action='resolve_conflicts_with_prefrontal'
                ))

                logger.warning(f"⚠️ Detected {len(conflict_details)} conflicts in memories")

        except (asyncio.CancelledError, asyncio.TimeoutError) as e:
            logger.error(f"Error checking conflicts: {e}")

        return issues

    def _check_completeness(
        self,
        query: str,
        answer: str,
        memories: List[Dict[str, Any]]
    ) -> List[QualityIssue]:
        """检查答案完整性"""
        issues = []

        # 检查是否是多跳问题但只用了单个记忆
        if self._is_multihop_query(query) and len(memories) < 2:
            issues.append(QualityIssue(
                type='incomplete_reasoning',
                severity='medium',
                details={
                    'query_type': 'multihop',
                    'memory_count': len(memories),
                    'expected_min': 2
                },
                suggested_action='trigger_reflection_agent'
            ))

        # 检查是否包含"I don't know"或类似表达
        uncertainty_patterns = [
            r"i don't know",
            r"not sure",
            r"cannot determine",
            r"no information",
            r"unclear"
        ]

        for pattern in uncertainty_patterns:
            if re.search(pattern, answer.lower()):
                issues.append(QualityIssue(
                    type='explicit_uncertainty',
                    severity='medium',
                    details={'pattern': pattern, 'answer_excerpt': answer[:100]},
                    suggested_action='trigger_environment_exploration'
                ))
                break

        return issues

    def _determine_retry_strategy(self, issues: List[QualityIssue]) -> str:
        """根据问题类型决定重试策略"""

        # 优先级：环境探索 > Reflection推理 > 关键词补检索 > 冲突解决

        for issue in issues:
            if issue.severity == 'high':
                if issue.type in ['low_confidence', 'too_short', 'explicit_uncertainty']:
                    return 'environment_exploration'
                elif issue.type == 'contradiction':
                    return 'resolve_conflicts'
                elif issue.type == 'missing_keywords':
                    return 'augment_keywords'
                elif issue.type == 'incomplete_reasoning':
                    return 'trigger_reflection'

        return 'augment_search'

    def _calculate_confidence_adjustment(self, issues: List[QualityIssue]) -> float:
        """计算置信度调整系数"""
        adjustment = 1.0

        for issue in issues:
            if issue.severity == 'high':
                adjustment *= 0.7
            elif issue.severity == 'medium':
                adjustment *= 0.85
            elif issue.severity == 'low':
                adjustment *= 0.95

        return max(0.1, adjustment)  # 最低0.1

    def _extract_keywords(self, query: str) -> List[str]:
        """简单关键词提取（去除停用词）"""
        stopwords = {
            'what', 'when', 'where', 'who', 'why', 'how', 'is', 'are', 'was', 'were',
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'about', 'did', 'does', 'do'
        }

        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        return keywords

    def _is_explanation_query(self, query: str) -> bool:
        """判断是否是需要解释的查询（允许长回答）"""
        explanation_keywords = ['why', 'how', 'explain', 'reason', 'because']
        return any(kw in query.lower() for kw in explanation_keywords)

    def _is_multihop_query(self, query: str) -> bool:
        """判断是否是多跳推理查询"""
        multihop_patterns = [
            r"what.*and.*",
            r"who.*what.*",
            r"where.*when.*",
            r".*after.*",
            r".*before.*"
        ]
        return any(re.search(pattern, query.lower()) for pattern in multihop_patterns)


class LearningCaseLogger:
    """
    学习案例记录器
    记录失败案例到经验库，用于后续学习
    """

    def __init__(self, log_file_path: str = "data/learning_cases.jsonl"):
        self.log_file_path = log_file_path
        self._ensure_directory()

    def _ensure_directory(self):
        """确保日志目录存在"""
        from pathlib import Path
        Path(self.log_file_path).parent.mkdir(parents=True, exist_ok=True)

    async def log_failure_case(
        self,
        query: str,
        answer: str,
        memories_used: List[Dict[str, Any]],
        review_result: ReviewResult,
        expected_answer: Optional[str] = None,
        score: Optional[float] = None
    ):
        """记录失败案例"""

        case = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'answer': answer,
            'expected_answer': expected_answer,
            'score': score,
            'memories_used': [
                {
                    'id': m.get('id'),
                    'content_preview': m.get('content', '')[:100],
                    'confidence': m.get('metadata', {}).get('confidence')
                }
                for m in memories_used[:5]  # 只记录前5个
            ],
            'issues': [
                {
                    'type': issue.type,
                    'severity': issue.severity,
                    'details': issue.details
                }
                for issue in review_result.issues
            ],
            'retry_strategy': review_result.retry_strategy
        }

        # 写入JSONL文件
        try:
            import json
            from pathlib import Path

            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(case, ensure_ascii=False) + '\n')


        except (json.JSONDecodeError) as e:
            logger.error(f"Failed to log failure case: {e}")

    async def log_success_case(
        self,
        query: str,
        answer: str,
        memories_used: List[Dict[str, Any]],
        confidence: float,
        score: Optional[float] = None
    ):
        """记录成功案例（用于巩固高价值记忆）"""

        case = {
            'timestamp': datetime.now().isoformat(),
            'type': 'success',
            'query': query,
            'answer': answer,
            'score': score,
            'confidence': confidence,
            'memories_used': [m.get('id') for m in memories_used],
            'memory_hit_count': {
                m.get('id'): m.get('metadata', {}).get('hit_count', 0)
                for m in memories_used
            }
        }

        try:
            import json

            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(case, ensure_ascii=False) + '\n')


        except (json.JSONDecodeError) as e:
            logger.error(f"Failed to log success case: {e}")
