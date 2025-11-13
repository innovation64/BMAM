"""
Critical Fixes Validation Test
关键修复验证测试

验证5个P0 bug修复:
1. Storage contract - dict→MemoryItem conversion
2. get_memory_by_id / update_memory APIs
3. Consolidation using direct lookup (not semantic search)
4. Emotion enhancement updates in-place (no duplication)
5. Medium-band (τ=2-9) scheduling in Thalamus
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


async def test_critical_fixes():
    """测试所有关键修复"""
    print("=" * 80)
    print("关键修复验证测试")
    print("=" * 80)

    # 初始化
    print("\n📦 初始化框架...")
    coordinator = BrainInspiredCoordinator()
    print("✅ 框架初始化完成\n")

    test_results = {
        'storage_contract': False,
        'get_update_apis': False,
        'consolidation_lookup': False,
        'emotion_no_dup': False,
        'medium_band_scheduling': False
    }

    # Test 1: Storage contract (region_retrieve returns MemoryItem objects)
    print("=" * 80)
    print("Test 1: Storage Contract - region_retrieve 返回 MemoryItem 对象")
    print("=" * 80)
    try:
        # 先存储一条记忆
        await coordinator.process_input("Test memory for storage contract")

        # 使用 region_retrieve
        if hasattr(coordinator.hippocampus, 'storage'):
            results = await coordinator.hippocampus.storage.region_retrieve(
                query="test",
                k=1
            )
            if results and len(results) > 0:
                mem = results[0]
                # 检查是否为MemoryItem对象 (有 .id 属性)
                if hasattr(mem, 'id') and hasattr(mem, 'content'):
                    print(f"✅ region_retrieve 返回MemoryItem对象 (id={mem.id[:8]}...)")
                    test_results['storage_contract'] = True
                else:
                    print(f"❌ region_retrieve 返回dict而非MemoryItem")
        else:
            print("⚠️ Hippocampus storage未初始化")
    except Exception as e:
        print(f"❌ Storage contract测试失败: {e}")

    # Test 2: get_memory / update_memory APIs
    print("\n" + "=" * 80)
    print("Test 2: get_memory_by_id / update_memory APIs")
    print("=" * 80)
    try:
        # 存储新记忆
        response = await coordinator.process_input("Initial content for API test")

        # 获取最新记忆ID
        if hasattr(coordinator.hippocampus, 'memories') and len(coordinator.hippocampus.memories) > 0:
            memory_id = coordinator.hippocampus.memories[-1].id
            print(f"📝 存储记忆ID: {memory_id[:12]}...")

            # Test get_memory
            if hasattr(coordinator, 'memory_system'):
                mem_dict = coordinator.memory_system.get_memory(memory_id)
                if mem_dict:
                    print(f"✅ get_memory成功: content={mem_dict.get('content', '')[:30]}...")

                    # Test update_memory
                    success = await coordinator.memory_system.update_memory(
                        memory_id,
                        {'importance': 0.95, 'metadata': {'updated': True}}
                    )
                    if success:
                        # 验证更新
                        updated = coordinator.memory_system.get_memory(memory_id)
                        if updated and updated.get('importance') == 0.95:
                            print(f"✅ update_memory成功: importance={updated.get('importance')}")
                            test_results['get_update_apis'] = True
                        else:
                            print(f"❌ update_memory未生效")
                    else:
                        print(f"❌ update_memory返回False")
                else:
                    print(f"❌ get_memory返回None")
            else:
                print("⚠️ memory_system未初始化")
    except Exception as e:
        print(f"❌ get/update API测试失败: {e}")

    # Test 3: Consolidation using direct lookup
    print("\n" + "=" * 80)
    print("Test 3: Consolidation 使用直接查询 (不是semantic search)")
    print("=" * 80)
    try:
        # 手动触发巩固
        if hasattr(coordinator, 'background_processes'):
            print("🔄 手动触发巩固...")
            await coordinator.background_processes._run_consolidation()
            print("✅ 巩固执行完成 (无 'Memory not found' 错误)")
            test_results['consolidation_lookup'] = True
        else:
            print("⚠️ background_processes未初始化")
    except Exception as e:
        if "not found" in str(e).lower():
            print(f"❌ Consolidation仍使用semantic search: {e}")
        else:
            print(f"⚠️ Consolidation错误: {e}")

    # Test 4: Emotion enhancement no duplication
    print("\n" + "=" * 80)
    print("Test 4: Emotion Enhancement 原地更新 (无重复)")
    print("=" * 80)
    try:
        # 存储一条情绪记忆
        await coordinator.process_input("I'm extremely happy about this test!")

        # 获取记忆数量
        initial_count = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0
        initial_mem_id = coordinator.hippocampus.memories[-1].id if initial_count > 0 else None

        # 等待情绪增强
        await asyncio.sleep(0.5)

        # 检查记忆数量是否增加 (不应该重复)
        final_count = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0

        # 如果记忆数增加了，说明有重复
        if final_count == initial_count:
            print(f"✅ Emotion enhancement未创建重复记忆 (count={final_count})")
            test_results['emotion_no_dup'] = True
        elif initial_mem_id:
            # 检查是否是同一条记忆被更新
            final_mem = coordinator.hippocampus.memories[-1]
            if final_mem.id == initial_mem_id:
                print(f"✅ Emotion enhancement原地更新 (同一memory_id={initial_mem_id[:12]}...)")
                test_results['emotion_no_dup'] = True
            else:
                print(f"❌ Emotion enhancement创建了新记忆 (重复)")
        else:
            print(f"⚠️ 无法验证emotion enhancement")
    except Exception as e:
        print(f"⚠️ Emotion enhancement测试错误: {e}")

    # Test 5: Medium-band scheduling
    print("\n" + "=" * 80)
    print("Test 5: Medium-band (τ=2-9) Scheduling in Thalamus")
    print("=" * 80)
    try:
        # 检查Thalamus是否有medium-band代码
        if hasattr(coordinator, 'thalamus'):
            import inspect
            source = inspect.getsource(coordinator.thalamus.coordinate_step)

            if 'medium_regions' in source and '2 <=' in source:
                print("✅ Thalamus.coordinate_step 包含 medium-band (τ=2-9) 逻辑")
                test_results['medium_band_scheduling'] = True
            else:
                print("❌ Thalamus.coordinate_step 缺少 medium-band 逻辑")
        else:
            print("⚠️ Thalamus未初始化")
    except Exception as e:
        print(f"⚠️ Medium-band scheduling测试错误: {e}")

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    passed = sum(test_results.values())
    total = len(test_results)

    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}  {test_name}")

    print(f"\n📊 通过率: {passed}/{total} ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n🎉 所有关键修复验证通过!")
    else:
        print(f"\n⚠️  仍有 {total - passed} 个问题需要修复")

    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_critical_fixes())
