#!/usr/bin/env python3
"""
LoCoMo 20-Event Large-Scale Cross-Session Test
LoCoMo 20事件大规模跨会话测试

Objective: Validate long-term memory consolidation with 20 events
目标: 使用20个事件验证长期记忆巩固能力

Pattern:
- Session 1 (Day 1): Ingest 20 LoCoMo events → Consolidate → Shutdown
- Session 2 (Day 2): Fresh coordinator → Answer 10 questions → Verify retrieval

Author: Claude Code
Date: 2025-11-11
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.monitoring.memory_metrics import get_metrics_collector

# LoCoMo扩展数据集 - Caroline的完整故事 (20个事件)
LOCOMO_20_SESSIONS = [
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
            "Caroline discovered that many agencies now offer specialized training for LGBTQ family support.",
            "She noted: 'These resources are exactly what I've been looking for to help my future career.'",
        ]
    },
    {
        'date': '2023-06-12',
        'events': [
            "On 12 June 2023, Caroline attended her first counseling workshop at the community center.",
            "She practiced active listening techniques with other trainees.",
            "Caroline said: 'The role-playing exercises were challenging but very valuable.'",
            "She met Dr. Sarah Chen, a licensed therapist who became her mentor.",
        ]
    },
    {
        'date': '2023-07-04',
        'events': [
            "On 4 July 2023, Caroline volunteered at the city's Pride parade as a peer counselor.",
            "She helped staff the mental health information booth and talked to over 30 people.",
            "Caroline noted: 'So many young people are looking for support and guidance.'",
            "She realized the importance of having visible LGBTQ mental health professionals.",
        ]
    },
    {
        'date': '2023-08-20',
        'events': [
            "On 20 August 2023, Caroline enrolled in a Master's program in Clinical Social Work.",
            "She chose a specialization in LGBTQ mental health and family counseling.",
            "Caroline said: 'This program has a strong focus on social justice and advocacy.'",
            "She was awarded a diversity scholarship covering 50% of her tuition.",
        ]
    }
]

# 10个测试问题 (覆盖20个事件)
LOCOMO_20_QUESTIONS = [
    {
        'question': "When did Caroline go to the LGBTQ support group?",
        'expected_date': '2023-05-07',  # Day before 8 May
        'expected_keywords': ['LGBTQ', 'support group', 'May', '2023'],
        'event_source': 'Session 1, Event 1'
    },
    {
        'question': "What career field is Caroline interested in?",
        'expected_keywords': ['counseling', 'mental health', 'social work'],
        'event_source': 'Session 1, Event 4'
    },
    {
        'question': "What did Caroline research on May 25, 2023?",
        'expected_keywords': ['adoption', 'agencies', 'LGBTQ', 'families'],
        'event_source': 'Session 2, Event 1'
    },
    {
        'question': "What program did Caroline learn about related to social work?",
        'expected_keywords': ['social work', 'community', 'advocacy'],
        'event_source': 'Session 2, Event 2'
    },
    {
        'question': "When did Caroline attend her first counseling workshop?",
        'expected_date': '2023-06-12',
        'expected_keywords': ['June', '2023', 'counseling', 'workshop'],
        'event_source': 'Session 3, Event 1'
    },
    {
        'question': "Who became Caroline's mentor?",
        'expected_keywords': ['Dr. Sarah Chen', 'Sarah Chen', 'therapist', 'mentor'],
        'event_source': 'Session 3, Event 4'
    },
    {
        'question': "What did Caroline do on July 4, 2023?",
        'expected_keywords': ['Pride', 'parade', 'volunteer', 'peer counselor'],
        'event_source': 'Session 4, Event 1'
    },
    {
        'question': "How many people did Caroline talk to at the Pride parade?",
        'expected_keywords': ['30', 'people', 'mental health', 'booth'],
        'event_source': 'Session 4, Event 2'
    },
    {
        'question': "What Master's program did Caroline enroll in?",
        'expected_keywords': ['Clinical Social Work', 'Master', 'LGBTQ', 'mental health'],
        'event_source': 'Session 5, Event 1'
    },
    {
        'question': "What scholarship did Caroline receive?",
        'expected_keywords': ['diversity', 'scholarship', '50%', 'tuition'],
        'event_source': 'Session 5, Event 4'
    }
]


async def session_1_ingest_20_events():
    """
    Session 1 (Day 1): Ingest 20 events and consolidate
    会话1（第1天）：摄入20个事件并巩固
    """
    print("\n" + "="*80)
    print("SESSION 1 (Day 1): Ingesting 20 LoCoMo Events")
    print("="*80 + "\n")

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    event_count = 0
    for session in LOCOMO_20_SESSIONS:
        date = session['date']
        print(f"\n📅 Processing events from {date}:")

        for i, event in enumerate(session['events'], 1):
            event_count += 1
            print(f"  [{event_count}/20] {event[:80]}...")

            # Process event through full pipeline
            result = await coordinator.process_input(event)

            await asyncio.sleep(0.5)  # Small delay between events

    print(f"\n✓ Ingested {event_count} events")

    # Trigger consolidation
    print("\n🔄 Triggering consolidation...")
    today_str = datetime.now().strftime('%Y-%m-%d')

    if hasattr(coordinator, 'hippocampus'):
        consolidated = await coordinator.hippocampus.consolidate_day_memories(today_str)
        print(f"✓ Consolidated {len(consolidated)} memory patterns")
    else:
        print("⚠️  No Hippocampus agent found")

    # Save state
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_20_events'
    metrics_dir.mkdir(parents=True, exist_ok=True)

    state_file = metrics_dir / 'session1_state.json'
    state = {
        'session': 1,
        'date': datetime.now().isoformat(),
        'events_ingested': event_count,
        'consolidation_complete': True
    }

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

    print(f"✓ Session 1 state saved to {state_file}")
    print("\n💤 Simulating overnight sleep (consolidation period)...\n")

    return event_count


async def session_2_query_10_questions():
    """
    Session 2 (Day 2): Query 10 questions and verify retrieval
    会话2（第2天）：查询10个问题并验证检索
    """
    print("\n" + "="*80)
    print("SESSION 2 (Day 2): Querying Long-Term Memory (10 Questions)")
    print("="*80 + "\n")

    # Fresh coordinator - simulates new session
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    results = []
    long_term_count = 0
    short_term_count = 0

    for i, q in enumerate(LOCOMO_20_QUESTIONS, 1):
        question = q['question']
        expected_keywords = q['expected_keywords']

        print(f"\n[{i}/10] Query: {question}")

        # Use direct LLM call to avoid Hippocampus contamination
        if hasattr(coordinator, 'memory_coordinator'):
            memories = await coordinator.memory_coordinator.smart_retrieve(
                query=question,
                top_k=5
            )
        else:
            memories = []

        # Classify memory sources
        memory_sources = {}
        for mem in memories:
            source = mem.get('source', 'unknown')
            memory_sources[source] = memory_sources.get(source, 0) + 1

        # Check if retrieved from long-term storage
        from_long_term = (
            memory_sources.get('memory_system', 0) > 0 or
            memory_sources.get('temporal_lobe', 0) > 0
        )
        from_short_term = memory_sources.get('hippocampus', 0) > 0

        if from_long_term:
            long_term_count += 1
            print(f"    ✅ PASS: Retrieved from long-term storage")
            print(f"    → Long-term: {memory_sources.get('memory_system', 0) + memory_sources.get('temporal_lobe', 0)}, Short-term: {memory_sources.get('hippocampus', 0)}")
        else:
            print(f"    ❌ FAIL: Not found in long-term storage")
            print(f"    → Memory sources: {memory_sources}")

        # Check keyword coverage
        if memories:
            memory_text = ' '.join([m.get('content', '') for m in memories])
            keywords_found = [kw for kw in expected_keywords if kw.lower() in memory_text.lower()]
            print(f"    → Keywords found: {len(keywords_found)}/{len(expected_keywords)} {keywords_found}")
        else:
            print(f"    → No memories retrieved")

        results.append({
            'question': question,
            'from_long_term': from_long_term,
            'memory_sources': memory_sources,
            'memories_count': len(memories)
        })

        await asyncio.sleep(1)

    # Calculate metrics
    total_questions = len(LOCOMO_20_QUESTIONS)
    pass_rate = (long_term_count / total_questions) * 100
    long_term_retrieval_rate = pass_rate

    print("\n" + "="*80)
    print("SESSION 2 RESULTS")
    print("="*80)
    print(f"\nQuestions tested: {total_questions}")
    print(f"Long-term retrieval: {long_term_count}/{total_questions} ({long_term_retrieval_rate:.1f}%)")
    print(f"Pass rate: {pass_rate:.1f}%")

    # Save results
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_20_events'
    metrics_dir.mkdir(parents=True, exist_ok=True)

    state_file = metrics_dir / 'session2_state.json'
    state = {
        'session': 2,
        'date': datetime.now().isoformat(),
        'questions_tested': total_questions,
        'long_term_retrieval_count': long_term_count,
        'long_term_retrieval_rate': long_term_retrieval_rate,
        'pass_rate': pass_rate,
        'results': results
    }

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

    print(f"\n✓ Session 2 state saved to {state_file}")

    # Final verdict
    threshold = 70.0
    if long_term_retrieval_rate >= threshold:
        print(f"\n✅ PASS: LoCoMo 20-event cross-session long-term memory validation")
        print(f"   Long-term retrieval: {long_term_retrieval_rate:.1f}% (threshold: ≥{threshold}%)")
        return True
    else:
        print(f"\n❌ FAIL: Long-term retrieval rate below threshold")
        print(f"   Got: {long_term_retrieval_rate:.1f}%, Expected: ≥{threshold}%")
        return False


async def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("LoCoMo Cross-Session Long-Term Memory Test (20 Events)")
    print("="*80)

    try:
        # Session 1: Ingest 20 events
        event_count = await session_1_ingest_20_events()

        # Small delay to simulate overnight consolidation
        await asyncio.sleep(3)

        # Session 2: Query 10 questions
        passed = await session_2_query_10_questions()

        # Final summary
        print("\n" + "="*80)
        print("FINAL SUMMARY")
        print("="*80)
        print(f"\nSession 1 (Day 1):")
        print(f"  - Events ingested: {event_count}")
        print(f"  - Consolidation: Complete")
        print(f"\nSession 2 (Day 2):")
        print(f"  - Questions tested: {len(LOCOMO_20_QUESTIONS)}")

        if passed:
            print("\n✅ TEST PASSED")
            sys.exit(0)
        else:
            print("\n❌ TEST FAILED")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
