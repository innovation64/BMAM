"""
Advanced Memory System with FAISS Vector Database and Embeddings
高级记忆系统：基于FAISS向量数据库和嵌入技术
"""

import os
import json
import uuid
import logging
import asyncio
import threading
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import faiss
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Integer, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sentence_transformers import SentenceTransformer
import openai
# Import MemoryItem from the dedicated module
from .memory_item import MemoryItem
from ..utils.config import get_absolute_path
# Import centralized config
from ..utils import get_logger

# Configure logging
logger = get_logger(__name__)

Base = declarative_base()


# MemoryItem is now imported from memory_item.py module


class MemoryRecord(Base):
    """SQLAlchemy model for persistent memory storage"""
    __tablename__ = 'memories'
    
    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String, nullable=False)
    importance = Column(Float, default=0.5)
    emotion_tags = Column(JSON)
    emotion_intensity = Column(Float, default=0.5)
    brain_region = Column(String, default="hippocampus")
    consolidation_level = Column(Integer, default=0)
    access_frequency = Column(Integer, default=0)
    decay_rate = Column(Float, default=0.1)
    stress_marker = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime)
    last_consolidated = Column(DateTime)
    associations = Column(JSON)
    source_reliability = Column(Float, default=1.0)
    context_tags = Column(JSON)
    memory_metadata = Column(JSON)
    embedding_id = Column(String)
    is_active = Column(Boolean, default=True)


