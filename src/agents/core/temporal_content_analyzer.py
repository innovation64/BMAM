"""
Temporal Content Analyzer - 时间内容分析器
Extract and understand temporal information from conversation content

核心能力:
1. 从内容中提取时间信息 (不只是从query)
2. 理解相对时间 ("yesterday", "last week")
3. 判断内容类型 (实时对话 vs 历史内容 vs 虚构内容)
4. 自动时间定位 (temporal grounding)
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TemporalEvent:
    """时间事件"""
    text: str  # 事件文本
    time_expression: str  # 时间表达 ("yesterday", "May 8, 2023")
    absolute_time: Optional[datetime] = None  # 绝对时间
    relative_offset: Optional[timedelta] = None  # 相对偏移
    confidence: float = 1.0  # 置信度


@dataclass
class TemporalInfo:
    """时间信息"""
    content_type: str = 'realtime'  # 'realtime' | 'historical' | 'fictional'
    reference_time: Optional[datetime] = None  # 参考时间
    events: List[TemporalEvent] = field(default_factory=list)
    timeline_id: str = 'realtime'  # 时间轴ID
    confidence: float = 1.0  # 整体置信度


class TemporalContentAnalyzer:
    """
    时间内容分析器
    Analyze temporal information in content (not just queries)
    """

    # 月份映射
    MONTHS = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }

    # 相对时间映射 (英文)
    RELATIVE_TIME_EN = {
        'yesterday': timedelta(days=-1),
        'today': timedelta(days=0),
        'tomorrow': timedelta(days=1),
        'last week': timedelta(weeks=-1),
        'next week': timedelta(weeks=1),
        'last month': timedelta(days=-30),
        'next month': timedelta(days=30),
        'last year': timedelta(days=-365),
        'next year': timedelta(days=365),
    }

    # 相对时间映射 (中文)
    RELATIVE_TIME_ZH = {
        '昨天': timedelta(days=-1),
        '今天': timedelta(days=0),
        '明天': timedelta(days=1),
        '前天': timedelta(days=-2),
        '后天': timedelta(days=2),
        '上周': timedelta(weeks=-1),
        '下周': timedelta(weeks=1),
        '上个月': timedelta(days=-30),
        '下个月': timedelta(days=30),
        '去年': timedelta(days=-365),
        '明年': timedelta(days=365),
    }

    def __init__(self):
        pass

    def extract_temporal_info(
        self,
        content: str,
        context: Dict[str, Any] = None
    ) -> TemporalInfo:
        """
        从内容中提取时间信息
        Extract temporal information from content

        Args:
            content: Content to analyze
            context: Additional context (e.g., previous conversation)

        Returns:
            TemporalInfo object
        """
        content_lower = content.lower()
        context = context or {}

        # 1. 检测内容类型
        content_type = self._detect_content_type(content, context)

        # 2. 提取参考时间
        reference_time = self._extract_reference_time(content, context)

        # 3. 提取时间事件
        events = self._extract_temporal_events(content, reference_time)

        # 4. 生成时间轴ID
        timeline_id = self._generate_timeline_id(content_type, reference_time, context)

        # 5. 计算置信度
        confidence = self._calculate_confidence(content_type, reference_time, events)

        return TemporalInfo(
            content_type=content_type,
            reference_time=reference_time,
            events=events,
            timeline_id=timeline_id,
            confidence=confidence
        )

    def _detect_content_type(self, content: str, context: Dict) -> str:
        """
        检测内容类型
        Returns: 'realtime' | 'historical' | 'fictional'
        """
        content_lower = content.lower()

        # 1. 检测历史标记
        historical_markers = [
            r'session \d+.*date:',  # "Session 1 - Date: ..."
            r'on \d+ \w+ \d{4}',  # "on 8 May 2023"
            r'\d{4}年',  # "2023年"
            r'dialogue from',  # "Dialogue from past"
            r'conversation on',  # "Conversation on May 8"
        ]

        for pattern in historical_markers:
            if re.search(pattern, content_lower):
                return 'historical'

        # 2. 检测虚构标记
        fictional_markers = [
            r'story.*set in',  # "Story set in 1920"
            r'novel',  # "Novel"
            r'fiction',  # "Fiction"
            r'chapter \d+',  # "Chapter 1"
            r'《.*》',  # Chinese book title
        ]

        for pattern in fictional_markers:
            if re.search(pattern, content_lower):
                return 'fictional'

        # 3. 默认为实时
        return 'realtime'

    def _extract_reference_time(
        self,
        content: str,
        context: Dict
    ) -> Optional[datetime]:
        """
        提取参考时间 (基准时间点)
        """
        # 1. 从session header提取
        # Pattern: "Session 1 - Date: 1:56 pm on 8 May, 2023"
        session_pattern = r'(\d+):(\d+)\s+(am|pm)\s+on\s+(\d+)\s+([a-z]+)[,\s]*(\d{4})'
        match = re.search(session_pattern, content.lower())
        if match:
            hour, minute, am_pm, day, month_name, year = match.groups()

            hour = int(hour)
            if am_pm.lower() == 'pm' and hour != 12:
                hour += 12
            elif am_pm.lower() == 'am' and hour == 12:
                hour = 0

            month = self.MONTHS.get(month_name.lower(), 1)

            try:
                return datetime(int(year), month, int(day), hour, int(minute))
            except ValueError:
                pass

        # 2. 从简单日期提取
        # Pattern: "8 May 2023", "May 8, 2023"
        date_patterns = [
            r'(\d{1,2})\s+([a-z]+)[,\s]+(\d{4})',  # "8 May 2023"
            r'([a-z]+)\s+(\d{1,2})[,\s]+(\d{4})',  # "May 8, 2023"
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # "2023-05-08"
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',  # "2023年5月8日"
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, content.lower())
            if matches:
                match = matches[0]
                try:
                    if pattern.endswith('日'):  # Chinese format
                        year, month, day = match
                        return datetime(int(year), int(month), int(day))
                    elif '-' in pattern:  # ISO format
                        year, month, day = match
                        return datetime(int(year), int(month), int(day))
                    elif match[1].isdigit():  # Month day, year
                        month_str, day, year = match
                        month = self.MONTHS.get(month_str.lower(), 1)
                        return datetime(int(year), month, int(day))
                    else:  # Day month year
                        day, month_str, year = match
                        month = self.MONTHS.get(month_str.lower(), 1)
                        return datetime(int(year), month, int(day))
                except ValueError:
                    continue

        # 3. 从context获取
        if 'reference_time' in context:
            return context['reference_time']

        # 4. 默认返回None (让调用者决定)
        return None

    def _extract_temporal_events(
        self,
        content: str,
        reference_time: Optional[datetime]
    ) -> List[TemporalEvent]:
        """
        提取时间事件
        """
        events = []

        # 1. 提取相对时间 (英文)
        for time_expr, offset in self.RELATIVE_TIME_EN.items():
            pattern = r'\b' + re.escape(time_expr) + r'\b'
            matches = re.finditer(pattern, content.lower())

            for match in matches:
                # 提取事件文本 (前后各50个字符)
                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                event_text = content[start:end].strip()

                absolute_time = None
                if reference_time:
                    absolute_time = reference_time + offset

                events.append(TemporalEvent(
                    text=event_text,
                    time_expression=time_expr,
                    absolute_time=absolute_time,
                    relative_offset=offset,
                    confidence=0.9 if reference_time else 0.5
                ))

        # 2. 提取相对时间 (中文)
        for time_expr, offset in self.RELATIVE_TIME_ZH.items():
            if time_expr in content:
                # Find all occurrences
                start_pos = 0
                while True:
                    pos = content.find(time_expr, start_pos)
                    if pos == -1:
                        break

                    # Extract event text
                    start = max(0, pos - 50)
                    end = min(len(content), pos + len(time_expr) + 50)
                    event_text = content[start:end].strip()

                    absolute_time = None
                    if reference_time:
                        absolute_time = reference_time + offset

                    events.append(TemporalEvent(
                        text=event_text,
                        time_expression=time_expr,
                        absolute_time=absolute_time,
                        relative_offset=offset,
                        confidence=0.9 if reference_time else 0.5
                    ))

                    start_pos = pos + 1

        # 3. 提取数字相对时间 ("2 days ago", "3 months later")
        numeric_patterns = [
            (r'(\d+)\s+days?\s+ago', lambda n: timedelta(days=-int(n))),
            (r'(\d+)\s+weeks?\s+ago', lambda n: timedelta(weeks=-int(n))),
            (r'(\d+)\s+months?\s+ago', lambda n: timedelta(days=-int(n)*30)),
            (r'(\d+)\s+years?\s+ago', lambda n: timedelta(days=-int(n)*365)),
            (r'(\d+)\s+天前', lambda n: timedelta(days=-int(n))),
            (r'(\d+)\s+周前', lambda n: timedelta(weeks=-int(n))),
            (r'(\d+)\s+个月前', lambda n: timedelta(days=-int(n)*30)),
            (r'(\d+)\s+年前', lambda n: timedelta(days=-int(n)*365)),
        ]

        for pattern, offset_fn in numeric_patterns:
            matches = re.finditer(pattern, content.lower())
            for match in matches:
                n = match.group(1)
                offset = offset_fn(n)

                start = max(0, match.start() - 50)
                end = min(len(content), match.end() + 50)
                event_text = content[start:end].strip()

                absolute_time = None
                if reference_time:
                    absolute_time = reference_time + offset

                events.append(TemporalEvent(
                    text=event_text,
                    time_expression=match.group(0),
                    absolute_time=absolute_time,
                    relative_offset=offset,
                    confidence=0.8 if reference_time else 0.4
                ))

        return events

    def _generate_timeline_id(
        self,
        content_type: str,
        reference_time: Optional[datetime],
        context: Dict
    ) -> str:
        """
        生成时间轴ID
        """
        if content_type == 'realtime':
            return 'realtime'

        # 从context获取
        if 'timeline_id' in context:
            return context['timeline_id']

        # 基于reference_time生成
        if reference_time:
            return f'{content_type}_{reference_time.strftime("%Y%m%d")}'

        return f'{content_type}_unknown'

    def _calculate_confidence(
        self,
        content_type: str,
        reference_time: Optional[datetime],
        events: List[TemporalEvent]
    ) -> float:
        """
        计算整体置信度
        """
        if content_type == 'realtime':
            return 1.0

        if not reference_time:
            return 0.3

        if events:
            # 平均事件置信度
            avg_event_confidence = sum(e.confidence for e in events) / len(events)
            return min(1.0, 0.7 + avg_event_confidence * 0.3)

        return 0.6


# 测试代码
if __name__ == '__main__':
    analyzer = TemporalContentAnalyzer()

    # Test 1: Example session
    content1 = """
Session 1 - Date: 1:56 pm on 8 May, 2023
PersonA: I went to a support group yesterday.
PersonB: That's great!
"""

    info1 = analyzer.extract_temporal_info(content1)
    for event in info1.events:
        pass

    # Test 2: Chinese novel
    content2 = """
《三体》第一部
2007年，叶文洁收到了来自三体世界的回信。
这个回信改变了人类的命运。
"""

    info2 = analyzer.extract_temporal_info(content2)

    # Test 3: Real-time conversation
    content3 = "Hi, how are you today?"

    info3 = analyzer.extract_temporal_info(content3)
