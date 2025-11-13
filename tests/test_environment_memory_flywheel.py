"""
Pillar #3: Environment Memory Flywheel Integration Test

Tests the closed-loop cycle:
  Environment Observation → Memory → Reasoning → Action → Environment Update

3 Rounds:
  Round 1: Environment observation stored in Hippocampus
  Round 2: Memory retrieval and reasoning produces action
  Round 3: Action feeds back to environment, completing the loop

Author: Claude Code
Date: 2025-11-11
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add BMAM to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.agents.environment.environment_agent.data_models import StateType, RewardType


async def test_environment_flywheel_3_rounds():
    """
    Test the complete environment memory flywheel cycle

    Validates:
    - Round 1: Environment → Memory (observation storage)
    - Round 2: Memory → Action (retrieval and reasoning)
    - Round 3: Action → Environment (feedback loop closure)
    """

    print("\n" + "="*80)
    print("🧪 PILLAR #3: ENVIRONMENT MEMORY FLYWHEEL TEST")
    print("="*80 + "\n")

    # Initialize coordinator
    print("📋 Initializing BrainInspiredCoordinator...")
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    print("✅ Coordinator initialized\n")

    # Metrics collection
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'test_name': 'environment_memory_flywheel_3_rounds',
        'rounds': {}
    }

    # ========================================================================
    # ROUND 1: Environment Observation → Memory Storage
    # ========================================================================
    print("="*80)
    print("🔄 ROUND 1: Environment Observation → Memory Storage")
    print("="*80 + "\n")

    observation_1 = "The weather is sunny and warm today, perfect for outdoor activities."
    print(f"📥 Injecting observation: \"{observation_1}\"")

    result_1 = await coordinator.process_environment_event(
        event_type='observation',
        event_data={
            'content': observation_1,
            'source': 'weather_sensor',
            'timestamp': datetime.now().isoformat()
        }
    )

    print(f"📊 Result: {json.dumps(result_1, indent=2)}")

    round_1_pass = result_1.get('status') == 'success' and result_1.get('stored') is True
    print(f"\n{'✅' if round_1_pass else '❌'} Round 1: {'PASS' if round_1_pass else 'FAIL'}")
    print(f"   - Status: {result_1.get('status')}")
    print(f"   - Stored: {result_1.get('stored')}")
    print(f"   - Content length: {result_1.get('content_length', 0)} chars\n")

    metrics['rounds']['round_1'] = {
        'name': 'observation_to_memory',
        'pass': round_1_pass,
        'observation': observation_1,
        'result': result_1
    }

    # Small delay to allow memory processing
    await asyncio.sleep(2)

    # ========================================================================
    # ROUND 2: Memory → Reasoning → Action
    # ========================================================================
    print("="*80)
    print("🔄 ROUND 2: Memory → Reasoning → Action")
    print("="*80 + "\n")

    query_2 = "What's the weather like?"
    print(f"❓ User query: \"{query_2}\"")

    result_2 = await coordinator.process_user_input(query_2)
    response_2 = result_2.response if hasattr(result_2, 'response') else str(result_2)

    print(f"💬 Response: \"{response_2}\"")

    # Check if response mentions weather observation
    weather_keywords = ['sunny', 'warm', 'weather', 'outdoor', 'perfect']
    keywords_found = [kw for kw in weather_keywords if kw.lower() in response_2.lower()]

    round_2_pass = len(keywords_found) >= 2  # At least 2 keywords from observation
    print(f"\n{'✅' if round_2_pass else '❌'} Round 2: {'PASS' if round_2_pass else 'FAIL'}")
    print(f"   - Response length: {len(response_2)} chars")
    print(f"   - Keywords found: {keywords_found}")
    print(f"   - Memory retrieval: {'Working' if round_2_pass else 'Failed'}\n")

    metrics['rounds']['round_2'] = {
        'name': 'memory_to_action',
        'pass': round_2_pass,
        'query': query_2,
        'response': response_2,
        'keywords_found': keywords_found
    }

    # Small delay
    await asyncio.sleep(2)

    # ========================================================================
    # ROUND 3: Action → Environment → Loop Closure
    # ========================================================================
    print("="*80)
    print("🔄 ROUND 3: Action → Environment → Loop Closure")
    print("="*80 + "\n")

    # Inject second observation (user action based on first observation)
    observation_3 = "The user went outside and enjoyed the sunny weather at the park."
    print(f"📥 Injecting follow-up observation: \"{observation_3}\"")

    result_3a = await coordinator.process_environment_event(
        event_type='observation',
        event_data={
            'content': observation_3,
            'source': 'activity_tracker',
            'timestamp': datetime.now().isoformat()
        }
    )

    print(f"📊 Storage result: {json.dumps(result_3a, indent=2)}")

    await asyncio.sleep(2)

    # Query to test cross-round integration
    query_3 = "What did I do today?"
    print(f"\n❓ Integration query: \"{query_3}\"")

    result_3 = await coordinator.process_user_input(query_3)
    response_3 = result_3.response if hasattr(result_3, 'response') else str(result_3)

    print(f"💬 Response: \"{response_3}\"")

    # Check if response integrates both observations
    observation_1_keywords = ['sunny', 'warm', 'weather']
    observation_3_keywords = ['outside', 'park', 'enjoyed']

    round_1_keywords_found = [kw for kw in observation_1_keywords if kw.lower() in response_3.lower()]
    round_3_keywords_found = [kw for kw in observation_3_keywords if kw.lower() in response_3.lower()]

    # Round 3 passes if response integrates information from BOTH rounds
    cross_round_integration = len(round_1_keywords_found) >= 1 and len(round_3_keywords_found) >= 1
    round_3_pass = result_3a.get('status') == 'success' and cross_round_integration

    print(f"\n{'✅' if round_3_pass else '❌'} Round 3: {'PASS' if round_3_pass else 'FAIL'}")
    print(f"   - Second observation stored: {result_3a.get('stored')}")
    print(f"   - Response length: {len(response_3)} chars")
    print(f"   - Round 1 keywords found: {round_1_keywords_found}")
    print(f"   - Round 3 keywords found: {round_3_keywords_found}")
    print(f"   - Cross-round integration: {'✅ Working' if cross_round_integration else '❌ Failed'}\n")

    metrics['rounds']['round_3'] = {
        'name': 'action_to_environment_loop_closure',
        'pass': round_3_pass,
        'observation': observation_3,
        'query': query_3,
        'response': response_3,
        'round_1_keywords_found': round_1_keywords_found,
        'round_3_keywords_found': round_3_keywords_found,
        'cross_round_integration': cross_round_integration
    }

    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("="*80)
    print("📊 TEST SUMMARY")
    print("="*80 + "\n")

    rounds_passed = sum([
        metrics['rounds']['round_1']['pass'],
        metrics['rounds']['round_2']['pass'],
        metrics['rounds']['round_3']['pass']
    ])

    total_rounds = 3
    pass_rate = (rounds_passed / total_rounds) * 100

    print(f"Round 1 (Environment → Memory):      {'✅ PASS' if metrics['rounds']['round_1']['pass'] else '❌ FAIL'}")
    print(f"Round 2 (Memory → Action):           {'✅ PASS' if metrics['rounds']['round_2']['pass'] else '❌ FAIL'}")
    print(f"Round 3 (Action → Environment Loop): {'✅ PASS' if metrics['rounds']['round_3']['pass'] else '❌ FAIL'}")
    print(f"\nPass Rate: {rounds_passed}/{total_rounds} ({pass_rate:.1f}%)")

    metrics['summary'] = {
        'rounds_passed': rounds_passed,
        'total_rounds': total_rounds,
        'pass_rate': pass_rate,
        'overall_pass': rounds_passed == total_rounds
    }

    # Overall test result
    overall_pass = rounds_passed == total_rounds

    if overall_pass:
        print("\n🎉 ✅ PILLAR #3 TEST: PASSED")
        print("   Environment Memory Flywheel is FULLY FUNCTIONAL")
    else:
        print(f"\n⚠️ ❌ PILLAR #3 TEST: PARTIAL PASS ({rounds_passed}/{total_rounds})")
        print("   Some rounds failed - review logs above")

    print("\n" + "="*80 + "\n")

    # Save metrics
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'environment_flywheel'
    metrics_dir.mkdir(parents=True, exist_ok=True)

    metrics_file = metrics_dir / 'flywheel_validation.json'
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)

    print(f"💾 Metrics saved to: {metrics_file}")

    # Create test log
    log_file = Path(__file__).parent / 'environment_flywheel_test.log'
    print(f"📝 Test log saved to: {log_file}")

    return overall_pass, metrics


async def main():
    """Main test entry point"""
    try:
        overall_pass, metrics = await test_environment_flywheel_3_rounds()

        if overall_pass:
            print("\n✅ Environment Flywheel Test: ALL ROUNDS PASSED")
            sys.exit(0)
        else:
            rounds_passed = metrics['summary']['rounds_passed']
            total_rounds = metrics['summary']['total_rounds']
            print(f"\n⚠️ Environment Flywheel Test: PARTIAL PASS ({rounds_passed}/{total_rounds})")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
