#!/usr/bin/env python3
"""
最终验证: Q4和Q7修复
确保使用最新的分布式推理代码
"""
import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator

async def test_q4_q7_fixes():
    print("=" * 80)
    print("🔧 最终验证: Q4和Q7修复 (使用最新分布式推理代码)")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # 验证agents连接
    print(f"\n✅ Reflection Agent: {coordinator.reasoning_validator.reflection_agent is not None}")
    print(f"✅ Consolidation Agent: {coordinator.reasoning_validator.consolidation_agent is not None}")

    # 学习记忆
    print("\n📝 学习记忆...")
    memories = [
        "On 8 May, 2023, Caroline attended an LGBTQ support group for the first time.",
        "Caroline found transgender stories very inspiring and emotional.",
        "On 25 May, 2023, Caroline researched adoption agencies.",
        "Caroline is passionate about helping marginalized communities."
    ]

    for mem in memories:
        print(f"   ✓ {mem[:60]}...")
        await coordinator.process_input(mem)

    print("\n" + "=" * 80)

    # 测试Q4 - 研究提取 (修复: 后处理验证)
    print("\n【测试 1/2】Q4 - 研究提取")
    print("-" * 80)
    print("❓ Question: What did Caroline research?")
    print("✅ Expected: Adoption agencies")
    print("🔧 Fix: 后处理验证 - 检测并替换generic phrases")

    answer_q4 = await coordinator.process_input("What did Caroline research?")
    print(f"\n🤖 Answer: {answer_q4}")

    # 判断
    if "adoption" in answer_q4.lower() and "agencies" in answer_q4.lower():
        print("✅ PASS - 返回了具体对象!")
    elif "the object being researched" in answer_q4.lower() or "what was researched" in answer_q4.lower():
        print("❌ FAIL - 仍然是generic phrase")
    else:
        print("⚠️  PARTIAL - 未返回期望答案但也不是generic")

    print("\n" + "=" * 80)

    # 测试Q7 - 兴趣推理 (修复: 问题分类逻辑)
    print("\n【测试 2/2】Q7 - 兴趣推理")
    print("-" * 80)
    print("❓ Question: What is Caroline interested in?")
    print("✅ Expected: Adoption, LGBTQ advocacy")
    print("🔧 Fix: 问题分类 - 'what is X interested' 不是identity问题")

    # 先检查问题分类
    question_type = coordinator._detect_question_type("What is Caroline interested in?")
    print(f"\n🔍 Detected question type: {question_type}")

    if question_type == 'identity':
        print("❌ 问题分类错误! 仍然被判定为identity")
    elif question_type == 'multi_hop':
        print("✅ 问题分类正确! 判定为multi_hop")

    answer_q7 = await coordinator.process_input("What is Caroline interested in?")
    print(f"\n🤖 Answer: {answer_q7}")

    # 判断
    if "transgender woman" in answer_q7.lower() and "adoption" not in answer_q7.lower():
        print("❌ FAIL - 返回了identity而不是兴趣!")
    elif any(kw in answer_q7.lower() for kw in ['adoption', 'lgbtq', 'advocacy', 'support', 'helping', 'communities']):
        print("✅ PASS - 返回了兴趣相关内容!")
    else:
        print("⚠️  PARTIAL - 未返回期望关键词")

    print("\n" + "=" * 80)
    print("📊 测试完成!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_q4_q7_fixes())
