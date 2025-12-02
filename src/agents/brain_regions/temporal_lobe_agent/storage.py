"""
Storage operations for Temporal Lobe Agent
存储操作模块
"""

import logging
import uuid
import sqlite3
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
import numpy as np

from .data_models import SemanticMemory, MemoryType

logger = logging.getLogger(__name__)


class StorageMixin:
    """Storage operations mixin for TemporalLobeAgent"""

    def _init_persistence(self):
        """Initialize auto-persistence mechanism (SQLite database)"""
        self.db_path = Path("data/temporal_lobe.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database schema if not exists
        self._init_database()

        # Auto-load existing memories from database
        self._load_from_database()

    def _init_database(self):
        """Initialize SQLite database schema for semantic memories and KG"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Semantic memories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_subtype TEXT,
                timestamp TEXT,
                entities TEXT,
                relations TEXT,
                importance REAL,
                event_time TEXT,
                embedding BLOB,
                memory_type TEXT,
                consolidation_level REAL,
                access_count INTEGER,
                metadata TEXT
            )
        """)

        # Knowledge graph triples table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                confidence REAL,
                timestamp TEXT
            )
        """)

        # Create indexes for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_timestamp
            ON semantic_memories(timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_kg_subject
            ON knowledge_graph(subject)
        """)

        conn.commit()
        conn.close()
        logger.info(f"✅ TemporalLobe database initialized at {self.db_path}")

    def _load_from_database(self):
        """Load existing memories from SQLite database on startup"""
        if not self.db_path.exists():
            logger.info("📂 No existing database found, starting fresh")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM semantic_memories")
            rows = cursor.fetchall()

            for row in rows:
                memory = self._row_to_memory(row)
                self.memories.append(memory)
                self.memory_dict[memory.id] = memory

                # Rebuild BM25 index
                self._update_bm25_index(memory)

            # Load knowledge graph triples
            cursor.execute("SELECT subject, predicate, object FROM knowledge_graph")
            kg_rows = cursor.fetchall()
            for subject, predicate, obj in kg_rows:
                self.kg.add_triple(subject, predicate, obj)

            logger.info(
                f"✅ Loaded {len(self.memories)} memories and "
                f"{len(kg_rows)} KG triples from database"
            )

        except sqlite3.OperationalError as e:
            logger.warning(f"Failed to load from database: {e}")
        finally:
            conn.close()

    def _row_to_memory(self, row: tuple) -> SemanticMemory:
        """Convert SQLite row to SemanticMemory object"""
        (
            id, content, memory_subtype, timestamp, entities, relations,
            importance, event_time, embedding, memory_type,
            consolidation_level, access_count, metadata
        ) = row

        return SemanticMemory(
            id=id,
            content=content,
            memory_subtype=memory_subtype,
            timestamp=datetime.fromisoformat(timestamp) if timestamp else datetime.now(),
            entities=json.loads(entities) if entities else [],
            relations=json.loads(relations) if relations else [],
            importance=importance or 0.5,
            metadata=json.loads(metadata) if metadata else {},
            event_time=datetime.fromisoformat(event_time) if event_time else None,
            embedding=pickle.loads(embedding) if embedding else None,
            memory_type=MemoryType(memory_type) if memory_type else None,
            consolidation_level=consolidation_level or 0.0,
            access_count=access_count or 0
        )

    def _save_to_database(self, memory: SemanticMemory):
        """Save a single memory to SQLite database (auto-persistence)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO semantic_memories
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.content,
                memory.memory_subtype,
                memory.timestamp.isoformat() if memory.timestamp else None,
                json.dumps(memory.entities) if memory.entities else None,
                json.dumps(memory.relations) if memory.relations else None,
                memory.importance,
                memory.event_time.isoformat() if memory.event_time else None,
                pickle.dumps(memory.embedding) if memory.embedding is not None else None,
                memory.memory_type.value if memory.memory_type else None,
                memory.consolidation_level if hasattr(memory, 'consolidation_level') else 0.0,
                memory.access_count if hasattr(memory, 'access_count') else 0,
                json.dumps(memory.metadata) if memory.metadata else None
            ))

            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save memory to database: {e}")
        finally:
            conn.close()

    def _save_kg_triple_to_database(self, subject: str, predicate: str, obj: str):
        """Save a single KG triple to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO knowledge_graph (subject, predicate, object, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (subject, predicate, obj, 1.0, datetime.now().isoformat()))

            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save KG triple to database: {e}")
        finally:
            conn.close()

    async def store_memory(
        self,
        content: str,
        memory_subtype: str = 'semantic',
        entities: List[str] = None,
        relations: List[Tuple[str, str, str]] = None,
        importance: float = 0.5,
        metadata: Dict[str, Any] = None,
        event_time: datetime = None,  # 🔥 NEW: 事件发生时间
        memory_type: Optional[MemoryType] = None  # 🔥 阶段1: 记忆类型
    ) -> Dict[str, Any]:
        """
        存储语义记忆

        Args:
            content: 记忆内容
            memory_subtype: 'semantic' or 'common_sense'
            entities: 相关实体
            relations: 关系三元组 [(source, relation, target)]
            importance: 重要性
            metadata: 元数据
            event_time: 事件发生时间 (None = 使用当前时间)
            memory_type: 记忆类型 (FACTUAL/RELATIONAL/TEMPORAL/PROCEDURAL/SUMMARY)

        Returns:
            {'memory_id': str, 'stored': bool, 'kg_updated': bool}
        """

        # 🔥 如果是字符串，转换为datetime
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        # 🔥 优先级2: 计算并缓存embedding（如果embedding_service可用）
        embedding = None
        if self.embedding_service:
            try:
                embedding_result = await self.embedding_service.encode_text(content)
                # 转换为list（避免numpy序列化问题）
                if hasattr(embedding_result, 'tolist'):
                    embedding = embedding_result.tolist()
                else:
                    embedding = embedding_result
            except (RuntimeError, ValueError) as e:
                logger.warning(f"Failed to compute embedding for memory: {e}")

        # 创建记忆项
        memory = SemanticMemory(
            id=uuid.uuid4().hex,
            content=content,
            memory_subtype=memory_subtype,
            timestamp=datetime.now(),  # 学习时间
            entities=entities or [],
            relations=relations or [],
            importance=importance,
            metadata=metadata or {},
            event_time=event_time,  # 🔥 事件时间
            embedding=embedding,  # 🔥 优先级2: 缓存embedding
            memory_type=memory_type  # 🔥 阶段1: 记忆类型
        )

        logger.info(f"🟢 [TemporalLobe] Created SemanticMemory: id={memory.id[:16]}, "
                   f"source_memory_id={metadata.get('source_memory_id', 'N/A') if metadata else 'N/A'}, "
                   f"content_len={len(content)}")

        # 存储到列表
        self.memories.append(memory)
        self.memory_dict[memory.id] = memory

        logger.debug(f"📥 [TemporalLobe] Added to self.memories, total count={len(self.memories)}")

        # 🧠 Key-Value Store Integration
        if self.memory_store:
            self.memory_store.store(
                memory_id=memory.id,
                content=memory.content,
                vector=np.array(memory.embedding) if memory.embedding else None,
                entities=memory.entities,
                timestamp=memory.timestamp,
                relations=memory.relations,
                details=memory.metadata,
                importance=memory.importance
            )

        # 🔥 自动持久化到SQLite数据库
        try:
            self._save_to_database(memory)
            logger.debug(f"💾 [TemporalLobe] Saved to database: {memory.id[:16]}")
        except Exception as db_error:
            logger.error(f"❌ [TemporalLobe] Failed to save to database: {db_error}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")

        # 更新BM25索引
        self._update_bm25_index(memory)

        # 🔥 更新知识图谱
        kg_updated = False
        for (source, relation, target) in memory.relations:
            self.kg.add_triple(source, relation, target)
            # 🔥 持久化KG triple
            self._save_kg_triple_to_database(source, relation, target)
            kg_updated = True

        if self.kg_builder and (memory.entities or memory.relations):
            try:
                builder_entities = [
                    {'name': name, 'type': 'Unknown', 'mentions': 1}
                    for name in memory.entities
                ]
                builder_relations = [
                    {'source': source, 'relation': relation, 'target': target}
                    for (source, relation, target) in memory.relations
                ]
                self.kg_builder.add_to_graph(builder_entities, builder_relations)
            except (Exception) as e:
                logger.warning(f"Failed to sync semantic memory into shared KG: {e}")

        # 容量控制
        if len(self.memories) > self.capacity:
            await self._trigger_forgetting()

        self.total_stored += 1

        result = {
            'memory_id': memory.id,
            'stored': True,
            'kg_updated': kg_updated,
            'capacity_status': self._get_capacity_status()
        }

        logger.info(f"✅ [TemporalLobe] store_memory completed: id={memory.id[:16]}, "
                   f"total_memories={len(self.memories)}, total_stored={self.total_stored}")

        return result

    async def ingest_kg_relations(
        self,
        relations: List[Dict[str, Any]],
        source_memory_id: Optional[str] = None,
        source_region: str = 'hippocampus',
        sync_builder: bool = False
    ) -> Dict[str, Any]:
        """
        接收来自其他脑区的知识图谱关系 (例如海马体自动抽取)
        并更新颞叶内部的知识图谱
        """
        if not relations:
            return {'triples_added': 0, 'source_memory_id': source_memory_id}

        triples_added = 0
        entity_names: Set[str] = set()

        for rel in relations:
            source = rel.get('source')
            relation = rel.get('relation')
            target = rel.get('target')

            if not (source and relation and target):
                continue

            self.kg.add_triple(source, relation, target)
            # 🔥 持久化KG triple
            self._save_kg_triple_to_database(source, relation, target)
            triples_added += 1
            entity_names.add(source)
            entity_names.add(target)

        if triples_added:
            logger.info(
                f"🔗 Ingested {triples_added} KG relations from {source_region} "
                f"(memory={source_memory_id[:8] if source_memory_id else 'unknown'})"
            )

        if sync_builder and self.kg_builder and triples_added:
            try:
                builder_entities = [
                    {'name': name, 'type': 'Unknown', 'mentions': 1}
                    for name in entity_names
                    if name
                ]
                self.kg_builder.add_to_graph(builder_entities, relations)
            except (Exception) as e:
                logger.warning(f"Failed to sync relations to shared KG builder: {e}")

        return {
            'triples_added': triples_added,
            'source_memory_id': source_memory_id
        }
