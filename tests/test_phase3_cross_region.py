import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
import sys
import os
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.coordination.memory_coordinator import MemoryCoordinator
from src.agents.brain_regions.temporal_lobe_agent.temporal_lobe_agent import TemporalLobeAgent
from src.agents.brain_regions.hippocampus_agent import HippocampusAgent

@pytest.mark.asyncio
async def test_kg_coverage_calculation():
    """Test _calculate_kg_coverage with real KG logic"""
    # Setup mocks without spec to allow dynamic attribute assignment
    mock_hippocampus = AsyncMock()
    mock_temporal_lobe = AsyncMock()
    
    # Mock KG
    mock_kg = MagicMock()
    # Setup KG to return relations for 'apple' but not 'banana'
    mock_kg.query_relations.side_effect = lambda entity, rel=None: [('apple', 'is_a', 'fruit')] if entity == 'apple' else []
    mock_kg.reverse_index = {}
    
    mock_temporal_lobe.kg = mock_kg
    
    coordinator = MemoryCoordinator(
        hippocampus=mock_hippocampus,
        temporal_lobe=mock_temporal_lobe,
        consolidation_agent=AsyncMock(),
        forgetting_agent=AsyncMock(),
        agent_lifecycle_manager=AsyncMock()
    )
    
    # Test Case 1: High Coverage
    # Query: "apple" (exists in KG)
    memories = []
    coverage = coordinator._calculate_kg_coverage(memories, "apple")
    assert coverage == 1.0
    
    # Test Case 2: Low Coverage
    # Query: "banana" (not in KG)
    coverage = coordinator._calculate_kg_coverage(memories, "banana")
    assert coverage == 0.0
    
    # Test Case 3: Mixed Coverage
    # Query: "apple and banana"
    coverage = coordinator._calculate_kg_coverage(memories, "apple and banana")
    # Tokens: apple, banana. Covered: apple. 1/2 = 0.5
    assert coverage == 0.5

@pytest.mark.asyncio
async def test_smart_retrieve_fallback_trigger():
    """Test that low KG coverage triggers fallback"""
    mock_hippocampus = AsyncMock()
    mock_temporal_lobe = AsyncMock()
    
    # Mock KG to be empty -> 0 coverage
    mock_kg = MagicMock()
    mock_kg.query_relations.return_value = []
    mock_kg.reverse_index = {}
    mock_temporal_lobe.kg = mock_kg
    
    # Mock search results
    mock_hippocampus.search_memories.return_value = {'memories': [{'id': '1', 'content': 'mem1'}]}
    mock_temporal_lobe.search_memories.return_value = {'memories': [{'id': '2', 'content': 'mem2'}]}
    
    coordinator = MemoryCoordinator(
        hippocampus=mock_hippocampus,
        temporal_lobe=mock_temporal_lobe,
        consolidation_agent=AsyncMock(),
        forgetting_agent=AsyncMock(),
        agent_lifecycle_manager=AsyncMock()
    )
    
    # Mock _pure_semantic_fallback to verify it's called
    coordinator._pure_semantic_fallback = AsyncMock(return_value=[{'id': '3', 'content': 'fallback_mem'}])
    
    # Run smart_retrieve
    results = await coordinator.smart_retrieve(query="unknown entity", k=5, strategy="hybrid")
    
    # Verify fallback was triggered
    coordinator._pure_semantic_fallback.assert_called_once()
    
    # Verify results contain fallback memory
    assert any(m['id'] == '3' for m in results)

@pytest.mark.asyncio
async def test_cross_region_integration():
    """Integration test for cross-region retrieval"""
    pass
