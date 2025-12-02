"""
Key-Value Stores - 键值分离存储

基于论文 "Key-value memory in the brain" (Benna & Fusi, 2024)

核心概念：
- 键 (Key): 用于检索的表征，优化目标是可辨别性 (Discriminability)
- 值 (Value): 记忆的实际内容，优化目标是保真度 (Fidelity)
- 查询 (Query): 检索线索，与键进行匹配

神经科学对应：
- 海马体 (Hippocampus): 存储"键" - 快速索引，高可辨别性
- 新皮层 (Neocortex): 存储"值" - 详细内容，高保真度

优势：
1. 键和值可独立优化
2. 键可以高度压缩，快速检索
3. 值可以详细完整，准确存储
4. 支持多种类型的键（语义、实体、时间、关系）
"""

import logging
import json
import sqlite3
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


@dataclass
class KeyEntry:
    """键条目"""
    memory_id: str
    vector_key: Optional[np.ndarray] = None      # 语义向量键
    entity_keys: List[str] = field(default_factory=list)  # 实体键
    temporal_key: Optional[datetime] = None      # 时间键
    relation_keys: List[Tuple[str, str, str]] = field(default_factory=list)  # 关系键 (subject, predicate, object)
    discriminative_keys: List[str] = field(default_factory=list)  # 辨别性键
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0


