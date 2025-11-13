"""
DB Persistence Diagnostic
DB持久化诊断

检查:
1. memory_system是否初始化
2. DB文件路径
3. store_memory是否写入DB
4. get_memory是否能读取
"""

import asyncio
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def diagnose_db():
    print("=" * 80)
    print("DB持久化诊断")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    print("\n✅ Coordinator初始化完成\n")

    # Check 1: memory_system存在性
    print("=" * 80)
    print("Check 1: memory_system存在性")
    print("=" * 80)

    has_memory_system = hasattr(coordinator, 'memory_system') and coordinator.memory_system
    print(f"coordinator.memory_system: {has_memory_system}")

    if has_memory_system:
        print(f"  Type: {type(coordinator.memory_system).__name__}")
        print(f"  Has db_manager: {hasattr(coordinator.memory_system, 'db_manager')}")
        print(f"  Has vector_db: {hasattr(coordinator.memory_system, 'vector_db')}")

        if hasattr(coordinator.memory_system, 'db_manager'):
            db_mgr = coordinator.memory_system.db_manager
            print(f"  DB path: {getattr(db_mgr, 'db_path', 'N/A')}")

            # Check if DB file exists
            db_path = getattr(db_mgr, 'db_path', None)
            if db_path:
                exists = Path(db_path).exists()
                size = Path(db_path).stat().st_size if exists else 0
                print(f"  DB file exists: {exists}")
                print(f"  DB file size: {size} bytes")
    else:
        print("  ❌ memory_system未初始化")

    # Check 2: 存储一条新记忆
    print("\n" + "=" * 80)
    print("Check 2: 存储新记忆并验证DB写入")
    print("=" * 80)

    test_content = "DB persistence diagnostic test memory"
    print(f"📝 存储测试记忆: {test_content}")

    # Store via coordinator
    response = await coordinator.process_input(test_content)

    # Get the memory ID from hippocampus
    if hasattr(coordinator, 'hippocampus') and hasattr(coordinator.hippocampus, 'memories'):
        if len(coordinator.hippocampus.memories) > 0:
            latest_mem = coordinator.hippocampus.memories[-1]
            memory_id = latest_mem.id
            print(f"✅ 存储成功，memory_id: {memory_id[:16]}...")

            # Check 3: 通过memory_system.get_memory读取
            print("\n" + "=" * 80)
            print("Check 3: 通过memory_system.get_memory读取")
            print("=" * 80)

            if has_memory_system:
                mem_dict = coordinator.memory_system.get_memory(memory_id)
                if mem_dict:
                    print(f"✅ get_memory成功")
                    print(f"  ID: {mem_dict.get('id', 'N/A')[:16]}...")
                    print(f"  Content: {mem_dict.get('content', '')[:50]}...")
                    print(f"  Memory type: {mem_dict.get('memory_type', 'N/A')}")
                else:
                    print(f"❌ get_memory返回None")

                    # 诊断: 检查DB是否真的写入了
                    print("\n🔍 诊断: 检查DB manager状态")
                    if hasattr(coordinator.memory_system, 'db_manager'):
                        db_mgr = coordinator.memory_system.db_manager

                        # Try to load directly from DB
                        mem_obj = db_mgr.load_memory(memory_id)
                        if mem_obj:
                            print(f"  ✅ DB有此记忆 (db_manager.load_memory成功)")
                            print(f"  Content: {getattr(mem_obj, 'content', '')[:50]}...")
                        else:
                            print(f"  ❌ DB没有此记忆 (db_manager.load_memory返回None)")

                        # Check total memory count in DB
                        try:
                            from sqlalchemy import func
                            if hasattr(db_mgr, 'session'):
                                from src.memory.memory_system.database_manager import Memory as DBMemory
                                count = db_mgr.session.query(func.count(DBMemory.id)).scalar()
                                print(f"  DB总记忆数: {count}")
                        except Exception as e:
                            print(f"  ⚠️ 无法查询DB总数: {e}")
            else:
                print("  ⚠️ memory_system未初始化，跳过")

            # Check 4: 通过hippocampus.retrieve_memory_by_id读取
            print("\n" + "=" * 80)
            print("Check 4: 通过hippocampus.retrieve_memory_by_id读取")
            print("=" * 80)

            if hasattr(coordinator.hippocampus, 'retrieve_memory_by_id'):
                mem_dict2 = await coordinator.hippocampus.retrieve_memory_by_id(memory_id)
                if mem_dict2:
                    print(f"✅ retrieve_memory_by_id成功")
                    print(f"  Content: {mem_dict2.get('content', '')[:50]}...")
                else:
                    print(f"❌ retrieve_memory_by_id返回None")
            else:
                print("  ⚠️ hippocampus没有retrieve_memory_by_id方法")

            # Check 5: 检查memory_dict
            print("\n" + "=" * 80)
            print("Check 5: 检查hippocampus.memory_dict")
            print("=" * 80)

            if hasattr(coordinator.hippocampus, 'memory_dict'):
                in_dict = memory_id in coordinator.hippocampus.memory_dict
                print(f"memory_id在memory_dict中: {in_dict}")
                print(f"memory_dict大小: {len(coordinator.hippocampus.memory_dict)}")
                print(f"memories列表大小: {len(coordinator.hippocampus.memories)}")
            else:
                print("  ⚠️ hippocampus没有memory_dict")
        else:
            print("❌ hippocampus.memories为空")
    else:
        print("❌ hippocampus未初始化或没有memories属性")

    # Summary
    print("\n" + "=" * 80)
    print("诊断总结")
    print("=" * 80)
    print("""
    如果get_memory返回None，可能原因:
    1. memory_system未连接到实际DB
    2. store_memory未真正写入DB (只写了内存)
    3. DB manager配置错误
    4. DB文件路径不匹配
    """)
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose_db())
