"""
Phase 2 测试: 元认知与冲突检测
Test Metacognition & Conflict Detection

测试内容:
1. PrefrontalAgent.assess_confidence - 元认知评估
2. PrefrontalAgent.detect_conflicts - 冲突检测
3. MemoryRetrievalAgent.retrieve_multi_source - 多源并行检索
4. ReasoningValidatorAgent.unified_reasoning_with_conflict_resolution - 带冲突解决的统一推理
5. BrainCoordinator.cross_time_cross_text_reasoning - 跨时空跨文本推理
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.agents.base import AgentMessage


async def test_metacognitive_assessment():
    """测试元认知评估"""
    print("\n" + "=" * 80)
    print("TEST 1: Metacognitive Assessment (元认知评估)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 准备测试数据
    query = "What is Caroline's relationship status?"

    # 模拟内部检索结果
    internal_results = [
        {'content': 'Caroline is single', 'timestamp': datetime.now().isoformat()},
        {'content': 'Caroline has friends for 4 years', 'timestamp': datetime.now().isoformat()},
        {'content': 'Caroline attended LGBTQ support group', 'timestamp': (datetime.now() - timedelta(days=1)).isoformat()}
    ]

    # 调用元认知评估
    assessment = await coordinator.prefrontal_storage.process_message(AgentMessage(
        sender='test',
        receiver='prefrontal',
        message_type='request',
        content={
            'action': 'assess_confidence',
            'query': query,
            'internal_results': internal_results
        }
    ))

    print(f"✅ Metacognitive Assessment Results:")
    print(f"   Query: {query}")
    print(f"   Confidence: {assessment.get('confidence', 0):.2f}")
    print(f"   Should use external: {assessment.get('should_use_external', False)}")
    print(f"   Coverage ratio: {assessment.get('coverage_ratio', 0):.2f}")
    print(f"   Consistency score: {assessment.get('consistency_score', 0):.2f}")
    print(f"   Recency score: {assessment.get('recency_score', 0):.2f}")
    print(f"   Reasoning: {assessment.get('reasoning', '')}")
    print(f"   Missing info: {assessment.get('missing_info', [])}")

    await coordinator.stop_system()

    return assessment.get('confidence', 0) > 0.5  # Pass if confidence > 0.5


async def test_conflict_detection():
    """测试冲突检测"""
    print("\n" + "=" * 80)
    print("TEST 2: Conflict Detection (冲突检测)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 准备冲突测试数据
    multi_source_results = {
        'episodic': [
            {
                'content': 'Yesterday at 2pm, Caroline attended LGBTQ support group',
                'timestamp': (datetime.now() - timedelta(days=1, hours=-2)).isoformat(),
                'entities': ['Caroline', 'LGBTQ', 'support group'],
                'source_type': 'episodic'
            },
            {
                'content': 'Yesterday at 2pm, Caroline researched adoption agencies',
                'timestamp': (datetime.now() - timedelta(days=1, hours=-2)).isoformat(),
                'entities': ['Caroline', 'adoption', 'agencies'],
                'source_type': 'episodic'
            }
        ],
        'semantic': [
            {
                'content': 'Caroline is a software engineer',
                'entities': ['Caroline', 'engineer'],
                'source_type': 'semantic'
            }
        ],
        'external': [
            {
                'content': 'Caroline is a therapist specializing in LGBTQ counseling',
                'entities': ['Caroline', 'therapist', 'LGBTQ'],
                'source_type': 'external'
            }
        ]
    }

    # 调用冲突检测
    conflicts = await coordinator.prefrontal_storage.process_message(AgentMessage(
        sender='test',
        receiver='prefrontal',
        message_type='request',
        content={
            'action': 'detect_conflicts',
            'multi_source_results': multi_source_results
        }
    ))

    print(f"✅ Conflict Detection Results:")
    print(f"   Total conflicts detected: {len(conflicts)}")

    for i, conflict in enumerate(conflicts[:5], 1):
        print(f"\n   Conflict {i}:")
        print(f"      Type: {conflict.get('conflict_type')}")
        print(f"      Severity: {conflict.get('severity', 0):.2f}")
        print(f"      Explanation: {conflict.get('explanation', '')}")

    await coordinator.stop_system()

    return len(conflicts) > 0  # Pass if any conflicts detected


async def test_multi_source_retrieval():
    """测试多源并行检索"""
    print("\n" + "=" * 80)
    print("TEST 3: Multi-Source Parallel Retrieval (多源并行检索)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 先存储一些测试记忆
    test_memories = [
        "Caroline attended an LGBTQ support group yesterday",
        "Caroline is researching adoption agencies",
        "Caroline is a therapist who helps LGBTQ clients"
    ]

    for mem in test_memories:
        await coordinator.short_term_memory.process_message(AgentMessage(
            sender='test',
            receiver='short_term_memory',
            message_type='request',
            content={
                'action': 'store',
                'content': mem,
                'metadata': {}
            }
        ))

    # 多源检索
    query = "What does Caroline do professionally?"

    results = await coordinator.memory_retrieval.retrieve_multi_source(
        query=query,
        strategy='adaptive',
        k=5,
        brain_coordinator=coordinator
    )

    print(f"✅ Multi-Source Retrieval Results:")
    print(f"   Query: {query}")
    print(f"   Strategy: {results.get('retrieval_strategy', 'unknown')}")
    print(f"   Retrieval time: {results.get('retrieval_time_ms', 0):.1f}ms")
    print(f"   Sources used: {[k for k in results.keys() if k not in ['retrieval_strategy', 'retrieval_time_ms']]}")

    total_memories = 0
    for source, memories in results.items():
        if source not in ['retrieval_strategy', 'retrieval_time_ms']:
            print(f"   {source}: {len(memories)} memories")
            total_memories += len(memories)

    await coordinator.stop_system()

    return total_memories > 0  # Pass if any memories retrieved


async def test_conflict_resolution():
    """测试冲突解决"""
    print("\n" + "=" * 80)
    print("TEST 4: Unified Reasoning with Conflict Resolution (带冲突解决的统一推理)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 准备冲突记忆
    multi_source_memories = {
        'episodic': [
            {
                'content': 'Caroline is a therapist',
                'timestamp': datetime.now().isoformat(),
                'entities': ['Caroline', 'therapist']
            }
        ],
        'semantic': [
            {
                'content': 'Caroline works as a software engineer',
                'entities': ['Caroline', 'engineer']
            }
        ]
    }

    query = "What is Caroline's profession?"

    # 调用带冲突解决的统一推理
    result = await coordinator.reasoning_validator.unified_reasoning_with_conflict_resolution(
        query=query,
        multi_source_memories=multi_source_memories,
        prefrontal_agent=coordinator.prefrontal_storage,
        context={'capabilities': ['fact_integration']}
    )

    print(f"✅ Conflict Resolution Results:")
    print(f"   Query: {query}")
    print(f"   Answer: {result.get('answer', 'N/A')}")
    print(f"   Confidence: {result.get('confidence', 0):.2f}")
    print(f"   Conflicts detected: {result.get('conflicts_detected', 0)}")
    print(f"   Resolution strategy: {result.get('resolution_strategy', 'N/A')}")
    print(f"   Sources used: {result.get('sources_used', [])}")

    if result.get('reasoning_chain'):
        print(f"\n   Reasoning Chain:")
        for step in result['reasoning_chain'][:3]:
            print(f"      - {step}")

    await coordinator.stop_system()

    return result.get('answer') is not None  # Pass if an answer was generated


async def test_cross_time_cross_text_reasoning():
    """测试跨时空跨文本推理 - 完整流程"""
    print("\n" + "=" * 80)
    print("TEST 5: Cross-Time Cross-Text Reasoning (跨时空跨文本推理)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 先存储一些时间相关的记忆
    time_based_memories = [
        {
            'content': 'Yesterday, Caroline attended an LGBTQ support group',
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat()
        },
        {
            'content': 'Last week, Caroline researched adoption agencies',
            'timestamp': (datetime.now() - timedelta(days=7)).isoformat()
        },
        {
            'content': 'Caroline is a therapist specializing in LGBTQ counseling',
            'timestamp': (datetime.now() - timedelta(days=30)).isoformat()
        }
    ]

    for mem_data in time_based_memories:
        await coordinator.short_term_memory.process_message(AgentMessage(
            sender='test',
            receiver='short_term_memory',
            message_type='request',
            content={
                'action': 'store',
                'content': mem_data['content'],
                'metadata': {'timestamp': mem_data['timestamp']}
            }
        ))

    # 跨时空推理
    query = "What makes Caroline a good fit for helping LGBTQ individuals?"

    result = await coordinator.cross_time_cross_text_reasoning(
        query=query,
        time_constraint=None
    )

    print(f"✅ Cross-Time Cross-Text Reasoning Results:")
    print(f"   Query: {query}")
    print(f"   Answer: {result.get('answer', 'N/A')}")
    print(f"   Confidence: {result.get('confidence', 0):.2f}")
    print(f"   Processing time: {result.get('processing_time_ms', 0):.1f}ms")
    print(f"   Sources used: {result.get('sources_used', [])}")
    print(f"   Conflicts detected: {result.get('conflicts_detected', 0)}")
    print(f"   Resolution strategy: {result.get('resolution_strategy', 'N/A')}")

    print(f"\n   Metacognitive Assessment:")
    meta = result.get('metacognitive_assessment', {})
    print(f"      Confidence: {meta.get('confidence', 0):.2f}")
    print(f"      External needed: {meta.get('should_use_external', False)}")

    if result.get('reasoning_chain'):
        print(f"\n   Reasoning Chain:")
        for step in result['reasoning_chain'][:3]:
            print(f"      - {step}")

    await coordinator.stop_system()

    return result.get('answer') is not None and result.get('confidence', 0) > 0.3


async def main():
    """运行所有Phase 2测试"""
    print("\n" + "🧠" * 40)
    print("PHASE 2 TESTING: Metacognition & Conflict Detection")
    print("🧠" * 40)

    tests = [
        ("Metacognitive Assessment", test_metacognitive_assessment),
        ("Conflict Detection", test_conflict_detection),
        ("Multi-Source Retrieval", test_multi_source_retrieval),
        ("Conflict Resolution", test_conflict_resolution),
        ("Cross-Time Cross-Text Reasoning", test_cross_time_cross_text_reasoning)
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results[test_name] = "✅ PASSED" if passed else "⚠️ PARTIAL"
        except Exception as e:
            results[test_name] = f"❌ FAILED: {str(e)}"
            import traceback
            print(f"\nError traceback:\n{traceback.format_exc()}")

    # 总结
    print("\n" + "=" * 80)
    print("PHASE 2 TEST SUMMARY")
    print("=" * 80)

    for test_name, result in results.items():
        print(f"{result}: {test_name}")

    passed_count = sum(1 for r in results.values() if "PASSED" in r)
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 测试通过")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
