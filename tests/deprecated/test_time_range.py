#!/usr/bin/env python3
"""
Quick test to verify time_range filtering is working
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.coordination.brain_coordinator import BrainInspiredCoordinator


async def test_time_range():
    """Test time_range extraction and filtering"""

    print("=" * 60)
    print("Time Range Filtering Test")
    print("=" * 60)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Learning events with dates
    learning_events = [
        "On 8 May 2023, Caroline attended an LGBTQ support group meeting.",
        "On 12 May 2023, Caroline went to a gender identity clinic.",
        "On 25 May 2023, Caroline researched adoption agencies.",
        "On 2 June 2023, Caroline attended a cooking class."
    ]

    print("\n📚 Learning events:")
    for event in learning_events:
        print(f"  - {event}")
        result = await coordinator.process_input(event)
        print(f"    ✓ Stored")

    print("\n" + "=" * 60)
    print("Testing Temporal Query with Time Range")
    print("=" * 60)

    # This query should trigger temporal_calculation capability
    # and extract time_range: {'start': '2023-05-08', 'end': '2023-05-25'}
    query = "What did Caroline do between 8 May 2023 and 25 May 2023?"

    print(f"\n❓ Query: {query}")
    print("\nExpected:")
    print("  - Should extract time_range: {'start': '2023-05-08', 'end': '2023-05-25'}")
    print("  - Should filter out the June 2 event")
    print("  - Should include the May 8, 12, and 25 events")

    result = await coordinator.process_input(query)

    print(f"\n✅ Answer: {result.response}")
    print(f"\n📊 Routing: {result.routing_decision}")
    print(f"🧠 Agents: {result.agents_involved}")
    print(f"💾 Memories: {len(result.memories_retrieved)}")

    await coordinator.stop_system()
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_time_range())
