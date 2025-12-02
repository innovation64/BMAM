"""
测试KG开关在实际对话中是否工作
"""

import asyncio
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def test_kg_switch():
    """测试KG开关"""

    print("=" * 60)
    print("测试 KG 开关功能")
    print("=" * 60)

    # Initialize coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 测试1: 关闭KG增强检索
    print("\n📊 测试1: KG增强检索 = False")
    context1 = {
        'kg_enhanced_search': False
    }
    result1 = await coordinator.process_user_input("你好", context1)
    print(f"  成功: {result1.success}")
    print(f"  记忆数: {len(result1.memories_retrieved)}")
    print(f"  响应长度: {len(result1.response)}")

    # 测试2: 开启KG增强检索
    print("\n📊 测试2: KG增强检索 = True")
    context2 = {
        'kg_enhanced_search': True
    }
    result2 = await coordinator.process_user_input("你好", context2)
    print(f"  成功: {result2.success}")
    print(f"  记忆数: {len(result2.memories_retrieved)}")
    print(f"  响应长度: {len(result2.response)}")

    print("\n" + "=" * 60)
    if result1.success and result2.success:
        print("✅ KG开关测试全部通过!")
    else:
        print("❌ 部分测试失败")
        if not result1.success:
            print(f"  测试1失败: {result1.error}")
        if not result2.success:
            print(f"  测试2失败: {result2.error}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_kg_switch())