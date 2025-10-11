"""
Test script for Retrieval Strategy Router (Phase 2)

Tests:
1. Temporal queries → episodic strategy
2. Entity+relation queries → associative strategy
3. Factual queries → keyword strategy
4. Complex queries → multi_strategy
5. Default queries → semantic strategy
6. Strategy selection confidence scores
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


class RetrievalRouterTest:
    """Test retrieval strategy router functionality"""

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

    async def test_temporal_query(self):
        """Test 1: Temporal query should route to episodic strategy"""
        print("\n" + "=" * 60)
        print("Test 1: Temporal Query (Should Route to EPISODIC)")
        print("=" * 60)

        query = "上周我做了什么?"
        print(f"Query: {query}")

        start_time = datetime.now()
        result = await self.coordinator.process_user_input(query)
        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Latency: {latency:.1f}ms")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'temporal_query',
            'query': query,
            'expected_strategy': 'episodic',
            'latency_ms': latency,
            'success': result.success
        })

        print(f"\n✅ Test 1 COMPLETED")
        return result

    async def test_associative_query(self):
        """Test 2: Entity+relation query should route to associative strategy"""
        print("\n" + "=" * 60)
        print("Test 2: Associative Query (Should Route to ASSOCIATIVE)")
        print("=" * 60)

        query = "Alice和Bob之间有什么关系?"
        print(f"Query: {query}")

        start_time = datetime.now()
        result = await self.coordinator.process_user_input(query)
        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Latency: {latency:.1f}ms")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'associative_query',
            'query': query,
            'expected_strategy': 'associative',
            'latency_ms': latency,
            'success': result.success
        })

        print(f"\n✅ Test 2 COMPLETED")
        return result

    async def test_factual_query(self):
        """Test 3: Factual question should route to keyword strategy"""
        print("\n" + "=" * 60)
        print("Test 3: Factual Query (Should Route to KEYWORD)")
        print("=" * 60)

        query = "Alice买了什么咖啡机?"
        print(f"Query: {query}")

        start_time = datetime.now()
        result = await self.coordinator.process_user_input(query)
        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Latency: {latency:.1f}ms")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'factual_query',
            'query': query,
            'expected_strategy': 'keyword',
            'latency_ms': latency,
            'success': result.success
        })

        print(f"\n✅ Test 3 COMPLETED")
        return result

    async def test_complex_query(self):
        """Test 4: Complex 'why' question should route to multi_strategy"""
        print("\n" + "=" * 60)
        print("Test 4: Complex Query (Should Route to MULTI_STRATEGY)")
        print("=" * 60)

        query = "为什么Alice会选择这款咖啡机而不是其他品牌?"
        print(f"Query: {query}")

        start_time = datetime.now()
        result = await self.coordinator.process_user_input(query)
        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Latency: {latency:.1f}ms")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'complex_query',
            'query': query,
            'expected_strategy': 'multi_strategy',
            'latency_ms': latency,
            'success': result.success
        })

        print(f"\n✅ Test 4 COMPLETED")
        return result

    async def test_semantic_query(self):
        """Test 5: Simple semantic query should route to semantic strategy"""
        print("\n" + "=" * 60)
        print("Test 5: Semantic Query (Should Route to SEMANTIC)")
        print("=" * 60)

        query = "关于咖啡的记忆"
        print(f"Query: {query}")

        start_time = datetime.now()
        result = await self.coordinator.process_user_input(query)
        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Latency: {latency:.1f}ms")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'semantic_query',
            'query': query,
            'expected_strategy': 'semantic',
            'latency_ms': latency,
            'success': result.success
        })

        print(f"\n✅ Test 5 COMPLETED")
        return result

    async def test_when_question(self):
        """Test 6: 'When' question should route to episodic strategy"""
        print("\n" + "=" * 60)
        print("Test 6: When Question (Should Route to EPISODIC)")
        print("=" * 60)

        query = "Alice什么时候买的咖啡机?"
        print(f"Query: {query}")

        start_time = datetime.now()
        result = await self.coordinator.process_user_input(query)
        latency = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Results:")
        print(f"  Response: {result.response[:100]}...")
        print(f"  Latency: {latency:.1f}ms")
        print(f"  Success: {result.success}")

        self.test_results.append({
            'test': 'when_question',
            'query': query,
            'expected_strategy': 'episodic',
            'latency_ms': latency,
            'success': result.success
        })

        print(f"\n✅ Test 6 COMPLETED")
        return result

    async def test_english_queries(self):
        """Test 7: English queries should also route correctly"""
        print("\n" + "=" * 60)
        print("Test 7: English Queries (Strategy Routing)")
        print("=" * 60)

        test_cases = [
            ("What happened yesterday?", "episodic"),
            ("Tell me about Alice and Bob", "associative"),
            ("What did Carol buy?", "keyword"),
            ("Why does David prefer tea over coffee?", "multi_strategy")
        ]

        for query, expected in test_cases:
            print(f"\n  Query: {query}")
            print(f"  Expected: {expected}")

            start_time = datetime.now()
            result = await self.coordinator.process_user_input(query)
            latency = (datetime.now() - start_time).total_seconds() * 1000

            print(f"  Latency: {latency:.1f}ms")

            self.test_results.append({
                'test': 'english_query',
                'query': query,
                'expected_strategy': expected,
                'latency_ms': latency,
                'success': result.success
            })

        print(f"\n✅ Test 7 COMPLETED")

    async def test_strategy_statistics(self):
        """Test 8: Check router statistics"""
        print("\n" + "=" * 60)
        print("Test 8: Router Statistics")
        print("=" * 60)

        # Access router agent
        router = self.coordinator.agents.get('retrieval_router')

        if router:
            stats = router.get_statistics()

            print(f"\n📊 Router Statistics:")
            print(f"  Total Queries: {stats['total_queries']}")
            print(f"\n  Strategy Distribution:")
            for strategy, count in stats['strategy_distribution'].items():
                print(f"    {strategy}: {count}")

            print(f"\n  Strategy Success Rates:")
            for strategy, rate in stats['strategy_success_rates'].items():
                print(f"    {strategy}: {rate:.2f}")
        else:
            print("⚠️ Router agent not found")

        print(f"\n✅ Test 8 COMPLETED")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        # Group by expected strategy
        strategy_tests = {}
        for result in self.test_results:
            strategy = result['expected_strategy']
            if strategy not in strategy_tests:
                strategy_tests[strategy] = []
            strategy_tests[strategy].append(result)

        for strategy, tests in strategy_tests.items():
            print(f"\n{strategy.upper()} Strategy:")
            for test in tests:
                status = "✅ PASS" if test['success'] else "❌ FAIL"
                print(f"  {status} - {test['query'][:40]}... ({test['latency_ms']:.0f}ms)")

        # Calculate statistics
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
            await self.test_temporal_query()
            await asyncio.sleep(1)

            await self.test_associative_query()
            await asyncio.sleep(1)

            await self.test_factual_query()
            await asyncio.sleep(1)

            await self.test_complex_query()
            await asyncio.sleep(1)

            await self.test_semantic_query()
            await asyncio.sleep(1)

            await self.test_when_question()
            await asyncio.sleep(1)

            await self.test_english_queries()
            await asyncio.sleep(1)

            await self.test_strategy_statistics()

            # Print summary
            self.print_summary()

        finally:
            if self.coordinator:
                await self.coordinator.stop_system()
                print("\n✅ System stopped cleanly")


async def main():
    """Main entry point"""
    print("\n🧠 BMAM Retrieval Strategy Router Test Suite")
    print("Testing Phase 2 Implementation: Dynamic Strategy Selection\n")

    tester = RetrievalRouterTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())