#!/usr/bin/env python3
"""
快速测试CapabilityOrchestrator集成

测试3个问题:
1. 简单事实问题 (fact_extraction)
2. 时间计算问题 (temporal_calculation)
3. 身份推理问题 (identity_inference)
"""

import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainCoordinator


async def test_capability_orchestrator():
    """快速测试CapabilityOrchestrator"""
    print("=" * 80)
    print("🧪 Testing CapabilityOrchestrator Integration")
    print("=" * 80)

    coordinator = BrainCoordinator()

    test_cases = [
        {
            'learning': "On 8 May 2023, Caroline attended an LGBTQ support group meeting.",
            'question': "What did Caroline attend on 8 May 2023?",
            'expected_capability': 'fact_extraction'
        },
        {
            'learning': "On 25 May, 2023, Caroline researched adoption agencies. On 3 June, 2023, Caroline had a consultation with Dr. Anderson.",
            'question': "How many days passed between Caroline researching adoption agencies and having the consultation?",
            'expected_capability': 'temporal_calculation'
        },
        {
            'learning': "On 8 May 2023, Caroline attended an LGBTQ support group meeting. On 12 May 2023, Caroline went to a gender identity clinic.",
            'question': "What is Caroline's gender identity?",
            'expected_capability': 'identity_inference'
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"Test Case {i}: {test['expected_capability']}")
        print(f"{'='*80}")

        # 学习阶段
        print(f"\n📚 Learning: {test['learning']}")
        learn_result = await coordinator.process_input(test['learning'])
        print(f"✅ Learned (stored: {learn_result.memory_stored})")

        # 问答阶段
        print(f"\n❓ Question: {test['question']}")
        result = await coordinator.process_input(test['question'])

        print(f"\n📊 Result:")
        print(f"  Mode: {result.routing_decision.get('mode', 'N/A')}")
        print(f"  Capabilities: {result.routing_decision.get('capabilities', [])}")
        print(f"  Response: {result.response}")
        print(f"  Confidence: {result.insights.get('confidence', 0.0):.2f}")
        print(f"  Processing Time: {result.processing_time:.2f}s")

        # 验证是否使用了CapabilityOrchestrator
        if result.routing_decision.get('mode') == 'capability_orchestrator':
            print(f"  ✅ Used CapabilityOrchestrator")
            expected_cap = test['expected_capability']
            actual_caps = result.routing_decision.get('capabilities', [])
            if expected_cap in actual_caps:
                print(f"  ✅ Detected expected capability: {expected_cap}")
            else:
                print(f"  ⚠️ Expected {expected_cap}, got {actual_caps}")
        else:
            print(f"  ⚠️ Used fallback mode: {result.routing_decision.get('mode')}")

    print(f"\n{'='*80}")
    print("✅ Testing completed!")
    print(f"{'='*80}")


if __name__ == '__main__':
    asyncio.run(test_capability_orchestrator())
