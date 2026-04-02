"""
Database Models for Memory Persistence
记忆持久化的数据库模型

This module defines SQLAlchemy ORM models for storing memory records
in a relational database with comprehensive metadata support.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Float, DateTime, Text, Integer, Boolean, JSON
)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MemoryRecord(Base):
    """
    SQLAlchemy Model for Persistent Memory Storage
    用于持久化记忆存储的SQLAlchemy模型

    Stores comprehensive memory information including emotional tags,
    consolidation levels, access patterns, and vector embeddings.

    Attributes:
        id: Unique memory identifier (UUID)
        content: Memory content text
        memory_type: Type classification (episodic/semantic/procedural)
        importance: Importance score (0.0-1.0)
        emotion_tags: List of emotion labels
        emotion_intensity: Emotional intensity (0.0-1.0)
        brain_region: Associated brain region simulation
        consolidation_level: Memory consolidation stage (0-3)
        access_frequency: Number of times accessed
        decay_rate: Memory decay rate
        stress_marker: Whether memory is stress-related
        timestamp: Creation timestamp
        last_accessed: Last access timestamp
        last_consolidated: Last consolidation timestamp
        associations: List of associated memory IDs
        source_reliability: Source reliability score (0.0-1.0)
        context_tags: Contextual tags for episodic retrieval
        memory_metadata: Additional metadata dictionary
        embedding_id: FAISS vector index ID
        is_active: Whether memory is active (soft delete flag)
    """
    __tablename__ = 'memories'

    # Primary identification
    id = Column(String, primary_key=True)
    content = Column(Text, nullable=False)
    memory_type = Column(String, nullable=False)

    # Importance and emotion
    importance = Column(Float, default=0.5)
    emotion_tags = Column(JSON)
    emotion_intensity = Column(Float, default=0.5)

    # Brain-inspired attributes
    brain_region = Column(String, default="hippocampus")
    consolidation_level = Column(Integer, default=0)
    access_frequency = Column(Integer, default=0)
    decay_rate = Column(Float, default=0.1)
    stress_marker = Column(Boolean, default=False)

    # Temporal tracking
    timestamp = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime)
    last_consolidated = Column(DateTime)

    # Network and context
    associations = Column(JSON)
    source_reliability = Column(Float, default=1.0)
    context_tags = Column(JSON)
    memory_metadata = Column(JSON)

    # User isolation
    user_id = Column(String, nullable=False, default='default', index=True)

    # Vector embedding reference
    embedding_id = Column(String)

    # Lifecycle management
    is_active = Column(Boolean, default=True)
