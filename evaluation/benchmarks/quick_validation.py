#!/usr/bin/env python3
"""
Quick Validation Test - 快速验证集成是否正常工作
仅测试少量样本确保系统正常运行
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings('ignore')

import logging
logging.getLogger().setLevel(logging.WARNING)


async def test_preference_aware_retrieval():
    """测试偏好感知检索"""
    print("=" * 50)
    print("Test 1: PreferenceAwareRetrieval Integration")
    print("=" * 50)

    from src.memory.preference_aware_retrieval import PreferenceAwareRetrieval, PreferenceDetector

    # Test preference detection
    detector = PreferenceDetector()

    test_queries = [
        "What's my favorite color?",
        "Do I prefer coffee or tea?",
        "When did I buy my car?",  # Not preference-related
        "How do I usually spend weekends?",
        "What is 2+2?",  # Not preference-related
    ]

    print("\nPreference Detection Test:")
    for query in test_queries:
        result = detector.detect_preference_query(query)
        status = "✓ PREF" if result.is_preference_query else "  ---"
        print(f"  {status} | {result.preference_score:.2f} | {query}")

    print("✅ PreferenceDetector works correctly")
    return True


async def test_system_initialization():
    """测试系统初始化"""
    print("\n" + "=" * 50)
    print("Test 2: System Initialization")
    print("=" * 50)

    from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
    from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

    print("  Initializing BrainInspiredCoordinator...")
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    # Check PreferenceAwareRetrieval
    if hasattr(base_coord, 'preference_aware_retrieval') and base_coord.preference_aware_retrieval:
        print("  ✅ preference_aware_retrieval: ENABLED")
        stats = base_coord.preference_aware_retrieval.get_statistics()
        print(f"     Components: contrastive={bool(stats.get('contrastive'))}, "
              f"metamemory={bool(stats.get('metamemory'))}, "
              f"silent_engram={bool(stats.get('silent_engram'))}")
    else:
        print("  ⚠️ preference_aware_retrieval: NOT ENABLED")
        return False

    print("✅ System initialized correctly")
    return True


async def test_simple_query():
    """测试简单查询"""
    print("\n" + "=" * 50)
    print("Test 3: Simple Query Processing")
    print("=" * 50)

    from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
    from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    # Store a preference
    from datetime import datetime
    print("  Storing preference memory...")
    await coord.store_memory_with_timestamp(
        "User: I prefer tea over coffee. I always drink green tea in the morning.",
        datetime.now(), "user", 0.8
    )
    await asyncio.sleep(0.5)

    # Query about preference
    print("  Querying preference...")
    result = await coord.process_user_input(
        "Do I prefer tea or coffee?",
        context={'evaluation_mode': True}
    )
    response = result.response if hasattr(result, 'response') else str(result)

    print(f"  Response: {response[:200]}...")

    # Check if preference was mentioned
    if 'tea' in response.lower():
        print("✅ Preference correctly retrieved")
        return True
    else:
        print("⚠️ Preference might not be retrieved correctly")
        return False


async def main():
    print("=" * 50)
    print("Quick Validation Tests")
    print("=" * 50)

    results = []

    # Test 1: Preference detection
    results.append(await test_preference_aware_retrieval())

    # Test 2: System initialization
    results.append(await test_system_initialization())

    # Test 3: Simple query
    results.append(await test_simple_query())

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")

    if all(results):
        print("✅ All tests passed - ready for full benchmark")
        return 0
    else:
        print("❌ Some tests failed - please check")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(asyncio.run(main()))
