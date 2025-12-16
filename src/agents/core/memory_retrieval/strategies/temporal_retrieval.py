"""
Temporal Retrieval Strategy
时间检索策略 - 基于时间维度的记忆检索
"""

from .base import RetrievalStrategy
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)


class TemporalRetrievalStrategy(RetrievalStrategy):
    """
    时间检索策略

    功能:
    1. 根据时间范围过滤记忆
    2. 自动从查询中提取时间表达式
    3. 支持相对时间('yesterday', 'last week')和绝对时间
    4. 结合语义检索提高准确性

    特性:
    - 智能时间解析
    - 相对时间支持
    - 时间范围过滤
    """

    @property
    def strategy_name(self) -> str:
        return "temporal"

    async def retrieve(
        self,
        query: str,
        time_range: Optional[Dict[str, Any]] = None,
        k: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        时间检索主入口

        Args:
            query: 查询文本
            time_range: 时间范围 {'start': ISO时间, 'end': ISO时间} 或 {'relative': 'yesterday'}
            k: 返回数量

        Returns:
            检索结果
        """
        if not self.db_manager:
            return {'error': 'Database manager not available', 'memories': []}

        logger.info(f"Temporal retrieval: query='{query}', time_range={time_range}")

        # 1. 自动从query中提取时间表达式(如果未提供time_range)
        if not time_range:
            time_range = self._extract_time_from_query(query)
            logger.debug(f"Extracted time range from query: {time_range}")

        # 2. 解析时间范围
        start_time, end_time = self._parse_time_range(time_range)

        # 3. 获取候选记忆
        all_memories = self.db_manager.search_memories(limit=500)

        # 4. 时间过滤
        filtered_memories = []
        for memory in all_memories:
            mem_time = self._get_memory_timestamp(memory)

            if mem_time:
                # 应用时间过滤
                if start_time and mem_time < start_time:
                    continue
                if end_time and mem_time > end_time:
                    continue

                # 计算时间匹配度
                time_match_score = self._calculate_time_match(
                    mem_time,
                    start_time,
                    end_time
                )

                filtered_memories.append({
                    'memory': memory.to_dict(),
                    'timestamp': mem_time.isoformat(),
                    'retrieval_confidence': time_match_score,
                    'retrieval_method': 'temporal'
                })

        # 5. 按时间排序(默认最新在前)
        filtered_memories.sort(
            key=lambda m: m['timestamp'],
            reverse=True
        )

        # 6. 如果有query文本,进行语义过滤
        if query.strip():
            filtered_memories = self._semantic_filter(query, filtered_memories)

        # 7. 返回top-k
        result_memories = filtered_memories[:k]

        logger.info(
            f"Temporal retrieval: {len(all_memories)} → "
            f"{len(filtered_memories)} → {len(result_memories)} memories"
        )

        return {
            'memories': result_memories,
            'total_count': len(result_memories),
            'strategy': self.strategy_name,
            'time_range': {
                'start': start_time.isoformat() if start_time else None,
                'end': end_time.isoformat() if end_time else None
            }
        }

    def _extract_time_from_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        从查询中提取时间表达式

        支持的模式:
        - 'yesterday', 'last week', 'last month', 'last year'
        - '3 days ago', '2 weeks ago'
        - 具体日期模式

        Args:
            query: 查询文本

        Returns:
            时间范围字典或None
        """
        query_lower = query.lower()

        # 相对时间模式
        if 'yesterday' in query_lower or '昨天' in query:
            return {'relative': 'yesterday'}

        if 'last week' in query_lower or '上周' in query:
            return {'relative': 'last_week'}

        if 'last month' in query_lower or '上个月' in query:
            return {'relative': 'last_month'}

        if 'last year' in query_lower or '去年' in query:
            return {'relative': 'last_year'}

        # 'N days/weeks/months ago' 模式
        days_ago_match = re.search(r'(\d+)\s*days?\s*ago', query_lower)
        if days_ago_match:
            days = int(days_ago_match.group(1))
            return {'relative': f'{days}_days_ago'}

        weeks_ago_match = re.search(r'(\d+)\s*weeks?\s*ago', query_lower)
        if weeks_ago_match:
            weeks = int(weeks_ago_match.group(1))
            return {'relative': f'{weeks}_weeks_ago'}

        # 具体年份 (e.g., '2023', 'in 2022')
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            year = int(year_match.group(1))
            return {
                'start': f'{year}-01-01T00:00:00',
                'end': f'{year}-12-31T23:59:59'
            }

        return None

    def _parse_time_range(
        self,
        time_range: Optional[Dict[str, Any]]
    ) -> tuple[Optional[datetime], Optional[datetime]]:
        """
        解析时间范围

        Args:
            time_range: 时间范围字典

        Returns:
            (start_time, end_time) 元组
        """
        if not time_range:
            return None, None

        start_time = None
        end_time = None

        # 相对时间
        if 'relative' in time_range:
            relative = time_range['relative']
            now = datetime.now()

            if relative == 'yesterday':
                start_time = now - timedelta(days=1)
                end_time = now

            elif relative == 'last_week':
                start_time = now - timedelta(weeks=1)
                end_time = now

            elif relative == 'last_month':
                start_time = now - timedelta(days=30)
                end_time = now

            elif relative == 'last_year':
                start_time = now - timedelta(days=365)
                end_time = now

            # 'N days/weeks ago'
            elif '_days_ago' in relative:
                days = int(relative.split('_')[0])
                start_time = now - timedelta(days=days)
                end_time = now

            elif '_weeks_ago' in relative:
                weeks = int(relative.split('_')[0])
                start_time = now - timedelta(weeks=weeks)
                end_time = now

        # 绝对时间
        else:
            if 'start' in time_range:
                try:
                    start_time = datetime.fromisoformat(time_range['start'])
                except Exception as e:
                    logger.warning(f"Failed to parse start time: {e}")

            if 'end' in time_range:
                try:
                    end_time = datetime.fromisoformat(time_range['end'])
                except Exception as e:
                    logger.warning(f"Failed to parse end time: {e}")

        return start_time, end_time

    def _get_memory_timestamp(self, memory) -> Optional[datetime]:
        """
        获取记忆的事件时间 - 🔥 2025-12-14 修复: 优先使用 metadata.event_time

        优先级:
        1. metadata['event_time'] - 真正的事件发生时间
        2. metadata['conversation_date'] - 对话日期
        3. timestamp - 存储时间 (fallback)

        Args:
            memory: 记忆对象 (可以是对象或字典格式)

        Returns:
            datetime对象或None
        """
        try:
            # 1. 优先从 metadata 获取 event_time (真正的事件时间)
            metadata = None
            if hasattr(memory, 'metadata') and memory.metadata:
                metadata = memory.metadata
            elif isinstance(memory, dict):
                metadata = memory.get('metadata', {})
                # 处理嵌套格式 {'memory': {..., 'metadata': {...}}}
                if 'memory' in memory and isinstance(memory['memory'], dict):
                    metadata = memory['memory'].get('metadata', {})

            if metadata:
                # 优先使用 event_time
                event_time = metadata.get('event_time')
                if event_time:
                    if isinstance(event_time, str):
                        try:
                            return datetime.fromisoformat(event_time.replace('Z', '+00:00')).replace(tzinfo=None)
                        except ValueError:
                            pass
                    elif isinstance(event_time, datetime):
                        return event_time

                # 其次使用 conversation_date
                conv_date = metadata.get('conversation_date')
                if conv_date:
                    if isinstance(conv_date, str):
                        try:
                            return datetime.fromisoformat(conv_date.replace('Z', '+00:00')).replace(tzinfo=None)
                        except ValueError:
                            pass
                    elif isinstance(conv_date, datetime):
                        return conv_date

            # 2. 最后回退到 timestamp (存储时间)
            ts = None
            if hasattr(memory, 'timestamp') and memory.timestamp:
                ts = memory.timestamp
            elif isinstance(memory, dict):
                ts = memory.get('timestamp')
                if not ts and 'memory' in memory:
                    ts = memory['memory'].get('timestamp')

            if ts:
                if isinstance(ts, str):
                    try:
                        return datetime.fromisoformat(ts.replace('Z', '+00:00')).replace(tzinfo=None)
                    except ValueError:
                        pass
                elif isinstance(ts, datetime):
                    return ts

        except Exception as e:
            logger.debug(f"Failed to get memory timestamp: {e}")

        return None

    def _calculate_time_match(
        self,
        mem_time: datetime,
        start_time: Optional[datetime],
        end_time: Optional[datetime]
    ) -> float:
        """
        计算时间匹配度

        在时间范围内的记忆,越接近范围中心,分数越高

        Args:
            mem_time: 记忆时间
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            匹配度分数 [0.5, 1.0]
        """
        if not start_time or not end_time:
            return 0.8  # 默认分数

        try:
            # 计算范围中心
            range_center = start_time + (end_time - start_time) / 2

            # 计算距离
            time_range_span = (end_time - start_time).total_seconds()
            distance_from_center = abs((mem_time - range_center).total_seconds())

            # 归一化距离 [0, 1],然后反转为分数
            if time_range_span > 0:
                normalized_distance = min(distance_from_center / (time_range_span / 2), 1.0)
                score = 0.5 + 0.5 * (1 - normalized_distance)
            else:
                score = 1.0

            return score

        except Exception as e:
            logger.debug(f"Failed to calculate time match: {e}")
            return 0.7

    def _semantic_filter(self, query: str, memories: List[Dict]) -> List[Dict]:
        """
        语义过滤(简单版)

        过滤掉与query完全无关的记忆

        Args:
            query: 查询文本
            memories: 记忆列表

        Returns:
            过滤后的记忆列表
        """
        if not query or not memories:
            return memories

        # 简单的关键词匹配
        query_lower = query.lower()
        query_tokens = set(re.findall(r'\w+', query_lower))

        filtered = []
        for mem in memories:
            content = str(mem.get('memory', {}).get('content', '')).lower()
            content_tokens = set(re.findall(r'\w+', content))

            # 至少匹配一个关键词
            if query_tokens & content_tokens:
                filtered.append(mem)

        return filtered if filtered else memories  # 如果全部过滤掉,返回原列表
