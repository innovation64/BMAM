"""
Memory Transfer Example - 记忆迁移示例
Demonstrates cross-machine memory portability

场景:
- A电脑: 塑造记忆A (通过对话、学习)
- 导出: memory_A.bma
- B电脑: 导入memory_A.bma，继续学习，塑造新记忆
- 导出: memory_B.bma
- A电脑: 导入memory_B.bma，切换到B的记忆状态

核心理念: 每个记忆体是独一无二的灵魂，不可合并，只可迁移
"""

import asyncio
from pathlib import Path
import sys

# Add BMAM to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from BMAM.src.memory.memory_transfer import MemoryTransferSystem, TransferReport


async def scenario_machine_a_export():
    """
    场景1: A电脑 - 塑造记忆并导出

    A电脑上运行框架，通过对话和学习塑造了记忆A
    现在需要导出，以便在B电脑继续
    """
    print("=" * 60)
    print("场景1: A电脑 - 塑造记忆并导出")
    print("=" * 60)

    # 假设已经有coordinator实例（通过对话塑造了记忆）
    # coordinator = BrainInspiredCoordinator()
    # ... 进行了大量对话、学习 ...

    # 初始化迁移系统
    transfer_system = MemoryTransferSystem(coordinator=None)  # 实际使用时传入coordinator

    # 导出记忆
    print("\n📤 正在导出记忆...")
    report = await transfer_system.export_memory(
        output_dir=Path("exports/"),
        name="alice_memory_20251112",
        description="Alice在A电脑上塑造的记忆 - 关于AI、编程、生活的对话",
        tags=["alice", "programming", "AI"]
    )

    if report.success:
        print(f"\n✅ 导出成功!")
        print(f"   归档路径: {report.archive_path}")
        print(f"   总记忆数: {report.total_memories}")
        print(f"   脑区分布:")
        for region, count in report.memories_by_region.items():
            print(f"     - {region}: {count} 条记忆")
        print(f"\n💾 现在可以将 {report.archive_path} 传输到B电脑")
    else:
        print(f"\n❌ 导出失败:")
        for error in report.errors:
            print(f"   - {error}")

    return report


async def scenario_machine_b_import():
    """
    场景2: B电脑 - 导入A的记忆，继续学习

    将A电脑导出的 memory_A.bma 传输到B电脑
    导入后，框架将拥有A的完整记忆，可以继续学习
    """
    print("\n" + "=" * 60)
    print("场景2: B电脑 - 导入A的记忆")
    print("=" * 60)

    # B电脑上的全新环境
    transfer_system = MemoryTransferSystem(coordinator=None)

    # 导入A电脑的记忆
    print("\n📥 正在导入A电脑的记忆...")
    archive_path = Path("exports/alice_memory_20251112.bma")

    report = await transfer_system.import_memory(
        archive_path=archive_path,
        create_backup=True,  # 如果B电脑已有记忆，先备份
        validate_before_import=True
    )

    if report.success:
        print(f"\n✅ 导入成功!")
        print(f"   总记忆数: {report.total_memories}")
        print(f"   脑区分布:")
        for region, count in report.memories_by_region.items():
            print(f"     - {region}: {count} 条记忆")
        print(f"   关系验证: {report.relationships_validated} 条")

        if report.backup_path:
            print(f"\n💾 原有记忆已备份到: {report.backup_path}")

        print("\n🎯 现在B电脑拥有A的完整记忆，可以继续学习!")
        print("   框架将基于A的记忆继续巩固、重塑、遗忘...")
    else:
        print(f"\n❌ 导入失败:")
        for error in report.errors:
            print(f"   - {error}")

        if report.backup_path:
            print(f"\n🔄 已自动回滚到备份: {report.backup_path}")

    return report