class KeyStore:
    """
    键存储 (海马体职责)

    优化目标: 最大化可辨别性 (Discriminability)

    存储多种类型的检索键：
    1. 语义向量键 - 用于相似度检索
    2. 实体键 - 用于精确实体匹配
    3. 时间键 - 用于时序检索
    4. 关系键 - 用于多跳路径查询
    5. 辨别性键 - 用于区分相似记忆
    """

    def __init__(self, enable_vector_index: bool = True):
        """
        初始化键存储

        Args:
            enable_vector_index: 是否启用向量索引
        """
        self.enable_vector_index = enable_vector_index

        # 主存储
        self.keys: Dict[str, KeyEntry] = {}

        # 索引结构
        self.vector_keys: Dict[str, np.ndarray] = {}                    # memory_id -> vector
        self.entity_index: Dict[str, Set[str]] = defaultdict(set)       # entity -> memory_ids
        self.temporal_index: Dict[str, Set[str]] = defaultdict(set)     # date_str -> memory_ids
        self.relation_index: Dict[Tuple[str, str], Set[str]] = defaultdict(set)  # (entity, relation) -> memory_ids
        self.discriminative_index: Dict[str, Set[str]] = defaultdict(set)  # disc_key -> memory_ids

        # 时间排序列表
        self.temporal_sorted: List[Tuple[datetime, str]] = []  # [(timestamp, memory_id), ...]

        # 统计
        self.total_queries = 0
        self.cache_hits = 0

        logger.info("KeyStore initialized")

    def store_key(
        self,
        memory_id: str,
        vector: Optional[np.ndarray] = None,
        entities: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
        relations: Optional[List[Tuple[str, str, str]]] = None,
        discriminative: Optional[List[str]] = None
    ):
        """
        存储检索键

        Args:
            memory_id: 记忆ID
            vector: 语义向量
            entities: 实体列表
            timestamp: 时间戳
            relations: 关系三元组列表 [(subject, predicate, object), ...]
            discriminative: 辨别性特征列表
        """
        # 创建键条目
        entry = KeyEntry(
            memory_id=memory_id,
            vector_key=vector.copy() if vector is not None else None,
            entity_keys=entities or [],
            temporal_key=timestamp,
            relation_keys=relations or [],
            discriminative_keys=discriminative or []
        )

        self.keys[memory_id] = entry

        # 更新向量索引
        if vector is not None:
            self.vector_keys[memory_id] = vector.copy()

        # 更新实体索引
        for entity in (entities or []):
            self.entity_index[entity].add(memory_id)

        # 更新时间索引
        if timestamp:
            date_key = timestamp.strftime('%Y-%m-%d')
            self.temporal_index[date_key].add(memory_id)

            # 插入排序列表
            import bisect
            bisect.insort(self.temporal_sorted, (timestamp, memory_id))

        # 更新关系索引
        for subject, predicate, obj in (relations or []):
            self.relation_index[(subject, predicate)].add(memory_id)
            self.relation_index[(obj, f"inv_{predicate}")].add(memory_id)

        # 更新辨别性索引
        for disc_key in (discriminative or []):
            self.discriminative_index[disc_key].add(memory_id)

        logger.debug(f"Key stored: {memory_id}, entities={entities}, relations={len(relations or [])}")

    def query(
        self,
        query_vector: Optional[np.ndarray] = None,
        query_entities: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        relation_path: Optional[List[Tuple[str, str]]] = None,
        discriminative_hints: Optional[List[str]] = None,
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Tuple[str, float]]:
        """
        多模态键查询

        Args:
            query_vector: 查询向量
            query_entities: 查询实体
            time_range: 时间范围 (start, end)
            relation_path: 关系路径 [(entity, relation), ...]
            discriminative_hints: 辨别性提示
            top_k: 返回数量
            min_score: 最小分数阈值

        Returns:
            [(memory_id, score), ...] 按分数降序
        """
        self.total_queries += 1

        # 收集候选
        candidates = self._get_candidates(
            query_entities, time_range, relation_path, discriminative_hints
        )

        if not candidates and query_vector is not None:
            # 如果没有结构化匹配，使用全部向量键
            candidates = set(self.vector_keys.keys())

        if not candidates:
            return []

        # 计算分数
        scored_results = []
        for memory_id in candidates:
            score = self._calculate_score(
                memory_id, query_vector, query_entities,
                discriminative_hints
            )
            if score >= min_score:
                scored_results.append((memory_id, score))

                # 更新访问统计
                if memory_id in self.keys:
                    self.keys[memory_id].access_count += 1
                    self.keys[memory_id].last_accessed = datetime.now()

        # 排序并返回
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:top_k]

    def _get_candidates(
        self,
        query_entities: Optional[List[str]],
        time_range: Optional[Tuple[datetime, datetime]],
        relation_path: Optional[List[Tuple[str, str]]],
        discriminative_hints: Optional[List[str]]
    ) -> Set[str]:
        """获取候选记忆ID"""
        candidate_sets = []

        # 实体匹配
        if query_entities:
            entity_candidates = set()
            for entity in query_entities:
                entity_candidates.update(self.entity_index.get(entity, set()))
            if entity_candidates:
                candidate_sets.append(entity_candidates)

        # 时间范围匹配
        if time_range:
            start, end = time_range
            time_candidates = set()
            for ts, mem_id in self.temporal_sorted:
                if start <= ts <= end:
                    time_candidates.add(mem_id)
            if time_candidates:
                candidate_sets.append(time_candidates)

        # 关系路径匹配
        if relation_path:
            relation_candidates = self._follow_relation_path(relation_path)
            if relation_candidates:
                candidate_sets.append(relation_candidates)

        # 辨别性匹配
        if discriminative_hints:
            disc_candidates = set()
            for hint in discriminative_hints:
                disc_candidates.update(self.discriminative_index.get(hint, set()))
            if disc_candidates:
                candidate_sets.append(disc_candidates)

        # 合并候选（交集或并集，取决于策略）
        if not candidate_sets:
            return set()

        # 使用交集确保精确匹配
        result = candidate_sets[0]
        for s in candidate_sets[1:]:
            result = result & s
            if not result:
                # 如果交集为空，回退到并集
                result = set()
                for s in candidate_sets:
                    result.update(s)
                break

        return result

    def _follow_relation_path(
        self,
        path: List[Tuple[str, str]]
    ) -> Set[str]:
        """
        跟随关系路径查找记忆

        用于多跳推理：
        path = [("Alice", "met"), ("?", "went_to")]
        找到 Alice met 的人，然后找这个人 went_to 的地方
        """
        if not path:
            return set()

        current_entities = {path[0][0]}  # 起始实体
        visited_memories = set()

        for entity_pattern, relation in path:
            next_entities = set()

            for entity in current_entities:
                # 查找关系
                memory_ids = self.relation_index.get((entity, relation), set())
                visited_memories.update(memory_ids)

                # 提取目标实体
                for mem_id in memory_ids:
                    if mem_id in self.keys:
                        for subj, pred, obj in self.keys[mem_id].relation_keys:
                            if subj == entity and pred == relation:
                                next_entities.add(obj)
                            elif obj == entity and pred == f"inv_{relation}":
                                next_entities.add(subj)

            current_entities = next_entities
            if not current_entities:
                break

        return visited_memories

    def _calculate_score(
        self,
        memory_id: str,
        query_vector: Optional[np.ndarray],
        query_entities: Optional[List[str]],
        discriminative_hints: Optional[List[str]]
    ) -> float:
        """计算检索分数"""
        if memory_id not in self.keys:
            return 0.0

        entry = self.keys[memory_id]
        scores = []
        weights = []

        # 向量相似度
        if query_vector is not None and memory_id in self.vector_keys:
            vec_score = self._cosine_similarity(query_vector, self.vector_keys[memory_id])
            scores.append(vec_score)
            weights.append(0.5)

        # 实体匹配度
        if query_entities and entry.entity_keys:
            entity_overlap = len(set(query_entities) & set(entry.entity_keys))
            entity_score = entity_overlap / max(len(entry.entity_keys), 1)
            scores.append(entity_score)
            weights.append(0.3)

        # 辨别性匹配加分
        if discriminative_hints and entry.discriminative_keys:
            disc_match = len(set(discriminative_hints) & set(entry.discriminative_keys))
            if disc_match > 0:
                disc_score = min(1.0, disc_match * 0.3)
                scores.append(disc_score)
                weights.append(0.2)

        if not scores:
            return 0.5  # 默认分数

        return sum(s * w for s, w in zip(scores, weights)) / sum(weights)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def remove_key(self, memory_id: str):
        """移除键"""
        if memory_id not in self.keys:
            return

        entry = self.keys[memory_id]

        # 清理索引
        if memory_id in self.vector_keys:
            del self.vector_keys[memory_id]

        for entity in entry.entity_keys:
            self.entity_index[entity].discard(memory_id)

        if entry.temporal_key:
            date_key = entry.temporal_key.strftime('%Y-%m-%d')
            self.temporal_index[date_key].discard(memory_id)
            self.temporal_sorted = [
                (ts, mid) for ts, mid in self.temporal_sorted if mid != memory_id
            ]

        for subj, pred, obj in entry.relation_keys:
            self.relation_index[(subj, pred)].discard(memory_id)
            self.relation_index[(obj, f"inv_{pred}")].discard(memory_id)

        for disc_key in entry.discriminative_keys:
            self.discriminative_index[disc_key].discard(memory_id)

        del self.keys[memory_id]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_keys': len(self.keys),
            'vector_keys': len(self.vector_keys),
            'entity_index_size': len(self.entity_index),
            'temporal_index_size': len(self.temporal_index),
            'relation_index_size': len(self.relation_index),
            'discriminative_index_size': len(self.discriminative_index),
            'total_queries': self.total_queries
        }


