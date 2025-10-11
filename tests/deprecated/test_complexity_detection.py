"""
快速测试动态复杂度检测系统
"""
import asyncio
from src.coordination.brain_coordinator import BrainInspiredCoordinator

async def test_complexity_detection():
    coordinator = BrainInspiredCoordinator()

    # 测试不同复杂度的问题
    test_cases = [
        # Level 0: 即时反应
        ("Hello", 0, "greeting"),
        ("Thanks", 0, "greeting"),

        # Level 1: 记忆直取
        ("What is Caroline's identity?", 1, "identity"),
        ("When did Caroline go to LGBTQ group?", 1, "temporal"),

        # Level 2: 推理链
        ("What did Caroline research about?", 2, "research"),

        # Level 3: 深度推理
        ("What fields would Caroline likely pursue in her education?", 3, "multi_hop"),
        ("Based on Caroline's interests, why would she be suitable for social work?", 3, "multi_hop"),
    ]

    print("🎯 测试动态复杂度检测系统\n")
    print("="*80)

    for query, expected_level, expected_type in test_cases:
        result = coordinator._detect_task_complexity(query)

        level_match = "✅" if result['level'] == expected_level else "❌"
        type_match = "✅" if result['question_type'] == expected_type else "❌"

        print(f"\n问题: {query}")
        print(f"  {level_match} Level: {result['level']} (expected: {expected_level})")
        print(f"  {type_match} Type: {result['question_type']} (expected: {expected_type})")
        print(f"  迭代次数: {result['max_iterations']}")
        print(f"  需要记忆: {result['needs_memory']}")
        print(f"  需要推理: {result['needs_reasoning']}")
        print(f"  原因: {result['reason']}")

    print("\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(test_complexity_detection())
