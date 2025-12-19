"""
Unit tests for HippocampusAgent - Episodic Memory System
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestEpisodicMemory:
    """Test EpisodicMemory data structure"""

    def test_memory_creation(self):
        """Test basic memory creation"""
        from src.agents.brain_regions.hippocampus_agent.core import EpisodicMemory

        memory = EpisodicMemory(
            id="test_001",
            content="Met Sarah at the coffee shop",
            timestamp=datetime.now(),
            entities=["Sarah", "coffee shop"],
            importance=0.8
        )

        assert memory.id == "test_001"
        assert "Sarah" in memory.content
        assert len(memory.entities) == 2
        assert memory.importance == 0.8
        assert memory.access_count == 0

    def test_memory_with_metadata(self):
        """Test memory with metadata"""
        from src.agents.brain_regions.hippocampus_agent.core import EpisodicMemory

        memory = EpisodicMemory(
            id="test_002",
            content="Birthday party",
            timestamp=datetime.now(),
            metadata={
                "event_time": "2024-05-15",
                "event_type": "celebration",
                "hit_count": 3
            }
        )

        assert memory.metadata["event_time"] == "2024-05-15"
        assert memory.metadata["hit_count"] == 3

    def test_memory_with_emotions(self):
        """Test memory with emotional tags"""
        from src.agents.brain_regions.hippocampus_agent.core import EpisodicMemory

        memory = EpisodicMemory(
            id="test_003",
            content="Got the job offer!",
            timestamp=datetime.now(),
            emotion_tags=["joy", "excitement"],
            emotion_intensity=0.9
        )

        assert "joy" in memory.emotion_tags
        assert memory.emotion_intensity == 0.9


class TestHippocampusStorage:
    """Test Hippocampus storage functionality"""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service"""
        service = AsyncMock()
        service.encode_text = AsyncMock(return_value=[0.1] * 1536)
        return service

    @pytest.fixture
    def mock_kg_builder(self):
        """Create mock KG builder"""
        builder = Mock()
        builder.extract_from_text = AsyncMock(return_value=([], []))
        return builder

    @pytest.mark.asyncio
    async def test_store_memory_basic(self, mock_embedding_service, mock_kg_builder):
        """Test basic memory storage"""
        from src.agents.brain_regions.hippocampus_agent import HippocampusAgent

        with patch('src.agents.brain_regions.hippocampus_agent.storage.get_story_arc_manager'):
            agent = HippocampusAgent(
                embedding_service=mock_embedding_service,
                kg_builder=mock_kg_builder
            )

            result = await agent.store_memory(
                content="Had lunch with Tom at the Italian restaurant",
                entities=["Tom", "Italian restaurant"],
                importance=0.7
            )

            assert result["stored"] is True
            assert "memory_id" in result

    @pytest.mark.asyncio
    async def test_store_memory_with_metadata(self, mock_embedding_service, mock_kg_builder):
        """Test memory storage with metadata"""
        from src.agents.brain_regions.hippocampus_agent import HippocampusAgent

        with patch('src.agents.brain_regions.hippocampus_agent.storage.get_story_arc_manager'):
            agent = HippocampusAgent(
                embedding_service=mock_embedding_service,
                kg_builder=mock_kg_builder
            )

            result = await agent.store_memory(
                content="Meeting scheduled for tomorrow",
                metadata={
                    "conversation_date": "2024-05-10",
                    "speaker": "user"
                }
            )

            assert result["stored"] is True
            # Verify metadata was processed
            memory_id = result["memory_id"]
            memory = agent.memory_dict.get(memory_id)
            assert memory is not None
            assert "storage_time" in memory.metadata


class TestHippocampusRetrieval:
    """Test Hippocampus retrieval functionality"""

    @pytest.fixture
    def agent_with_memories(self):
        """Create agent with pre-stored memories"""
        from src.agents.brain_regions.hippocampus_agent.core import EpisodicMemory, HippocampusAgentCore

        agent = HippocampusAgentCore()

        # Add test memories
        memories = [
            EpisodicMemory(
                id="mem_1",
                content="Met Sarah at Central Park on Monday",
                timestamp=datetime(2024, 5, 1),
                entities=["Sarah", "Central Park"]
            ),
            EpisodicMemory(
                id="mem_2",
                content="Had coffee with Tom at Starbucks",
                timestamp=datetime(2024, 5, 2),
                entities=["Tom", "Starbucks"]
            ),
            EpisodicMemory(
                id="mem_3",
                content="Sarah's birthday party was amazing",
                timestamp=datetime(2024, 5, 3),
                entities=["Sarah"]
            ),
        ]

        for mem in memories:
            agent.memories.append(mem)
            agent.memory_dict[mem.id] = mem
            for entity in mem.entities:
                agent.entity_index[entity.lower()].append(mem.id)

        return agent

    def test_retrieve_by_entity(self, agent_with_memories):
        """Test retrieval by entity"""
        agent = agent_with_memories

        # Find memories about Sarah
        sarah_memory_ids = agent.entity_index.get("sarah", [])
        assert len(sarah_memory_ids) == 2
        assert "mem_1" in sarah_memory_ids
        assert "mem_3" in sarah_memory_ids

    def test_retrieve_by_content_keyword(self, agent_with_memories):
        """Test retrieval by content keyword"""
        agent = agent_with_memories

        # Search for "coffee" in memories
        matching = [m for m in agent.memories if "coffee" in m.content.lower()]
        assert len(matching) == 1
        assert matching[0].id == "mem_2"


class TestEventTimeExtraction:
    """Test event time extraction from content"""

    def test_extract_absolute_date(self):
        """Test extraction of absolute dates"""
        from src.agents.brain_regions.hippocampus_agent.storage import extract_event_time_from_content

        content = "On May 7, 2024, I visited the museum"
        event_time, method = extract_event_time_from_content(content)

        assert event_time is not None
        assert method in ['absolute', 'relative', 'metadata', 'fallback']

    def test_extract_relative_date(self):
        """Test extraction of relative dates"""
        from src.agents.brain_regions.hippocampus_agent.storage import extract_event_time_from_content

        content = "[Context: This conversation is on 08 May 2024] Yesterday I went hiking"
        event_time, method = extract_event_time_from_content(content)

        assert event_time is not None
        # Should extract May 7, 2024 (yesterday from context)

    def test_extract_from_metadata(self):
        """Test extraction from metadata"""
        from src.agents.brain_regions.hippocampus_agent.storage import extract_event_time_from_content

        content = "Had a great day at the beach"
        metadata = {"conversation_date": "2024-05-10T14:30:00"}
        event_time, method = extract_event_time_from_content(content, metadata=metadata)

        assert event_time is not None


class TestMemoryConsolidation:
    """Test memory consolidation criteria"""

    def test_consolidation_metadata_defaults(self):
        """Test that new memories have consolidation metadata"""
        from src.agents.brain_regions.hippocampus_agent.core import EpisodicMemory

        memory = EpisodicMemory(
            id="test",
            content="Test content",
            timestamp=datetime.now(),
            metadata={
                "hit_count": 0,
                "confidence": 0.5,
                "shaping_method": "initial_store"
            }
        )

        assert memory.metadata["hit_count"] == 0
        assert memory.metadata["confidence"] == 0.5
        assert memory.metadata["shaping_method"] == "initial_store"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
