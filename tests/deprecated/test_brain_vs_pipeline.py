"""
对比测试: BrainNetwork vs Pipeline
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator

async def test_mode(mode_name, use_brain_network):
    """Test a specific mode"""
    os.environ['USE_BRAIN_NETWORK'] = 'true' if use_brain_network else 'false'

    print(f"\n{'='*80}")
    print(f"Testing: {mode_name}")
    print(f"{'='*80}\n")

    coordinator = BrainInspiredCoordinator()

    test_queries = [
        "Hello, how are you?",
        "What is your favorite color?",
        "Tell me about yourself"
    ]

    total_time = 0
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query}")
        start = time.time()
        result = await coordinator.process_user_input(query)
        elapsed = time.time() - start
        total_time += elapsed

        print(f"Response: {result.response[:100]}...")
        print(f"Time: {elapsed:.2f}s")
        print(f"Agents: {len(result.agents_involved)}")

    avg_time = total_time / len(test_queries)
    print(f"\n{'='*80}")
    print(f"{mode_name} Summary:")
    print(f"Total time: {total_time:.2f}s")
    print(f"Average time: {avg_time:.2f}s")
    print(f"{'='*80}\n")

    return {
        'mode': mode_name,
        'total_time': total_time,
        'avg_time': avg_time
    }

async def main():
    print("\n" + "="*80)
    print("🧠 BrainNetwork vs Pipeline 对比测试")
    print("="*80)

    # Test 1: BrainNetwork
    brain_result = await test_mode("🧠 BrainNetwork (Parallel)", use_brain_network=True)

    # Test 2: Pipeline
    pipeline_result = await test_mode("⚙️  Pipeline (Sequential)", use_brain_network=False)

    # Summary
    print("\n" + "="*80)
    print("📊 性能对比总结")
    print("="*80)
    print(f"\nBrainNetwork平均: {brain_result['avg_time']:.2f}s")
    print(f"Pipeline平均: {pipeline_result['avg_time']:.2f}s")

    speedup = pipeline_result['avg_time'] / brain_result['avg_time']
    print(f"\n加速比: {speedup:.2f}x")

    if speedup > 1:
        print(f"✅ BrainNetwork快{speedup:.2f}倍!")
    else:
        print(f"⚠️  Pipeline反而更快")

if __name__ == "__main__":
    asyncio.run(main())
