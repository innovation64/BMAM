#!/usr/bin/env python3
"""
调试版本：详细追踪coordinator初始化的每一步
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_coordinator_init_debug():
    """逐步测试coordinator初始化"""
    print("=" * 60)
    print("  详细调试 BrainInspiredCoordinator 初始化")
    print("=" * 60)

    try:
        print("\n[1/10] 导入BrainInspiredCoordinator...")
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
        print("✅ 导入成功")

        print("\n[2/10] 创建coordinator实例...")
        print("    (这会触发__init__方法)")

        # 使用猴子补丁来追踪初始化过程
        original_init = BrainInspiredCoordinator.__init__

        def traced_init(self):
            print("    [2.1] 进入__init__")
            print("    [2.2] 设置配置...")
            # 调用原始__init__，但我们需要手动追踪
            # 由于无法直接插入，我们只能观察外部行为
            original_init(self)
            print("    [2.10] __init__完成！")

        # 不使用猴子补丁，直接创建并观察
        print("    开始创建...")
        coordinator = BrainInspiredCoordinator()
        print("✅ Coordinator初始化完成！")

        print("\n[3/10] 检查coordinator属性...")
        agent_count = len([a for a in dir(coordinator) if a.endswith('_agent') or a in ['personality', 'reflection', 'consolidation']])
        print(f"✅ 发现 {agent_count} 个agent相关属性")

        return True

    except Exception as e:
        print(f"\n❌ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_coordinator_init_debug()
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试成功")
        sys.exit(0)
    else:
        print("❌ 测试失败")
        sys.exit(1)
