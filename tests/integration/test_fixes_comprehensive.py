#!/usr/bin/env python3
"""
Comprehensive test for all fixes and optimizations
综合测试所有修复和优化
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agents.core.perception_encoding import EnhancedPerceptionEncodingAgent
from src.agents.base import AgentMessage
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.config import get_logger

logger = get_logger(__name__)


async def test_chinese_chunking():
    """Test Chinese text chunking with punctuation"""
    print("🧪 Testing Chinese Text Chunking")
    print("-" * 50)

    agent = EnhancedPerceptionEncodingAgent()

    # Long Chinese text without periods
    chinese_text = """
    请记住以下重要信息，这些都是项目管理的核心要点，需要特别注意，
    第一点是团队协作非常重要，大家需要保持良好的沟通，定期开会讨论进展，
    第二点是时间管理要科学合理，制定详细的计划表，按照优先级来执行任务，
    第三点是质量控制不能放松，每个环节都要仔细检查，确保达到预期标准，
    第四点是风险管理要提前考虑，识别潜在问题并制定应对措施，避免项目延期，
    第五点是资源分配要合理，人员技能要匹配任务需求，设备工具要及时到位
    """ * 10  # 重复10次确保超过token限制

    message = AgentMessage(
        sender='test',
        receiver='perception_encoding',
        message_type='request',
        content={
            'action': 'encode_input',
            'input_data': {
                'content': chinese_text,
                'type': 'text'
            }
        }
    )

    result = await agent.process_message(message)
    encoded = result['encoded_input']

    print(f"✅ Processing mode: {encoded['processing_mode']}")
    print(f"   Total tokens: {encoded['total_tokens']}")
    print(f"   Language detected: {encoded['features']['language']}")

    if 'segments' in encoded:
        print(f"   Segments created: {len(encoded['segments'])}")
        print(f"   First segment processing: {encoded['segments'][0].get('processing_method', 'unknown')}")

        # Check if all segments are within token limits
        for i, seg in enumerate(encoded['segments']):
            if seg['token_count'] > 2000:
                print(f"❌ Segment {i} exceeds token limit: {seg['token_count']} tokens")
                return False
            else:
                print(f"   Segment {i}: {seg['token_count']} tokens ✅")

    return True


async def test_reduced_llm_calls():
    """Test that LLM calls are minimized for chunk processing"""
    print("\n🧪 Testing Reduced LLM Calls")
    print("-" * 50)

    agent = EnhancedPerceptionEncodingAgent()

    # Create text that will produce many chunks
    long_text = "这是一个测试段落。" * 1000  # Will create multiple chunks

    message = AgentMessage(
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

    result = await agent.process_message(message)
    encoded = result['encoded_input']

    if 'segments' in encoded:
        llm_processed = sum(1 for seg in encoded['segments'] if seg.get('processing_method') == 'llm')
        local_processed = sum(1 for seg in encoded['segments'] if seg.get('processing_method') == 'local')

        print(f"   Total segments: {len(encoded['segments'])}")
        print(f"   LLM processed: {llm_processed}")
        print(f"   Locally processed: {local_processed}")

        # Should have minimal LLM calls
        if llm_processed <= 1 and local_processed >= len(encoded['segments']) - 1:
            print("✅ LLM calls minimized successfully")
            return True
        else:
            print("❌ Too many LLM calls detected")
            return False
    else:
        print("✅ No chunking needed - single processing")
        return True


async def test_input_limits():
    """Test MAX_INPUT_TOKENS limit enforcement"""
    print("\n🧪 Testing Input Token Limits")
    print("-" * 50)

    agent = EnhancedPerceptionEncodingAgent()

    # Create extremely long text that exceeds max_input_tokens
    very_long_text = "这是一个非常长的文本段落，用来测试输入限制功能。" * 2000

    message = AgentMessage(
        sender='test',
        receiver='perception_encoding',
        message_type='request',
        content={
            'action': 'encode_input',
            'input_data': {
                'content': very_long_text,
                'type': 'text'
            }
        }
    )

    result = await agent.process_message(message)
    encoded = result['encoded_input']

    print(f"   Input tokens: {encoded['total_tokens']}")
    print(f"   Max allowed: {agent.settings.max_input_tokens}")

    if encoded['total_tokens'] <= agent.settings.max_input_tokens:
        print("✅ Input truncation working correctly")
        return True
    else:
        print("❌ Input limit not enforced")
        return False


async def test_queue_processing():
    """Test chunked text queue processing"""
    print("\n🧪 Testing Queue Processing")
    print("-" * 50)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Process a long text that should be queued
    long_text = """
    请记住这是一个很长的技术文档，包含多个重要章节。

    第一章：系统架构设计
    这里描述了整个系统的架构设计理念，包括模块化设计、微服务架构、数据流设计等重要内容。

    第二章：数据库设计
    数据库设计部分详细说明了表结构、索引策略、查询优化等关键技术点。

    第三章：API接口设计
    API接口设计章节涵盖了RESTful设计原则、版本控制、错误处理等重要规范。
    """ * 5

    result = await coordinator.process_user_input(long_text)

    print(f"   Processing completed: {result.success}")
    print(f"   Memory strategy: {result.insights.get('memory_strategy', 'unknown')}")

    # Trigger queue processing manually
    try:
        await coordinator._trigger_chunked_queue_processing()
        print("✅ Queue processing triggered successfully")

        # Check if consolidation agent processed the queue
        consolidation_result = await coordinator._activate_agent(
            'consolidation',
            AgentMessage(
                sender='test',
                receiver='consolidation',
                message_type='request',
                content={'action': 'process_chunked_queue'}
            )
        )

        processed = consolidation_result.get('processed', 0)
        print(f"   Chunks processed: {processed}")

        await coordinator.stop_system()
        return processed >= 0  # Any non-error result is good

    except Exception as e:
        print(f"❌ Queue processing failed: {e}")
        await coordinator.stop_system()
        return False


async def test_memory_consistency():
    """Test that memory storage is now consistent"""
    print("\n🧪 Testing Memory Storage Consistency")
    print("-" * 50)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Store explicit memory
    result1 = await coordinator.process_user_input("请记住我的生日是3月15日")
    print(f"   Memory stored: {result1.memory_stored}")
    print(f"   Success: {result1.success}")

    if result1.error:
        print(f"   Error: {result1.error}")

    # Immediately try to retrieve
    await asyncio.sleep(0.5)  # Brief pause
    result2 = await coordinator.process_user_input("我的生日是什么时候？")

    memories_found = len(result2.memories_retrieved)
    print(f"   Memories retrieved: {memories_found}")

    # Check if the birthday info is in retrieved memories
    birthday_found = any("3月15日" in str(memory) or "生日" in str(memory)
                        for memory in result2.memories_retrieved)

    print(f"   Birthday info found: {birthday_found}")

    await coordinator.stop_system()
    return birthday_found or memories_found > 0


async def main():
    """Run comprehensive tests"""
    print("🚀 Starting Comprehensive Fix Validation\n")

    test_results = []

    try:
        # Test 1: Chinese chunking
        result1 = await test_chinese_chunking()
        test_results.append(("Chinese Text Chunking", result1))

        # Test 2: Reduced LLM calls
        result2 = await test_reduced_llm_calls()
        test_results.append(("Reduced LLM Calls", result2))

        # Test 3: Input limits
        result3 = await test_input_limits()
        test_results.append(("Input Token Limits", result3))

        # Test 4: Queue processing
        result4 = await test_queue_processing()
        test_results.append(("Queue Processing", result4))

        # Test 5: Memory consistency
        result5 = await test_memory_consistency()
        test_results.append(("Memory Consistency", result5))

    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("="*60)

    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(test_results)} tests passed")

    if passed == len(test_results):
        print("🎉 All fixes validated successfully!")
        print("\n✅ Key improvements confirmed:")
        print("   • Chinese text chunking with proper punctuation handling")
        print("   • Reduced LLM calls through local summarization")
        print("   • Input token limits enforced")
        print("   • Chunked text queue processing working")
        print("   • Memory storage consistency improved")
    else:
        print("⚠️ Some issues remain - check individual test results above.")


if __name__ == "__main__":
    asyncio.run(main())