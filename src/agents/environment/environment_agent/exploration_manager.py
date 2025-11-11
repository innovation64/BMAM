"""
Environment Agent Module - Exploration Manager
环境智能体模块 - 探索管理器

处理外部数据源探索和知识获取。
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..data_sources import (
    ExplorationQuery, ExplorationResult, DataSourceType, DataSourcePriority
)

logger = logging.getLogger(__name__)


class ExplorationManagerMixin:
    """探索管理Mixin"""

    async def explore_external(
        self,
        query: str,
        query_type: str = "general",
        max_results: int = 5,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """探索外部数据源"""
        self.exploration_count += 1

        exploration_query = ExplorationQuery(
            query=query,
            query_type=query_type,
            max_results=max_results,
            priority=DataSourcePriority[priority.upper()]
        )

        # Select appropriate data source
        data_source = await self._select_data_source(exploration_query)
        if not data_source:
            return {'error': 'No suitable data source available'}

        # Execute query
        try:
            result = await data_source.query(exploration_query)

            # Store to memory if significant
            if result.total_results > 0 and self.brain_coordinator:
                await self._store_exploration_to_memory(exploration_query, result)

            # Log exploration
            await self._log_exploration_event(exploration_query, result, data_source.source_type)

            return {
                'exploration_complete': True,
                'query': query,
                'source_type': data_source.source_type.value,
                'total_results': result.total_results,
                'results': result.results[:max_results],
                'confidence': result.confidence
            }

        except Exception as e:
            logger.error(f"Exploration failed: {e}")
            return {'error': f'Exploration failed: {str(e)}'}

    async def _select_data_source(self, query: ExplorationQuery):
        """选择合适的数据源"""
        available_sources = self.data_source_registry.get_available_sources()

        for source in available_sources:
            if source.is_available():
                return source

        return None

    async def _store_exploration_to_memory(
        self,
        query: ExplorationQuery,
        result: ExplorationResult
    ):
        """存储探索结果到记忆"""
        try:
            if hasattr(self.brain_coordinator, 'hippocampus'):
                hippocampus = self.brain_coordinator.hippocampus

                # Create summary of exploration
                content = f"External exploration: {query.query}"
                if result.results:
                    content += f" | Found: {result.results[0].get('title', result.results[0].get('snippet', 'result'))}"

                await hippocampus.store_memory(
                    content=content,
                    entities=[query.query],
                    importance=0.6,
                    emotion_tags=[],
                    emotion_intensity=0.3,
                    metadata={
                        'query_type': query.query_type,
                        'total_results': result.total_results,
                        'source': 'external_exploration'
                    }
                )
        except Exception as e:
            logger.error(f"Failed to store exploration to memory: {e}")

    async def _log_exploration_event(
        self,
        query: ExplorationQuery,
        result: ExplorationResult,
        source_type: DataSourceType
    ):
        """记录探索事件"""
        logger.info(
            f"Exploration: query='{query.query}', "
            f"type={query.query_type}, source={source_type.value}, "
            f"results={result.total_results}"
        )

    async def get_data_source_statistics(self) -> Dict[str, Any]:
        """获取数据源统计"""
        stats = {
            'total_sources': len(self.data_source_registry.get_available_sources()),
            'available_sources': [],
            'exploration_count': self.exploration_count
        }

        for source in self.data_source_registry.get_available_sources():
            stats['available_sources'].append({
                'type': source.source_type.value,
                'available': source.is_available()
            })

        return stats


__all__ = ['ExplorationManagerMixin']
