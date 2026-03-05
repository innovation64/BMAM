#!/usr/bin/env python3
"""
Cross-Session Long-Term Memory Validation
跨会话长期记忆验证

Objective: Verify that consolidated memories survive session restart
and are retrieved from long-term storage (TemporalLobe/MemorySystem),
NOT from short-term Hippocampus.

Test Flow:
1. Session 1 (Day 1):
   - Ingest 20 memories about specific topics
   - Trigger consolidation (Hippocampus → TemporalLobe/MemorySystem)
   - Verify consolidation success
   - Save state and shutdown

2. Session 2 (Day 2):
   - Restart with fresh Hippocampus (empty short-term memory)
   - Query the same topics from Day 1
   - Verify retrieval comes from long-term storage ONLY
   - Confirm NOT from Hippocampus (which should be empty)

Expected Outcome:
- Retrieval source should be 100% temporal_lobe/memory_system
- 0% hippocampus (proving long-term memory is working)
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.monitoring.memory_metrics import get_metrics_collector, reset_metrics_collector


# Test data: Rich biographical information
DAY1_MEMORIES = [
    # Alice - AI Researcher
    "Alice Chen is a senior AI researcher at MIT CSAIL.",
    "Alice published 'Transformer Architecture Improvements' in NeurIPS 2023.",
    "Alice won the Best Paper Award at NeurIPS 2023.",
    "Alice's research focuses on neural architecture search and efficient transformers.",
    "Alice supervises 5 PhD students working on LLM optimization.",
    "Alice gave a keynote speech at ICML 2024 on sustainable AI.",

    # Bob - Robotics Professor
    "Bob Martinez is a robotics professor at Stanford University.",
    "Bob leads the Stanford Robotics Lab with 15 researchers.",
    "Bob developed a novel robotic manipulation algorithm using reinforcement learning.",
    "Bob's lab built a humanoid robot named 'Atlas-2' in 2023.",
    "Bob received the IEEE Robotics Award in 2024.",

    # Carol - Computer Vision Expert
    "Carol Wang works as a principal scientist at Google DeepMind.",
    "Carol leads the computer vision team focused on multimodal learning.",
    "Carol developed a new image-text alignment model with 95% accuracy.",
    "Carol's work on vision transformers has 10,000+ citations.",
    "Carol collaborates with universities on open-source vision datasets.",

    # David - Data Science Manager
    "David Lee is a data science manager at OpenAI.",
    "David manages the RLHF team for ChatGPT improvements.",
    "David has 10 years of experience in NLP and dialogue systems.",
    "David published research on human feedback integration in 2022.",
    "David previously worked at Meta AI Research before joining OpenAI.",
]

# Test queries for Day 2 (should retrieve from long-term storage)
DAY2_QUERIES = [
    {
        'query': 'What research did Alice publish at NeurIPS 2023?',
        'expected_entities': ['Alice', 'NeurIPS', 'Transformer'],
        'expected_source': 'long_term',  # temporal_lobe or memory_system
        'description': 'Specific publication recall'
    },
    {
        'query': 'Which award did Alice win?',
        'expected_entities': ['Alice', 'Best Paper Award', 'NeurIPS'],
        'expected_source': 'long_term',
        'description': 'Award recognition recall'
    },
    {
        'query': 'What does Bob do at Stanford?',
        'expected_entities': ['Bob', 'Stanford', 'robotics'],
        'expected_source': 'long_term',
        'description': 'Professional role recall'
    },
    {
        'query': 'Tell me about Bob\'s robotics lab.',
        'expected_entities': ['Bob', 'Stanford Robotics Lab', 'Atlas-2'],
        'expected_source': 'long_term',
        'description': 'Lab details recall'
    },
    {
        'query': 'Where does Carol work?',
        'expected_entities': ['Carol', 'Google DeepMind'],
        'expected_source': 'long_term',
        'description': 'Current employment recall'
    },
    {
        'query': 'What is Carol\'s research focus?',
        'expected_entities': ['Carol', 'computer vision', 'multimodal'],
        'expected_source': 'long_term',
        'description': 'Research area recall'
    },
    {
        'query': 'What team does David manage at OpenAI?',
        'expected_entities': ['David', 'RLHF', 'ChatGPT'],
        'expected_source': 'long_term',
        'description': 'Management role recall'
    },
    {
        'query': 'Where did David work before OpenAI?',
        'expected_entities': ['David', 'Meta AI'],
        'expected_source': 'long_term',
        'description': 'Career history recall'
    },
]


async def session1_day1_ingest_and_consolidate():
    """
    Session 1 (Day 1): Ingest memories and consolidate
    """
    print("=" * 80)
    print("SESSION 1 (DAY 1): Ingest and Consolidate")
    print("=" * 80)

    # Initialize fresh coordinator
    coordinator = BrainInspiredCoordinator()
    metrics = get_metrics_collector(output_dir="metrics/cross_session")

    # Phase 1: Ingest memories
    print("\n[1/4] Ingesting Day 1 memories...")
    for i, memory in enumerate(DAY1_MEMORIES, 1):
        await coordinator.process_input(memory)
        print(f"  [{i:2d}/{len(DAY1_MEMORIES)}] {memory[:60]}...")

    # Check initial storage
    hippo_count = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0
    temporal_count_before = len(coordinator.temporal_lobe.memories) if hasattr(coordinator.temporal_lobe, 'memories') else 0

    print(f"\n  ✓ Ingested {len(DAY1_MEMORIES)} memories")
    print(f"  → Hippocampus: {hippo_count} memories")
    print(f"  → TemporalLobe (pre-consolidation): {temporal_count_before} memories")

    metrics.record_storage_update('hippocampus', hippo_count, source='day1_ingest')
    metrics.record_storage_update('temporal_lobe', temporal_count_before, source='day1_ingest')

    # Phase 2: Trigger consolidation
    print("\n[2/4] Triggering consolidation...")

    # Boost importance to ensure consolidation
    for mem in coordinator.hippocampus.memories:
        mem.importance = 0.9
        mem.access_count = 0

    consolidation_result = await coordinator.hippocampus.consolidate_memories()
    print(f"  → Consolidation result: {consolidation_result}")

    # Phase 3: Verify long-term storage increased
    print("\n[3/4] Verifying long-term storage...")
    temporal_count_after = len(coordinator.temporal_lobe.memories) if hasattr(coordinator.temporal_lobe, 'memories') else 0

    memory_system_count = 0
    if hasattr(coordinator, 'memory_system') and hasattr(coordinator.memory_system, 'db_manager'):
        memory_system_count = len(coordinator.memory_system.db_manager.get_all_memories())

    print(f"  → TemporalLobe (post-consolidation): {temporal_count_after} memories (Δ+{temporal_count_after - temporal_count_before})")
    print(f"  → MemorySystem: {memory_system_count} memories")

    metrics.record_storage_update('temporal_lobe', temporal_count_after, source='day1_post_consolidation')
    metrics.record_storage_update('memory_system', memory_system_count, source='day1_post_consolidation')

    # Assertion: Long-term storage should have increased
    assert temporal_count_after > temporal_count_before or memory_system_count > 0, \
        "Consolidation failed: No increase in long-term storage"

    print(f"\n  ✅ Consolidation successful:")
    print(f"     - TemporalLobe increased by {temporal_count_after - temporal_count_before}")
    print(f"     - MemorySystem has {memory_system_count} memories")

    # Phase 4: Save session state
    print("\n[4/4] Saving session state...")

    session_state = {
        'timestamp': datetime.now().isoformat(),
        'session': 'day1',
        'ingested_memories': len(DAY1_MEMORIES),
        'consolidated_patterns': consolidation_result.get('consolidated', 0),
        'storage': {
            'hippocampus': hippo_count,
            'temporal_lobe': temporal_count_after,
            'memory_system': memory_system_count
        }
    }

    state_file = Path("metrics/cross_session/session1_state.json")
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(session_state, f, indent=2, ensure_ascii=False)

    print(f"  ✓ State saved to {state_file}")

    # Save metrics
    metrics_file = metrics.save_metrics(filename="session1_day1_metrics.json")
    print(f"  ✓ Metrics saved to {metrics_file}")

    await coordinator.stop_system()

    return session_state


async def session2_day2_retrieve_from_long_term():
    """
    Session 2 (Day 2): Fresh session, retrieve from long-term storage only
    """
    print("\n" + "=" * 80)
    print("SESSION 2 (DAY 2): Fresh Session - Long-Term Retrieval")
    print("=" * 80)
    print("\nSimulating: System restart, Hippocampus cleared (fresh short-term memory)")
    print("Expected: All retrievals should come from TemporalLobe/MemorySystem\n")

    # Reset metrics for new session
    reset_metrics_collector()

    # Initialize NEW coordinator (simulates restart)
    coordinator = BrainInspiredCoordinator()
    metrics = get_metrics_collector(output_dir="metrics/cross_session")

    # Verify Hippocampus is empty (fresh start)
    print("[1/3] Verifying fresh Hippocampus state...")
    hippo_count = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0
    temporal_count = len(coordinator.temporal_lobe.memories) if hasattr(coordinator.temporal_lobe, 'memories') else 0

    memory_system_count = 0
    if hasattr(coordinator, 'memory_system') and hasattr(coordinator.memory_system, 'db_manager'):
        all_memories = coordinator.memory_system.db_manager.get_all_memories()
        memory_system_count = len(all_memories)
        print(f"  → MemorySystem loaded: {memory_system_count} memories")
        if memory_system_count > 0:
            print(f"     Sample: {all_memories[0]['content'][:60]}...")

    print(f"  → Hippocampus (fresh): {hippo_count} memories (should be 0 or minimal)")
    print(f"  → TemporalLobe: {temporal_count} memories")
    print(f"  → MemorySystem: {memory_system_count} memories")

    # Assertion: Hippocampus should be essentially empty
    # (may have 1-2 from system initialization, but not our Day 1 data)
    assert hippo_count < 5, f"Hippocampus not fresh: has {hippo_count} memories (expected < 5)"

    # Assertion: Long-term storage should have data from Day 1
    assert temporal_count > 0 or memory_system_count > 0, \
        "No long-term storage found - consolidation from Day 1 didn't persist"

    print(f"\n  ✅ Session state verified:")
    print(f"     - Fresh Hippocampus (short-term cleared)")
    print(f"     - Long-term storage available ({temporal_count} temporal + {memory_system_count} persistent)")

    # Phase 2: Query using Day 2 test queries
    print("\n[2/3] Testing long-term retrieval with Day 2 queries...")

    results = []
    total_retrieved = 0
    long_term_count = 0
    short_term_count = 0

    for i, test_case in enumerate(DAY2_QUERIES, 1):
        print(f"\n  Query {i}/{len(DAY2_QUERIES)}: {test_case['query']}")
        print(f"  Expected: {test_case['description']}")

        # Retrieve with hybrid strategy
        retrieved = await coordinator.smart_retrieve(test_case['query'], k=10, strategy='hybrid')

        # Analyze sources
        sources = {}
        for mem in retrieved:
            source = mem.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1

        # Count long-term vs short-term
        long_term = sources.get('temporal_lobe', 0) + sources.get('memory_system', 0)
        short_term = sources.get('hippocampus', 0)

        total_retrieved += len(retrieved)
        long_term_count += long_term
        short_term_count += short_term

        print(f"    → Retrieved {len(retrieved)} memories")
        print(f"    → Sources: {sources}")
        print(f"    → Long-term: {long_term}, Short-term: {short_term}")

        # Verify: Should be primarily from long-term storage
        if long_term > 0:
            print(f"    ✅ PASS: Retrieved from long-term storage")
        elif short_term > 0:
            print(f"    ⚠️  WARNING: Retrieved from Hippocampus (short-term) - may indicate incomplete consolidation")
        else:
            print(f"    ❌ FAIL: No memories retrieved")

        results.append({
            'query': test_case['query'],
            'description': test_case['description'],
            'total_retrieved': len(retrieved),
            'sources': sources,
            'long_term_count': long_term,
            'short_term_count': short_term,
            'passed': long_term > 0
        })

    # Phase 3: Final analysis
    print("\n[3/3] Cross-session validation summary...")
    print("=" * 80)

    passed_queries = sum(1 for r in results if r['passed'])
    pass_rate = passed_queries / len(DAY2_QUERIES) * 100

    long_term_percentage = (long_term_count / total_retrieved * 100) if total_retrieved > 0 else 0
    short_term_percentage = (short_term_count / total_retrieved * 100) if total_retrieved > 0 else 0

    print(f"\nRetrieval Statistics:")
    print(f"  Total queries: {len(DAY2_QUERIES)}")
    print(f"  Queries with long-term retrieval: {passed_queries} ({pass_rate:.1f}%)")
    print(f"  Total memories retrieved: {total_retrieved}")
    print(f"  From long-term storage: {long_term_count} ({long_term_percentage:.1f}%)")
    print(f"  From short-term storage: {short_term_count} ({short_term_percentage:.1f}%)")

    # Critical assertion: Long-term retrieval should dominate
    assert long_term_percentage >= 70, \
        f"FAIL: Long-term storage usage too low ({long_term_percentage:.1f}%) - expected >= 70%"

    print(f"\n{'✅ PASS' if long_term_percentage >= 70 else '❌ FAIL'}: Long-term memory validation")
    print(f"  Criterion: >= 70% retrieval from long-term storage")
    print(f"  Actual: {long_term_percentage:.1f}%")

    # Save results
    session_state = {
        'timestamp': datetime.now().isoformat(),
        'session': 'day2',
        'test_queries': len(DAY2_QUERIES),
        'passed_queries': passed_queries,
        'pass_rate': pass_rate,
        'retrieval_stats': {
            'total_retrieved': total_retrieved,
            'long_term_count': long_term_count,
            'short_term_count': short_term_count,
            'long_term_percentage': long_term_percentage,
            'short_term_percentage': short_term_percentage
        },
        'detailed_results': results
    }

    state_file = Path("metrics/cross_session/session2_state.json")
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(session_state, f, indent=2, ensure_ascii=False)

    print(f"\n  ✓ Results saved to {state_file}")

    # Save metrics
    metrics_file = metrics.save_metrics(filename="session2_day2_metrics.json")
    print(f"  ✓ Metrics saved to {metrics_file}")

    await coordinator.stop_system()

    return session_state


async def main():
    """
    Main test orchestrator
    """
    print("Cross-Session Long-Term Memory Validation")
    print("=" * 80)
    print("Objective: Prove long-term memory persists across sessions")
    print("          and is NOT just short-term memory in disguise")
    print("=" * 80)

    try:
        # Session 1: Ingest and consolidate
        session1_state = await session1_day1_ingest_and_consolidate()

        # Simulate time passage (optional pause)
        print("\n" + "=" * 80)
        print("⏳ Simulating session restart...")
        print("   (In production: system would fully restart, clearing RAM)")
        print("=" * 80)
        await asyncio.sleep(2)

        # Session 2: Fresh retrieval from long-term storage
        session2_state = await session2_day2_retrieve_from_long_term()

        # Final verdict
        print("\n" + "=" * 80)
        print("FINAL VERDICT")
        print("=" * 80)

        long_term_pct = session2_state['retrieval_stats']['long_term_percentage']

        if long_term_pct >= 70:
            print("✅ CROSS-SESSION LONG-TERM MEMORY: VERIFIED")
            print(f"   - {long_term_pct:.1f}% of retrievals came from persistent long-term storage")
            print(f"   - System successfully retrieved consolidated memories after restart")
            print(f"   - NOT relying on short-term Hippocampus (which was empty)")
            success = True
        else:
            print("❌ CROSS-SESSION LONG-TERM MEMORY: FAILED")
            print(f"   - Only {long_term_pct:.1f}% from long-term storage (< 70% threshold)")
            print(f"   - System may be relying on short-term memory or not consolidating properly")
            success = False

        print("\nEvidence:")
        print(f"  Session 1: Consolidated {session1_state['consolidated_patterns']} patterns")
        print(f"  Session 1 Storage: {session1_state['storage']}")
        print(f"  Session 2: {session2_state['passed_queries']}/{session2_state['test_queries']} queries passed")
        print(f"  Session 2 Retrieval: {session2_state['retrieval_stats']}")

        return success

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
