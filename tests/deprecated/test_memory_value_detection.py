"""
测试基于记忆价值的动态复杂度检测

展示: 记忆系统思维 vs QA系统思维的区别
"""
from src.coordination.memory_based_complexity import MemoryBasedComplexityDetector

def test_memory_value_detection():
    detector = MemoryBasedComplexityDetector()

    print("🧠 测试基于记忆价值的动态复杂度检测\n")
    print("="*80)
    print("核心思想: 这是记忆系统,不是QA系统!")
    print("- 每次交互都是学习机会")
    print("- 即使简单问候也可能包含重要信号")
    print("="*80)

    # 测试用例: 展示记忆系统的智能
    test_cases = [
        # Case 1: 看似简单的问候,但包含情绪信号
        {
            'query': 'Hi, I'm feeling really stressed today',
            'question_type': 'greeting',
            'expected_level': 3,  # QA系统会认为是Level 0, 但记忆系统识别到情绪异常!
            'reason': '包含强烈情绪信号 (stressed) + 异常检测'
        },

        # Case 2: 平常的陈述,但包含时间+情绪
        {
            'query': 'Yesterday I felt so happy when I met my friend',
            'question_type': 'simple',
            'expected_level': 3,  # 高记忆价值: 时间+情绪+社交
            'reason': '包含时间信息 + 情绪 + 人物关系'
        },

        # Case 3: 看似复杂的问题,但记忆价值低
        {
            'query': 'What is 2+2?',
            'question_type': 'simple',
            'expected_level': 0,  # 数学计算,无记忆价值
            'reason': '无情绪/时间/社交/行为信号'
        },

        # Case 4: 事实查询 + 学习信号
        {
            'query': 'Caroline researched adoption agencies on May 25',
            'question_type': 'research',
            'expected_level': 3,  # 高价值: 时间+行为+事实
            'reason': '时间信息 + 行为 + 事实知识'
        },

        # Case 5: 行为改变信号
        {
            'query': 'I used to say hi every morning, but today I cannot',
            'question_type': 'simple',
            'expected_level': 3,  # 异常检测: 行为改变 + 困扰信号
            'reason': '异常检测: behavior_change + distress_signal'
        },

        # Case 6: 简单问候 (真正的低价值)
        {
            'query': 'Hello',
            'question_type': 'greeting',
            'expected_level': 0,
            'reason': '极低记忆价值,即时反应'
        },

        # Case 7: 多跳推理 + 高记忆价值
        {
            'query': 'Based on Caroline attending LGBTQ groups and her emotions, what career would suit her?',
            'question_type': 'multi_hop',
            'expected_level': 3,
            'reason': '多跳推理 + 情绪信号 + 社交信息'
        },
    ]

    print("\n📋 测试用例:\n")

    for i, case in enumerate(test_cases, 1):
        result = detector.detect_complexity(case['query'], case['question_type'])

        level_match = "✅" if result['level'] == case['expected_level'] else "❌"

        print(f"\n{i}. {case['query'][:70]}")
        print(f"   {level_match} Level: {result['level']} (expected: {case['expected_level']})")
        print(f"   💎 Memory Value: {result['memory_value']:.2f}")
        print(f"   ⚠️  Anomaly: {result['anomaly_detected']}")
        print(f"   🔄 Iterations: {result['max_iterations']}")
        print(f"   📝 Reason: {result['reason']}")
        print(f"   💡 Expected reason: {case['reason']}")

    print("\n" + "="*80)
    print("🎯 关键洞察:")
    print("1. 'Hi, I'm feeling stressed' → Level 3 (QA系统会认为是Level 0!)")
    print("2. '2+2=?' → Level 0 (虽然是问题,但无记忆价值)")
    print("3. 'I used to say hi but cannot' → Level 3 (异常检测触发!)")
    print("\n这就是记忆系统vs QA系统的本质区别!")
    print("="*80)

if __name__ == "__main__":
    test_memory_value_detection()
