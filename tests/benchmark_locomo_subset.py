import asyncio
import time
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.coordination.memory_coordinator import MemoryCoordinator
from src.agents.brain_regions.temporal_lobe_agent.temporal_lobe_agent import TemporalLobeAgent
from src.agents.brain_regions.hippocampus_agent import HippocampusAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_benchmark():
    print("\n🚀 Starting LoCoMo Subset Benchmark (Synthetic)...")
    
    # 1. Setup Environment (Mocks for speed, but logic is real)
    mock_hippocampus = AsyncMock(spec=HippocampusAgent)
    mock_temporal_lobe = AsyncMock(spec=TemporalLobeAgent)
    
    # Mock KG with partial coverage
    # Entities: apple, banana, cherry, date, elderberry
    # KG has: apple, banana
    mock_kg = MagicMock()
    def query_relations_side_effect(entity, rel=None):
        if entity in ['apple', 'banana']:
            return [(entity, 'is_a', 'fruit')]
        return []
    
    mock_kg.query_relations.side_effect = query_relations_side_effect
    mock_kg.reverse_index = {}
    mock_temporal_lobe.kg = mock_kg
    
    # Mock search results
    # Hippocampus returns some memories
    mock_hippocampus.search_memories.return_value = {'memories': [
        {'id': '1', 'content': 'I like apples and bananas.', 'score': 0.9},
        {'id': '2', 'content': 'Cherries are red.', 'score': 0.8}
    ]}
    mock_temporal_lobe.search_memories.return_value = {'memories': []}
    
    coordinator = MemoryCoordinator(
        hippocampus=mock_hippocampus,
        temporal_lobe=mock_temporal_lobe,
        consolidation_agent=AsyncMock(),
        forgetting_agent=AsyncMock(),
        agent_lifecycle_manager=AsyncMock()
    )
    
    # Mock _pure_semantic_fallback
    coordinator._pure_semantic_fallback = AsyncMock(return_value=[
        {'id': 'fallback_1', 'content': 'Elderberries are used in syrup.', 'score': 0.7}
    ])
    
    # 2. Run Queries
    queries = [
        "Tell me about apples",       # High coverage
        "What about cherries?",       # Low coverage (trigger fallback)
        "Do you know elderberries?",  # Low coverage (trigger fallback)
    ]
    
    results = []
    
    for query in queries:
        print(f"\n🔹 Query: {query}")
        t_start = time.time()
        
        # Run smart_retrieve
        memories = await coordinator.smart_retrieve(query=query, k=3, strategy="hybrid")
        
        t_end = time.time()
        duration = t_end - t_start
        
        # Check if fallback was triggered (by checking for fallback memory or log)
        fallback_triggered = any(m.get('id') == 'fallback_1' for m in memories)
        
        print(f"   Time: {duration:.4f}s")
        print(f"   Memories: {len(memories)}")
        print(f"   Fallback Triggered: {fallback_triggered}")
        
        results.append({
            'query': query,
            'time': duration,
            'fallback': fallback_triggered
        })
        
    # 3. Report
    print("\n📊 Benchmark Results:")
    print(f"{'Query':<30} | {'Time (s)':<10} | {'Fallback':<10}")
    print("-" * 55)
    for r in results:
        print(f"{r['query']:<30} | {r['time']:.4f}     | {str(r['fallback']):<10}")
        
    print("\n✅ Benchmark Complete.")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