class ValueStore:
    """
    值存储 (新皮层职责)

    优化目标: 最大化保真度 (Fidelity)

    存储记忆的实际内容：
    1. 文本内容
    2. 详细元数据
    3. 来源可靠性
    4. 关联信息
    """

    def __init__(self, db_path: Optional[str] = None, use_memory: bool = False):
        """
        初始化值存储

        Args:
            db_path: SQLite数据库路径（如果为None且use_memory=False，使用内存字典）
            use_memory: 是否使用纯内存存储
        """
        self.db_path = db_path
        self.use_memory = use_memory or db_path is None

        if self.use_memory:
            self.memory_store: Dict[str, Dict[str, Any]] = {}
        else:
            self._init_db()

        self._lock = threading.Lock()

        logger.info(f"ValueStore initialized: {'memory' if self.use_memory else db_path}")

    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS memory_values (
                memory_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                details TEXT,
                source_reliability REAL DEFAULT 1.0,
                importance REAL DEFAULT 0.5,
                emotion_intensity REAL DEFAULT 0.0,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_importance ON memory_values(importance)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON memory_values(created_at)')
        conn.commit()
        conn.close()

    def store_value(
        self,
        memory_id: str,
        content: str,
        details: Optional[Dict[str, Any]] = None,
        reliability: float = 1.0,
        importance: float = 0.5,
        emotion_intensity: float = 0.0
    ):
        """
        存储记忆内容

        Args:
            memory_id: 记忆ID
            content: 记忆内容
            details: 详细元数据
            reliability: 来源可靠性
            importance: 重要性
            emotion_intensity: 情感强度
        """
        now = datetime.now().isoformat()

        if self.use_memory:
            with self._lock:
                self.memory_store[memory_id] = {
                    'content': content,
                    'details': details or {},
                    'reliability': reliability,
                    'importance': importance,
                    'emotion_intensity': emotion_intensity,
                    'created_at': now,
                    'last_accessed': now,
                    'access_count': 0
                }
        else:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT OR REPLACE INTO memory_values
                (memory_id, content, details, source_reliability, importance,
                 emotion_intensity, created_at, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                memory_id, content, json.dumps(details or {}),
                reliability, importance, emotion_intensity, now, now
            ))
            conn.commit()
            conn.close()

        logger.debug(f"Value stored: {memory_id}, importance={importance}")

    def retrieve_value(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        检索记忆内容

        Args:
            memory_id: 记忆ID

        Returns:
            记忆内容字典，如果不存在返回None
        """
        if self.use_memory:
            with self._lock:
                if memory_id not in self.memory_store:
                    return None

                entry = self.memory_store[memory_id]
                entry['access_count'] += 1
                entry['last_accessed'] = datetime.now().isoformat()

                return {
                    'content': entry['content'],
                    'details': entry['details'],
                    'reliability': entry['reliability'],
                    'importance': entry['importance'],
                    'emotion_intensity': entry['emotion_intensity']
                }
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute('''
                SELECT content, details, source_reliability, importance, emotion_intensity
                FROM memory_values WHERE memory_id = ?
            ''', (memory_id,))
            row = cursor.fetchone()

            if row:
                # 更新访问统计
                conn.execute('''
                    UPDATE memory_values
                    SET access_count = access_count + 1, last_accessed = ?
                    WHERE memory_id = ?
                ''', (datetime.now().isoformat(), memory_id))
                conn.commit()

            conn.close()

            if row:
                return {
                    'content': row[0],
                    'details': json.loads(row[1]) if row[1] else {},
                    'reliability': row[2],
                    'importance': row[3],
                    'emotion_intensity': row[4]
                }

            return None

    def batch_retrieve(self, memory_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量检索记忆内容

        Args:
            memory_ids: 记忆ID列表

        Returns:
            {memory_id: value_dict, ...}
        """
        results = {}

        if self.use_memory:
            with self._lock:
                for memory_id in memory_ids:
                    if memory_id in self.memory_store:
                        entry = self.memory_store[memory_id]
                        results[memory_id] = {
                            'content': entry['content'],
                            'details': entry['details'],
                            'reliability': entry['reliability'],
                            'importance': entry['importance'],
                            'emotion_intensity': entry['emotion_intensity']
                        }
        else:
            conn = sqlite3.connect(self.db_path)
            placeholders = ','.join('?' * len(memory_ids))
            cursor = conn.execute(f'''
                SELECT memory_id, content, details, source_reliability, importance, emotion_intensity
                FROM memory_values WHERE memory_id IN ({placeholders})
            ''', memory_ids)

            for row in cursor:
                results[row[0]] = {
                    'content': row[1],
                    'details': json.loads(row[2]) if row[2] else {},
                    'reliability': row[3],
                    'importance': row[4],
                    'emotion_intensity': row[5]
                }

            conn.close()

        return results

    def remove_value(self, memory_id: str):
        """移除记忆内容"""
        if self.use_memory:
            with self._lock:
                if memory_id in self.memory_store:
                    del self.memory_store[memory_id]
        else:
            conn = sqlite3.connect(self.db_path)
            conn.execute('DELETE FROM memory_values WHERE memory_id = ?', (memory_id,))
            conn.commit()
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self.use_memory:
            with self._lock:
                return {
                    'total_values': len(self.memory_store),
                    'storage_type': 'memory'
                }
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute('SELECT COUNT(*) FROM memory_values')
            count = cursor.fetchone()[0]
            conn.close()
            return {
                'total_values': count,
                'storage_type': 'sqlite',
                'db_path': self.db_path
            }


class KeyValueMemoryStore:
    """
    统一的键值记忆存储

    整合KeyStore和ValueStore，提供统一接口
    """

    def __init__(
        self,
        value_store_path: Optional[str] = None,
        enable_vector_index: bool = True
    ):
        """
        初始化键值记忆存储

        Args:
            value_store_path: 值存储数据库路径
            enable_vector_index: 是否启用向量索引
        """
        self.key_store = KeyStore(enable_vector_index=enable_vector_index)
        self.value_store = ValueStore(db_path=value_store_path)

        logger.info("KeyValueMemoryStore initialized")

    def store(
        self,
        memory_id: str,
        content: str,
        vector: Optional[np.ndarray] = None,
        entities: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
        relations: Optional[List[Tuple[str, str, str]]] = None,
        discriminative: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
        emotion_intensity: float = 0.0
    ):
        """
        存储记忆（键和值分别存储）

        Args:
            memory_id: 记忆ID
            content: 记忆内容
            vector: 语义向量
            entities: 实体列表
            timestamp: 时间戳
            relations: 关系三元组
            discriminative: 辨别性特征
            details: 详细元数据
            importance: 重要性
            emotion_intensity: 情感强度
        """
        # 存储键
        self.key_store.store_key(
            memory_id=memory_id,
            vector=vector,
            entities=entities,
            timestamp=timestamp,
            relations=relations,
            discriminative=discriminative
        )

        # 存储值
        self.value_store.store_value(
            memory_id=memory_id,
            content=content,
            details=details,
            importance=importance,
            emotion_intensity=emotion_intensity
        )

    def retrieve(
        self,
        query_vector: Optional[np.ndarray] = None,
        query_entities: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        relation_path: Optional[List[Tuple[str, str]]] = None,
        discriminative_hints: Optional[List[str]] = None,
        top_k: int = 10,
        include_content: bool = True
    ) -> List[Dict[str, Any]]:
        """
        检索记忆

        Args:
            query_vector: 查询向量
            query_entities: 查询实体
            time_range: 时间范围
            relation_path: 关系路径
            discriminative_hints: 辨别性提示
            top_k: 返回数量
            include_content: 是否包含完整内容

        Returns:
            检索结果列表
        """
        # 键检索
        key_results = self.key_store.query(
            query_vector=query_vector,
            query_entities=query_entities,
            time_range=time_range,
            relation_path=relation_path,
            discriminative_hints=discriminative_hints,
            top_k=top_k
        )

        if not key_results:
            return []

        # 获取值
        memory_ids = [r[0] for r in key_results]

        if include_content:
            values = self.value_store.batch_retrieve(memory_ids)
        else:
            values = {}

        # 组装结果
        results = []
        for memory_id, score in key_results:
            result = {
                'memory_id': memory_id,
                'score': score,
                'key_info': self.key_store.keys.get(memory_id)
            }

            if memory_id in values:
                result.update(values[memory_id])

            results.append(result)

        return results

    def remove(self, memory_id: str):
        """移除记忆"""
        self.key_store.remove_key(memory_id)
        self.value_store.remove_value(memory_id)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'key_store': self.key_store.get_statistics(),
            'value_store': self.value_store.get_statistics()
        }
