"""
Database Manager for Memory Persistence
记忆持久化数据库管理器

Provides comprehensive database operations for storing, retrieving,
and querying memory records using SQLAlchemy ORM.
"""

import os
import threading
from typing import List, Optional, Any, Dict
from pathlib import Path
from datetime import datetime
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .database_models import Base, MemoryRecord
from .database_queries import DatabaseQueryMixin
from ..memory_item import MemoryItem
from ...utils.paths import BMAMPaths

logger = logging.getLogger(__name__)


class DatabaseManager(DatabaseQueryMixin):
    """
    Enhanced Database Manager for Memory Persistence
    增强的记忆持久化数据库管理器

    Handles all database operations including CRUD, search, and statistics
    with thread-safe access and automatic session management.

    Attributes:
        db_url: Database connection URL
        engine: SQLAlchemy engine
        SessionLocal: Session factory
        lock: Thread lock for concurrent access safety

    Example:
        >>> db = DatabaseManager()
        >>> db.save_memory(memory_item)
        >>> memories = db.search_memories(memory_type='episodic')
    """

    def __init__(self, db_url: str = None) -> None:
        """
        Initialize Database Manager
        初始化数据库管理器

        Args:
            db_url: Database URL (default: from env or SQLite)
        """
        self.db_url = db_url or os.getenv(
            "DATABASE_URL",
            f"sqlite:///{BMAMPaths.BRAIN_MEMORY_DB}"
        )

        # Create data directory for SQLite
        if "sqlite://" in self.db_url:
            db_path = self.db_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(self.db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self._migrate_add_user_id_column()
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.lock = threading.Lock()

        logger.debug(f"Database initialized: {self.db_url}")

    def _migrate_add_user_id_column(self) -> None:
        """Add user_id column if missing (backward-compatible migration)."""
        from sqlalchemy import inspect, text
        inspector = inspect(self.engine)
        columns = [c['name'] for c in inspector.get_columns('memories')]
        if 'user_id' not in columns:
            with self.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE memories ADD COLUMN user_id VARCHAR "
                    "NOT NULL DEFAULT 'default'"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_memories_user_id "
                    "ON memories(user_id)"
                ))
                # Backfill from memory_metadata JSON where possible
                conn.execute(text(
                    "UPDATE memories SET user_id = "
                    "json_extract(memory_metadata, '$.user_id') "
                    "WHERE json_extract(memory_metadata, '$.user_id') IS NOT NULL"
                ))
                conn.commit()
            logger.info("Migration: added user_id column to memories table")

    def get_session(self) -> Session:
        """
        Get New Database Session
        获取新的数据库会话

        Returns:
            SQLAlchemy session object
        """
        return self.SessionLocal()

    def save_memory(self, memory: MemoryItem) -> bool:
        """
        Save Memory to Database
        保存记忆到数据库

        Args:
            memory: MemoryItem instance to save

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.lock:
                session = self.get_session()
                try:
                    # Extract user_id from metadata for first-class column
                    meta = memory.metadata or {}
                    user_id = meta.get('user_id', 'default')

                    record = MemoryRecord(
                        id=memory.id,
                        content=memory.content,
                        memory_type=memory.memory_type,
                        importance=memory.importance,
                        emotion_tags=memory.emotion_tags,
                        emotion_intensity=memory.emotion_intensity,
                        brain_region=memory.brain_region,
                        consolidation_level=memory.consolidation_level,
                        access_frequency=memory.access_frequency,
                        decay_rate=memory.decay_rate,
                        stress_marker=memory.stress_marker,
                        timestamp=memory.timestamp,
                        last_accessed=memory.last_accessed,
                        last_consolidated=memory.last_consolidated,
                        associations=memory.associations,
                        source_reliability=memory.source_reliability,
                        context_tags=memory.context_tags,
                        memory_metadata=memory.metadata,
                        embedding_id=memory.embedding_id,
                        user_id=user_id
                    )
                    session.merge(record)
                    session.commit()
                    logger.debug(f"Saved memory {memory.id} to database")
                    return True
                finally:
                    session.close()
        except Exception as e:
            logger.error(f"Failed to save memory {memory.id}: {e}")
            return False

    def load_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """
        Load Memory by ID
        通过ID加载记忆

        Updates access frequency and last accessed timestamp.

        Args:
            memory_id: Unique memory identifier

        Returns:
            MemoryItem if found, None otherwise
        """
        try:
            session = self.get_session()
            try:
                record = session.query(MemoryRecord).filter_by(
                    id=memory_id,
                    is_active=True
                ).first()

                if not record:
                    return None

                memory = self._record_to_memory(record)

                # Update access tracking
                record.access_frequency += 1
                record.last_accessed = datetime.now()
                session.commit()

                return memory
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to load memory {memory_id}: {e}")
            return None

    def _record_to_memory(self, record: MemoryRecord) -> MemoryItem:
        """
        Convert Database Record to MemoryItem
        将数据库记录转换为MemoryItem

        Args:
            record: SQLAlchemy MemoryRecord instance

        Returns:
            MemoryItem instance
        """
        return MemoryItem(
            id=record.id,
            content=record.content,
            memory_type=record.memory_type,
            importance=record.importance,
            emotion_tags=record.emotion_tags or [],
            emotion_intensity=record.emotion_intensity,
            brain_region=record.brain_region,
            consolidation_level=record.consolidation_level,
            access_frequency=record.access_frequency,
            decay_rate=record.decay_rate,
            stress_marker=record.stress_marker,
            timestamp=record.timestamp,
            last_accessed=record.last_accessed,
            last_consolidated=record.last_consolidated,
            associations=record.associations or [],
            source_reliability=record.source_reliability,
            context_tags=record.context_tags or [],
            metadata=record.memory_metadata or {},
            embedding_id=record.embedding_id
        )

    def get_all_memories(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get All Active Memories (for testing and validation)
        获取所有活跃记忆（用于测试和验证）

        Returns all active memories from the database as dictionaries.
        Useful for verifying consolidation and storage mechanisms.

        Args:
            limit: Optional maximum number of memories to return

        Returns:
            List of memory dicts with fields:
            - id: str
            - content: str
            - memory_type: str
            - importance: float
            - timestamp: str (ISO format)
            - consolidation_level: int
            - brain_region: str
            - metadata: dict
            - source: str = 'memory_system'
        """
        memories = []
        try:
            session = self.get_session()
            try:
                query = session.query(MemoryRecord).filter_by(is_active=True)

                if limit:
                    query = query.limit(limit)

                records = query.all()

                for record in records:
                    # Convert to dict format (similar to TemporalLobe format)
                    memory_dict = {
                        'id': record.id,
                        'content': record.content,
                        'memory_type': record.memory_type,
                        'importance': record.importance,
                        'timestamp': record.timestamp.isoformat() if record.timestamp else None,
                        'consolidation_level': record.consolidation_level,
                        'brain_region': record.brain_region,
                        'metadata': record.memory_metadata or {},
                        'source': 'memory_system',  # Add source label
                        'access_frequency': record.access_frequency,
                        'emotion_tags': record.emotion_tags or [],
                        'context_tags': record.context_tags or []
                    }
                    memories.append(memory_dict)

                logger.debug(f"Retrieved {len(memories)} memories from database")

            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")

        return memories
