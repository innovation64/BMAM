#!/usr/bin/env python3
"""
Flexible Date Parser - Multi-locale date parsing with configurable patterns

替换硬编码的英文日期正则,支持:
1. 多语言配置 (en, zh, es, etc.)
2. 可扩展的日期模式
3. dateparser 库作为 fallback
4. 相对日期解析 (yesterday, 上周, etc.)

Author: Person E
"""

import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
import logging

logger = logging.getLogger(__name__)

# 尝试导入 dateparser (可选依赖)
try:
    import dateparser
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False
    logger.warning("dateparser not available, using config-based parsing only")


class FlexibleDateParser:
    """
    灵活的多语言日期解析器

    支持:
    - 配置驱动的日期模式 (替换硬编码正则)
    - 多语言支持 (en, zh, es, ...)
    - 相对日期 (yesterday, tomorrow, 上周, ...)
    - dateparser 作为 fallback
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化日期解析器

        Args:
            config_path: 配置文件路径,默认使用 date_parser_config.json
        """
        if config_path is None:
            config_path = Path(__file__).parent / "date_parser_config.json"

        self.config_path = config_path
        self.config = self._load_config()
        self.default_locale = self.config.get("default_locale", "en")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError) as e:
            logger.error(f"Failed to load date parser config: {e}")
            # 返回最小配置
            return {
                "default_locale": "en",
                "locales": {},
                "fallback_parser": None
            }

    def parse_possible_date(
        self,
        text: str,
        locale: Optional[str] = None,
        reference_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        """
        尝试从文本中解析日期 (drop-in replacement)

        Args:
            text: 输入文本
            locale: 语言/地区代码 (e.g., 'en', 'zh', 'es')
            reference_date: 参考日期 (用于相对日期计算)

        Returns:
            datetime 对象,如果解析失败返回 None

        Examples:
            >>> parser = FlexibleDateParser()
            >>> parser.parse_possible_date("May 8, 2023")
            datetime.datetime(2023, 5, 8, 0, 0)
            >>> parser.parse_possible_date("2023年5月8日", locale='zh')
            datetime.datetime(2023, 5, 8, 0, 0)
            >>> parser.parse_possible_date("yesterday")
            datetime.datetime(2025, 10, 29, 0, 0)
        """
        if not text or not isinstance(text, str):
            return None

        text = text.strip()
        if not text:
            return None

        locale = locale or self.default_locale
        reference_date = reference_date or datetime.now()

        # 策略 1: 相对日期 (today, yesterday, 昨天, etc.)
        relative_result = self._parse_relative_date(text, locale, reference_date)
        if relative_result:
            return relative_result

        # 策略 2: 配置化的模式匹配
        pattern_result = self._parse_with_patterns(text, locale, reference_date)
        if pattern_result:
            return pattern_result

        # 策略 3: dateparser fallback (如果可用)
        if self._should_use_fallback():
            fallback_result = self._parse_with_dateparser(text, locale, reference_date)
            if fallback_result:
                return fallback_result

        return None

    def _parse_relative_date(
        self,
        text: str,
        locale: str,
        reference_date: datetime
    ) -> Optional[datetime]:
        """解析相对日期 (yesterday, 昨天, etc.)"""
        locale_config = self.config.get("locales", {}).get(locale, {})
        relative_dates = locale_config.get("relative_dates", {})

        text_lower = text.lower()

        # 🔥 2025-12-16: 首先尝试解析复杂相对日期模式
        # "the sunday before 25 May", "the friday before May 25"
        complex_result = self._parse_complex_relative_date(text_lower, locale, reference_date)
        if complex_result:
            return complex_result

        # 简单相对日期关键词匹配
        for keyword, days_offset in relative_dates.items():
            if keyword in text_lower:
                result = reference_date + timedelta(days=days_offset)
                return result.replace(hour=0, minute=0, second=0, microsecond=0)

        return None

    def _parse_complex_relative_date(
        self,
        text: str,
        locale: str,
        reference_date: datetime
    ) -> Optional[datetime]:
        """
        🔥 2025-12-16: 解析复杂相对日期表达式

        处理以下模式:
        - "the sunday before 25 May" → 25 May 前的那个周日
        - "the friday before May 25, 2023" → 2023年5月25日前的那个周五
        - "sunday before May 25th" → May 25 前的那个周日
        - "the week before 9 June" → 9 June 前一周 (约 2 June)
        """
        locale_config = self.config.get("locales", {}).get(locale, {})
        weekdays = locale_config.get("weekdays", {})
        months_map = locale_config.get("months", {})

        # 🔥 先尝试 "the week before [date]" 模式
        week_before_result = self._parse_week_before_pattern(text, months_map, reference_date)
        if week_before_result:
            return week_before_result

        # 模式: "the [weekday] before [date]"
        pattern = r'(?:the\s+)?(\w+day)\s+before\s+(\d{1,2})?\s*(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)(?:\s+(\d{4}))?'

        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            # 尝试另一种格式: "the [weekday] before [month] [day]"
            pattern2 = r'(?:the\s+)?(\w+day)\s+before\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?'
            match = re.search(pattern2, text, re.IGNORECASE)
            if match:
                weekday_str = match.group(1).lower()
                month_str = match.group(2).lower()
                day = int(match.group(3))
                year = int(match.group(4)) if match.group(4) else reference_date.year
            else:
                return None
        else:
            weekday_str = match.group(1).lower()
            day = int(match.group(2)) if match.group(2) else 1
            month_str = match.group(3).lower()
            year = int(match.group(4)) if match.group(4) else reference_date.year

        # 获取目标weekday的编号 (0=Monday, 6=Sunday)
        target_weekday = weekdays.get(weekday_str)
        if target_weekday is None:
            return None

        # 获取月份
        month = months_map.get(month_str)
        if month is None:
            return None

        try:
            # 构建参考日期
            anchor_date = datetime(year, month, day)

            # 计算这个日期之前的目标weekday
            # weekday(): 0=Monday, 6=Sunday
            days_back = (anchor_date.weekday() - target_weekday) % 7
            if days_back == 0:
                days_back = 7  # 如果是同一天，回退一周

            result = anchor_date - timedelta(days=days_back)
            logger.debug(f"Complex relative date: '{weekday_str} before {day} {month_str}' → {result}")
            return result.replace(hour=0, minute=0, second=0, microsecond=0)

        except (ValueError, Exception) as e:
            logger.warning(f"Failed to parse complex relative date: {e}")
            return None

    def _parse_week_before_pattern(
        self,
        text: str,
        months_map: Dict[str, int],
        reference_date: datetime
    ) -> Optional[datetime]:
        """
        🔥 2025-12-16: 解析 "the week before [date]" 模式

        Examples:
        - "the week before 9 June 2023" → 2 June 2023 (7 days before)
        - "week before June 9" → June 2 of reference year
        """
        # 模式: "the week before [day] [month] [year?]"
        pattern1 = r'(?:the\s+)?week\s+before\s+(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)(?:\s+(\d{4}))?'

        match = re.search(pattern1, text, re.IGNORECASE)
        if not match:
            # 尝试 "week before [month] [day]" 格式
            pattern2 = r'(?:the\s+)?week\s+before\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{4}))?'
            match = re.search(pattern2, text, re.IGNORECASE)
            if match:
                month_str = match.group(1).lower()
                day = int(match.group(2))
                year = int(match.group(3)) if match.group(3) else reference_date.year
            else:
                return None
        else:
            day = int(match.group(1))
            month_str = match.group(2).lower()
            year = int(match.group(3)) if match.group(3) else reference_date.year

        month = months_map.get(month_str)
        if month is None:
            return None

        try:
            anchor_date = datetime(year, month, day)
            result = anchor_date - timedelta(days=7)
            logger.debug(f"Week before pattern: 'week before {day} {month_str}' → {result}")
            return result.replace(hour=0, minute=0, second=0, microsecond=0)
        except (ValueError, Exception) as e:
            logger.warning(f"Failed to parse week before pattern: {e}")
            return None

    def _parse_with_patterns(
        self,
        text: str,
        locale: str,
        reference_date: datetime
    ) -> Optional[datetime]:
        """使用配置化的正则模式解析日期"""
        locale_config = self.config.get("locales", {}).get(locale, {})
        patterns = locale_config.get("patterns", [])
        months_map = locale_config.get("months", {})

        # 按优先级排序
        patterns_sorted = sorted(patterns, key=lambda p: p.get("priority", 999))

        for pattern_config in patterns_sorted:
            regex = pattern_config.get("regex")
            groups = pattern_config.get("groups", [])

            if not regex:
                continue

            try:
                match = re.search(regex, text, re.IGNORECASE)
                if match:
                    # 提取日期组件
                    components = {}
                    for i, group_name in enumerate(groups, 1):
                        value = match.group(i)
                        if value:
                            components[group_name] = value

                    # 转换为 datetime
                    date_obj = self._components_to_datetime(
                        components,
                        months_map,
                        reference_date.year
                    )

                    if date_obj:
                        return date_obj

            except (Exception) as e:
                logger.warning(f"Pattern matching failed: {e}")
                continue

        return None

    def _components_to_datetime(
        self,
        components: Dict[str, str],
        months_map: Dict[str, int],
        default_year: int
    ) -> Optional[datetime]:
        """将日期组件转换为 datetime 对象"""
        try:
            # 提取年月日
            year = int(components.get("year", default_year))

            # 处理月份 (可能是数字或字符串)
            month_str = components.get("month")
            if month_str:
                if month_str.isdigit():
                    month = int(month_str)
                else:
                    month = months_map.get(month_str.lower())
                    if not month:
                        logger.warning(f"Unknown month: {month_str}")
                        return None
            else:
                return None

            # 处理日期
            day_str = components.get("day")
            if day_str:
                day = int(day_str)
            else:
                day = 1  # 默认为月初

            # 构造 datetime
            return datetime(year, month, day)

        except (ValueError) as e:
            logger.warning(f"Invalid date components: {components}, error: {e}")
            return None

    def _should_use_fallback(self) -> bool:
        """检查是否应该使用 fallback parser"""
        return (
            DATEPARSER_AVAILABLE and
            self.config.get("fallback_parser") == "dateparser"
        )

    def _parse_with_dateparser(
        self,
        text: str,
        locale: str,
        reference_date: datetime
    ) -> Optional[datetime]:
        """使用 dateparser 库作为 fallback"""
        if not DATEPARSER_AVAILABLE:
            return None

        try:
            settings = self.config.get("dateparser_settings", {})
            settings["RELATIVE_BASE"] = reference_date

            # 添加语言支持
            languages = [locale, "en"]  # 总是包含英语作为备选

            result = dateparser.parse(
                text,
                languages=languages,
                settings=settings
            )

            return result

        except (Exception) as e:
            logger.warning(f"dateparser failed: {e}")
            return None

    def extract_all_dates(
        self,
        text: str,
        locale: Optional[str] = None,
        reference_date: Optional[datetime] = None
    ) -> List[datetime]:
        """
        从文本中提取所有可能的日期

        Args:
            text: 输入文本
            locale: 语言代码
            reference_date: 参考日期

        Returns:
            日期列表

        Examples:
            >>> parser = FlexibleDateParser()
            >>> parser.extract_all_dates("Between May 8 and June 3, 2023")
            [datetime(2023, 5, 8), datetime(2023, 6, 3)]
        """
        locale = locale or self.default_locale
        reference_date = reference_date or datetime.now()

        locale_config = self.config.get("locales", {}).get(locale, {})
        patterns = locale_config.get("patterns", [])
        months_map = locale_config.get("months", {})

        dates = []

        # 使用所有模式查找
        for pattern_config in patterns:
            regex = pattern_config.get("regex")
            groups = pattern_config.get("groups", [])

            if not regex:
                continue

            try:
                for match in re.finditer(regex, text, re.IGNORECASE):
                    components = {}
                    for i, group_name in enumerate(groups, 1):
                        value = match.group(i)
                        if value:
                            components[group_name] = value

                    date_obj = self._components_to_datetime(
                        components,
                        months_map,
                        reference_date.year
                    )

                    if date_obj and date_obj not in dates:
                        dates.append(date_obj)

            except (Exception) as e:
                logger.warning(f"Pattern extraction failed: {e}")
                continue

        return sorted(dates)

    def get_supported_locales(self) -> List[str]:
        """获取支持的语言列表"""
        return list(self.config.get("locales", {}).keys())

    def add_custom_pattern(
        self,
        locale: str,
        pattern_name: str,
        regex: str,
        groups: List[str],
        priority: int = 100
    ) -> None:
        """
        动态添加自定义日期模式

        Args:
            locale: 语言代码
            pattern_name: 模式名称
            regex: 正则表达式
            groups: 捕获组名称列表 ['day', 'month', 'year']
            priority: 优先级 (数字越小优先级越高)

        Examples:
            >>> parser = FlexibleDateParser()
            >>> parser.add_custom_pattern(
            ...     'en',
            ...     'custom_ddmmyyyy',
            ...     r'(\\d{2})\\.(\\d{2})\\.(\\d{4})',
            ...     ['day', 'month', 'year'],
            ...     priority=1
            ... )
        """
        if locale not in self.config.get("locales", {}):
            self.config["locales"][locale] = {
                "name": locale,
                "months": {},
                "patterns": []
            }

        pattern = {
            "name": pattern_name,
            "regex": regex,
            "groups": groups,
            "priority": priority
        }

        self.config["locales"][locale]["patterns"].append(pattern)


# 便捷函数 (drop-in replacement for legacy code)
def parse_possible_date(
    text: str,
    locale: str = "en",
    reference_date: Optional[datetime] = None
) -> Optional[datetime]:
    """
    便捷函数: 解析日期 (兼容旧代码)

    Args:
        text: 输入文本
        locale: 语言代码 (默认: 'en')
        reference_date: 参考日期

    Returns:
        datetime 对象或 None

    Examples:
        >>> from src.utils.flexible_date_parser import parse_possible_date
        >>> parse_possible_date("May 8, 2023")
        datetime.datetime(2023, 5, 8, 0, 0)
        >>> parse_possible_date("2023年5月8日", locale='zh')
        datetime.datetime(2023, 5, 8, 0, 0)
    """
    parser = FlexibleDateParser()
    return parser.parse_possible_date(text, locale, reference_date)


# 单例模式 (性能优化)
_global_parser: Optional[FlexibleDateParser] = None


def get_global_parser() -> FlexibleDateParser:
    """获取全局单例解析器"""
    global _global_parser
    if _global_parser is None:
        _global_parser = FlexibleDateParser()
    return _global_parser


# 向后兼容: 替换旧 DateExtractor
class DateExtractor:
    """
    向后兼容的 DateExtractor 类

    使用新的 FlexibleDateParser 作为后端
    """

    @staticmethod
    def extract_dates_from_query(query: str, default_year: int = 2023) -> List[datetime]:
        """兼容旧接口"""
        parser = get_global_parser()
        reference_date = datetime(default_year, 1, 1)
        return parser.extract_all_dates(query, locale="en", reference_date=reference_date)

    @staticmethod
    def extract_time_range(query: str, default_year: int = 2023) -> Optional[Dict[str, Any]]:
        """兼容旧接口"""
        dates = DateExtractor.extract_dates_from_query(query, default_year)

        if not dates:
            return None

        if len(dates) == 1:
            date = dates[0]
            start_of_month = datetime(date.year, date.month, 1)

            if date.month == 12:
                end_of_month = datetime(date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_of_month = datetime(date.year, date.month + 1, 1) - timedelta(days=1)

            return {
                'start': start_of_month.strftime('%Y-%m-%d'),
                'end': end_of_month.strftime('%Y-%m-%d')
            }

        dates_sorted = sorted(dates)
        return {
            'start': dates_sorted[0].strftime('%Y-%m-%d'),
            'end': dates_sorted[-1].strftime('%Y-%m-%d')
        }

    @staticmethod
    def detect_temporal_question(query: str) -> bool:
        """兼容旧接口"""
        temporal_keywords = [
            'how long', 'how many days', 'how many months', 'how many years',
            'duration', 'between', 'passed', 'elapsed', 'since', 'until',
            'when', 'date', 'time'
        ]

        query_lower = query.lower()
        return any(keyword in query_lower for keyword in temporal_keywords)
