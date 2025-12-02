#!/usr/bin/env python3
"""
测试修复的有效性
Test the effectiveness of our fixes
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.config import get_logger

logger = get_logger(__name__)

async def test_memory_storage_timing():
    """测试记忆存储时序问题修复"""
    print("🧪 Testing memory storage timing fixes...")

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Test 1: Store a preference
    result1 = await coordinator.process_user_input("请记住我喜欢喝绿茶")
    print(f"✅ Test 1 - Preference storage: memory_stored={result1.memory_stored}, success={result1.success}")
    if result1.error:
        print(f"❌ Error: {result1.error}")

    # Test 2: Immediately try to retrieve it
    result2 = await coordinator.process_user_input("我喜欢什么茶？")
    print(f"✅ Test 2 - Immediate retrieval: memories_found={len(result2.memories_retrieved)}, success={result2.success}")
    if result2.error:
        print(f"❌ Error: {result2.error}")

    # Check if the preference was found
    preference_found = any("绿茶" in str(memory) for memory in result2.memories_retrieved)
    print(f"🔍 Preference found in retrieved memories: {preference_found}")

    await coordinator.stop_system()
    return preference_found

async def test_selective_agent_activation():
    """测试选择性智能体激活"""
    print("\n🧪 Testing selective agent activation...")

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Test simple greeting (should not activate stress_response)
    result1 = await coordinator.process_user_input("你好")
    agents_used = result1.agents_involved
    print(f"✅ Simple greeting - Agents used: {agents_used}")
    print(f"   Stress analysis skipped: {'stress_response' not in agents_used}")

    # Test stress-related input (should activate stress_response)
    result2 = await coordinator.process_user_input("我今天工作压力很大，感到很焦虑")
    agents_used2 = result2.agents_involved
    print(f"✅ Stress content - Agents used: {agents_used2}")
    print(f"   Stress analysis activated: {'stress_response' in agents_used2}")

    await coordinator.stop_system()
    return len(agents_used) < len(agents_used2)

async def test_timeout_protection():
    """测试超时保护"""
    print("\n🧪 Testing timeout protection...")

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Test with a complex request that might timeout
    start_time = asyncio.get_event_loop().time()
    result = await coordinator.process_user_input("请分析我的记忆模式并提供详细的个性化建议")
    end_time = asyncio.get_event_loop().time()

    processing_time = end_time - start_time
    print(f"✅ Complex request completed in {processing_time:.2f}s")
    print(f"   Success: {result.success}")
    print(f"   Within reasonable time: {processing_time < 30}")

    if result.error:
        print(f"❌ Error: {result.error}")

    await coordinator.stop_system()
    return processing_time < 30

async def main():
    """运行所有测试"""
    print("🚀 Starting comprehensive fix validation tests...\n")

    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ Warning: OPENAI_API_KEY not found. Some tests may fail due to embedding errors.")
        print("This is expected behavior - the system should handle this gracefully.\n")

    test_results = []

    try:
        # Test 1: Memory storage timing
        result1 = await test_memory_storage_timing()
        test_results.append(("Memory Storage Timing", result1))

        # Test 2: Selective agent activation
        result2 = await test_selective_agent_activation()
        test_results.append(("Selective Agent Activation", result2))

        # Test 3: Timeout protection
        result3 = await test_timeout_protection()
        test_results.append(("Timeout Protection", result3))

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "="*50)
    print("📊 TEST RESULTS SUMMARY")
    print("="*50)

    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(test_results)} tests passed")

    if passed == len(test_results):
        print("🎉 All fixes working correctly!")
    else:
        print("⚠️ Some issues remain - check the test output above.")

if __name__ == "__main__":
    asyncio.run(main())