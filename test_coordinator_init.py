#!/usr/bin/env python3
"""
简单测试：验证BrainInspiredCoordinator能否成功初始化
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_coordinator_init():
    """测试coordinator初始化"""
    print("=" * 60)
    print("  测试 BrainInspiredCoordinator 初始化")
    print("=" * 60)

    try:
        print("\n🔧 导入 BrainInspiredCoordinator...")
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
        print("✅ 导入成功")

        print("\n🔧 初始化 BrainInspiredCoordinator...")
        coordinator = BrainInspiredCoordinator()
        print("✅ 初始化成功！")

        print("\n📊 Coordinator 信息:")
        print(f"   - 智能体数量: {len([a for a in dir(coordinator) if a.endswith('_agent') or a in ['personality', 'reflection', 'consolidation']])}")

        return True

    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_coordinator_init())
    sys.exit(0 if success else 1)
