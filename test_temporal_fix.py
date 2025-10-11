"""
快速测试时间推理修复
"""
import asyncio
from src.coordination.brain_coordinator import BrainInspiredCoordinator

async def main():
    print("🧪 Testing Temporal Reasoning Fix")
    print("=" * 60)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 学习记忆 (包含对话日期)
    memory = "On 8 May 2023, Caroline said: 'I went to a LGBTQ support group yesterday.'"
    print(f"\n📚 Learning: {memory}")
    await coordinator.process_user_input(memory, {})

    # 测试问题
    question = "When did Caroline go to the LGBTQ support group?"
    print(f"\n❓ Question: {question}")
    print("-" * 60)

    result = await coordinator.process_user_input(
        question,
        {'benchmark_mode': True, 'force_english': True}
    )

    print(f"\n✅ Answer: {result.response}")
    print(f"📊 Memories: {len(result.memories_retrieved)}")

    # 检查答案
    expected = "7 May 2023"
    if expected in result.response:
        print(f"\n🎉 SUCCESS! Got expected answer: {expected}")
    else:
        print(f"\n❌ FAILED! Expected '{expected}', got: {result.response}")

    await coordinator.stop_system()

if __name__ == "__main__":
    asyncio.run(main())
