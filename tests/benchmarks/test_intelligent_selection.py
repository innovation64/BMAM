"""
Quick test for intelligent answer selection
"""

import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator

LOCOMO_SESSIONS = [
    {
        'date': '2023-05-25',
        'events': [
            "On 25 May 2023, Caroline researched adoption agencies that support LGBTQ families.",
        ]
    }
]

LOCOMO_QUESTIONS = [
    ("What did Caroline research?", "adoption agencies"),
]

async def main():
    print("=" * 80)
    print("🧪 Testing Intelligent Answer Selection")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Phase 1: Learn
    print("\n📚 Phase 1: Learning...")
    for session in LOCOMO_SESSIONS:
        for event in session['events']:
            await coordinator.process_user_input(event)
            print(f"  ✅ Learned: {event[:60]}...")

    # Phase 2: Test
    print("\n❓ Phase 2: Testing...")
    question, expected = LOCOMO_QUESTIONS[0]
    print(f"\n  Q: {question}")
    print(f"  Expected: {expected}")

    result = await coordinator.process_user_input(question)
    answer = result.response

    print(f"  Got: {answer}")
    correct = expected.lower() in answer.lower()
    print(f"  {'✅ CORRECT' if correct else '❌ WRONG'}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