class EmbeddingService:
    """Advanced Embedding Service with Multiple Model Support"""
    
    def __init__(self):
        # 使用带缓存的OpenAI嵌入服务
        from ..services.openai_embedding_service import OpenAIEmbeddingService
        self.service = OpenAIEmbeddingService(use_cache=True)
        self.dimension = self.service.dimension
        self.model_name = self.service.model
        
        logger.info(f"Initializing embedding service: {self.model_name} with caching enabled")
    
    async def encode_text(self, text: str) -> np.ndarray:
        """Encode text to vector embedding"""
        # 直接调用embedding服务，现在会在API失败时抛出异常防止污染
        try:
            result = await self.service.encode_text(text)
            return np.array(result, dtype=np.float32)
        except Exception as e:
            logger.warning(f"Embedding service failed for text: {e}")
            raise  # 重新抛出异常让调用者处理
    
    async def encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Encode multiple texts in batch with caching"""
        try:
            results = await self.service.encode_batch(texts)
            return [np.array(result, dtype=np.float32) for result in results]
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            # 逐一处理，但如果单个也失败则跳过防止污染
            results = []
            for text in texts:
                try:
                    embedding = await self.encode_text(text)
                    results.append(embedding)
                except Exception as embed_error:
                    logger.warning(f"Skipping text embedding due to error: {embed_error}")
                    # 跳过失败的文本，不添加到结果中
                    continue
            return results


class FAISSVectorDatabase:
    """FAISS-based Vector Database for Semantic Memory Retrieval"""
    
    def __init__(self, dimension: int = None, index_path: str = None):
        # 默认使用OpenAI的1536维，与EmbeddingService保持一致
        self.dimension = dimension or 1536
        self.index_path = str(get_absolute_path(index_path or os.getenv("VECTOR_INDEX_PATH", "data/memory_vectors.index")))
        
        # Create data directory if it doesn't exist
        Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize FAISS index (Inner Product for cosine similarity)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_mapping: Dict[int, str] = {}  # FAISS index -> memory ID
        self.reverse_mapping: Dict[str, int] = {}  # memory ID -> FAISS index
        self.lock = threading.Lock()
        
        logger.info(f"Initializing FAISS vector database (dimension: {self.dimension})")
        self.load_index()
    
    def add_vector(self, memory_id: str, vector: np.ndarray) -> int:
        """Add vector to FAISS index with memory ID mapping"""
        with self.lock:
            if memory_id in self.reverse_mapping:
                return self.reverse_mapping[memory_id]
            
            # Normalize vector for cosine similarity
            vector = vector / np.linalg.norm(vector)
            vector = vector.reshape(1, -1).astype(np.float32)
            
            # Add to FAISS index
            faiss_id = self.index.ntotal
            self.index.add(vector)
            
            # Update mappings
            self.id_mapping[faiss_id] = memory_id
            self.reverse_mapping[memory_id] = faiss_id
            
            logger.debug(f"Added vector for memory {memory_id} at FAISS index {faiss_id}")
            return faiss_id
    
    def search(self, query_vector: np.ndarray, k: int = 10, threshold: float = 0.3) -> List[Tuple[str, float]]:
        """Search for similar vectors using FAISS"""
        with self.lock:
            if self.index.ntotal == 0:
                return []
            
            # Normalize query vector
            query_vector = query_vector / np.linalg.norm(query_vector)
            query_vector = query_vector.reshape(1, -1).astype(np.float32)
            
            # Search with FAISS
            similarities, indices = self.index.search(query_vector, min(k, self.index.ntotal))
            
            results = []
            for sim, idx in zip(similarities[0], indices[0]):
                if sim >= threshold and idx in self.id_mapping:  # 使用传入的threshold参数
                    memory_id = self.id_mapping[idx]
                    results.append((memory_id, float(sim)))
            
            logger.debug(f"Vector search found {len(results)} results above threshold {threshold}")
            return results
    
    def remove_vector(self, memory_id: str):
        """Remove vector from index (logical deletion)"""
        with self.lock:
            if memory_id in self.reverse_mapping:
                faiss_id = self.reverse_mapping[memory_id]
                del self.id_mapping[faiss_id]
                del self.reverse_mapping[memory_id]
                logger.debug(f"Removed vector for memory {memory_id}")

    def reset(self):
        """Rebuild FAISS structures from scratch."""
        with self.lock:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_mapping.clear()
            self.reverse_mapping.clear()
            logger.info("FAISS index reset; mappings cleared")
    
    def save_index(self):
        """Persist FAISS index and mappings to disk"""
        with self.lock:
            try:
                faiss.write_index(self.index, self.index_path)
                
                # Save mappings separately
                mapping_path = self.index_path.replace('.index', '_mappings.json')
                with open(mapping_path, 'w') as f:
                    json.dump({
                        'id_mapping': self.id_mapping,
                        'reverse_mapping': self.reverse_mapping
                    }, f, indent=2)
                
                logger.info(f"Saved FAISS index with {self.index.ntotal} vectors to {self.index_path}")
                
            except Exception as e:
                logger.error(f"Failed to save FAISS index: {e}")
    
    def load_index(self):
        """Load FAISS index and mappings from disk"""
        try:
            if os.path.exists(self.index_path):
                loaded_index = faiss.read_index(self.index_path)
                
                # 检查维度是否匹配
                if loaded_index.d != self.dimension:
                    logger.warning(f"FAISS index dimension mismatch: expected {self.dimension}, got {loaded_index.d}")
                    logger.info("Rebuilding FAISS index with correct dimension")
                    self.index = faiss.IndexFlatIP(self.dimension)
                    return
                
                self.index = loaded_index
                
                # Load mappings
                mapping_path = self.index_path.replace('.index', '_mappings.json')
                if os.path.exists(mapping_path):
                    with open(mapping_path, 'r') as f:
                        mappings = json.load(f)
                        # 修复：JSON加载后键是字符串，需要转换回int
                        self.id_mapping = {int(k): v for k, v in mappings['id_mapping'].items()}
                        self.reverse_mapping = mappings['reverse_mapping']
                
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors from {self.index_path}")
            else:
                logger.info("No existing FAISS index found, starting with empty index")
                
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            logger.info("Starting with empty FAISS index")
            self.index = faiss.IndexFlatIP(self.dimension)
    
    def clean_corrupted_index(self):
        """Clean corrupted FAISS index by rebuilding from scratch"""
        logger.info("Cleaning corrupted FAISS index...")
        
        with self.lock:
            # Reset index and mappings
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_mapping.clear()
            self.reverse_mapping.clear()
            
            # Remove corrupted files
            try:
                if os.path.exists(self.index_path):
                    os.remove(self.index_path)
                    logger.info(f"Removed corrupted index file: {self.index_path}")
                
                mapping_path = self.index_path.replace('.index', '_mappings.json')
                if os.path.exists(mapping_path):
                    os.remove(mapping_path)
                    logger.info(f"Removed corrupted mapping file: {mapping_path}")
                    
            except Exception as e:
                logger.warning(f"Failed to remove corrupted files: {e}")
            
            logger.info("FAISS index cleaned successfully")
    
    def rebuild_index_from_database(self, db_manager):
        """Rebuild FAISS index from clean database records"""
        logger.info("Rebuilding FAISS index from database...")
        
        from .memory_system import EmbeddingService
        embedding_service = EmbeddingService()
        
        with self.lock:
            # Get all memories from database
            memories = db_manager.search_memories()
            
            clean_count = 0
            for memory in memories:
                try:
                    # Re-encode content to get clean embedding
                    import asyncio
                    
                    # Create temporary event loop if needed
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Get clean embedding
                    embedding = loop.run_until_complete(
                        embedding_service.encode_text(memory.content)
                    )
                    
                    # Add to index
                    faiss_id = self.add_vector(memory.id, embedding)
                    logger.debug(f"Rebuilt vector for memory {memory.id}")
                    clean_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to rebuild vector for memory {memory.id}: {e}")
                    continue
            
            # Save clean index
            self.save_index()
            logger.info(f"Rebuilt FAISS index with {clean_count} clean vectors")


class DatabaseManager:
    """Enhanced Database Manager for Memory Persistence"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///data/brain_memory.db")
        
        # Create data directory for SQLite
        if "sqlite://" in self.db_url:
            db_path = self.db_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(self.db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.lock = threading.Lock()
        
        logger.info(f"Database initialized: {self.db_url}")
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    
    def save_memory(self, memory: MemoryItem) -> bool:
        """Save memory to database"""
        try:
            with self.lock:
                session = self.get_session()
                try:
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
                        embedding_id=memory.embedding_id
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
        """Load memory by ID"""
        try:
            session = self.get_session()
            try:
                record = session.query(MemoryRecord).filter_by(id=memory_id, is_active=True).first()
                if record:
                    memory = MemoryItem(
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
                    # Update access frequency
                    record.access_frequency += 1
                    record.last_accessed = datetime.now()
                    session.commit()
                    
                    return memory
            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to load memory {memory_id}: {e}")
        return None
    
    def search_memories(self, **filters) -> List[MemoryItem]:
        """Search memories with various filters"""
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
                    query = query.filter(MemoryRecord.importance >= filters['min_importance'])
                if 'consolidation_level' in filters:
                    query = query.filter_by(consolidation_level=filters['consolidation_level'])
                
                records = query.limit(filters.get('limit', 100)).all()
                
                for record in records:
                    memory = MemoryItem(
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
                    memories.append(memory)

            finally:
                session.close()
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")

        return memories

    def get_recent_memories(self, limit: int = 1000) -> List[MemoryItem]:
        """Fetch most recent active memories for maintenance tasks."""
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

                return [
                    MemoryItem(
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
                    for record in records
                ]
            finally:
                session.close()
        except Exception as exc:
            logger.error(f"Failed to fetch recent memories: {exc}")
            return []
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory database statistics"""
        try:
            session = self.get_session()
            try:
                total = session.query(MemoryRecord).filter_by(is_active=True).count()
                episodic = session.query(MemoryRecord).filter_by(is_active=True, memory_type='episodic').count()
                semantic = session.query(MemoryRecord).filter_by(is_active=True, memory_type='semantic').count()
                
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


class AdvancedMemorySystem:
    """Integrated Memory System with FAISS Vector Search"""
    
    def __init__(self):
        logger.info("Initializing Advanced Memory System...")
        
        # Initialize components
        self.embedding_service = EmbeddingService()
        self.vector_db = FAISSVectorDatabase(dimension=self.embedding_service.dimension)
        self.db_manager = DatabaseManager()
        
        logger.info("Advanced Memory System initialized successfully")
    
    async def store_memory(self, content: str, memory_type: str = "episodic", 
                    importance: float = 0.5, emotion_tags: List[str] = None,
                    context_tags: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Store a new memory with embedding"""
        try:
            # Create memory item
            memory = MemoryItem(
                content=content,
                memory_type=memory_type,
                importance=importance,
                emotion_tags=emotion_tags or [],
                context_tags=context_tags or [],
                metadata=metadata or {}
            )
            
            # Generate embedding
            try:
                memory.embedding = await self.embedding_service.encode_text(content)
                
                # Add to vector database
                faiss_id = self.vector_db.add_vector(memory.id, memory.embedding)
                memory.embedding_id = str(faiss_id)
            except Exception as e:
                logger.warning(f"Failed to generate embedding for memory: {e}")
                # Don't store memory without valid embedding to prevent FAISS pollution
                return None
            
            # Save to persistent storage
            success = self.db_manager.save_memory(memory)
            
            if success:
                # Persist vector index
                self.vector_db.save_index()
                
                # 验证FAISS映射是否正确更新
                if memory.id in self.vector_db.reverse_mapping:
                    faiss_id = self.vector_db.reverse_mapping[memory.id]
                    logger.info(f"✅ Successfully stored memory {memory.id} -> FAISS index {faiss_id}")
                    logger.debug(f"📊 Vector DB stats: total_vectors={self.vector_db.index.ntotal}, mappings={len(self.vector_db.reverse_mapping)}")
                else:
                    logger.error(f"⚠️ Memory {memory.id} stored in DB but NOT in FAISS mapping!")
                
                return memory.id
            else:
                logger.error(f"Failed to store memory {memory.id}")
                return None
                
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return None
    
    async def search_memories(self, query: str, search_type: str = "semantic", 
                       k: int = 10, threshold: float = 0.1, **filters) -> List[Dict[str, Any]]:
        """Search memories using various methods"""
        try:
            if search_type == "semantic":
                return await self._semantic_search(query, k, threshold)
            elif search_type == "hybrid":
                return self._hybrid_search(query, k, threshold, **filters)
            else:
                return self._keyword_search(query, **filters)
                
        except Exception as e:
            logger.error(f"Error searching memories: {e}", exc_info=True)
            return []
    
    async def _semantic_search(self, query: str, k: int, threshold: float) -> List[Dict[str, Any]]:
        """Perform semantic search using vector similarity"""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.encode_text(query)
            
            # Search similar vectors
            similar_memories = self.vector_db.search(query_embedding, k, threshold)
        except Exception as e:
            logger.warning(f"Failed to generate query embedding for '{query}': {e}")
            # Fall back to keyword search if embedding fails
            return []
        
        # Load full memory objects
        results = []
        for memory_id, similarity in similar_memories:
            memory = self.db_manager.load_memory(memory_id)
            if memory:
                result = memory.to_dict()
                result['similarity_score'] = similarity
                result['search_type'] = 'semantic'
                results.append(result)
        
        logger.info(f"Semantic search for '{query}' found {len(results)} results")
        return results
    
    def _hybrid_search(self, query: str, k: int, threshold: float, **filters) -> List[Dict[str, Any]]:
        """Combine semantic search with filters"""
        # Start with semantic search
        semantic_results = self._semantic_search(query, k * 2, threshold)
        
        # Apply additional filters
        filtered_results = []
        for result in semantic_results:
            memory = MemoryItem.from_dict(result)
            
            # Apply filters
            if filters.get('memory_type') and memory.memory_type != filters['memory_type']:
                continue
            if filters.get('min_importance') and memory.importance < filters['min_importance']:
                continue
            if filters.get('brain_region') and memory.brain_region != filters['brain_region']:
                continue
            
            result['search_type'] = 'hybrid'
            filtered_results.append(result)
            
            if len(filtered_results) >= k:
                break
        
        logger.info(f"Hybrid search for '{query}' found {len(filtered_results)} results")
        return filtered_results
    
    def _keyword_search(self, query: str, **filters) -> List[Dict[str, Any]]:
        """Simple keyword-based search"""
        memories = self.db_manager.search_memories(**filters)

        results = []
        query_lower = query.lower()
        for memory in memories:
            if query_lower in memory.content.lower():
                result = memory.to_dict()
                result['search_type'] = 'keyword'
                results.append(result)

        logger.info(f"Keyword search for '{query}' found {len(results)} results")
        return results

    async def enforce_storage_limits(self, max_vectors: int = 5000) -> bool:
        """Rebuild FAISS index if vector count exceeds configured limit."""
        if max_vectors <= 0:
            return False

        current_total = self.vector_db.index.ntotal
        if current_total <= max_vectors:
            return False

        logger.warning(
            "FAISS index size %s exceeds limit %s; rebuilding with most recent memories",
            current_total,
            max_vectors,
        )

        recent_memories = self.db_manager.get_recent_memories(limit=max_vectors)
        if not recent_memories:
            logger.warning("No recent memories available for compaction; aborting rebuild")
            return False

        self.vector_db.reset()

        try:
            texts = [memory.content for memory in recent_memories]
            embeddings = await self.embedding_service.encode_batch(texts)
        except Exception as exc:
            logger.error(f"Failed to rebuild FAISS index during compaction: {exc}")
            return False

        for memory, embedding in zip(recent_memories, embeddings):
            if embedding is None:
                continue
            self.vector_db.add_vector(memory.id, embedding)

        self.vector_db.save_index()
        logger.info("FAISS index compacted to %s vectors", self.vector_db.index.ntotal)
        return True

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get specific memory by ID"""
        memory = self.db_manager.load_memory(memory_id)
        return memory.to_dict() if memory else None
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        db_stats = self.db_manager.get_memory_stats()
        vector_stats = {
            'vector_count': self.vector_db.index.ntotal,
            'vector_dimension': self.vector_db.dimension,
            'index_path': self.vector_db.index_path
        }
        
        return {
            'database': db_stats,
            'vectors': vector_stats,
            'embedding_model': self.embedding_service.model_name,
            'embedding_type': 'openai_cached'
        }


# Global memory system instance
memory_system = AdvancedMemorySystem()


def main():
    """Test the memory system"""
    print("Testing Advanced Memory System...")
    
    # Test storing memories
    memories = [
        "I love learning about artificial intelligence and neural networks",
        "Today I had a great conversation with my colleague about machine learning",
        "I'm feeling anxious about the upcoming presentation next week",
        "The weather is beautiful today, perfect for a walk in the park"
    ]
    
    for content in memories:
        memory_id = memory_system.store_memory(
            content=content,
            importance=0.7,
            emotion_tags=["positive"] if "love" in content or "great" in content else ["neutral"]
        )
        print(f"Stored memory: {memory_id}")
    
    # Test semantic search
    print("\n=== Semantic Search Results ===")
    results = memory_system.search_memories("artificial intelligence", search_type="semantic", k=3)
    for i, result in enumerate(results, 1):
        print(f"{i}. Similarity: {result['similarity_score']:.3f}")
        print(f"   Content: {result['content']}")
        print(f"   Type: {result['memory_type']}")
    
    # Test system stats
    print("\n=== System Statistics ===")
    stats = memory_system.get_system_stats()
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
