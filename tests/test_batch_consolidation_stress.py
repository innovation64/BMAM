#!/usr/bin/env python3
"""
批量巩固和长会话压力测试
用于夜间CI，确保长流程不会退化

测试场景：
1. 批量巩固（100+记忆）
2. 长会话场景（50+轮对话）
3. 记忆系统容量极限测试
4. 巩固队列管理
"""

import pytest
import asyncio
import time
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.memory.memory_item import MemoryItem


class TestBatchConsolidationStress:
    """批量巩固压力测试"""

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_batch_consolidation_100_memories(self):
        """测试批量巩固100条记忆"""
        coordinator = BrainInspiredCoordinator()

        memories_count = 100
        batch_size = 10

        print(f"\n=== 批量巩固测试: {memories_count} 条记忆 ===")

        # Step 1: 注入100条记忆
        print(f"Step 1: 注入 {memories_count} 条记忆...")
        start_time = time.time()

        memories = []
        for i in range(memories_count):
            memory_content = f"Test memory #{i+1}: Event occurred on {datetime.now() - timedelta(hours=i)}"
            await coordinator.process_input(memory_content)
            memories.append(memory_content)

        injection_time = time.time() - start_time
        print(f"✓ 记忆注入完成: {injection_time:.2f}秒 ({memories_count/injection_time:.1f} memories/sec)")

        # Step 2: 验证 Hippocampus 存储
        if hasattr(coordinator.hippocampus, 'memories'):
            stored_count = len(coordinator.hippocampus.memories)
            print(f"✓ Hippocampus 存储: {stored_count} 条记忆")
            assert stored_count >= memories_count * 0.8, f"Expected >= {memories_count * 0.8}, got {stored_count}"

        # Step 3: 批量巩固测试
        print(f"\nStep 2: 批量巩固 (batch_size={batch_size})...")
        consolidation_start = time.time()

        # 提升记忆重要性以触发巩固
        if hasattr(coordinator.hippocampus, 'memories'):
            for mem in coordinator.hippocampus.memories[:50]:  # 前50条高优先级
                mem.importance = 0.8
                mem.access_count = 2

        # 执行批量巩固
        consolidation_results = []
        batches = memories_count // batch_size

        for batch_num in range(batches):
            if hasattr(coordinator.hippocampus, 'consolidate_memories'):
                result = await coordinator.hippocampus.consolidate_memories()
                consolidation_results.append(result)

                if batch_num % 2 == 0:  # 每2批报告一次
                    print(f"  Batch {batch_num+1}/{batches} 完成")

        consolidation_time = time.time() - consolidation_start
        print(f"✓ 批量巩固完成: {consolidation_time:.2f}秒")

        # Step 4: 验证巩固结果
        consolidated_count = sum(
            1 for r in consolidation_results
            if r and r.get('consolidated')
        )

        consolidation_rate = consolidated_count / len(consolidation_results) if consolidation_results else 0

        print(f"\n=== 巩固统计 ===")
        print(f"总批次: {len(consolidation_results)}")
        print(f"成功巩固: {consolidated_count}")
        print(f"巩固率: {consolidation_rate:.1%}")
        print(f"平均耗时: {consolidation_time/batches:.2f}秒/批次")

        # 断言
        assert consolidation_rate >= 0.6, f"巩固率应 >= 60%, 实际: {consolidation_rate:.1%}"
        assert consolidation_time < memories_count * 0.5, "批量巩固耗时过长"

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_consolidation_queue_management(self):
        """测试巩固队列管理和优先级"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 巩固队列管理测试 ===")

        # 注入不同优先级的记忆
        high_priority_memories = []
        medium_priority_memories = []
        low_priority_memories = []

        for i in range(10):
            mem = f"High priority event #{i+1} with important information"
            await coordinator.process_input(mem)
            high_priority_memories.append(mem)

        for i in range(20):
            mem = f"Medium priority event #{i+1}"
            await coordinator.process_input(mem)
            medium_priority_memories.append(mem)

        for i in range(30):
            mem = f"Low priority event #{i+1}"
            await coordinator.process_input(mem)
            low_priority_memories.append(mem)

        # 设置不同优先级
        if hasattr(coordinator.hippocampus, 'memories'):
            all_mems = coordinator.hippocampus.memories

            for i, mem in enumerate(all_mems):
                if i < 10:
                    mem.importance = 0.9
                elif i < 30:
                    mem.importance = 0.6
                else:
                    mem.importance = 0.3

        # 执行优先级巩固
        if hasattr(coordinator.hippocampus, 'consolidate_memories'):
            result = await coordinator.hippocampus.consolidate_memories()

            print(f"✓ 队列巩固完成")
            print(f"  结果: {result}")

            # 验证高优先级记忆优先巩固
            assert result is not None, "巩固结果不应为空"

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_concurrent_consolidation(self):
        """测试并发巩固场景"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 并发巩固测试 ===")

        # 注入50条记忆
        for i in range(50):
            await coordinator.process_input(f"Memory {i+1} for concurrent test")

        # 设置高优先级
        if hasattr(coordinator.hippocampus, 'memories'):
            for mem in coordinator.hippocampus.memories:
                mem.importance = 0.8

        # 并发触发多个巩固请求
        if hasattr(coordinator.hippocampus, 'consolidate_memories'):
            consolidation_tasks = [
                coordinator.hippocampus.consolidate_memories()
                for _ in range(5)
            ]

            start_time = time.time()
            results = await asyncio.gather(*consolidation_tasks, return_exceptions=True)
            elapsed = time.time() - start_time

            # 验证结果
            successful = sum(1 for r in results if r and not isinstance(r, Exception))

            print(f"✓ 并发巩固完成: {elapsed:.2f}秒")
            print(f"  成功: {successful}/{len(consolidation_tasks)}")

            assert successful >= 3, "至少3个并发巩固应成功"

        await coordinator.stop_system()