async def scenario_machine_b_continue_learning():
    """
    场景3: B电脑 - 继续学习，塑造新记忆

    B电脑导入了A的记忆后，继续进行对话和学习
    记忆会通过巩固、重塑、遗忘机制继续演化
    """
    print("\n" + "=" * 60)
    print("场景3: B电脑 - 继续学习（基于A的记忆）")
    print("=" * 60)

    # 模拟B电脑上的学习过程
    print("\n📚 B电脑上的学习活动:")
    print("   - 对话: 讨论新的AI模型架构")
    print("   - 学习: 阅读最新论文")
    print("   - 思考: 反思之前的对话")
    print("")
    print("🧠 记忆塑造机制自动运行:")
    print("   ✓ 巩固: 将重要的情节记忆转为语义记忆")
    print("   ✓ 重塑: 根据新知识重组现有记忆")
    print("   ✓ 遗忘: 淘汰不重要的短期记忆")
    print("")
    print("💡 结果: 形成了B电脑独特的记忆状态")

    # 过了一段时间后，导出B的记忆
    transfer_system = MemoryTransferSystem(coordinator=None)

    print("\n📤 导出B电脑塑造的记忆...")
    report = await transfer_system.export_memory(
        output_dir=Path("exports/"),
        name="alice_memory_b_20251113",
        description="Alice在B电脑继续学习后的记忆 - 包含新的AI知识",
        tags=["alice", "AI", "advanced"]
    )

    if report.success:
        print(f"\n✅ B电脑的记忆导出成功!")
        print(f"   归档路径: {report.archive_path}")
        print(f"   总记忆数: {report.total_memories}")
        print(f"\n💾 现在可以将此记忆传回A电脑，或用于其他用途")

    return report


async def scenario_machine_a_switch_to_b_memory():
    """
    场景4: A电脑 - 切换到B的记忆

    将B电脑的 memory_B.bma 传回A电脑
    A电脑导入后，将拥有B的记忆状态
    """
    print("\n" + "=" * 60)
    print("场景4: A电脑 - 切换到B的记忆")
    print("=" * 60)

    # A电脑导入B的记忆
    transfer_system = MemoryTransferSystem(coordinator=None)

    print("\n📥 A电脑导入B的记忆...")
    archive_path = Path("exports/alice_memory_b_20251113.bma")

    report = await transfer_system.import_memory(
        archive_path=archive_path,
        create_backup=True,  # 先备份A当前的记忆
        validate_before_import=True
    )

    if report.success:
        print(f"\n✅ 切换成功!")
        print(f"   A电脑现在拥有B电脑的记忆状态")
        print(f"   包含B电脑学到的所有新知识")

        if report.backup_path:
            print(f"\n💾 A电脑原有记忆已备份到: {report.backup_path}")
            print(f"   如需恢复，可以重新导入该备份")

        print("\n🎯 A电脑可以基于B的记忆继续学习!")
    else:
        print(f"\n❌ 切换失败:")
        for error in report.errors:
            print(f"   - {error}")

    return report


async def main():
    """
    完整流程演示
    """
    print("╔" + "=" * 58 + "╗")
    print("║  记忆迁移完整流程演示 - Memory Transfer Full Demo        ║")
    print("╚" + "=" * 58 + "╝")

    # 场景1: A电脑导出
    await scenario_machine_a_export()

    # 场景2: B电脑导入
    await scenario_machine_b_import()

    # 场景3: B电脑继续学习
    await scenario_machine_b_continue_learning()

    # 场景4: A电脑切换到B的记忆
    await scenario_machine_a_switch_to_b_memory()

    print("\n" + "=" * 60)
    print("总结:")
    print("=" * 60)
    print("✅ 记忆可以在不同电脑间完整迁移")
    print("✅ 每个记忆体是独立的'灵魂'，不存在合并")
    print("✅ 导入后可以无缝继续学习和记忆塑造")
    print("✅ 支持备份和恢复机制")
    print("\n核心理念: 记忆是完整的个体，通过巩固、重塑、遗忘")
    print("         主动塑造，不可合并，只可迁移和切换。")
    print("=" * 60)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
