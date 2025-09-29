#!/usr/bin/env python3
"""
Test Enhanced Perception Encoding Agent
测试增强的感知编码智能体
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.core.perception_encoding import EnhancedPerceptionEncodingAgent
from src.agents.base import AgentMessage
from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.utils.config import get_logger

logger = get_logger(__name__)


async def test_perception_agent():
    """Test the enhanced perception encoding agent directly"""
    print("🧪 Testing Enhanced Perception Encoding Agent\n")

    agent = EnhancedPerceptionEncodingAgent()

    # Test 1: Short text
    print("Test 1: Short Text Processing")
    print("-" * 50)

    short_text = "记住我喜欢喝绿茶，每天下午3点。"

    message1 = AgentMessage(
        sender='test',
        receiver='perception_encoding',
        message_type='request',
        content={
            'action': 'encode_input',
            'input_data': {
                'content': short_text,
                'type': 'text'
            }
        }
    )

    result1 = await agent.process_message(message1)
    encoded = result1['encoded_input']

    print(f"✅ Processing mode: {encoded['processing_mode']}")
    print(f"   Total tokens: {encoded['total_tokens']}")
    print(f"   Features: {encoded['features']}")
    print()

    # Test 2: Long text that requires chunking
    print("Test 2: Long Text with Chunking")
    print("-" * 50)

    # Create a long text by repeating content
    long_text = """
    人工智能的发展历程非常精彩。从1956年达特茅斯会议开始，AI经历了多个发展阶段。
    早期的符号主义AI专注于逻辑推理和知识表示，试图通过规则系统模拟人类思维。

    到了1980年代，专家系统兴起，在特定领域展现了强大的问题解决能力。
    然而，知识获取瓶颈和脆弱性问题限制了其发展。

    1990年代，机器学习开始崛起，特别是统计学习方法的引入，为AI带来了新的突破。
    支持向量机、决策树、贝叶斯网络等算法在各种应用中取得了成功。

    进入21世纪，深度学习的革命性突破改变了整个领域。2012年AlexNet在ImageNet竞赛中的胜利，
    标志着深度学习时代的开始。卷积神经网络在计算机视觉领域取得了惊人的成果。

    """ * 20  # Repeat to make it long enough

    message2 = AgentMessage(
        sender='test',
        receiver='perception_encoding',
        message_type='request',
        content={
            'action': 'encode_input',
            'input_data': {
                'content': long_text,
                'type': 'text'
            }
        }
    )

    result2 = await agent.process_message(message2)
    encoded2 = result2['encoded_input']

    print(f"✅ Processing mode: {encoded2['processing_mode']}")
    print(f"   Total tokens: {encoded2['total_tokens']}")
    print(f"   Chunk count: {encoded2.get('chunk_count', 0)}")

    if 'segments' in encoded2:
        print(f"   Segments created: {len(encoded2['segments'])}")
        for i, seg in enumerate(encoded2['segments'][:3]):  # Show first 3 segments
            print(f"\n   Segment {i+1}:")
            print(f"     Summary: {seg.get('summary', 'N/A')[:100]}...")
            print(f"     Keywords: {seg.get('keywords', [])}")
            print(f"     Token count: {seg.get('token_count', 0)}")

    if 'overview' in encoded2:
        overview = encoded2['overview']
        print(f"\n   Overview:")
        print(f"     Theme: {overview.get('theme', 'N/A')}")
        print(f"     Category: {overview.get('category', 'N/A')}")
        print(f"     Storage priority: {overview.get('storage_priority', 'N/A')}")
        print(f"     Global keywords: {overview.get('global_keywords', [])[:5]}")


async def test_coordinator_integration():
    """Test integration with the coordinator"""
    print("\n\n🧪 Testing Coordinator Integration with Long Text")
    print("=" * 50)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Test with a moderately long text
    long_input = """
    我想让你记住以下重要信息：

    1. 项目管理原则：
       - 始终保持清晰的目标和里程碑
       - 定期进行团队沟通和进度更新
       - 风险管理是项目成功的关键

    2. 技术架构设计：
       - 模块化设计提高代码可维护性
       - 性能优化应该基于实际测量数据
       - 安全性必须从设计阶段就考虑

    3. 团队协作要点：
       - 建立明确的责任分工
       - 鼓励知识共享和技术讨论
       - 及时反馈和认可团队成员的贡献
    """ * 5  # Repeat to trigger chunking

    result = await coordinator.process_user_input(long_input)

    print(f"✅ Processing completed")
    print(f"   Success: {result.success}")
    print(f"   Processing time: {result.processing_time:.2f}s")
    print(f"   Memory stored: {result.memory_stored}")
    print(f"   Agents involved: {result.agents_involved}")

    if result.insights:
        print(f"\n   Insights:")
        print(f"     Memory strategy: {result.insights.get('memory_strategy', 'N/A')}")

    await coordinator.stop_system()


async def test_memory_retrieval_with_chunks():
    """Test if chunked memories can be retrieved"""
    print("\n\n🧪 Testing Memory Retrieval of Chunked Content")
    print("=" * 50)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Store a long text with explicit memory request
    long_text_to_remember = """
    请记住这些详细的技术规范：

    数据库配置要求：
    - 使用PostgreSQL 14或更高版本
    - 启用UUID扩展
    - 设置连接池大小为100
    - 配置自动备份每日执行

    API设计规范：
    - 所有端点使用RESTful风格
    - 响应格式统一为JSON
    - 实现版本控制通过URL路径
    - 错误码遵循HTTP标准

    性能指标要求：
    - API响应时间小于200ms
    - 数据库查询优化到100ms以内
    - 缓存命中率保持在80%以上
    """ * 3

    # Store the information
    result1 = await coordinator.process_user_input(long_text_to_remember)
    print(f"✅ Storage result: memory_stored={result1.memory_stored}")

    # Try to retrieve specific information
    await asyncio.sleep(1)  # Brief delay

    query = "数据库配置要求是什么？"
    result2 = await coordinator.process_user_input(query)

    print(f"\n✅ Retrieval result:")
    print(f"   Memories found: {len(result2.memories_retrieved)}")
    print(f"   Response: {result2.response[:200]}...")

    if result2.memories_retrieved:
        for i, mem in enumerate(result2.memories_retrieved[:3]):
            print(f"\n   Retrieved memory {i+1}:")
            print(f"     Content: {str(mem)[:150]}...")

    await coordinator.stop_system()


async def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Perception Agent Tests\n")

    try:
        # Test 1: Direct agent testing
        await test_perception_agent()

        # Test 2: Coordinator integration
        await test_coordinator_integration()

        # Test 3: Memory retrieval with chunks
        await test_memory_retrieval_with_chunks()

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())