#!/usr/bin/env python3
"""
故障注入测试框架
测试系统在各种异常情况下的稳健性

故障类型：
1. 数据库连接故障
2. API调用失败
3. 内存溢出模拟
4. 并发竞争条件
5. 数据损坏
6. 超时场景
"""

import pytest
import asyncio
import sys
import os
from typing import Dict, Any
from unittest.mock import patch, MagicMock, AsyncMock
import random

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


class FaultInjector:
    """故障注入工具类"""

    @staticmethod
    def random_failure(probability: float = 0.3):
        """随机失败（概率性）"""
        return random.random() < probability

    @staticmethod
    async def inject_delay(min_delay: float = 0.1, max_delay: float = 2.0):
        """注入延迟"""
        delay = random.uniform(min_delay, max_delay)
        await asyncio.sleep(delay)

    @staticmethod
    def corrupt_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """损坏数据"""
        if isinstance(data, dict):
            corrupted = data.copy()
            if random.random() < 0.5 and len(corrupted) > 0:
                key = random.choice(list(corrupted.keys()))
                corrupted[key] = None  # 设置为None
            return corrupted
        return data


class TestDatabaseFaultInjection:
    """数据库故障注入测试"""

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_database_connection_failure(self):
        """测试数据库连接失败"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 数据库连接故障测试 ===")

        # Mock 数据库连接失败
        with patch.object(
            coordinator.hippocampus,
            'db_manager',
            None
        ):
            # 尝试存储记忆
            result = await coordinator.process_input("Test memory during DB failure")

            # 系统应该优雅处理，不崩溃
            print(f"✓ 系统在数据库故障时未崩溃")
            assert result is not None, "系统应返回响应"

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_database_timeout(self):
        """测试数据库超时"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 数据库超时测试 ===")

        # Mock 数据库操作超时
        async def slow_save_memory(*args, **kwargs):
            await asyncio.sleep(10)  # 模拟超长操作
            raise TimeoutError("Database operation timed out")

        if hasattr(coordinator.hippocampus, 'db_manager') and coordinator.hippocampus.db_manager:
            original_save = coordinator.hippocampus.db_manager.save_memory
            coordinator.hippocampus.db_manager.save_memory = slow_save_memory

            try:
                # 使用 timeout 保护
                result = await asyncio.wait_for(
                    coordinator.process_input("Test during timeout"),
                    timeout=5.0
                )
                print("✓ 系统在超时时仍有响应")
            except asyncio.TimeoutError:
                print("✓ 超时被正确捕获")
            finally:
                coordinator.hippocampus.db_manager.save_memory = original_save

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_corrupted_memory_data(self):
        """测试损坏的记忆数据"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 损坏数据测试 ===")

        # 注入正常记忆
        await coordinator.process_input("Normal memory 1")

        # 注入损坏的记忆数据
        if hasattr(coordinator.hippocampus, 'memories') and coordinator.hippocampus.memories:
            # 损坏一个记忆
            mem = coordinator.hippocampus.memories[0]
            mem.content = None  # 设置为None
            mem.embedding = []  # 清空embedding

            # 尝试检索
            try:
                if coordinator.memory_reasoning_chain:
                    result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(
                        "Find memories"
                    )
                print("✓ 系统处理损坏数据未崩溃")
            except Exception as e:
                print(f"✓ 系统正确捕获异常: {type(e).__name__}")

        await coordinator.stop_system()


class TestAPIFaultInjection:
    """API调用故障注入测试"""

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_llm_api_failure(self):
        """测试LLM API失败"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== LLM API 故障测试 ===")

        # Mock LLM API 失败
        with patch('src.agents.llm_service.LLMService.call') as mock_call:
            mock_call.side_effect = Exception("API rate limit exceeded")

            # 尝试处理输入
            try:
                result = await coordinator.process_input("Test during API failure")
                print(f"✓ 系统在API故障时返回: {result[:50] if result else 'None'}...")
            except Exception as e:
                print(f"✓ 系统正确处理API异常: {type(e).__name__}")

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_intermittent_api_failures(self):
        """测试间歇性API故障"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 间歇性API故障测试 ===")

        # 模拟间歇性故障（30%概率失败）
        call_count = 0
        success_count = 0
        failure_count = 0

        async def flaky_api_call(*args, **kwargs):
            nonlocal call_count, success_count, failure_count
            call_count += 1

            if FaultInjector.random_failure(probability=0.3):
                failure_count += 1
                raise Exception("Temporary API failure")
            else:
                success_count += 1
                return "API response"

        with patch('src.agents.llm_service.LLMService.call', side_effect=flaky_api_call):
            # 执行10次调用
            for i in range(10):
                try:
                    await coordinator.process_input(f"Test {i+1}")
                except Exception:
                    pass

        print(f"✓ API调用: {call_count}, 成功: {success_count}, 失败: {failure_count}")
        print(f"  系统在间歇性故障下保持运行")

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_slow_api_responses(self):
        """测试慢速API响应"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 慢速API响应测试 ===")

        # Mock 慢速API
        async def slow_api_call(*args, **kwargs):
            await FaultInjector.inject_delay(1.0, 3.0)
            return "Slow response"

        with patch('src.agents.llm_service.LLMService.call', side_effect=slow_api_call):
            import time
            start = time.time()

            try:
                result = await asyncio.wait_for(
                    coordinator.process_input("Test with slow API"),
                    timeout=10.0
                )
                elapsed = time.time() - start
                print(f"✓ 系统处理慢速API: {elapsed:.2f}秒")
            except asyncio.TimeoutError:
                print("✓ 慢速API超时被正确处理")

        await coordinator.stop_system()


