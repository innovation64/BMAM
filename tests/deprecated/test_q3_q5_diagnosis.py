#!/usr/bin/env python3
"""
诊断Q3-Q5失败原因
追踪每个问题的完整执行流程，找出哪个agent/router的问题
"""

import asyncio
import os
import sys

# 设置环境变量
os.environ['USE_BRAIN_NETWORK'] = 'true'
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def diagnose_question(coordinator, question, expected, memories_text):
    """诊断单个问题"""
    print("\n" + "="*80)
    print(f"🔍 诊断问题: {question}")
    print(f"📌 期望答案: {expected}")
    print("="*80)

    # 1. 学习记忆
    print("\n📚 Step 1: 学习记忆...")
    for mem in memories_text:
        result = await coordinator.process_user_input(mem, {})
        print(f"  ✅ 学到: {mem[:60]}...")

    # 2. 提问并追踪
    print(f"\n❓ Step 2: 提问 '{question}'")
    result = await coordinator.process_user_input(question, {})

    # 3. 分析结果
    print(f"\n📊 Step 3: 分析结果")
    print(f"  🤖 系统答案: {result.response}")
    print(f"  📌 期望答案: {expected}")
    print(f"  ✅ 正确性: {'PASS' if expected.lower() in result.response.lower() else 'FAIL'}")

    # 4. 分析路由决策
    print(f"\n🧭 Step 4: 路由决策分析")
    routing = result.routing_decision
    print(f"  模式: {routing.get('mode')}")
    print(f"  涉及智能体: {result.agents_involved}")

    # 5. 分析能力检测
    if 'capabilities' in routing:
        print(f"\n🎯 Step 5: 能力检测")
        caps = routing.get('capabilities', [])
        print(f"  检测到的能力: {caps}")
        for cap in caps:
            if isinstance(cap, dict):
                print(f"    - {cap.get('name')}: priority={cap.get('priority')}, reason={cap.get('reason')}")

    # 6. 检查记忆检索
    print(f"\n💾 Step 6: 记忆检索")
    from src.agents.core.memory_retrieval import MemoryRetrievalAgent
    retrieval_agent = coordinator.memory_retrieval
    memories = await coordinator.memory_system.search_memories(query=question, k=5)
    print(f"  检索到 {len(memories)} 条记忆:")
    for i, mem in enumerate(memories[:3], 1):
        content = mem.get('content', '')[:80]
        score = mem.get('score', 0)
        print(f"    {i}. [score={score:.3f}] {content}...")

    # 7. 分析推理链
    if hasattr(result, 'reasoning_chain'):
        print(f"\n🔗 Step 7: 推理链")
        for step in result.reasoning_chain:
            print(f"  {step}")

    return result

async def main():
    print("🧪 诊断Q3-Q5失败原因")
    print("="*80)

    # 初始化coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # 测试用例
    test_cases = [
        {
            'question': "What is Caroline's identity?",
            'expected': 'transgender woman',
            'memories': [
                "On 8 May 2023, Caroline attended an LGBTQ support group for the first time.",
                "She heard transgender stories that were inspiring and felt empowered.",
                "On 25 May 2023, Caroline researched adoption agencies that support LGBTQ families.",
                "She learned about social work programs focused on community advocacy."
            ]
        },
        {
            'question': "What fields would Caroline be likely to pursue in her education?",
            'expected': 'social work / psychology',
            'memories': [
                "On 8 May 2023, Caroline attended an LGBTQ support group for the first time.",
                "She heard transgender stories that were inspiring and felt empowered.",
                "On 25 May 2023, Caroline researched adoption agencies that support LGBTQ families.",
                "She learned about social work programs focused on community advocacy."
            ]
        },
        {
            'question': "What community did Caroline engage with?",
            'expected': 'LGBTQ community',
            'memories': [
                "On 8 May 2023, Caroline attended an LGBTQ support group for the first time.",
                "She heard transgender stories that were inspiring and felt empowered.",
                "On 25 May 2023, Caroline researched adoption agencies that support LGBTQ families.",
                "She learned about social work programs focused on community advocacy."
            ]
        }
    ]

    results = []
    for i, case in enumerate(test_cases, 3):
        # 每个case重新初始化coordinator
        await coordinator.stop_system()
        import os
        os.system('rm -f data/memory_vectors.index data/brain_memory.db')
        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()

        result = await diagnose_question(
            coordinator,
            case['question'],
            case['expected'],
            case['memories']
        )
        results.append({
            'q_num': i,
            'question': case['question'],
            'expected': case['expected'],
            'got': result.response,
            'pass': case['expected'].lower() in result.response.lower()
        })

    # 汇总分析
    print("\n" + "="*80)
    print("📊 诊断汇总")
    print("="*80)
    for r in results:
        status = "✅ PASS" if r['pass'] else "❌ FAIL"
        print(f"\nQ{r['q_num']}: {r['question'][:50]}...")
        print(f"  {status}")
        print(f"  期望: {r['expected']}")
        print(f"  实际: {r['got'][:100]}...")

    # 找出问题根源
    print("\n" + "="*80)
    print("🔍 根源分析")
    print("="*80)

    # Q3: identity问题
    print("\n📌 Q3 (身份识别) 失败原因:")
    print("  1. 检查identity_inference能力是否被正确触发")
    print("  2. 检查记忆中'transgender'关键词是否被正确检索")
    print("  3. 检查LLM prompt是否引导正确推理")

    # Q4: fields问题
    print("\n📌 Q4 (教育领域) 失败原因:")
    print("  1. 检查multi_hop_inference/interest_inference能力")
    print("  2. 检查'social work programs'记忆是否被检索")
    print("  3. 检查答案类型是否匹配(fields vs career)")

    # Q5: community问题
    print("\n📌 Q5 (社区类型) 失败原因:")
    print("  1. 检查fact_extraction能力")
    print("  2. 检查'LGBTQ support group'记忆是否被检索")
    print("  3. 检查答案是否过于复杂(应该是简单事实)")

    await coordinator.stop_system()

if __name__ == "__main__":
    asyncio.run(main())
