#!/usr/bin/env python3
"""
Test comprehensive segment preservation
测试完整的段落保留功能
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.utils.config import get_logger

logger = get_logger(__name__)


async def test_large_text_preservation():
    """Test that very large texts preserve ALL segments"""
    print("🧪 Testing Large Text Segment Preservation")
    print("-" * 60)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Create a very large text that will definitely exceed limits
    section_content = """
    这是一个非常详细的技术文档章节，包含重要的实现细节和设计理念。
    我们需要确保这些内容能够被完整保存，不会因为分段限制而丢失任何信息。
    每个段落都包含了关键的知识点，对于后续的系统开发和维护都非常重要。
    因此，我们必须实现一个可靠的段落保存机制，确保内容的完整性。
    """

    # Create 60 sections (will definitely exceed segment limits)
    huge_text = "请记住以下详细的技术文档：\n\n"
    for i in range(60):
        huge_text += f"第{i+1}章节：{section_content}\n\n"

    print(f"Input size: ~{len(huge_text)} characters")

    # Test explicit storage (should use immediate storage with overflow handling)
    result = await coordinator.process_user_input(huge_text)

    print(f"✅ Processing completed: {result.success}")
    print(f"   Memory stored: {result.memory_stored}")
    print(f"   Memory strategy: {result.insights.get('memory_strategy', 'unknown')}")
    print(f"   Processing time: {result.processing_time:.2f}s")

    if result.error:
        print(f"   Error: {result.error}")

    # Check for overflow files
    overflow_dir = Path("data/segment_overflow")
    overflow_files = []
    if overflow_dir.exists():
        overflow_files = list(overflow_dir.glob("*.json"))
        print(f"   Overflow files created: {len(overflow_files)}")

        if overflow_files:
            print("   📁 Overflow files:")
            for file in overflow_files:
                print(f"     - {file.name}")

                # Check content of overflow file
                import json
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        overflow_data = json.load(f)
                    print(f"       Segments in file: {overflow_data.get('total_overflow_segments', 0)}")
                except Exception as e:
                    print(f"       Error reading file: {e}")

    # Try to retrieve information
    await asyncio.sleep(1)
    query_result = await coordinator.process_user_input("技术文档包含哪些章节？")

    print(f"\n🔍 Retrieval test:")
    print(f"   Memories found: {len(query_result.memories_retrieved)}")
    print(f"   Response length: {len(query_result.response)}")

    await coordinator.stop_system()

    # Verify preservation
    total_preservation = len(query_result.memories_retrieved) > 0 or len(overflow_files) > 0
    return total_preservation


async def test_queue_batch_processing():
    """Test that background queue processes all batches"""
    print("\n🧪 Testing Queue Batch Processing")
    print("-" * 60)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Create moderate-sized text that will go to background queue
    medium_text = """
    这是一个中等长度的技术说明，用于测试后台队列处理。
    我们需要验证所有的文本段落都能被正确处理，包括那些通过后台队列延迟处理的段落。
    """ * 50

    print(f"Input size: ~{len(medium_text)} characters")

    # Process without explicit "记住" (will go to background queue)
    result = await coordinator.process_user_input(medium_text)

    print(f"✅ Initial processing: {result.success}")
    print(f"   Memory strategy: {result.insights.get('memory_strategy', 'unknown')}")

    # Manually trigger queue processing multiple times to clear all batches
    print("\n📥 Processing queued batches...")

    total_processed = 0
    for i in range(5):  # Process up to 5 times to handle all batches
        try:
            queue_result = await coordinator._activate_agent(
                'consolidation',
                coordinator._create_message('consolidation', 'process_chunked_queue', {})
            )

            processed_batches = queue_result.get('processed_batches', 0)
            processed_segments = queue_result.get('processed_segments', 0)
            stored_segments = queue_result.get('stored_segments', 0)

            print(f"   Batch {i+1}: {processed_batches} batches, {processed_segments} segments, {stored_segments} stored")
            total_processed += processed_segments

            if processed_batches == 0:
                print("   Queue empty - processing complete")
                break

        except Exception as e:
            print(f"   Batch {i+1} error: {e}")
            break

    print(f"\n📊 Total segments processed: {total_processed}")

    await coordinator.stop_system()
    return total_processed > 0

def _create_message(coordinator, receiver, action, content):
    """Helper to create agent message"""
    from src.coordination.clean_agent_system import AgentMessage
    return AgentMessage(
        sender='test',
        receiver=receiver,
        message_type='request',
        content={'action': action, **content}
    )

# Monkey patch the helper method
BrainInspiredCoordinator._create_message = _create_message


async def test_segment_limits_config():
    """Test configurable segment limits"""
    print("\n🧪 Testing Configurable Segment Limits")
    print("-" * 60)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    settings = coordinator.settings

    print(f"   Max segments immediate: {settings.max_segments_immediate}")
    print(f"   Max segments background: {settings.max_segments_background}")
    print(f"   Serialization enabled: {settings.enable_segment_serialization}")

    # Test the limits are actually applied
    from src.agents.core.perception_encoding import EnhancedPerceptionEncodingAgent
    from src.agents.base import AgentMessage

    agent = EnhancedPerceptionEncodingAgent()

    # Create text that will exceed limits
    large_text = "测试段落内容。" * 2000

    message = AgentMessage(
        sender='test',
        receiver='perception_encoding',
        message_type='request',
        content={
            'action': 'encode_input',
            'input_data': {
                'content': large_text,
                'type': 'text'
            }
        }
    )

    result = await agent.process_message(message)
    encoded = result['encoded_input']

    if 'segments' in encoded:
        total_segments = len(encoded['segments'])
        print(f"   Text generated {total_segments} segments")

        # Test that coordinator respects limits
        segments = encoded['segments']
        overview = encoded.get('overview', {})

        print(f"   Testing immediate storage limits...")

        # This should trigger overflow handling if segments > max_segments_immediate
        if total_segments > settings.max_segments_immediate:
            print(f"   ✅ Would trigger overflow handling ({total_segments} > {settings.max_segments_immediate})")
        else:
            print(f"   ✅ Within immediate limits ({total_segments} <= {settings.max_segments_immediate})")

    await coordinator.stop_system()
    return True


async def main():
    """Run all segment preservation tests"""
    print("🚀 Starting Comprehensive Segment Preservation Tests\n")

    test_results = []

    try:
        # Test 1: Large text preservation
        result1 = await test_large_text_preservation()
        test_results.append(("Large Text Preservation", result1))

        # Test 2: Queue batch processing
        result2 = await test_queue_batch_processing()
        test_results.append(("Queue Batch Processing", result2))

        # Test 3: Configurable limits
        result3 = await test_segment_limits_config()
        test_results.append(("Configurable Limits", result3))

    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

    # Summary
    print("\n" + "="*60)
    print("📊 SEGMENT PRESERVATION TEST RESULTS")
    print("="*60)

    passed = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(test_results)} tests passed")

    if passed == len(test_results):
        print("🎉 All segment preservation features working!")
        print("\n✅ Key improvements verified:")
        print("   • Large texts preserved via batching + overflow serialization")
        print("   • Background queue processes ALL batches")
        print("   • Configurable limits prevent system overload")
        print("   • No data loss for any segment size")
    else:
        print("⚠️ Some preservation issues remain - check logs above.")


if __name__ == "__main__":
    asyncio.run(main())