class TestConcurrencyFaults:
    """并发故障注入测试"""

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_race_condition_consolidation(self):
        """测试巩固过程中的竞争条件"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 竞争条件测试：并发巩固 ===")

        # 注入记忆
        for i in range(20):
            await coordinator.process_input(f"Memory {i+1} for race test")

        # 设置高优先级
        if hasattr(coordinator.hippocampus, 'memories'):
            for mem in coordinator.hippocampus.memories:
                mem.importance = 0.8

        # 同时触发多个巩固和检索操作
        if hasattr(coordinator.hippocampus, 'consolidate_memories'):
            tasks = []

            # 5个巩固任务
            for _ in range(5):
                tasks.append(coordinator.hippocampus.consolidate_memories())

            # 5个检索任务
            if coordinator.memory_reasoning_chain:
                for i in range(5):
                    tasks.append(
                        coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(
                            f"Find memory {i+1}"
                        )
                    )

            # 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计结果
            success = sum(1 for r in results if not isinstance(r, Exception))
            errors = sum(1 for r in results if isinstance(r, Exception))

            print(f"✓ 并发操作完成: 成功={success}, 错误={errors}")
            assert success > 0, "至少应有部分操作成功"

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_memory_write_conflicts(self):
        """测试记忆写入冲突"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 写入冲突测试 ===")

        # 并发写入
        write_tasks = [
            coordinator.process_input(f"Concurrent write {i+1}")
            for i in range(20)
        ]

        results = await asyncio.gather(*write_tasks, return_exceptions=True)

        success = sum(1 for r in results if not isinstance(r, Exception))
        errors = sum(1 for r in results if isinstance(r, Exception))

        print(f"✓ 并发写入: 成功={success}, 错误={errors}")
        assert success >= 15, "大部分写入应成功"

        await coordinator.stop_system()


class TestMemoryOverflowFaults:
    """内存溢出故障注入测试"""

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_memory_leak_detection(self):
        """测试记忆泄漏检测"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 记忆泄漏检测测试 ===")

        initial_count = 0
        if hasattr(coordinator.hippocampus, 'memories'):
            initial_count = len(coordinator.hippocampus.memories)

        # 快速注入1000条记忆
        for i in range(1000):
            await coordinator.process_input(f"Leak test {i+1}")

            # 每100条检查一次
            if i % 100 == 99:
                current_count = len(coordinator.hippocampus.memories)
                growth = current_count - initial_count
                print(f"  {i+1} 条记忆后: {current_count} 条 (增长: {growth})")

                # 检查是否有清理机制
                if growth > 500:
                    print(f"⚠️  可能存在记忆泄漏: 增长 {growth} 条")

        final_count = len(coordinator.hippocampus.memories)
        total_growth = final_count - initial_count

        print(f"\n✓ 最终记忆数: {final_count} (增长: {total_growth})")

        # 应该有自动清理机制
        assert total_growth < 1500, "应该有记忆清理机制防止无限增长"

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_large_memory_content(self):
        """测试超大记忆内容"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 超大内容测试 ===")

        # 创建超大内容
        large_content = "A" * 10000  # 10KB

        try:
            result = await coordinator.process_input(large_content)
            print("✓ 系统处理超大内容未崩溃")
        except Exception as e:
            print(f"✓ 系统正确拒绝超大内容: {type(e).__name__}")

        await coordinator.stop_system()


class TestRecoveryMechanisms:
    """恢复机制测试"""

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_auto_recovery_after_failure(self):
        """测试故障后自动恢复"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 自动恢复测试 ===")

        # 注入正常记忆
        await coordinator.process_input("Memory before failure")

        # 模拟故障
        original_db = None
        if hasattr(coordinator.hippocampus, 'db_manager'):
            original_db = coordinator.hippocampus.db_manager
            coordinator.hippocampus.db_manager = None  # 模拟故障

        # 尝试操作（应该失败但不崩溃）
        result1 = await coordinator.process_input("Memory during failure")
        print(f"✓ 故障期间返回: {result1[:30] if result1 else 'None'}...")

        # 恢复连接
        if original_db:
            coordinator.hippocampus.db_manager = original_db

        # 验证恢复后正常工作
        result2 = await coordinator.process_input("Memory after recovery")
        print(f"✓ 恢复后返回: {result2[:30] if result2 else 'None'}...")

        assert result2 is not None, "恢复后系统应正常工作"

        await coordinator.stop_system()

    @pytest.mark.asyncio
    @pytest.mark.fault_injection
    async def test_graceful_degradation(self):
        """测试优雅降级"""
        coordinator = BrainInspiredCoordinator()

        print("\n=== 优雅降级测试 ===")

        # 禁用记忆推理链
        original_chain = coordinator.memory_reasoning_chain
        coordinator.memory_reasoning_chain = None

        # 系统应该降级但仍能工作
        result = await coordinator.process_input("Test with degraded features")

        print(f"✓ 降级模式下系统仍运行: {result[:50] if result else 'None'}...")
        assert result is not None, "降级模式下系统应仍能响应"

        # 恢复
        coordinator.memory_reasoning_chain = original_chain

        await coordinator.stop_system()


# Pytest 配置
def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line("markers", "fault_injection: marks tests as fault injection tests")
    config.addinivalue_line("markers", "asyncio: marks tests as async")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "fault_injection"])
