"""
Debug LoCoMo Answer Generation Issue
检查为什么返回 "transgender woman" 而不是日期
"""

import asyncio
import json
from src.coordination.brain_coordinator import BrainInspiredCoordinator


async def main():
    print("=" * 80)
    print("🔍 Debugging LoCoMo Answer Issue")
    print("=" * 80)
    print()

    # 初始化
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 学习测试记忆
    test_memories = [
        "On 8 May 2023, Caroline said: 'I went to a LGBTQ support group yesterday. The transgender stories were so inspiring!'",
        "Caroline is a transgender woman.",
    ]

    print("📚 Phase 1: Learning memories")
    print("-" * 80)
    for i, memory in enumerate(test_memories, 1):
        print(f"{i}. {memory}")
        result = await coordinator.process_user_input(memory, {})
        # 不打印响应,只学习
    print("\n✅ Memories learned\n")

    # 测试问题
    test_question = "When did Caroline go to the LGBTQ support group?"
    print(f"❓ Question: {test_question}")
    print("-" * 80)

    # 测试 (带详细日志)
    result = await coordinator.process_user_input(
        test_question,
        {'benchmark_mode': True, 'force_english': True}
    )

    print(f"\n📋 Result:")
    print(f"  Response: {result.response}")
    print(f"  Memories retrieved: {len(result.memories_retrieved)}")
    print(f"  Success: {result.success}")
    print()

    # 打印检索到的记忆
    if result.memories_retrieved:
        print("🔍 Retrieved Memories:")
        for i, mem in enumerate(result.memories_retrieved[:3], 1):
            content = mem.get('memory', {}).get('content', str(mem))
            print(f"  {i}. {content[:150]}...")
    else:
        print("⚠️  No memories retrieved!")

    # 检查agent日志
    if result.agent_logs:
        print("\n📝 Agent Logs:")
        for agent_id, logs in result.agent_logs.items():
            if logs and agent_id == 'conversation':
                print(f"  {agent_id}:")
                for log in logs[-2:]:  # Last 2 logs
                    print(f"    - {log}")

    await coordinator.stop_system()

    print("\n" + "=" * 80)
    print("Debug complete!")


if __name__ == "__main__":
    asyncio.run(main())