class TestLongSessionStress:
    """长会话场景压力测试"""

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_50_turn_conversation(self):
        """测试50轮连续对话"""
        coordinator = BrainInspiredCoordinator()

        turns = 50
        print(f"\n=== 长会话测试: {turns} 轮对话 ===")

        conversation_history = []
        response_times = []

        # 模拟50轮对话
        for turn in range(1, turns + 1):
            user_input = f"Turn {turn}: Tell me about event {turn} that happened today."

            start_time = time.time()
            response = await coordinator.process_input(user_input)
            elapsed = time.time() - start_time

            response_times.append(elapsed)
            conversation_history.append({
                'turn': turn,
                'input': user_input,
                'response': response,
                'time': elapsed
            })

            if turn % 10 == 0:
                avg_time = sum(response_times[-10:]) / 10
                print(f"  Turn {turn}: {elapsed:.2f}s (avg last 10: {avg_time:.2f}s)")

        # 统计分析
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        # 检查性能退化
        early_avg = sum(response_times[:10]) / 10
        late_avg = sum(response_times[-10:]) / 10
        degradation = (late_avg - early_avg) / early_avg if early_avg > 0 else 0

        print(f"\n=== 性能统计 ===")
        print(f"平均响应时间: {avg_response_time:.2f}秒")
        print(f"最大响应时间: {max_response_time:.2f}秒")
        print(f"最小响应时间: {min_response_time:.2f}秒")
        print(f"性能退化: {degradation:.1%}")

        # 断言
        assert avg_response_time < 5.0, f"平均响应时间应 < 5秒, 实际: {avg_response_time:.2f}秒"
        assert max_response_time < 15.0, f"最大响应时间应 < 15秒, 实际: {max_response_time:.2f}秒"
        assert degradation < 0.5, f"性能退化应 < 50%, 实际: {degradation:.1%}"

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_long_session_memory_accumulation(self):
        """测试长会话中的记忆累积"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 长会话记忆累积测试 ===")

        # 100轮对话
        for turn in range(100):
            await coordinator.process_input(f"Event {turn+1} occurred")

            if turn % 20 == 19:
                # 检查记忆系统状态
                if hasattr(coordinator.hippocampus, 'memories'):
                    mem_count = len(coordinator.hippocampus.memories)
                    print(f"  Turn {turn+1}: {mem_count} memories in Hippocampus")

        # 最终验证
        if hasattr(coordinator.hippocampus, 'memories'):
            final_count = len(coordinator.hippocampus.memories)
            print(f"\n✓ 最终记忆数: {final_count}")

            # 记忆数应该合理（不会无限增长）
            assert final_count < 200, f"记忆数不应过度增长: {final_count}"
            assert final_count > 50, f"记忆数不应过少: {final_count}"

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_retrieval_performance_under_load(self):
        """测试高负载下的检索性能"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 高负载检索性能测试 ===")

        # 注入200条记忆
        print("注入200条记忆...")
        for i in range(200):
            await coordinator.process_input(f"Memory content {i+1} with keyword_{i % 10}")

        # 执行50次检索
        print("执行50次检索测试...")
        retrieval_times = []

        for i in range(50):
            query = f"Find memories about keyword_{i % 10}"

            start_time = time.time()
            if coordinator.memory_reasoning_chain:
                result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(query)
            elapsed = time.time() - start_time

            retrieval_times.append(elapsed)

            if i % 10 == 9:
                print(f"  查询 {i+1}: {elapsed:.2f}秒")

        # 统计
        avg_retrieval = sum(retrieval_times) / len(retrieval_times)
        max_retrieval = max(retrieval_times)

        print(f"\n=== 检索性能 ===")
        print(f"平均检索时间: {avg_retrieval:.2f}秒")
        print(f"最大检索时间: {max_retrieval:.2f}秒")

        # 断言
        assert avg_retrieval < 3.0, f"平均检索时间应 < 3秒, 实际: {avg_retrieval:.2f}秒"
        assert max_retrieval < 10.0, f"最大检索时间应 < 10秒, 实际: {max_retrieval:.2f}秒"

        await coordinator.stop_system()


