"""
Quick Test for Memory Shaping Fixes
快速测试记忆塑造修复

验证:
1. Amygdala情绪标记修复
2. 定期反思机制
3. 后台巩固/遗忘进程
"""

import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def test_memory_shaping():
    """测试记忆塑造修复"""
    print("=" * 60)
    print("记忆塑造修复测试")
    print("=" * 60)

    # 初始化
    print("\n1️⃣ 初始化框架...")
    coordinator = BrainInspiredCoordinator()
    print("✅ 框架初始化完成")

    # 测试情绪标记 (有情绪关键词)
    print("\n2️⃣ 测试Amygdala情绪标记...")
    test_inputs = [
        "I'm so happy today! I won the lottery!",  # happy
        "I'm so sad, my friend passed away...",    # sad
        "I'm stressed about the deadline",          # stress
        "Normal conversation without emotion"       # no emotion
    ]

    for i, text in enumerate(test_inputs):
        print(f"\n   测试 {i+1}: {text[:50]}...")
        try:
            response = await coordinator.process_input(text)
            print(f"   ✅ 处理成功")
        except Exception as e:
            print(f"   ❌ 错误: {e}")

    # 检查Amygdala状态
    print(f"\n3️⃣ 检查Amygdala记忆...")
    if hasattr(coordinator, 'amygdala'):
        emotion_count = len(coordinator.amygdala.memories)
        print(f"   Amygdala: {emotion_count} 条情绪记忆")
        if emotion_count > 0:
            print(f"   ✅ 情绪标记工作正常！")
            for mem in coordinator.amygdala.memories[:3]:
                print(f"      - {mem.emotion_tags} (强度={mem.emotion_intensity:.2f})")
        else:
            print(f"   ⚠️  没有情绪记忆 (可能关键词匹配失败)")

    # 测试反思机制 (第10次对话应触发)
    print(f"\n4️⃣ 测试定期反思机制 (需要10次对话)...")
    print(f"   当前对话计数: {getattr(coordinator, '_conversation_count', 0)}")

    # 补充对话到10次
    remaining = 10 - getattr(coordinator, '_conversation_count', 0)
    if remaining > 0:
        print(f"   补充 {remaining} 次对话以触发反思...")
        for i in range(remaining):
            await coordinator.process_input(f"Test conversation {i+1}")
        print(f"   ✅ 已达到10次对话，反思应该触发")

    # 检查后台进程状态
    print(f"\n5️⃣ 检查后台巩固/遗忘进程...")
    if hasattr(coordinator, 'background_processes'):
        bg = coordinator.background_processes
        print(f"   配置:")
        print(f"      - Enabled: {bg.config.enabled}")
        print(f"      - Running: {bg.running}")
        print(f"      - 巩固间隔: {bg.config.consolidation_interval_seconds}秒")
        print(f"      - 遗忘间隔: {bg.config.forgetting_interval_seconds}秒")
        if bg.running:
            print(f"   ✅ 后台进程运行中!")
        else:
            print(f"   ⚠️  后台进程未运行")
    else:
        print(f"   ❌ 后台进程未初始化")

    # 总结
    print(f"\n" + "=" * 60)
    print("测试总结:")
    print("=" * 60)

    print(f"\n✅ 修复验证:")
    print(f"   1. Amygdala修复: {'✅ 成功' if emotion_count > 0 else '⚠️ 需检查'}")
    print(f"   2. 反思机制: {'✅ 已添加' if hasattr(coordinator, '_conversation_count') else '❌ 未添加'}")
    print(f"   3. 后台进程: {'✅ 已启用' if hasattr(coordinator, 'background_processes') and coordinator.background_processes.running else '⚠️ 未运行'}")

    # 显示五脑区状态
    print(f"\n📊 五脑区记忆分布:")
    if hasattr(coordinator, 'hippocampus'):
        print(f"   Hippocampus: {len(coordinator.hippocampus.memories)} 条")
    if hasattr(coordinator, 'temporal_lobe'):
        print(f"   Temporal Lobe: {len(coordinator.temporal_lobe.memories)} 条")
    if hasattr(coordinator, 'amygdala'):
        print(f"   Amygdala: {len(coordinator.amygdala.memories)} 条")
    if hasattr(coordinator, 'prefrontal_agent'):
        wm_count = len(coordinator.prefrontal_agent.working_memory) if hasattr(coordinator.prefrontal_agent, 'working_memory') else 0
        print(f"   Prefrontal: {wm_count} 条")
    if hasattr(coordinator, 'basal_ganglia'):
        print(f"   Basal Ganglia: {len(coordinator.basal_ganglia.skills)} 个技能")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_memory_shaping())
