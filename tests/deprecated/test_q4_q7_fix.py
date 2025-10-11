#!/usr/bin/env python3
"""快速测试Q4和Q7的修复"""
import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

from src.coordination.brain_coordinator import BrainInspiredCoordinator

async def test_fixes():
    print("🔧 测试Q4和Q7修复")
    print("=" * 60)

    coordinator = BrainInspiredCoordinator()

    # 学习记忆
    print("\n📝 学习记忆...")
    await coordinator.process_input("On 25 May, 2023, Caroline researched adoption agencies.")
    await coordinator.process_input("Caroline attends LGBTQ support group.")
    await coordinator.process_input("Caroline found transgender stories inspiring.")

    # 测试Q4
    print("\n🧪 测试Q4: What did Caroline research?")
    print("Expected: Adoption agencies")
    answer = await coordinator.process_input("What did Caroline research?")
    print(f"Answer: {answer}")
    print("✅ PASS" if "adoption" in answer.lower() else "❌ FAIL")

    # 测试Q7
    print("\n🧪 测试Q7: What is Caroline interested in?")
    print("Expected: Adoption, LGBTQ advocacy")
    answer = await coordinator.process_input("What is Caroline interested in?")
    print(f"Answer: {answer}")
    # 检查不是返回identity
    if "transgender woman" in answer.lower():
        print("❌ FAIL - 仍然返回identity!")
    elif any(kw in answer.lower() for kw in ['adoption', 'lgbtq', 'advocacy', 'support']):
        print("✅ PASS")
    else:
        print("⚠️  PARTIAL - 未返回期望关键词")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_fixes())