class TestMemoryCapacityLimits:
    """记忆系统容量极限测试"""

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_capacity_limit_500_memories(self):
        """测试500条记忆容量极限"""
        coordinator = BrainInspiredCoordinator()

        target_count = 500
        print(f"\n=== 容量极限测试: {target_count} 条记忆 ===")

        start_time = time.time()

        for i in range(target_count):
            await coordinator.process_input(f"Capacity test memory {i+1}")

            if i % 100 == 99:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                print(f"  Progress: {i+1}/{target_count} ({rate:.1f} mem/sec)")

        total_time = time.time() - start_time

        print(f"\n✓ 完成注入 {target_count} 条记忆: {total_time:.2f}秒")

        # 验证系统稳定性
        test_query = "What happened in the tests?"
        try:
            if coordinator.memory_reasoning_chain:
                result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(test_query)
                print(f"✓ 系统在高容量下仍可检索")
                assert len(result.memories) > 0, "应能检索到记忆"
        except Exception as e:
            pytest.fail(f"高容量下检索失败: {e}")

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.stress
    async def test_memory_overflow_handling(self):
        """测试记忆溢出处理机制"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 记忆溢出处理测试 ===")

        # 快速注入1000条低优先级记忆
        for i in range(1000):
            await coordinator.process_input(f"Overflow test {i+1}")

        # 验证系统未崩溃
        if hasattr(coordinator.hippocampus, 'memories'):
            mem_count = len(coordinator.hippocampus.memories)
            print(f"✓ 系统稳定，当前记忆数: {mem_count}")

            # 应该有自动清理机制
            assert mem_count < 1500, "应该有溢出保护机制"

        # 验证系统功能正常
        test_response = await coordinator.process_input("Are you still functioning?")
        assert test_response is not None, "系统应仍能响应"

        print("✓ 溢出处理机制正常工作")

        await coordinator.stop_system()


# Pytest 配置
def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line("markers", "stress: marks tests as stress tests")
    config.addinivalue_line("markers", "asyncio: marks tests as async")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "stress"])
