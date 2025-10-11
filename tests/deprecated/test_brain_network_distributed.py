"""
测试BrainNetwork + 分布式记忆系统
验证完整的类脑架构
"""

import asyncio
import sys
import os

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

os.environ['USE_BRAIN_NETWORK'] = 'true'

from src.coordination.brain_coordinator import BrainInspiredCoordinator


async def test_brain_network_with_distributed_memory():
    print("=" * 80)
    print("🧠 测试BrainNetwork + 分布式记忆系统")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    print("\n📚 Phase 1: 学习Caroline的故事 (存储到分布式记忆)")
    print("-" * 80)

    # Session 1: 2023-05-08
    learning_inputs = [
        "On 8 May 2023, Caroline attended an LGBTQ support group for the first time. She heard transgender stories that were inspiring.",
        "Caroline is a transgender woman interested in social justice and psychology.",
        "Caroline researched social work programs and community advocacy."
    ]

    for i, text in enumerate(learning_inputs, 1):
        print(f"\n  学习 {i}/{len(learning_inputs)}: {text[:60]}...")
        result = await coordinator.process_user_input(text)
        print(f"  ✅ 响应: {result.response[:50]}...")
        print(f"  💾 Memory stored: {result.memory_stored}")

    # 检查分布式记忆统计
    dm = coordinator.brain_network.distributed_memory
    stats = dm.get_statistics()
    print(f"\n📊 记忆统计:")
    print(f"  总记忆数: {stats['total_memories']}")
    print(f"  Hippocampus (episodic): {stats['regions']['hippocampus']['size']}")
    print(f"  Temporal (semantic): {stats['regions']['temporal']['size']}")
    print(f"  Prefrontal (working): {stats['regions']['prefrontal']['size']}")

    print("\n❓ Phase 2: 测试问答 (从分布式记忆检索)")
    print("-" * 80)

    questions = [
        ("What is Caroline's identity?", "transgender woman"),
        ("What did Caroline research?", "social work"),
        ("When did Caroline go to the LGBTQ support group?", "8 May 2023")
    ]

    for i, (question, expected) in enumerate(questions, 1):
        print(f"\n  Q{i}: {question}")
        result = await coordinator.process_user_input(question)
        print(f"  🤖 Answer: {result.response}")
        print(f"  🔍 Memories retrieved: {len(result.memories_retrieved)}")
        print(f"  ⏱️  Time: {result.processing_time:.2f}s")
        print(f"  🎯 Converged: {result.routing_decision.get('converged', False)}")

        # 显示检索到的记忆来源
        if result.memories_retrieved:
            regions = set(m.get('region', 'unknown') for m in result.memories_retrieved)
            print(f"  🧠 Memory regions: {', '.join(regions)}")

    print("\n" + "=" * 80)
    print("✅ 测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_brain_network_with_distributed_memory())
