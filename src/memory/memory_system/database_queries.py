"""
Database Query Operations for Memory Retrieval
记忆检索的数据库查询操作

Provides specialized query operations for filtering and retrieving
memory records based on various criteria.
"""

from typing import List, Any, Dict
import logging

from sqlalchemy.orm import Session

from .database_models import MemoryRecord
from ..memory_item import MemoryItem

logger = logging.getLogger(__name__)


class DatabaseQueryMixin:
    """
    Database Query Operations Mixin
    数据库查询操作混入类

    Provides advanced query methods for memory retrieval with
    flexible filtering and sorting capabilities.

    Note:
        This mixin requires the class to have:
        - self.get_session() -> Session
        - self._record_to_memory(record) -> MemoryItem
    """

    def search_memories(self, **filters) -> List[MemoryItem]:
        """
        Search Memories with Various Filters
        使用多种过滤器搜索记忆

        Args:
            memory_type: Filter by memory type
            brain_region: Filter by brain region
            min_importance: Minimum importance threshold
            consolidation_level: Filter by consolidation level
            limit: Maximum number of results (default: 100)

        Returns:
            List of matching MemoryItem instances
        """
        memories = []
        try:
            session = self.get_session()
            try:
                query = session.query(MemoryRecord).filter_by(is_active=True)

                # Apply filters
                if 'memory_type' in filters:
                    query = query.filter_by(memory_type=filters['memory_type'])
                if 'brain_region' in filters:
                    query = query.filter_by(brain_region=filters['brain_region'])
                if 'min_importance' in filters:
                    query = query.filter(
                        MemoryRecord.importance >= filters['min_importance']
                    )
                if 'consolidation_level' in filters:
                    query = query.filter_by(
                        consolidation_level=filters['consolidation_level']
                    )
                if 'user_id' in filters:
                    uid = filters['user_id']
                    query = query.filter(
                        MemoryRecord.user_id.in_([uid, 'default'])
                    )

                records = query.limit(filters.get('limit', 100)).all()

                for record in records:
                    memory = self._record_to_memory(record)
                    memories.append(memory)

            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")

        return memories

    def load_memories_by_criteria(self, **criteria) -> List[MemoryItem]:
        """
        Load Memories Matching Specific Criteria
        加载符合特定条件的记忆

        Supports episodic and keyword-based retrieval with
        context tags, emotion tags, and temporal ordering.

        Args:
            context_tags: Filter by context tags (string or list)
            emotion_tags: Filter by emotion tags (string or list)
            memory_type: Filter by memory type
            min_importance: Minimum importance threshold
            consolidation_level: Filter by consolidation level
            limit: Maximum number of results (default: 100)

        Returns:
            List of matching MemoryItem instances, ordered by timestamp
        """
        memories = []
        try:
            session = self.get_session()
            try:
                query = session.query(MemoryRecord).filter_by(is_active=True)

                # Filter by context tags
                if 'context_tags' in criteria:
                    context = criteria['context_tags']
                    if isinstance(context, str):
                        context = [context]
                    for tag in context:
                        query = query.filter(
                            MemoryRecord.context_tags.contains(tag)
                        )

                # Filter by emotion tags
                if 'emotion_tags' in criteria:
                    emotion = criteria['emotion_tags']
                    if isinstance(emotion, str):
                        emotion = [emotion]
                    for tag in emotion:
                        query = query.filter(
                            MemoryRecord.emotion_tags.contains(tag)
                        )

                # Filter by memory type
                if 'memory_type' in criteria:
                    query = query.filter_by(memory_type=criteria['memory_type'])

                # Filter by importance threshold
                if 'min_importance' in criteria:
                    query = query.filter(
                        MemoryRecord.importance >= criteria['min_importance']
                    )

                # Filter by consolidation level
                if 'consolidation_level' in criteria:
                    query = query.filter_by(
                        consolidation_level=criteria['consolidation_level']
                    )

                # Filter by user_id (allow 'default' for backward compat)
                if 'user_id' in criteria:
                    uid = criteria['user_id']
                    query = query.filter(
                        MemoryRecord.user_id.in_([uid, 'default'])
                    )

                # Order by timestamp (most recent first)
                query = query.order_by(MemoryRecord.timestamp.desc())

                # Limit results
                limit = criteria.get('limit', 100)
                records = query.limit(limit).all()

                for record in records:
                    memory = self._record_to_memory(record)
                    memories.append(memory)
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to load memories by criteria: {e}")

        return memories

    def get_recent_memories(self, limit: int = 1000) -> List[MemoryItem]:
        """
        Fetch Most Recent Active Memories
        获取最近的活跃记忆

        Used for maintenance tasks like FAISS index rebuilding.

        Args:
            limit: Maximum number of memories to fetch

        Returns:
            List of recent MemoryItem instances
        """
        try:
            session = self.get_session()
            try:
                records = (
                    session.query(MemoryRecord)
                    .filter_by(is_active=True)
                    .order_by(MemoryRecord.timestamp.desc())
                    .limit(limit)
                    .all()
                )

                return [self._record_to_memory(record) for record in records]
            finally:
                session.close()
        except Exception as exc:
            logger.error(f"Failed to fetch recent memories: {exc}")
            return []

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get Memory Database Statistics
        获取记忆数据库统计信息

        Returns:
            Dictionary with memory counts by type and database info
        """
        try:
            session = self.get_session()
            try:
                total = session.query(MemoryRecord).filter_by(
                    is_active=True
                ).count()
                episodic = session.query(MemoryRecord).filter_by(
                    is_active=True,
                    memory_type='episodic'
                ).count()
                semantic = session.query(MemoryRecord).filter_by(
                    is_active=True,
                    memory_type='semantic'
                ).count()

                return {
                    'total_memories': total,
                    'episodic_memories': episodic,
                    'semantic_memories': semantic,
                    'database_url': self.db_url
                }
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {'error': str(e)}
