"""
记忆价值驱动的动态复杂度检测

核心思想: 这是记忆系统,不是QA系统!
- 每次交互都是学习机会
- 即使简单问候也可能包含情绪/习惯信号
- 动态决策基于: 记忆价值 + 异常检测 + 推理需求
"""

import re
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MemoryBasedComplexityDetector:
    """基于记忆价值的复杂度检测器"""

    def __init__(self):
        # 交互历史 (用于异常检测)
        self.interaction_history = []
        self.last_interaction_time = None
        self.user_emotion_baseline = 'neutral'  # 用户情绪基线

    def detect_complexity(self, query: str, question_type: str) -> Dict[str, Any]:
        """
        动态检测任务复杂度 - 基于记忆系统思维

        核心原则:
        1. 每次交互都是学习机会 - 即使简单问候也可能包含情绪/习惯信号
        2. 动态决策基于: 记忆价值 + 异常检测 + 推理需求
        3. 不是"问题简单就快速回答",而是"需要多深的认知处理"
        """
        query_lower = query.lower()

        # 🔍 步骤1: 评估记忆价值
        memory_value = self._evaluate_memory_value(query, query_lower)

        # 🔍 步骤2: 异常检测
        anomaly_info = self._detect_anomaly(query, query_lower)

        # 🔍 步骤3: 推理需求评估
        reasoning_depth = self._evaluate_reasoning_depth(query, question_type)

        # 🧠 动态决策逻辑 (记忆系统思维)

        # ⚠️ PRIORITY 1: 异常检测 → 深度处理
        if anomaly_info['detected']:
            return {
                'level': 3,
                'question_type': question_type,
                'max_iterations': 5,
                'needs_memory': True,
                'needs_reasoning': True,
                'memory_value': memory_value,
                'anomaly_detected': True,
                'reason': f"Anomaly detected: {anomaly_info['type']}"
            }

        # ⚠️ PRIORITY 2: 问题类型需要记忆/推理 → 至少Level 1
        # 对于需要记忆的问题类型（temporal, identity, research, multi_hop），
        # 即使memory_value低，也要检索记忆
        if question_type in ['temporal', 'identity', 'research', 'multi_hop']:
            if reasoning_depth >= 2:
                # 需要推理 → Level 2
                return {
                    'level': 2,
                    'question_type': question_type,
                    'max_iterations': 2,
                    'needs_memory': True,
                    'needs_reasoning': True,
                    'memory_value': memory_value,
                    'anomaly_detected': False,
                    'reason': f'{question_type.capitalize()} question requires memory+reasoning'
                }
            else:
                # 只需检索 → Level 1
                return {
                    'level': 1,
                    'question_type': question_type,
                    'max_iterations': 1,
                    'needs_memory': True,
                    'needs_reasoning': False,
                    'memory_value': memory_value,
                    'anomaly_detected': False,
                    'reason': f'{question_type.capitalize()} question requires memory retrieval'
                }

        # ⚠️ PRIORITY 3: 高记忆价值 → 深度处理
        if memory_value > 0.7:
            return {
                'level': 3,
                'question_type': question_type,
                'max_iterations': 5,
                'needs_memory': True,
                'needs_reasoning': True,
                'memory_value': memory_value,
                'anomaly_detected': False,
                'reason': f"High memory value ({memory_value:.2f})"
            }

        # 中等价值 + 需要推理 → 推理链
        if memory_value > 0.4 and reasoning_depth >= 2:
            return {
                'level': 2,
                'question_type': question_type,
                'max_iterations': 2,
                'needs_memory': True,
                'needs_reasoning': True,
                'memory_value': memory_value,
                'anomaly_detected': False,
                'reason': f'Moderate memory value ({memory_value:.2f}), reasoning depth {reasoning_depth}'
            }

        # 低价值 但需要记忆 → 记忆直取
        if memory_value >= 0.2:
            return {
                'level': 1,
                'question_type': question_type,
                'max_iterations': 1,
                'needs_memory': True,
                'needs_reasoning': False,
                'memory_value': memory_value,
                'anomaly_detected': False,
                'reason': f'Low-value interaction ({memory_value:.2f}), direct memory access'
            }

        # 🔥 特殊处理: factual/identity/temporal/research 问题ALWAYS需要记忆检索
        # 即使memory value很低,这些问题本质上是查询已有信息
        requires_memory_types = ['factual', 'identity', 'temporal', 'research']
        if question_type in requires_memory_types:
            return {
                'level': 1,
                'question_type': question_type,
                'max_iterations': 1,
                'needs_memory': True,  # 🔥 强制需要记忆
                'needs_reasoning': False,
                'memory_value': memory_value,
                'anomaly_detected': False,
                'reason': f'{question_type} question requires memory retrieval (forced Level 1)'
            }

        # 极低价值 + 简单问题类型 → 即时反应 (但仍然会存储!)
        return {
            'level': 0,
            'question_type': question_type,
            'max_iterations': 0,
            'needs_memory': False,
            'needs_reasoning': False,
            'memory_value': memory_value,
            'anomaly_detected': False,
            'reason': f'Minimal memory value ({memory_value:.2f}), instant response (still stored)'
        }

    def _evaluate_memory_value(self, query: str, query_lower: str) -> float:
        """
        评估记忆价值 - 这次交互值得多深的认知处理?

        考虑因素:
        - 情绪信号 (happy/sad/stressed)
        - 时间信息 (具体日期/时间)
        - 人物关系 (提到新人物/改变关系)
        - 行为模式 (习惯性动作/新行为)
        - 事实信息 (可存储的知识)
        """
        value = 0.0

        # 情绪信号 (+0.3) - 记忆系统最重要的信号!
        emotion_keywords = [
            'happy', 'sad', 'angry', 'stressed', 'excited', 'worried',
            'anxious', 'depressed', 'joyful', 'frustrated', 'scared',
            'love', 'hate', 'feel', 'felt', 'emotion',
            '开心', '难过', '焦虑', '压力', '兴奋', '担心', '感觉'
        ]
        if any(kw in query_lower for kw in emotion_keywords):
            value += 0.3
            logger.debug(f"📊 Emotion signal detected +0.3: {query[:50]}")

        # 时间信息 (+0.25) - 可用于时序记忆
        time_patterns = [
            r'\d{4}',  # 年份
            r'\d{1,2}:\d{2}',  # 时间
            r'january|february|march|april|may|june|july|august|september|october|november|december',
            r'monday|tuesday|wednesday|thursday|friday|saturday|sunday',
            r'today|yesterday|tomorrow|last week|next month|this morning',
            r'上午|下午|昨天|今天|明天|上周|下周'
        ]
        if any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in time_patterns):
            value += 0.25
            logger.debug(f"📊 Time information detected +0.25")

        # 人物关系 (+0.2) - 社交记忆
        relationship_keywords = [
            'friend', 'family', 'colleague', 'met', 'saw', 'talked to',
            'mother', 'father', 'sister', 'brother', 'partner',
            '朋友', '家人', '同事', '认识', '见到', '妈妈', '爸爸'
        ]
        if any(kw in query_lower for kw in relationship_keywords):
            value += 0.2
            logger.debug(f"📊 Relationship signal detected +0.2")

        # 行为/事件 (+0.2) - 行为记忆
        action_keywords = [
            'went', 'did', 'attended', 'started', 'stopped', 'changed',
            'bought', 'sold', 'learned', 'forgot', 'remembered',
            'moved', 'relocated', 'traveled', 'visited', 'called', 'wrote',  # 🔥 新增常见动作
            '去了', '做了', '参加', '开始', '停止', '改变', '学习', '搬家', '移动'
        ]
        if any(kw in query_lower for kw in action_keywords):
            value += 0.2
            logger.debug(f"📊 Action/event detected +0.2")

        # 学习/事实信息 (+0.2) - 知识记忆 (提升权重,事实陈述很重要!)
        factual_keywords = [
            'is', 'are', 'was', 'were', 'has', 'had', 'have',  # 🔥 扩展be动词和have
            'researched', 'studied', 'learned', 'decided', 'chose',  # 决策动词
            'identity', 'information', 'fact', 'single', 'married',  # 状态词
            '是', '学习', '研究', '知识', '事实', '决定'
        ]
        if any(kw in query_lower for kw in factual_keywords):
            value += 0.2  # 🔥 从0.15提升到0.2
            logger.debug(f"📊 Factual information detected +0.2")

        # 长度加成 (更长的输入可能包含更多信息)
        word_count = len(query.split())
        if word_count > 20:
            value += 0.1
        elif word_count > 10:
            value += 0.05

        logger.info(f"📊 Memory value: {value:.2f} for query: {query[:60]}")
        return min(1.0, value)

    def _detect_anomaly(self, query: str, query_lower: str) -> Dict[str, Any]:
        """
        异常检测 - 发现用户行为/情绪的突变

        例如:
        - 平时说"Hi" 突然变成 "I'm not okay"
        - 情绪突变 (开心→沮丧)
        - 行为模式改变
        """
        # 强烈情绪词 → 可能异常
        intense_emotions = [
            'extremely', 'very', 'really', 'so much', 'terrible', 'awful',
            'amazing', 'incredible', 'devastated', 'thrilled', 'overwhelmed',
            '非常', '特别', '极度', '太', '超级'
        ]

        # 否定/困扰信号
        distress_signals = [
            "can't", "won't", "never", "always", "nobody", "nothing",
            "not okay", "not well", "help", "worried", "concerned",
            "不行", "不好", "没有", "帮助", "担心"
        ]

        # 行为改变信号
        change_signals = [
            'changed', 'different', 'unusual', 'strange', 'weird',
            'not like', 'used to', 'before',
            '改变', '不同', '奇怪', '以前', '曾经'
        ]

        if any(signal in query_lower for signal in distress_signals):
            logger.warning(f"⚠️ Distress signal detected: {query[:60]}")
            return {'detected': True, 'type': 'distress_signal', 'severity': 'high'}

        if any(emotion in query_lower for emotion in intense_emotions):
            logger.info(f"⚠️ Intense emotion detected: {query[:60]}")
            return {'detected': True, 'type': 'intense_emotion', 'severity': 'medium'}

        if any(change in query_lower for change in change_signals):
            logger.info(f"⚠️ Behavior change detected: {query[:60]}")
            return {'detected': True, 'type': 'behavior_change', 'severity': 'medium'}

        return {'detected': False, 'type': None, 'severity': None}

    def _evaluate_reasoning_depth(self, query: str, question_type: str) -> int:
        """
        评估推理深度需求 (1-3)

        1: 简单检索
        2: 单次推理
        3: 多跳推理
        """
        query_lower = query.lower()

        # Level 3: 多跳推理指标
        multi_hop_indicators = [
            'would', 'likely', 'suitable', 'based on', 'given', 'considering',
            'why', 'how come', 'explain', 'analyze', 'compare',
            '为什么', '如何', '分析', '基于', '解释', '比较'
        ]
        if any(ind in query_lower for ind in multi_hop_indicators):
            return 3

        # Level 2: 单次推理
        inference_indicators = ['identity', 'temporal', 'research']
        if question_type in inference_indicators:
            return 2

        # Level 1: 简单检索
        return 1

    def update_interaction_history(self, query: str, emotion: str = None):
        """更新交互历史 (用于未来的异常检测)"""
        self.interaction_history.append({
            'query': query,
            'time': datetime.now(),
            'emotion': emotion
        })

        # 只保留最近100条
        if len(self.interaction_history) > 100:
            self.interaction_history = self.interaction_history[-100:]

        self.last_interaction_time = datetime.now()
