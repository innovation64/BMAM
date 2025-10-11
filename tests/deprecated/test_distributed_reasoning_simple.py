#!/usr/bin/env python3
"""
简化测试: 验证分布式推理架构
"""
import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator

async def test_collaborative_reasoning():
    print("=" * 60)
    print("🧠 测试分布式推理架构")
    print("=" * 60)

    # 初始化coordinator
    print("\n1️⃣  初始化BrainCoordinator...")
    coordinator = BrainInspiredCoordinator()

    # 检查agents是否正确连接
    print(f"✅ Reasoning Validator reflection_agent: {coordinator.reasoning_validator.reflection_agent is not None}")
    print(f"✅ Reasoning Validator consolidation_agent: {coordinator.reasoning_validator.consolidation_agent is not None}")

    # 学习一些记忆
    print("\n2️⃣  学习记忆...")
    learning_events = [
        "On 8 May, 2023, Caroline attended an LGBTQ support group for the first time.",
        "Caroline found transgender stories very inspiring and emotional.",
        "On 25 May, 2023, Caroline researched adoption agencies."
    ]

    for event in learning_events:
        print(f"   📝 {event}")
        await coordinator.process_input(event)

    # 测试Q5: 身份推理 (需要Consolidation协作)
    print("\n3️⃣  测试Q5 - 身份推理 (Consolidation协作)...")
    response = await coordinator.process_input("What is Caroline's identity?")
    print(f"   🤖 回答: {response}")

    # 测试Q3: 多跳推理 (需要Reflection协作)
    print("\n4️⃣  测试Q3 - 教育领域推理 (Reflection协作)...")
    response = await coordinator.process_input("What fields would Caroline be likely to pursue in her education?")
    print(f"   🤖 回答: {response}")

    print("\n" + "=" * 60)
    print("✅ 测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_collaborative_reasoning())
