"""
日期提取工具 - 从query中提取时间范围

用于temporal推理的时序过滤
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DateExtractor:
    """从查询中提取日期和时间范围"""

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

    @staticmethod
    def extract_dates_from_query(query: str, default_year: int = 2023) -> list:
        """
        从query中提取所有日期

        Returns:
            List of datetime objects
        """
        query_lower = query.lower()
        dates = []

        # Pattern 1: "DD Month YYYY" or "DD Month, YYYY"
        # Example: "8 May 2023", "25 May, 2023"
        pattern1 = r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[,\s]*(\d{4})?'
        matches1 = re.finditer(pattern1, query_lower)

        for match in matches1:
            day = int(match.group(1))
            month_str = match.group(2)
            year = int(match.group(3)) if match.group(3) else default_year

            month = DateExtractor.MONTHS.get(month_str, 1)

            try:
                date = datetime(year, month, day)
                dates.append(date)
                logger.debug(f"Extracted date: {date.strftime('%Y-%m-%d')}")
            except ValueError:
                logger.warning(f"Invalid date: {day}/{month}/{year}")

        # Pattern 2: "YYYY-MM-DD"
        # Example: "2023-05-08"
        pattern2 = r'(\d{4})-(\d{1,2})-(\d{1,2})'
        matches2 = re.finditer(pattern2, query_lower)

        for match in matches2:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3))

            try:
                date = datetime(year, month, day)
                dates.append(date)
                logger.debug(f"Extracted date: {date.strftime('%Y-%m-%d')}")
            except ValueError:
                logger.warning(f"Invalid date: {year}-{month}-{day}")

        return dates

    @staticmethod
    def extract_time_range(query: str, default_year: int = 2023) -> Optional[Dict[str, Any]]:
        """
        从query中提取时间范围

        Args:
            query: 用户问题
            default_year: 默认年份

        Returns:
            {'start': '2023-05-08', 'end': '2023-05-25'} or None
        """
        dates = DateExtractor.extract_dates_from_query(query, default_year)

        if not dates:
            return None

        # 如果只有一个日期,返回该日期所在月份的范围
        if len(dates) == 1:
            date = dates[0]
            # 返回该月的范围
            start_of_month = datetime(date.year, date.month, 1)

            # 计算月末
            if date.month == 12:
                end_of_month = datetime(date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_of_month = datetime(date.year, date.month + 1, 1) - timedelta(days=1)

            return {
                'start': start_of_month.strftime('%Y-%m-%d'),
                'end': end_of_month.strftime('%Y-%m-%d')
            }

        # 如果有多个日期,返回最小和最大日期之间的范围
        dates_sorted = sorted(dates)
        return {
            'start': dates_sorted[0].strftime('%Y-%m-%d'),
            'end': dates_sorted[-1].strftime('%Y-%m-%d')
        }

    @staticmethod
    def detect_temporal_question(query: str) -> bool:
        """
        检测是否是temporal问题

        Returns:
            True if temporal question
        """
        temporal_keywords = [
            'how long', 'how many days', 'how many months', 'how many years',
            'duration', 'between', 'passed', 'elapsed', 'since', 'until',
            'when', 'date', 'time'
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in temporal_keywords)


# 测试代码
if __name__ == '__main__':
    # 测试用例
    test_queries = [
        "How many days passed between 8 May 2023 and 25 May 2023?",
        "When did Caroline first meet Dr. Sarah on 27 May 2023?",
        "What happened on 12 May?",
        "Between May 8 and June 3, what did Caroline do?"
    ]

    extractor = DateExtractor()

    for query in test_queries:
        print(f"\n查询: {query}")
        dates = extractor.extract_dates_from_query(query)
        print(f"提取的日期: {[d.strftime('%Y-%m-%d') for d in dates]}")

        time_range = extractor.extract_time_range(query)
        print(f"时间范围: {time_range}")

        is_temporal = extractor.detect_temporal_question(query)
        print(f"是temporal问题: {is_temporal}")
