"""
Collaboration Triggers - 脑区协作触发器
根据查询特征和记忆状态，智能触发不同脑区的协作
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TriggerDecision:
    """触发决策"""
    should_trigger: bool
    trigger_type: str
    reason: str
    priority: int  # 1=highest, 5=lowest
    parameters: Dict[str, Any]


class CollaborationTriggerSystem:
    """
    脑区协作触发系统

    功能:
    1. 分析查询类型和记忆覆盖情况
    2. 决定是否触发 Reflection/KG/Environment/Prefrontal 协作
    3. 协调多脑区并行工作
    """

    def __init__(self):
        # 触发阈值配置
        self.config = {
            'reflection': {
                'coverage_threshold': 0.5,
                'abstract_coverage_threshold': 0.7,
                'identity_coverage_threshold': 0.8
            },
            'prefrontal': {
                'confidence_threshold': 0.4,
                'min_memories_for_temporal_check': 2,
                'conflict_word_overlap_threshold': 3
            },
            'environment': {
                'dual_threshold_coverage': 0.3,
                'dual_threshold_confidence': 0.3,
                'min_memories': 1,
                'realtime_coverage_threshold': 0.5
            },
            'temporal_orchestration': {
                'enabled': True,
                'hippocampus_k': 10,
                'temporal_lobe_k': 5
            },
            'causal_orchestration': {
                'enabled': True,
                'force_reflection': True,
                'kg_relation_types': ['causes', 'leads_to', 'results_in', 'because_of']
            }
        }

    async def analyze_triggers(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        query_features: Dict[str, Any],
        coverage: float,
        confidence: float,
        gaps: Dict[str, Any]
    ) -> Dict[str, TriggerDecision]:
        """
        综合分析所有触发条件

        Returns:
            Dict[trigger_name, TriggerDecision]
        """
        decisions = {}

        # 1. Reflection Agent 触发
        decisions['reflection'] = self._should_trigger_reflection(
            query, memories, coverage, gaps, query_features
        )

        # 2. Prefrontal Cortex 触发（冲突检测）
        decisions['prefrontal'] = self._should_trigger_prefrontal(
            query, memories, coverage, gaps, confidence, query_features
        )

        # 3. Environment Agent 触发（外部探索）
        decisions['environment'] = self._should_trigger_environment(
            query, memories, coverage, confidence, gaps
        )

        # 4. Temporal Orchestration 触发（时间序列协作）
        decisions['temporal'] = self._should_trigger_temporal_orchestration(
            query, query_features, coverage
        )

        # 5. Causal Orchestration 触发（因果推理协作）
        decisions['causal'] = self._should_trigger_causal_orchestration(
            query, gaps, coverage
        )

        # 日志记录
        triggered = [name for name, dec in decisions.items() if dec.should_trigger]
        if triggered:
            for name in triggered:
                logger.info(f"✓ Triggered: {name} ({decisions[name].reason})")

        return decisions

    def _should_trigger_reflection(
        self,
        query: str,
        memories: List[Dict],
        coverage: float,
        gaps: Dict[str, Any],
        query_features: Dict[str, Any]
    ) -> TriggerDecision:
        """
        Reflection Agent 触发条件:
        1. WHY 问题（因果推理）
        2. 覆盖率极低 (< 0.5)，需要抽象模式匹配
        3. 抽象概念查询 + 覆盖率不足
        """
        query_lower = query.lower()
        query_type = query_features.get('query_type', 'unknown')

        # 条件1: WHY/因果问题
        if gaps.get('causal') or query_lower.startswith('why ') or 'reason' in query_lower:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='reflection',
                reason='Causal/WHY-type question detected',
                priority=1,
                parameters={'focus': 'causal_inference', 'strategy': 'why_reasoning'}
            )

        # 条件2: 覆盖率极低
        if coverage < self.config['reflection']['coverage_threshold']:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='reflection',
                reason=f'Low coverage ({coverage:.2f}), need abstract pattern matching',
                priority=2,
                parameters={'focus': 'pattern_recognition', 'strategy': 'abstraction'}
            )

        # 条件3: 抽象概念 + 覆盖率不足
        abstract_keywords = ['concept', 'idea', 'theory', 'principle', 'belief', 'value']
        is_abstract = any(kw in query_lower for kw in abstract_keywords)

        if is_abstract and coverage < self.config['reflection']['abstract_coverage_threshold']:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='reflection',
                reason=f'Abstract concept query with moderate coverage ({coverage:.2f})',
                priority=2,
                parameters={'focus': 'concept_synthesis', 'strategy': 'abstraction'}
            )

        # 排除条件: Identity问题 + 高覆盖率
        if (query_type == 'identity' and
            coverage >= self.config['reflection']['identity_coverage_threshold'] and
            not gaps.get('entity')):
            return TriggerDecision(
                should_trigger=False,
                trigger_type='reflection',
                reason='Identity query with sufficient coverage, skip reflection',
                priority=5,
                parameters={}
            )

        return TriggerDecision(
            should_trigger=False,
            trigger_type='reflection',
            reason='No reflection trigger conditions met',
            priority=5,
            parameters={}
        )

    def _should_trigger_prefrontal(
        self,
        query: str,
        memories: List[Dict],
        coverage: float,
        gaps: Dict[str, Any],
        confidence: float,
        query_features: Dict[str, Any]
    ) -> TriggerDecision:
        """
        Prefrontal Cortex 触发条件:
        1. 日期冲突
        2. 内容冲突
        3. 低置信度 (< 0.4)
        4. 时间问题 + 多个记忆
        5. Multi-hop推理
        """

        # 检测冲突
        date_conflicts = self._detect_date_conflicts(memories)
        content_conflicts = self._detect_content_conflicts(memories)

        # 条件1: 日期冲突
        if date_conflicts:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='prefrontal',
                reason=f'Date conflicts detected ({len(date_conflicts)} conflicts)',
                priority=1,
                parameters={'conflicts': date_conflicts, 'conflict_type': 'temporal'}
            )

        # 条件2: 内容冲突
        if content_conflicts:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='prefrontal',
                reason=f'Content conflicts detected ({len(content_conflicts)} conflicts)',
                priority=1,
                parameters={'conflicts': content_conflicts, 'conflict_type': 'semantic'}
            )

        # 条件3: 低置信度
        if confidence < self.config['prefrontal']['confidence_threshold']:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='prefrontal',
                reason=f'Low confidence ({confidence:.2f}), need evaluation',
                priority=2,
                parameters={'task': 'confidence_assessment'}
            )

        # 条件4: 时间问题 + 多个记忆
        temporal_keywords = ['when', 'which year', 'which month', 'which day', 'what date']
        is_temporal = any(kw in query.lower() for kw in temporal_keywords)

        if is_temporal and len(memories) >= self.config['prefrontal']['min_memories_for_temporal_check']:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='prefrontal',
                reason='Temporal query with multiple memories, verify timeline',
                priority=2,
                parameters={'task': 'temporal_verification'}
            )

        # 条件5: Multi-hop推理
        if query_features.get('multi_hop'):
            return TriggerDecision(
                should_trigger=True,
                trigger_type='prefrontal',
                reason='Multi-hop reasoning requires executive control',
                priority=2,
                parameters={'task': 'multi_hop_coordination'}
            )

        return TriggerDecision(
            should_trigger=False,
            trigger_type='prefrontal',
            reason='No prefrontal trigger conditions met',
            priority=5,
            parameters={}
        )

    def _should_trigger_environment(
        self,
        query: str,
        memories: List[Dict],
        coverage: float,
        confidence: float,
        gaps: Dict[str, Any]
    ) -> TriggerDecision:
        """
        Environment Agent 触发条件:
        1. 双重低阈值 (coverage < 0.3 AND confidence < 0.3)
        2. 检索为空 (len(memories) <= 1)
        3. 外部指示词 ('search for', 'look up', 'latest')
        4. 实时信息需求
        """

        query_lower = query.lower()

        # 条件1: 双重低阈值
        if (coverage < self.config['environment']['dual_threshold_coverage'] and
            confidence < self.config['environment']['dual_threshold_confidence']):
            return TriggerDecision(
                should_trigger=True,
                trigger_type='environment',
                reason=f'Dual low threshold (coverage={coverage:.2f}, confidence={confidence:.2f})',
                priority=1,
                parameters={'strategy': 'general_exploration', 'reason': 'insufficient_internal'}
            )

        # 条件2: 检索为空
        if len(memories) <= self.config['environment']['min_memories']:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='environment',
                reason=f'Insufficient memories ({len(memories)}), trigger external search',
                priority=1,
                parameters={'strategy': 'targeted_search', 'reason': 'no_internal_memories'}
            )

        # 条件3: 外部指示词
        external_keywords = ['search for', 'look up', 'latest', 'recent', 'find information about']
        if any(kw in query_lower for kw in external_keywords):
            return TriggerDecision(
                should_trigger=True,
                trigger_type='environment',
                reason='Explicit external search request detected',
                priority=1,
                parameters={'strategy': 'web_search', 'reason': 'explicit_request'}
            )

        # 条件4: 实时信息需求
        realtime_keywords = ['now', 'today', 'current', 'this year', 'latest']
        if any(kw in query_lower for kw in realtime_keywords):
            if coverage < self.config['environment']['realtime_coverage_threshold']:
                return TriggerDecision(
                    should_trigger=True,
                    trigger_type='environment',
                    reason='Real-time information request with low coverage',
                    priority=2,
                    parameters={'strategy': 'current_data', 'reason': 'realtime_need'}
                )

        # 条件5: 实体缺口 + 覆盖率低
        if gaps.get('entity') and coverage < 0.4:
            return TriggerDecision(
                should_trigger=True,
                trigger_type='environment',
                reason='Entity gap cannot be filled internally',
                priority=2,
                parameters={'strategy': 'entity_search', 'reason': 'entity_gap'}
            )

        return TriggerDecision(
            should_trigger=False,
            trigger_type='environment',
            reason='No environment trigger conditions met',
            priority=5,
            parameters={}
        )

    def _should_trigger_temporal_orchestration(
        self,
        query: str,
        query_features: Dict[str, Any],
        coverage: float
    ) -> TriggerDecision:
        """
        Temporal Orchestration 触发条件:
        1. "When" 问题
        2. 查询类型为 temporal
        3. 时间关键词
        """

        if not self.config['temporal_orchestration']['enabled']:
            return TriggerDecision(False, 'temporal', 'Disabled', 5, {})

        query_lower = query.lower()

        # 条件1: "When" 问题
        if query_lower.startswith('when '):
            return TriggerDecision(
                should_trigger=True,
                trigger_type='temporal',
                reason='"When" question detected',
                priority=1,
                parameters={
                    'hippocampus_k': self.config['temporal_orchestration']['hippocampus_k'],
                    'temporal_lobe_k': self.config['temporal_orchestration']['temporal_lobe_k']
                }
            )

        # 条件2: 查询类型为 temporal
        if query_features.get('query_type') == 'temporal':
            return TriggerDecision(
                should_trigger=True,
                trigger_type='temporal',
                reason='Temporal query type identified',
                priority=1,
                parameters={
                    'hippocampus_k': self.config['temporal_orchestration']['hippocampus_k'],
                    'temporal_lobe_k': self.config['temporal_orchestration']['temporal_lobe_k']
                }
            )

        # 条件3: 时间关键词
        temporal_keywords = ['when did', 'which year', 'which month', 'which day', 'what date', 'what time']
        if any(kw in query_lower for kw in temporal_keywords):
            return TriggerDecision(
                should_trigger=True,
                trigger_type='temporal',
                reason='Temporal keywords detected',
                priority=2,
                parameters={
                    'hippocampus_k': self.config['temporal_orchestration']['hippocampus_k'],
                    'temporal_lobe_k': self.config['temporal_orchestration']['temporal_lobe_k']
                }
            )

        return TriggerDecision(
            should_trigger=False,
            trigger_type='temporal',
            reason='No temporal trigger conditions met',
            priority=5,
            parameters={}
        )

    def _should_trigger_causal_orchestration(
        self,
        query: str,
        gaps: Dict[str, Any],
        coverage: float
    ) -> TriggerDecision:
        """
        Causal Orchestration 触发条件:
        1. "Why" 问题
        2. 因果指示词
        3. 因果缺口标记
        """

        if not self.config['causal_orchestration']['enabled']:
            return TriggerDecision(False, 'causal', 'Disabled', 5, {})

        query_lower = query.lower()

        # 条件1: "Why" 问题
        if query_lower.startswith('why '):
            return TriggerDecision(
                should_trigger=True,
                trigger_type='causal',
                reason='"Why" question detected',
                priority=1,
                parameters={
                    'force_reflection': self.config['causal_orchestration']['force_reflection'],
                    'kg_relation_types': self.config['causal_orchestration']['kg_relation_types']
                }
            )

        # 条件2: 因果指示词
        causal_keywords = ['because', 'reason', 'cause', 'lead to', 'result in', 'due to', 'how come']
        if any(kw in query_lower for kw in causal_keywords):
            return TriggerDecision(
                should_trigger=True,
                trigger_type='causal',
                reason='Causal keywords detected',
                priority=1,
                parameters={
                    'force_reflection': self.config['causal_orchestration']['force_reflection'],
                    'kg_relation_types': self.config['causal_orchestration']['kg_relation_types']
                }
            )

        # 条件3: 因果缺口
        if gaps.get('causal'):
            return TriggerDecision(
                should_trigger=True,
                trigger_type='causal',
                reason='Causal gap detected',
                priority=2,
                parameters={
                    'force_reflection': self.config['causal_orchestration']['force_reflection'],
                    'kg_relation_types': self.config['causal_orchestration']['kg_relation_types']
                }
            )

        return TriggerDecision(
            should_trigger=False,
            trigger_type='causal',
            reason='No causal trigger conditions met',
            priority=5,
            parameters={}
        )

    def _detect_date_conflicts(self, memories: List[Dict]) -> List[Dict[str, Any]]:
        """
        检测日期冲突

        检测同一事件的不同日期描述
        """
        conflicts = []

        # 提取所有日期
        date_pattern = r'\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4})\b'

        memory_dates = []
        for mem in memories:
            content = mem.get('content', '')
            dates = re.findall(date_pattern, content)
            if dates:
                memory_dates.append({
                    'memory': mem,
                    'dates': dates,
                    'content': content
                })

        # 查找关键词重叠的记忆对
        for i in range(len(memory_dates)):
            for j in range(i + 1, len(memory_dates)):
                mem1 = memory_dates[i]
                mem2 = memory_dates[j]

                # 提取关键词
                words1 = set(re.findall(r'\b\w+\b', mem1['content'].lower()))
                words2 = set(re.findall(r'\b\w+\b', mem2['content'].lower()))

                overlap = words1 & words2
                if len(overlap) >= self.config['prefrontal']['conflict_word_overlap_threshold']:
                    # 检查日期是否不同
                    if mem1['dates'][0] != mem2['dates'][0]:
                        conflicts.append({
                            'type': 'date_conflict',
                            'memory1': mem1['memory']['id'],
                            'memory2': mem2['memory']['id'],
                            'date1': mem1['dates'][0],
                            'date2': mem2['dates'][0],
                            'overlap': list(overlap)[:5]
                        })

        return conflicts

    def _detect_content_conflicts(self, memories: List[Dict]) -> List[Dict[str, Any]]:
        """
        检测内容冲突

        检测否定对 (e.g., "likes" vs "dislikes")
        """
        conflicts = []

        negation_pairs = [
            ('likes', 'dislikes'),
            ('loves', 'hates'),
            ('is', 'is not'),
            ('can', 'cannot'),
            ('will', 'will not'),
            ('has', 'has not'),
            ('does', 'does not'),
            ('prefers', 'avoids')
        ]

        for i in range(len(memories)):
            for j in range(i + 1, len(memories)):
                content1 = memories[i].get('content', '').lower()
                content2 = memories[j].get('content', '').lower()

                # 检查否定对
                for pos, neg in negation_pairs:
                    if pos in content1 and neg in content2:
                        # 检查主语是否相同
                        words1 = set(re.findall(r'\b\w+\b', content1))
                        words2 = set(re.findall(r'\b\w+\b', content2))
                        overlap = words1 & words2

                        if len(overlap) >= 2:  # 至少2个词重叠
                            conflicts.append({
                                'type': 'content_conflict',
                                'memory1': memories[i]['id'],
                                'memory2': memories[j]['id'],
                                'positive_term': pos,
                                'negative_term': neg,
                                'overlap': list(overlap)[:5]
                            })

        return conflicts
