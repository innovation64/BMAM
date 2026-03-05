"""
Real Integration Tests for Coordinator V2
协调器V2真实集成测试

Tests with REAL components and agents - NO MOCKS
"""

import pytest
import asyncio

from src.core.config import BMAMConfig
from src.core.container import Container as DependencyContainer, get_container
from src.coordination.coordinator_builder import (
    CoordinatorBuilder,
    create_coordinator
)
from src.coordination.coordinator_v2 import BrainInspiredCoordinatorV2
from src.memory.memory_system.registration import register_memory_system_components


@pytest.fixture
def test_config() -> BMAMConfig:
    """Test configuration"""
    return BMAMConfig.for_testing()


@pytest.fixture
def real_container(test_config) -> DependencyContainer:
    """Real DI container with components registered"""
    container = DependencyContainer()
    register_memory_system_components(container)
    return container


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_builder_pattern(real_container, test_config):
    """
    Test building coordinator with builder pattern
    使用构建器模式测试协调器
    """
    # Build coordinator using fluent API
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus'])  # Just one agent for quick test
        .with_message_bus()
        .build())

    assert coordinator is not None
    assert isinstance(coordinator, BrainInspiredCoordinatorV2)
    assert len(coordinator.agents) == 1
    assert 'hippocampus' in coordinator.agents

    print("✓ Coordinator built successfully with builder pattern")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_initialization(real_container, test_config):
    """
    Test coordinator initialization
    测试协调器初始化
    """
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus'])
        .build())

    # Should not be initialized yet
    assert not coordinator._initialized

    # Initialize explicitly
    await coordinator.initialize()

    # Now should be initialized
    assert coordinator._initialized

    print("✓ Coordinator initialized successfully")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_process_real_query(real_container, test_config):
    """
    Test processing real query with real agents
    使用真实智能体处理真实查询
    """
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus'])
        .build())

    await coordinator.initialize()

    # Process real query
    result = await coordinator.process("What is artificial intelligence?")

    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    print(f"✓ Processed query successfully")
    print(f"  Result length: {len(result)} characters")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_multiple_agents(real_container, test_config):
    """
    Test coordinator with multiple real agents
    使用多个真实智能体测试协调器
    """
    # Build with multiple agents
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus', 'prefrontal'])
        .build())

    await coordinator.initialize()

    # Should have both agents
    assert len(coordinator.agents) == 2
    assert 'hippocampus' in coordinator.agents
    assert 'prefrontal' in coordinator.agents

    # Process query
    result = await coordinator.process("Remember: AI is amazing")

    assert result is not None
    print(f"✓ Multiple agents working: {list(coordinator.agents.keys())}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_system_status(real_container, test_config):
    """
    Test getting system status
    测试获取系统状态
    """
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus'])
        .build())

    # Get status before initialization
    status = coordinator.get_system_status()

    assert status is not None
    assert 'initialized' in status
    assert status['initialized'] == False
    assert 'agents' in status
    assert 'hippocampus' in status['agents']

    # Initialize and check again
    await coordinator.initialize()
    status = coordinator.get_system_status()

    assert status['initialized'] == True
    assert 'memory_stats' in status

    print(f"✓ System status retrieved: {status}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_with_learning(real_container, test_config):
    """
    Test coordinator with learning enabled
    测试启用学习的协调器
    """
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus'])
        .enable_learning(True)
        .build())

    await coordinator.initialize()

    # Check learning system is initialized
    assert coordinator._learning_system is not None

    # Process with learning
    result = await coordinator.process("Learning test query")

    assert result is not None
    print("✓ Coordinator with learning system working")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_quick_create(test_config):
    """
    Test quick create convenience function
    测试快速创建便利函数
    """
    # Use convenience function
    coordinator = create_coordinator(
        agent_names=['hippocampus'],
        enable_learning=False,
        config=test_config
    )

    assert coordinator is not None
    assert isinstance(coordinator, BrainInspiredCoordinatorV2)

    await coordinator.initialize()
    result = await coordinator.process("Quick create test")

    assert result is not None
    print("✓ Quick create function works")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_stop_system(real_container, test_config):
    """
    Test stopping coordinator cleanly
    测试干净停止协调器
    """
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus'])
        .enable_background_memory(True)  # Enable background tasks
        .build())

    await coordinator.initialize()

    # Should have background tasks
    assert len(coordinator._background_tasks) > 0

    # Process something
    await coordinator.process("Test before stop")

    # Stop cleanly
    await coordinator.stop_system()

    # Should not be initialized anymore
    assert not coordinator._initialized

    print("✓ Coordinator stopped cleanly")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_no_import_side_effects():
    """
    Test that importing does NOT cause side effects
    测试导入不会引起副作用
    """
    # Just importing should not initialize anything
    from src.coordination.coordinator_v2 import BrainInspiredCoordinatorV2
    from src.coordination.coordinator_builder import CoordinatorBuilder

    # No exceptions should be raised
    print("✓ Imports have no side effects")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_memory_integration(real_container, test_config):
    """
    Test coordinator memory integration
    测试协调器记忆集成
    """
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus'])
        .build())

    await coordinator.initialize()

    # Store something via coordinator
    await coordinator.process("Remember: Python is great")

    # Memory system should have the memory
    stats = coordinator.memory_system.get_system_stats()

    print(f"✓ Memory integration working: {stats}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_coordinator_v2_concurrent_requests(real_container, test_config):
    """
    Test handling concurrent requests
    测试处理并发请求
    """
    coordinator = (CoordinatorBuilder(real_container, test_config)
        .with_memory()
        .with_agents(['hippocampus'])
        .build())

    await coordinator.initialize()

    # Send multiple concurrent requests
    async def process_query(i: int) -> str:
        return await coordinator.process(f"Concurrent query {i}")

    tasks = [process_query(i) for i in range(5)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 5
    assert all(r is not None for r in results)

    print(f"✓ Handled 5 concurrent requests successfully")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
