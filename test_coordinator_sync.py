#!/usr/bin/env python3
"""
同步测试：验证BrainInspiredCoordinator能否成功初始化（不使用asyncio.run）
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_coordinator_init():
    """测试coordinator初始化（同步版本）"""
    print("=" * 60)
    print("  同步测试 BrainInspiredCoordinator 初始化")
    print("=" * 60)

    try:
        print("\n🔧 导入 BrainInspiredCoordinator...")
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
        print("✅ 导入成功")

        print("\n🔧 初始化 BrainInspiredCoordinator...")
        coordinator = BrainInspiredCoordinator()
        print("✅ 初始化成功！")

        print("\n📊 Coordinator 信息:")
        agent_count = len([a for a in dir(coordinator) if a.endswith('_agent') or a in ['personality', 'reflection', 'consolidation']])
        print(f"   - 智能体数量: {agent_count}")

        # 检查关键组件
        print(f"   - PersonalityAgent: {'✅' if hasattr(coordinator, 'personality') else '❌'}")
        print(f"   - MemoryRetrieval: {'✅' if hasattr(coordinator, 'memory_retrieval') else '❌'}")
        print(f"   - BrainNetwork: {'✅' if hasattr(coordinator, 'brain_network') else '❌'}")
        print(f"   - LearningManager: {'✅' if hasattr(coordinator, 'learning_manager') else '❌'}")

        return True

    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_coordinator_init()
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试成功")
        sys.exit(0)
    else:
        print("❌ 测试失败")
        sys.exit(1)
