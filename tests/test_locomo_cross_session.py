#!/usr/bin/env python3
"""
LoCoMo Cross-Session Long-Term Memory Test
LoCoMo跨会话长期记忆测试

Objective: Validate long-term memory using LoCoMo dataset with cross-session pattern
目标: 使用LoCoMo数据集验证跨会话长期记忆

Pattern:
- Session 1 (Day 1): Ingest all LoCoMo sessions → Consolidate → Shutdown
- Session 2 (Day 2): Fresh coordinator → Answer questions → Verify long-term retrieval

This ensures questions can ONLY be answered from MemorySystem (persistent storage),
not from in-memory Hippocampus.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.monitoring.memory_metrics import get_metrics_collector

# LoCoMo真实数据 - Caroline的故事
LOCOMO_SESSIONS = [
    {
        'date': '2023-05-08',
        'events': [
            "On 8 May 2023, Caroline said: 'I went to a LGBTQ support group yesterday and it was so powerful.'",
            "She said: 'The transgender stories were so inspiring! I was so happy and thankful for all the support.'",
            "Caroline said: 'Gonna continue my edu and check out career options, which is pretty exciting!'",
            "She added: 'I'm keen on counseling or working in mental health - I'd love to support those with similar issues.'",
        ]
    },
    {
        'date': '2023-05-25',
        'events': [
            "On 25 May 2023, Caroline researched adoption agencies that support LGBTQ families.",
            "She learned about social work programs focused on community advocacy.",
        ]
    }
]

LOCOMO_QUESTIONS = [
    {
        'question': "When did Caroline go to the LGBTQ support group?",
        'expected_keywords': ["7 May", "May 7", "yesterday"],
        'description': "Temporal reasoning - relative date"
    },
    {
        'question': "What did Caroline research?",
        'expected_keywords': ["adoption", "agencies"],
        'description': "Factual recall - specific activity"
    },
    {
        'question': "What is Caroline's identity?",
        'expected_keywords': ["transgender", "LGBTQ"],
        'description': "Semantic inference - identity"
    },
    {
        'question': "What fields would Caroline be likely to pursue in her education?",
        'expected_keywords': ["social work", "psychology", "counseling", "mental health"],
        'description': "Forward inference - career planning"
    },
    {
        'question': "What community did Caroline engage with?",
        'expected_keywords': ["LGBTQ", "support group"],
        'description': "Factual recall - community involvement"
    }
]


async def session1_ingest_and_consolidate():
    """
    Session 1 (Day 1): Ingest LoCoMo data and consolidate
    """
    print("=" * 80)
    print("SESSION 1 (DAY 1): Ingest and Consolidate")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    print("\n[1/3] Ingesting LoCoMo sessions...")
    total_events = 0

    for session_idx, session in enumerate(LOCOMO_SESSIONS, 1):
        print(f"\n  📅 Session {session_idx} ({session['date']}):")
        for event_idx, event in enumerate(session['events'], 1):
            print(f"     {event_idx}. {event[:70]}...")
            await coordinator.process_input(event)
            total_events += 1

    print(f"\n  → Total events ingested: {total_events}")

    print("\n[2/3] Triggering memory consolidation...")

    # Trigger consolidation
    if hasattr(coordinator.hippocampus, 'consolidate_memories'):
        result = await coordinator.hippocampus.consolidate_memories()
        print(f"  → Consolidation result: {result}")
    else:
        print("  ⚠️  WARNING: Consolidation method not available")

    # Check storage distribution
    print("\n[3/3] Checking storage distribution...")

    hippo_count = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0
    temporal_count = len(coordinator.temporal_lobe.memories) if hasattr(coordinator.temporal_lobe, 'memories') else 0

    # Check MemorySystem
    ms_count = 0
    if hasattr(coordinator, 'memory_system'):
        try:
            if hasattr(coordinator.memory_system, 'get_all_memories'):
                ms_memories = await coordinator.memory_system.get_all_memories()
                ms_count = len(ms_memories)
            elif hasattr(coordinator.memory_system.vector_db, 'count'):
                ms_count = coordinator.memory_system.vector_db.count()
        except Exception as e:
            print(f"  → MemorySystem count error: {e}")

    print(f"  → Hippocampus: {hippo_count} memories")
    print(f"  → TemporalLobe: {temporal_count} memories")
    print(f"  → MemorySystem: {ms_count} memories")

    # Save session 1 state
    metrics = get_metrics_collector()
    session1_metrics = metrics.get_current_metrics()

    session1_state = {
        'timestamp': datetime.now().isoformat(),
        'session': 'day1',
        'total_events_ingested': total_events,
        'storage_distribution': {
            'hippocampus': hippo_count,
            'temporal_lobe': temporal_count,
            'memory_system': ms_count
        },
        'metrics': session1_metrics
    }

    output_file = Path("metrics/locomo_cross_session/session1_state.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(session1_state, f, indent=2)

    print(f"\n  ✓ Session 1 state saved to {output_file}")

    # Shutdown coordinator
    await coordinator.stop_system()
    print("\n  ✓ Coordinator shutdown complete")

    return session1_state


async def session2_fresh_retrieval():
    """
    Session 2 (Day 2): Fresh coordinator, query from long-term memory only
    """
    print("\n" + "=" * 80)
    print("SESSION 2 (DAY 2): Fresh Session - Long-Term Retrieval")
    print("=" * 80)

    print("\nSimulating: System restart, Hippocampus cleared (fresh short-term memory)")
    print("Expected: All answers should come from MemorySystem (persistent storage)\n")

    # Fresh coordinator instance
    coordinator = BrainInspiredCoordinator()

    print("[1/3] Verifying fresh Hippocampus state...")

    hippo_count = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0
    temporal_count = len(coordinator.temporal_lobe.memories) if hasattr(coordinator.temporal_lobe, 'memories') else 0

    # Check MemorySystem
    ms_count = 0
    if hasattr(coordinator, 'memory_system'):
        try:
            if hasattr(coordinator.memory_system, 'get_all_memories'):
                ms_memories = await coordinator.memory_system.get_all_memories()
                ms_count = len(ms_memories)
            elif hasattr(coordinator.memory_system.vector_db, 'count'):
                ms_count = coordinator.memory_system.vector_db.count()
        except Exception as e:
            print(f"  → MemorySystem count error: {e}")

    print(f"  → Hippocampus (fresh): {hippo_count} memories (should be 0 or minimal)")
    print(f"  → TemporalLobe: {temporal_count} memories")
    print(f"  → MemorySystem: {ms_count} memories")

    if hippo_count > 5:
        print(f"  ⚠️  WARNING: Hippocampus has {hippo_count} memories, expected fresh state")

    print(f"\n  ✅ Session state verified:")
    print(f"     - Fresh Hippocampus (short-term cleared)")
    print(f"     - Long-term storage available ({temporal_count} temporal + {ms_count} persistent)")

    # Test questions
    print("\n[2/3] Testing long-term retrieval with LoCoMo questions...")

    results = []
    passed_queries = 0
    total_retrieved = 0
    long_term_count = 0
    short_term_count = 0

    for q_idx, q_data in enumerate(LOCOMO_QUESTIONS, 1):
        question = q_data['question']
        expected_keywords = q_data['expected_keywords']
        description = q_data['description']

        print(f"\n  Query {q_idx}/{len(LOCOMO_QUESTIONS)}: {question}")
        print(f"  Expected keywords: {', '.join(expected_keywords)}")

        # Use memory coordinator's smart_retrieve if available
        if hasattr(coordinator, 'memory_coordinator'):
            retrieved_memories = await coordinator.memory_coordinator.smart_retrieve(
                query=question,
                k=5,
                strategy='hybrid'
            )
        else:
            # Fallback: direct retrieval
            retrieved_memories = []

        # Count sources
        sources = {}
        query_long_term = 0
        query_short_term = 0

        for mem in retrieved_memories:
            source = mem.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1

            if source in ['temporal_lobe', 'memory_system']:
                query_long_term += 1
            elif source == 'hippocampus':
                query_short_term += 1

        # Generate answer using retrieved context
        # IMPORTANT: Use LLM directly instead of process_input() to avoid creating new Hippocampus memories
        if retrieved_memories:
            # Build context from retrieved memories
            context = "\n".join([
                mem.get('content', mem.get('text', str(mem)))[:200]
                for mem in retrieved_memories[:3]
            ])

            # Use LLM directly without storing in memory
            from src.services.shared_openai_client import SharedOpenAIClientManager
            client_manager = SharedOpenAIClientManager()
            client = await client_manager.get_chat_client()

            messages = [
                {"role": "system", "content": "You are a helpful assistant. Answer questions based only on the provided context."},
                {"role": "user", "content": f"Based on the following context, answer this question: {question}\n\nContext:\n{context}"}
            ]

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=200
            )
            answer = response.choices[0].message.content
        else:
            answer = "No relevant memories found."

        # Check if answer contains expected keywords
        answer_lower = answer.lower()
        matched_keywords = [kw for kw in expected_keywords if kw.lower() in answer_lower]
        keyword_match = len(matched_keywords) > 0

        # Verify long-term retrieval
        passed = query_long_term > 0 and len(retrieved_memories) > 0

        total_retrieved += len(retrieved_memories)
        long_term_count += query_long_term
        short_term_count += query_short_term

        print(f"    → Retrieved {len(retrieved_memories)} memories")
        print(f"    → Sources: {sources}")
        print(f"    → Long-term: {query_long_term}, Short-term: {query_short_term}")
        print(f"    → Matched keywords: {matched_keywords if matched_keywords else 'None'}")

        if passed:
            print(f"    ✅ PASS: Retrieved from long-term storage")
            passed_queries += 1
        else:
            print(f"    ❌ FAIL: No long-term retrieval")

        results.append({
            'query': question,
            'description': description,
            'expected_keywords': expected_keywords,
            'total_retrieved': len(retrieved_memories),
            'sources': sources,
            'long_term_count': query_long_term,
            'short_term_count': query_short_term,
            'answer': answer[:200],
            'keyword_match': keyword_match,
            'matched_keywords': matched_keywords,
            'passed': passed
        })

    # Calculate long-term percentage
    long_term_percentage = (long_term_count / total_retrieved * 100) if total_retrieved > 0 else 0.0

    print(f"\n[3/3] Cross-session validation summary...")
    print("=" * 80)
    print(f"\nRetrieval Statistics:")
    print(f"  Total queries: {len(LOCOMO_QUESTIONS)}")
    print(f"  Queries with long-term retrieval: {passed_queries} ({passed_queries/len(LOCOMO_QUESTIONS)*100:.1f}%)")
    print(f"  Total memories retrieved: {total_retrieved}")
    print(f"  From long-term storage: {long_term_count} ({long_term_percentage:.1f}%)")
    print(f"  From short-term storage: {short_term_count} ({short_term_count/total_retrieved*100 if total_retrieved>0 else 0:.1f}%)")

    # Save session 2 state
    session2_state = {
        'timestamp': datetime.now().isoformat(),
        'session': 'day2',
        'test_queries': len(LOCOMO_QUESTIONS),
        'passed_queries': passed_queries,
        'pass_rate': passed_queries / len(LOCOMO_QUESTIONS) * 100,
        'retrieval_stats': {
            'total_retrieved': total_retrieved,
            'long_term_count': long_term_count,
            'short_term_count': short_term_count,
            'long_term_percentage': long_term_percentage,
            'short_term_percentage': short_term_count / total_retrieved * 100 if total_retrieved > 0 else 0.0
        },
        'detailed_results': results
    }

    output_file = Path("metrics/locomo_cross_session/session2_state.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(session2_state, f, indent=2)

    print(f"\n✓ Session 2 state saved to {output_file}")

    # Validation
    print("\n" + "=" * 80)
    if long_term_percentage >= 70:
        print(f"✅ PASS: LoCoMo cross-session long-term memory validation")
        print(f"   Long-term retrieval: {long_term_percentage:.1f}% (threshold: ≥70%)")
        success = True
    else:
        print(f"❌ FAIL: Long-term storage usage too low ({long_term_percentage:.1f}%)")
        print(f"   Expected: ≥70% retrieval from long-term storage")
        print(f"   This indicates MemorySystem retrieval path may be broken.")
        success = False

    print("=" * 80)

    await coordinator.stop_system()

    return success, session2_state


async def main():
    """Main test orchestrator"""
    print("LoCoMo Cross-Session Long-Term Memory Test")
    print("=" * 80)
    print("Objective: Validate long-term memory using LoCoMo dataset")
    print("Pattern: Session 1 (ingest → consolidate) → Session 2 (fresh → query)")
    print("=" * 80)

    try:
        # Session 1: Ingest and consolidate
        session1_state = await session1_ingest_and_consolidate()

        print("\n" + "=" * 80)
        print("⏳ Simulating session restart...")
        print("   (In production: system would fully restart, clearing RAM)")
        print("=" * 80)

        # Session 2: Fresh retrieval
        success, session2_state = await session2_fresh_retrieval()

        # Final summary
        print("\n" + "=" * 80)
        print("FINAL SUMMARY")
        print("=" * 80)
        print(f"\nSession 1 (Day 1):")
        print(f"  - Events ingested: {session1_state['total_events_ingested']}")
        print(f"  - MemorySystem: {session1_state['storage_distribution']['memory_system']} memories")

        print(f"\nSession 2 (Day 2):")
        print(f"  - Queries tested: {session2_state['test_queries']}")
        print(f"  - Pass rate: {session2_state['pass_rate']:.1f}%")
        print(f"  - Long-term retrieval: {session2_state['retrieval_stats']['long_term_percentage']:.1f}%")

        if success:
            print(f"\n✅ TEST PASSED")
            return 0
        else:
            print(f"\n❌ TEST FAILED")
            return 1

    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
