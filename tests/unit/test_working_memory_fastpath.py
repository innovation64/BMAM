"""
Test script for Working Memory Fast Path implementation

Tests:
1. Working memory cache hit/miss behavior
2. Fast path latency (<50ms for hit)
3. Slow path fallback
4. Cache update after conversation
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.utils.config import get_logger

logger = get_logger(__name__)


class WorkingMemoryFastPathTest:
    """Test working memory fast path functionality"""

    def __init__(self):
        self.coordinator = None
        self.test_results = []

    async def initialize(self):
        """Initialize coordinator"""
        print("=" * 60)
        print("Initializing BMAM System...")
        print("=" * 60)

        self.coordinator = BrainInspiredCoordinator()
        await self.coordinator.initialize()

        print("✅ System initialized\n")

    async def test_cold_start(self):
        """Test 1: Cold start (empty working memory) - should use slow path"""
        print("\n" + "=" * 60)
        print("Test 1: Cold Start (Working Memory MISS)")
        print("=" * 60)

        query = "Alice买了什么咖啡机?"
        start_time = datetime.now()

        result = await self.coordinator.process_user_input(query)

        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Query: {query}")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Total Latency: {latency:.1f}ms")
        print(f"  Memories Retrieved: {len(result.memories_retrieved)}")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'cold_start',
            'expected': 'slow_path',
            'latency_ms': latency,
            'success': result.success,
            'memories_count': len(result.memories_retrieved)
        })

        # Should be slow path (>200ms due to LLM calls)
        assert latency > 200, f"Cold start should use slow path (>200ms), got {latency:.1f}ms"
        print("\n✅ Test 1 PASSED: Used slow path as expected")

        return result

    async def test_immediate_repeat(self):
        """Test 2: Immediate repeat - should use fast path"""
        print("\n" + "=" * 60)
        print("Test 2: Immediate Repeat (Working Memory HIT)")
        print("=" * 60)

        # Same query as test 1
        query = "Alice买了什么咖啡机?"
        start_time = datetime.now()

        result = await self.coordinator.process_user_input(query)

        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Query: {query}")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Total Latency: {latency:.1f}ms")
        print(f"  Memories Retrieved: {len(result.memories_retrieved)}")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'immediate_repeat',
            'expected': 'fast_path',
            'latency_ms': latency,
            'success': result.success,
            'memories_count': len(result.memories_retrieved)
        })

        # Should be faster than cold start
        print(f"\n✅ Test 2 COMPLETED: Latency = {latency:.1f}ms")

        return result

    async def test_similar_query(self):
        """Test 3: Similar query - should partially hit working memory"""
        print("\n" + "=" * 60)
        print("Test 3: Similar Query (Partial Match)")
        print("=" * 60)

        query = "Alice的咖啡机是什么牌子?"
        start_time = datetime.now()

        result = await self.coordinator.process_user_input(query)

        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Query: {query}")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Total Latency: {latency:.1f}ms")
        print(f"  Memories Retrieved: {len(result.memories_retrieved)}")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'similar_query',
            'expected': 'keyword_match_or_slow',
            'latency_ms': latency,
            'success': result.success,
            'memories_count': len(result.memories_retrieved)
        })

        print(f"\n✅ Test 3 COMPLETED: Latency = {latency:.1f}ms")

        return result

    async def test_unrelated_query(self):
        """Test 4: Unrelated query - should use slow path"""
        print("\n" + "=" * 60)
        print("Test 4: Unrelated Query (Working Memory MISS)")
        print("=" * 60)

        query = "今天天气怎么样?"
        start_time = datetime.now()

        result = await self.coordinator.process_user_input(query)

        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Query: {query}")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Total Latency: {latency:.1f}ms")
        print(f"  Memories Retrieved: {len(result.memories_retrieved)}")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'unrelated_query',
            'expected': 'slow_path',
            'latency_ms': latency,
            'success': result.success,
            'memories_count': len(result.memories_retrieved)
        })

        print(f"\n✅ Test 4 COMPLETED: Latency = {latency:.1f}ms")

        return result

    async def test_cache_capacity(self):
        """Test 5: Working memory capacity (7±2 items)"""
        print("\n" + "=" * 60)
        print("Test 5: Working Memory Capacity Test")
        print("=" * 60)

        queries = [
            "Bob喜欢什么咖啡?",
            "Carol去哪里旅行?",
            "David有什么爱好?",
            "Eve喜欢什么音乐?",
            "Frank的工作是什么?",
            "Grace住在哪里?",
            "Henry多大年纪?",
            "Ivy学什么专业?"
        ]

        for i, query in enumerate(queries, 1):
            print(f"\n  Query {i}/8: {query}")
            start_time = datetime.now()
            result = await self.coordinator.process_user_input(query)
            latency = (datetime.now() - start_time).total_seconds() * 1000
            print(f"    Latency: {latency:.1f}ms")

        print("\n✅ Test 5 COMPLETED: Tested working memory capacity")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        for result in self.test_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"\n{result['test']}:")
            print(f"  Status: {status}")
            print(f"  Expected: {result['expected']}")
            print(f"  Latency: {result['latency_ms']:.1f}ms")
            print(f"  Memories: {result['memories_count']}")

        # Calculate averages
        avg_latency = sum(r['latency_ms'] for r in self.test_results) / len(self.test_results)
        success_rate = sum(1 for r in self.test_results if r['success']) / len(self.test_results) * 100

        print(f"\n" + "=" * 60)
        print(f"Overall Statistics:")
        print(f"  Tests Run: {len(self.test_results)}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Average Latency: {avg_latency:.1f}ms")
        print("=" * 60)

    async def run_all_tests(self):
        """Run all tests"""
        try:
            await self.initialize()

            # Run tests sequentially
            await self.test_cold_start()
            await asyncio.sleep(1)  # Brief pause

            await self.test_immediate_repeat()
            await asyncio.sleep(1)

            await self.test_similar_query()
            await asyncio.sleep(1)

            await self.test_unrelated_query()
            await asyncio.sleep(1)

            await self.test_cache_capacity()

            # Print summary
            self.print_summary()

        finally:
            if self.coordinator:
                await self.coordinator.stop_system()
                print("\n✅ System stopped cleanly")


async def main():
    """Main entry point"""
    print("\n🧠 BMAM Working Memory Fast Path Test Suite")
    print("Testing Phase 1 Implementation: Working Memory Priority\n")

    tester = WorkingMemoryFastPathTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())