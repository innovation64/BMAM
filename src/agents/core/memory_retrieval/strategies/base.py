"""
Base Retrieval Strategy
检索策略抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RetrievalStrategy(ABC):
    """
    检索策略抽象基类

    设计原则:
    1. 定义统一的retrieve接口
    2. 提供公共的辅助方法
    3. 子类只需实现核心检索逻辑

    Usage:
        class MyStrategy(RetrievalStrategy):
            @property
            def strategy_name(self) -> str:
                return "my_strategy"

            async def retrieve(self, **kwargs) -> Dict[str, Any]:
                # 实现检索逻辑
                pass
    """

    def __init__(self, db_manager=None, embedding_service=None, vector_db=None):
        """
        初始化检索策略

        Args:
            db_manager: 数据库管理器
            embedding_service: 嵌入服务
            vector_db: 向量数据库
        """
        self.db_manager = db_manager
        self.embedding_service = embedding_service
        self.vector_db = vector_db
        self.logger = logger

    @abstractmethod
    async def retrieve(self, **kwargs) -> Dict[str, Any]:
        """
        执行检索 - 子类必须实现

        Returns:
            {
                'memories': List[Dict],
                'total_count': int,
                'strategy': str,
                'metadata': Dict
            }
        """
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """策略名称 - 子类必须实现"""
        pass

    def _update_memory_access(self, memory):
        """
        更新记忆访问统计 (公共逻辑)

        Args:
            memory: 记忆对象
        """
        if memory and self.db_manager:
            try:
                memory.access_frequency += 1
                memory.last_accessed = datetime.now()
                self.db_manager.save_memory(memory)
            except Exception as e:
                self.logger.warning(f"Failed to update memory access: {e}")

    def _filter_by_time_range(
        self,
        memories: List[Dict],
        time_range: Optional[Dict[str, Any]]
    ) -> List[Dict]:
        """
        按时间范围过滤 (公共逻辑)

        Args:
            memories: 记忆列表
            time_range: 时间范围字典 {'start': ISO时间, 'end': ISO时间}

        Returns:
            过滤后的记忆列表
        """
        if not time_range:
            return memories

        filtered_memories = []
        start_time = None
        end_time = None

        # 解析时间范围
        if 'start' in time_range:
            try:
                start_time = datetime.fromisoformat(time_range['start'])
            except Exception as e:
                self.logger.warning(f"Failed to parse start time: {e}")

        if 'end' in time_range:
            try:
                end_time = datetime.fromisoformat(time_range['end'])
            except Exception as e:
                self.logger.warning(f"Failed to parse end time: {e}")

        # 过滤记忆
        for mem in memories:
            timestamp_str = self._extract_timestamp(mem)

            if timestamp_str:
                try:
                    mem_time = datetime.fromisoformat(
                        timestamp_str.replace('Z', '+00:00')
                    ).replace(tzinfo=None)

                    # 时间范围过滤
                    if start_time and mem_time < start_time:
                        continue
                    if end_time and mem_time > end_time:
                        continue

                    filtered_memories.append(mem)
                except Exception as e:
                    self.logger.warning(f"Failed to parse memory timestamp {timestamp_str}: {e}")
                    # 无法解析时间的记忆也保留
                    filtered_memories.append(mem)
            else:
                # 没有时间戳的记忆也保留
                filtered_memories.append(mem)

        self.logger.debug(
            f"Time filtering: {len(memories)} → {len(filtered_memories)} memories"
        )

        return filtered_memories

    def _extract_timestamp(self, memory: Dict) -> Optional[str]:
        """
        从记忆对象中提取时间戳 (公共逻辑)

        Args:
            memory: 记忆字典

        Returns:
            时间戳字符串,如果没有则返回None
        """
        # 尝试多种可能的时间戳字段
        if 'memory' in memory and isinstance(memory['memory'], dict):
            return (memory['memory'].get('created_at') or
                    memory['memory'].get('timestamp'))
        elif 'timestamp' in memory:
            return memory['timestamp']
        elif 'created_at' in memory:
            return memory['created_at']

        return None

    def _sort_by_relevance(
        self,
        memories: List[Dict],
        sort_key: str = 'similarity'
    ) -> List[Dict]:
        """
        按相关性排序 (公共逻辑)

        Args:
            memories: 记忆列表
            sort_key: 排序键 ('similarity', 'importance', 'timestamp')

        Returns:
            排序后的记忆列表
        """
        if not memories:
            return memories

        try:
            return sorted(
                memories,
                key=lambda m: m.get(sort_key, 0.0),
                reverse=True
            )
        except Exception as e:
            self.logger.warning(f"Failed to sort memories: {e}")
            return memories
