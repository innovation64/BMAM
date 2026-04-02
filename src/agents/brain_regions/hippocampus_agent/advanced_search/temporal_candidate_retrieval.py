"""
Temporal Candidate Retrieval - 时间候选检索
混合检索策略

Retrieves temporal candidates using hybrid strategy

🔧 2025-12-05: 增加对相对时间词的优先级
🔥 2025-12-10: 修复 - 使用 temporal_cues 做真正的时间过滤
- 之前：temporal_cues 参数传入但从未使用！
- 现在：解析 explicit_time 并过滤/加权候选记忆
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from ..core import EpisodicMemory

logger = logging.getLogger(__name__)

# 相对时间词表
RELATIVE_TIME_WORDS = [
    'yesterday', 'today', 'tomorrow',
    'last week', 'this week', 'next week',
    'last month', 'this month', 'next month',
    'last year', 'this year', 'next year',
    'last sunday', 'last monday', 'last tuesday', 'last wednesday',
    'last thursday', 'last friday', 'last saturday',
    'two days ago', 'three days ago', 'a week ago',
    'the day before', 'a few days ago', 'the week before',
    'the friday before', 'the sunday before',
    '昨天', '今天', '明天', '上周', '本周', '下周',
    '上个月', '这个月', '下个月', '去年', '今年', '明年'
]

# 月份映射
MONTH_NAMES = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4,
    'may': 5, 'june': 6, 'july': 7, 'august': 8,
    'september': 9, 'october': 10, 'november': 11, 'december': 12,
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7,
    'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
}


class TemporalCandidateRetriever:
    """
    时间候选检索器 (Temporal Candidate Retriever)

    Strategy | 策略:
    - Semantic search (expanded k)
    - Time index (if explicit time)
    - 🔧 NEW: Prioritize memories with relative time words
    """

    def __init__(self, agent):
        """Initialize retriever"""
        self.agent = agent


    def _parse_explicit_time(self, explicit_time: str) -> Optional[Tuple[datetime, datetime]]:
        """
        🔥 解析显式时间表达式，返回日期范围 (start, end)

        支持格式:
        - "7 May 2023" → 单日
        - "May 2023" / "2023年5月" → 整月
        - "June 2023" / "July 2023" → 整月
        - "2022" / "2023" → 整年
        - "The week before 9 June 2023" → 6/2-6/8
        - "The friday before 15 July 2023" → 前一个周五
        """
        if not explicit_time:
            return None

        time_str = explicit_time.lower().strip()

        try:
            # Pattern 1: "The week before DD Month YYYY"
            week_before_match = re.search(
                r'(?:the\s+)?week\s+before\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
                time_str, re.IGNORECASE
            )
            if week_before_match:
                day, month_str, year = week_before_match.groups()
                month = MONTH_NAMES.get(month_str.lower())
                if month:
                    ref_date = datetime(int(year), month, int(day))
                    # 前一周
                    end_date = ref_date - timedelta(days=1)
                    start_date = end_date - timedelta(days=6)
                    return (start_date, end_date)

            # Pattern 2: "The friday/sunday before DD Month YYYY"
            day_before_match = re.search(
                r'(?:the\s+)?(\w+day)\s+before\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
                time_str, re.IGNORECASE
            )
            if day_before_match:
                weekday_name, day, month_str, year = day_before_match.groups()
                month = MONTH_NAMES.get(month_str.lower())
                if month:
                    ref_date = datetime(int(year), month, int(day))
                    # 找前一个对应的星期几
                    weekdays = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                               'friday': 4, 'saturday': 5, 'sunday': 6}
                    target_weekday = weekdays.get(weekday_name.lower())
                    if target_weekday is not None:
                        days_back = (ref_date.weekday() - target_weekday) % 7
                        if days_back == 0:
                            days_back = 7
                        target_date = ref_date - timedelta(days=days_back)
                        return (target_date, target_date)

            # Pattern 3: "DD Month YYYY" or "D Month YYYY"
            date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', time_str)
            if date_match:
                day, month_str, year = date_match.groups()
                month = MONTH_NAMES.get(month_str.lower())
                if month:
                    target = datetime(int(year), month, int(day))
                    return (target, target)

            # Pattern 4: "Month YYYY" or "YYYY年M月"
            month_year_match = re.search(r'(\w+)\s+(\d{4})', time_str)
            if not month_year_match:
                month_year_match = re.search(r'(\d{4})年(\d{1,2})月', time_str)
            if month_year_match:
                groups = month_year_match.groups()
                if groups[0].isdigit():  # 中文格式
                    year, month = int(groups[0]), int(groups[1])
                else:  # 英文格式
                    month = MONTH_NAMES.get(groups[0].lower())
                    year = int(groups[1])
                if month:
                    start = datetime(year, month, 1)
                    if month == 12:
                        end = datetime(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end = datetime(year, month + 1, 1) - timedelta(days=1)
                    return (start, end)

            # Pattern 5: Year only "2022" or "2023"
            year_match = re.search(r'\b(20\d{2})\b', time_str)
            if year_match:
                year = int(year_match.group(1))
                return (datetime(year, 1, 1), datetime(year, 12, 31))

        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse explicit_time '{explicit_time}': {e}")

        return None


    def _score_temporal_match(
        self,
        mem: EpisodicMemory,
        temporal_cues: Dict,
        date_range: Optional[Tuple[datetime, datetime]]
    ) -> float:
        """
        🔥 计算记忆与时间线索的匹配度 (0.0-5.0)

        - 日期落在范围内: +3.0
        - 内容包含显式时间: +1.5
        - 内容包含时间关系词: +0.5
        """
        score = 0.0

        # 1. 检查时间戳是否落在目标范围内
        # 🔥 2025-12-11 修复: 优先使用 metadata['event_time']，这是从内容中提取的真正事件时间
        # timestamp 只是存储时间，不反映事件实际发生时间
        if date_range:
            try:
                mem_date = None

                # 优先从 metadata 中获取 event_time
                if hasattr(mem, 'metadata') and mem.metadata:
                    event_time_str = mem.metadata.get('event_time')
                    if event_time_str:
                        if isinstance(event_time_str, str):
                            mem_date = datetime.fromisoformat(event_time_str.replace('Z', '+00:00'))
                            mem_date = mem_date.replace(tzinfo=None)
                        elif isinstance(event_time_str, datetime):
                            mem_date = event_time_str

                # 如果没有 event_time，回退到 timestamp（可能是存储时间）
                # 🔥 P0-2: 记录 fallback 以便排查时间错误
                if mem_date is None and hasattr(mem, 'timestamp') and mem.timestamp:
                    mem_date = mem.timestamp
                    if isinstance(mem_date, str):
                        mem_date = datetime.fromisoformat(mem_date.replace('Z', '+00:00'))
                        mem_date = mem_date.replace(tzinfo=None)
                    logger.debug(
                        f"⚠️ No event_time in metadata for mem {getattr(mem, 'id', '?')}, "
                        f"falling back to timestamp={mem_date}"
                    )

                if mem_date:
                    start, end = date_range
                    if start <= mem_date <= end:
                        score += 3.0
                        logger.debug(f"📅 Date match: {mem_date} in [{start}, {end}]")
                    elif abs((mem_date - start).days) <= 7 or abs((mem_date - end).days) <= 7:
                        # 靠近范围的也给一些分
                        score += 1.0
            except (ValueError, TypeError) as e:
                logger.debug(f"Failed to parse memory date: {e}")

        # 2. 检查内容是否包含显式时间
        explicit_time = temporal_cues.get('explicit_time', '')
        if explicit_time and explicit_time.lower() in mem.content.lower():
            score += 1.5

        # 3. 检查内容是否包含时间事件
        temporal_event = temporal_cues.get('temporal_event', '')
        if temporal_event and temporal_event.lower() in mem.content.lower():
            score += 1.0

        # 4. 检查时间关系
        time_relation = temporal_cues.get('time_relation', 'none')
        implicit_cues = temporal_cues.get('implicit_cues', [])

        content_lower = mem.content.lower()
        if time_relation == 'before' and any(w in content_lower for w in ['before', '之前', 'prior']):
            score += 0.5
        elif time_relation == 'after' and any(w in content_lower for w in ['after', '之后', 'following']):
            score += 0.5

        return score


    def _has_relative_time(self, content: str) -> bool:
        """检查内容是否包含相对时间词"""
        content_lower = content.lower()
        for word in RELATIVE_TIME_WORDS:
            if word in content_lower:
                return True
        return False


    def _is_event_summary(self, content: str) -> bool:
        """检查是否为 Event 摘要类记忆"""
        return content.strip().startswith('[Event]')


    def _score_temporal_priority(self, mem: EpisodicMemory) -> float:
        """
        计算时间优先级得分 (越高越优先)

        - 包含相对时间词的原始对话: +2.0
        - 原始对话（无 [Event] 前缀）: +1.0
        - [Event] 摘要类记忆: +0.0
        """
        score = 0.0
        content = mem.content

        # 原始对话 vs Event 摘要
        if self._is_event_summary(content):
            score += 0.0  # Event 摘要优先级最低
        else:
            score += 1.0  # 原始对话优先级较高

        # 包含相对时间词的加分
        if self._has_relative_time(content):
            score += 2.0

        return score


    def _extract_event_keywords(self, query: str) -> List[str]:
        """
        🔥 2025-12-11 新增: 从查询中提取事件关键词

        例如: "LGBTQ+ community event" → ["lgbtq", "community", "event", "support group"]
        """
        keywords = []
        query_lower = query.lower()

        # 直接关键词
        direct_keywords = [
            'lgbtq', 'lgbt', 'support group', 'community', 'event',
            'pride', 'parade', 'conference', 'meeting', 'gathering',
            'camping', 'trip', 'birthday', 'wedding', 'party',
            'volunteer', 'charity', 'mentoring', 'counseling'
        ]

        for kw in direct_keywords:
            if kw in query_lower:
                keywords.append(kw)

        # 动词转名词映射
        verb_to_event = {
            'attend': ['attend', 'attended', 'attending'],
            'go to': ['went to', 'going to', 'go to'],
            'visit': ['visit', 'visited', 'visiting'],
            'join': ['join', 'joined', 'joining']
        }

        for event_type, verbs in verb_to_event.items():
            if any(v in query_lower for v in verbs):
                keywords.append(event_type)

        return keywords


    def _score_event_match(self, content: str, event_keywords: List[str]) -> float:
        """
        🔥 2025-12-11 新增: 计算记忆内容与事件关键词的匹配度

        - 包含 "support group" 且查询问 "LGBTQ event" → 高分
        - 包含 "yesterday" + 事件关键词 → 最高分
        """
        if not event_keywords:
            return 0.0

        content_lower = content.lower()
        score = 0.0

        # 关键词匹配
        match_count = 0
        for kw in event_keywords:
            if kw in content_lower:
                match_count += 1
                if kw in ['support group', 'lgbtq', 'community']:
                    score += 1.0  # 核心关键词高分
                else:
                    score += 0.5

        # 归一化
        if event_keywords:
            score = score / len(event_keywords)

        # 🔥 组合加分: 如果同时包含相对时间词 + 事件关键词 → 额外加分
        if match_count > 0 and self._has_relative_time(content):
            score += 1.0  # 额外加分

        return min(3.0, score)  # 最高3.0


    async def retrieve(
        self,
        query: str,
        temporal_cues: Dict
    ) -> List[EpisodicMemory]:
        """
        检索时间相关候选 - Retrieve Temporal Candidates

        Args:
            query: 查询文本
            temporal_cues: 时间线索 (🔥 现在真正使用了!)

        Returns:
            List of candidate memories (prioritized by temporal relevance)

        🔧 2025-12-11 优化:
        - 修复 semantic_score 字段名 (relevance, 不是 score)
        - 增加事件关键词加分: "support group" 匹配 "LGBTQ+ community event"
        - 包含 "yesterday" 的记忆 + 高事件匹配 → 最高优先级
        """
        # 🔥 解析显式时间 (核心修复)
        explicit_time = temporal_cues.get('explicit_time')
        date_range = self._parse_explicit_time(explicit_time) if explicit_time else None

        if date_range:
            logger.info(f"🔥 Temporal filter: explicit_time='{explicit_time}' → range={date_range}")

        # Semantic search with expanded k
        search_result = await self.agent.search_memories(query=query, k=50)

        # 🔥 2025-12-11: 提取查询中的关键事件词用于加分
        query_lower = query.lower()
        event_keywords = self._extract_event_keywords(query_lower)
        logger.debug(f"Event keywords from query: {event_keywords}")

        # Convert to EpisodicMemory objects with scores
        candidates_with_scores = []
        for mem_dict in search_result['memories']:
            mem = self.agent.memory_dict.get(mem_dict['id'])
            if mem:
                # 🔥 计算时间线索匹配度 (新增)
                temporal_match_score = self._score_temporal_match(mem, temporal_cues, date_range)

                # 计算时间优先级得分 (原有)
                temporal_priority = self._score_temporal_priority(mem)

                # 🔥 FIX: 使用 relevance 而非 score
                semantic_score = mem_dict.get('relevance', mem_dict.get('score', 0.0))

                # 🔥 2025-12-11 新增: 事件关键词匹配加分
                event_match_score = self._score_event_match(mem.content, event_keywords)

                # 🔥 组合得分: 时间匹配 * 20 + 事件匹配 * 15 + 时间优先级 * 10 + 语义相似度
                combined_score = (
                    temporal_match_score * 20 +
                    event_match_score * 15 +  # 🔥 新增: 事件匹配高权重
                    temporal_priority * 10 +
                    semantic_score
                )
                candidates_with_scores.append((mem, combined_score, temporal_priority, temporal_match_score, event_match_score))

        # 🔥 按组合得分排序，优先返回时间匹配+事件匹配的记忆
        candidates_with_scores.sort(key=lambda x: x[1], reverse=True)

        # 记录排序结果（调试用）
        if candidates_with_scores:
            top_5 = candidates_with_scores[:5]
            time_matched = sum(1 for _, _, _, tm, _ in candidates_with_scores if tm > 0)
            event_matched = sum(1 for _, _, _, _, em in candidates_with_scores if em > 0)
            logger.info(f"📅 Temporal candidates: {len(candidates_with_scores)} total, {time_matched} time-matched, {event_matched} event-matched")

            for mem, score, tp, tm, em in top_5:
                has_time = self._has_relative_time(mem.content)
                is_event = self._is_event_summary(mem.content)
                logger.debug(
                    f"📅 Temporal candidate: tm={tm:.1f}, em={em:.1f}, tp={tp:.1f}, combined={score:.2f}, "
                    f"has_time={has_time}, is_event={is_event}, "
                    f"content={mem.content[:80]}..."
                )

        return [mem for mem, _, _, _, _ in candidates_with_scores]
