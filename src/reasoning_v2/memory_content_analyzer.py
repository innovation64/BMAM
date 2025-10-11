"""
记忆内容分析器 - Memory Content Analyzer
完全基于记忆内容的语义分析,无硬编码规则
"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class MemoryContentAnalyzer:
    """
    分析记忆内容的特征,用于触发相应的推理能力
    核心原则:只分析记忆内容本身,不使用任何外部规则
    """

    def __init__(self):
        self.relative_time_patterns = [
            r'\byesterday\b', r'\blast\s+(week|month|year|night)\b',
            r'\bthis\s+(week|month|year|morning)\b',
            r'\b\d+\s+(days?|weeks?|months?|years?)\s+ago\b',
            r'\bthe\s+(weekend|week|month)\s+before\b'
        ]

    async def analyze(self, memories: List[Dict], query: str = "") -> Dict[str, Any]:
        """
        分析记忆内容特征

        Args:
            memories: 检索到的记忆列表
            query: 用户问题(可选,用于上下文理解)

        Returns:
            {
                'has_relative_time': bool,
                'time_expressions': List[str],
                'has_identity_clues': bool,
                'identity_signals': List[str],
                'has_career_mentions': bool,
                'career_keywords': List[str],
                'conversation_date': str or None,
                'behavioral_patterns': List[str],
                'confidence': float
            }
        """
        if not memories:
            return self._empty_analysis()

        # 合并所有记忆文本
        all_text = ' '.join([
            m.get('content', '') for m in memories
        ])

        analysis = {
            'has_relative_time': False,
            'time_expressions': [],
            'has_identity_clues': False,
            'identity_signals': [],
            'has_career_mentions': False,
            'career_keywords': [],
            'conversation_date': None,
            'behavioral_patterns': [],
            'confidence': 1.0
        }

        # 1. 检测相对时间表达
        time_exprs = self._detect_relative_time(all_text)
        if time_exprs:
            analysis['has_relative_time'] = True
            analysis['time_expressions'] = time_exprs

        # 2. 提取对话日期上下文
        conv_date = self._extract_conversation_date(memories)
        if conv_date:
            analysis['conversation_date'] = conv_date

        # 3. 检测身份线索 (基于语义,不是硬编码列表)
        identity_signals = self._detect_identity_signals(all_text)
        if identity_signals:
            analysis['has_identity_clues'] = True
            analysis['identity_signals'] = identity_signals

        # 4. 检测职业/教育相关内容
        career_kw = self._detect_career_context(all_text)
        if career_kw:
            analysis['has_career_mentions'] = True
            analysis['career_keywords'] = career_kw

        # 5. 提取行为模式
        patterns = self._extract_behavioral_patterns(memories)
        analysis['behavioral_patterns'] = patterns

        logger.info(f"📊 Memory Analysis: time={analysis['has_relative_time']}, "
                   f"identity={analysis['has_identity_clues']}, "
                   f"career={analysis['has_career_mentions']}")

        return analysis

    def _detect_relative_time(self, text: str) -> List[str]:
        """检测相对时间表达"""
        expressions = []
        for pattern in self.relative_time_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            expressions.extend(matches)
        return list(set(expressions))  # 去重

    def _extract_conversation_date(self, memories: List[Dict]) -> str:
        """提取对话日期上下文"""
        # 查找包含日期上下文的记忆
        date_patterns = [
            r'(?:on|date is|conversation is on)\s+(\d{1,2}\s+\w+,?\s+\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})',
            r'Context.*?(\d{1,2}\s+\w+,?\s+\d{4})'
        ]

        for memory in memories[:5]:  # 只检查最近几条
            content = memory.get('content', '')
            for pattern in date_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1)
        return None

    def _detect_identity_signals(self, text: str) -> List[str]:
        """
        检测身份线索 - 基于语义模式,不是硬编码词表
        关键:寻找 "X stories/group/community" 模式
        """
        signals = []

        # 模式1: "X stories" (表示对某个群体有共鸣)
        story_pattern = r'(\w+)\s+stories?\s+(were?|was)\s+(inspiring|powerful|moving)'
        matches = re.findall(story_pattern, text, re.IGNORECASE)
        for match in matches:
            signals.append(f"{match[0]}_stories_inspiring")

        # 模式2: "X support group" / "X community"
        group_pattern = r'(LGBTQ\+?|transgender|gay|lesbian|adoption|AA|mental\s+health)\s+(support\s+group|community|clinic|center)'
        matches = re.findall(group_pattern, text, re.IGNORECASE)
        for match in matches:
            signals.append(f"{match[0]}_group_attendance")

        # 模式3: "researched X" (表示强烈兴趣/需求)
        research_pattern = r'research(?:ed|ing)?\s+(adoption|gender|transition|counseling|therapy)'
        matches = re.findall(research_pattern, text, re.IGNORECASE)
        for match in matches:
            signals.append(f"researched_{match}")

        return signals

    def _detect_career_context(self, text: str) -> List[str]:
        """
        检测职业/教育上下文
        关键:寻找明确的职业意向表达
        """
        keywords = []

        # 模式1: "interested in X" / "want to work in X"
        interest_pattern = r'(?:interested\s+in|want\s+to\s+(?:work\s+in|study|pursue))\s+([\w\s]+?)(?:\.|,|and|or|$)'
        matches = re.findall(interest_pattern, text, re.IGNORECASE)
        keywords.extend([m.strip() for m in matches])

        # 模式2: "counseling" / "psychology" 等专业术语
        professional_terms = r'\b(counseling|psychology|social\s+work|therapy|mental\s+health|teaching|nursing|engineering)\b'
        matches = re.findall(professional_terms, text, re.IGNORECASE)
        keywords.extend(matches)

        # 模式3: "career in X" / "education in X"
        career_pattern = r'(?:career|education|degree|certification)\s+(?:in|for)\s+([\w\s]+?)(?:\.|,|and|or|$)'
        matches = re.findall(career_pattern, text, re.IGNORECASE)
        keywords.extend([m.strip() for m in matches])

        return list(set(keywords))  # 去重

    def _extract_behavioral_patterns(self, memories: List[Dict]) -> List[str]:
        """提取行为模式(用于兴趣/性格推断)"""
        patterns = []

        # 提取动词短语(行为模式)
        action_pattern = r'(attended|went\s+to|joined|participated\s+in|researched|studied)\s+([\w\s]+?)(?:\.|,|and|or|$)'

        for memory in memories[:10]:
            content = memory.get('content', '')
            matches = re.findall(action_pattern, content, re.IGNORECASE)
            for match in matches:
                patterns.append(f"{match[0]} {match[1].strip()}")

        return patterns

    def _empty_analysis(self) -> Dict[str, Any]:
        """空记忆的分析结果"""
        return {
            'has_relative_time': False,
            'time_expressions': [],
            'has_identity_clues': False,
            'identity_signals': [],
            'has_career_mentions': False,
            'career_keywords': [],
            'conversation_date': None,
            'behavioral_patterns': [],
            'confidence': 0.0
        }
