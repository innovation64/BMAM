"""
LoCoMo 20-Question Extended Test
扩展测试: 从原始5个问题扩展到20个问题,全面测试记忆系统能力
"""

import asyncio
import json
import time
from datetime import datetime
from src.coordination.brain_coordinator import BrainInspiredCoordinator


# LoCoMo Caroline数据 (完整的Session 1-4)
CAROLINE_SESSIONS = {
    'session_1': [
        "On 8 May 2023, Caroline said: 'I went to a LGBTQ support group yesterday. The transgender stories were so inspiring! I was so happy and felt empowered.'",
        "She said: 'The transgender stories were so inspiring! I was so happy and felt empowered.'",
        "Caroline said: 'Gonna continue my edu and check out career options, whatever feels right.'",
        "She added: 'I'm keen on counseling or working in mental health - I'd love to support those with similar issues.'",
    ],
    'session_1_date_time': '2023-05-08',

    'session_2': [
        "On 25 May 2023, Caroline researched adoption agencies that support LGBTQ families.",
        "She learned about social work programs focused on community advocacy.",
    ],
    'session_2_date_time': '2023-05-25',

    'session_3': [
        "On 3 June 2023, Caroline volunteered at a local LGBTQ youth center.",
        "She mentioned: 'Working with these young people is so rewarding. Many are struggling with family acceptance.'",
        "Caroline said: 'I think I want to specialize in family counseling for LGBTQ individuals.'",
    ],
    'session_3_date_time': '2023-06-03',

    'session_4': [
        "On 15 June 2023, Caroline applied to graduate programs in social work and psychology.",
        "She said: 'I'm particularly interested in programs that focus on LGBTQ mental health.'",
        "Caroline mentioned: 'I'm single right now, focusing on my career goals.'",
        "She added: 'I want to get certified as a counselor within the next 2-3 years.'",
    ],
    'session_4_date_time': '2023-06-15',
}


# 20个测试问题 (从简单到复杂,全面覆盖)
TEST_QUESTIONS = [
    # === 原始5个问题 ===
    {
        'id': 'Q1',
        'question': 'When did Caroline go to the LGBTQ support group?',
        'expected': '7 May 2023',
        'type': 'temporal_calculation',
        'difficulty': 'easy'
    },
    {
        'id': 'Q2',
        'question': 'What did Caroline research?',
        'expected': 'adoption agencies',
        'type': 'fact_extraction',
        'difficulty': 'easy'
    },
    {
        'id': 'Q3',
        'question': "What is Caroline's identity?",
        'expected': 'transgender woman',
        'type': 'identity_inference',
        'difficulty': 'medium'
    },
    {
        'id': 'Q4',
        'question': 'What fields would Caroline be likely to pursue in her education?',
        'expected': 'psychology',  # 核心关键词
        'expected_keywords': ['psychology', 'social work'],
        'type': 'interest_inference',
        'difficulty': 'medium'
    },
    {
        'id': 'Q5',
        'question': 'What community did Caroline engage with?',
        'expected': 'LGBTQ community',
        'type': 'fact_extraction',
        'difficulty': 'easy'
    },

    # === 新增15个问题 ===

    # 时间推理 (Temporal)
    {
        'id': 'Q6',
        'question': 'When did Caroline volunteer at the LGBTQ youth center?',
        'expected': '3 June 2023',
        'type': 'temporal_calculation',
        'difficulty': 'easy'
    },
    {
        'id': 'Q7',
        'question': 'How many days passed between Caroline going to the support group and researching adoption agencies?',
        'expected': '17',
        'expected_keywords': ['17', 'eighteen'],
        'type': 'duration_inference',
        'difficulty': 'hard'
    },

    # 事实提取 (Fact Extraction)
    {
        'id': 'Q8',
        'question': 'What type of programs did Caroline apply to?',
        'expected': 'graduate programs',
        'expected_keywords': ['graduate', 'social work', 'psychology'],
        'type': 'fact_extraction',
        'difficulty': 'easy'
    },
    {
        'id': 'Q9',
        'question': 'What certification does Caroline want to get?',
        'expected': 'counselor',
        'expected_keywords': ['counselor', 'counseling'],
        'type': 'fact_extraction',
        'difficulty': 'medium'
    },

    # 身份/关系推理 (Identity/Relationship)
    {
        'id': 'Q10',
        'question': "What is Caroline's relationship status?",
        'expected': 'single',
        'type': 'relationship_inference',
        'difficulty': 'medium'
    },
    {
        'id': 'Q11',
        'question': 'What demographic does Caroline identify with?',
        'expected': 'LGBTQ',
        'expected_keywords': ['LGBTQ', 'transgender'],
        'type': 'identity_inference',
        'difficulty': 'medium'
    },

    # 兴趣推理 (Interest Inference)
    {
        'id': 'Q12',
        'question': 'What specific area of counseling is Caroline interested in?',
        'expected': 'family counseling',
        'expected_keywords': ['family', 'LGBTQ'],
        'type': 'interest_inference',
        'difficulty': 'medium'
    },
    {
        'id': 'Q13',
        'question': 'What population does Caroline want to work with?',
        'expected': 'LGBTQ individuals',
        'expected_keywords': ['LGBTQ', 'youth', 'families'],
        'type': 'interest_inference',
        'difficulty': 'easy'
    },

    # 模式识别 (Pattern Recognition)
    {
        'id': 'Q14',
        'question': 'What pattern can you identify in Caroline\'s activities across all sessions?',
        'expected': 'LGBTQ advocacy',
        'expected_keywords': ['LGBTQ', 'support', 'advocacy', 'community'],
        'type': 'pattern_recognition',
        'difficulty': 'hard'
    },
    {
        'id': 'Q15',
        'question': 'What common theme appears in Caroline\'s career interests?',
        'expected': 'mental health',
        'expected_keywords': ['mental health', 'counseling', 'support'],
        'type': 'pattern_recognition',
        'difficulty': 'medium'
    },

    # 多跳推理 (Multi-hop Inference)
    {
        'id': 'Q16',
        'question': 'Based on Caroline\'s experiences and interests, what career path is she most likely pursuing?',
        'expected': 'LGBTQ counselor',
        'expected_keywords': ['counselor', 'therapist', 'LGBTQ', 'mental health'],
        'type': 'multi_hop_inference',
        'difficulty': 'hard'
    },
    {
        'id': 'Q17',
        'question': 'Why might Caroline be interested in family counseling specifically?',
        'expected': 'family acceptance issues',
        'expected_keywords': ['family', 'acceptance', 'struggle'],
        'type': 'causal_reasoning',
        'difficulty': 'hard'
    },

    # 时间线推理 (Timeline)
    {
        'id': 'Q18',
        'question': 'What was the first activity Caroline did related to LGBTQ community?',
        'expected': 'support group',
        'expected_keywords': ['support group', 'LGBTQ support'],
        'type': 'temporal_calculation',
        'difficulty': 'medium'
    },
    {
        'id': 'Q19',
        'question': 'Within what timeframe does Caroline want to become certified?',
        'expected': '2-3 years',
        'expected_keywords': ['2', '3', 'years'],
        'type': 'duration_inference',
        'difficulty': 'easy'
    },

    # 综合推理 (Complex)
    {
        'id': 'Q20',
        'question': 'What motivated Caroline to pursue a career in counseling?',
        'expected': 'transgender stories inspired',
        'expected_keywords': ['inspired', 'empowered', 'transgender', 'stories', 'support'],
        'type': 'causal_reasoning',
        'difficulty': 'hard'
    },
]


async def test_locomo_20_questions():
    """测试20个LoCoMo问题"""

    print("=" * 80)
    print("🧪 LoCoMo 20-Question Extended Test")
    print("=" * 80)
    print()

    # 初始化coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Phase 1: 学习所有Sessions
    print("📚 Phase 1: Learning All Sessions (4 sessions)")
    print("-" * 80)

    for session_num in range(1, 5):
        session_key = f'session_{session_num}'
        session_date = CAROLINE_SESSIONS.get(f'{session_key}_date_time', 'Unknown')

        if session_key in CAROLINE_SESSIONS:
            print(f"\n📅 Session {session_num} ({session_date}):")

            for i, dialogue in enumerate(CAROLINE_SESSIONS[session_key], 1):
                # 学习对话
                result = await coordinator.process_user_input(dialogue, {})
                print(f"  {i}. {dialogue[:80]}...")

    print("\n✅ Learning complete")
    print()

    # Phase 2: 测试20个问题
    print("❓ Phase 2: Testing 20 Questions")
    print("-" * 80)
    print()

    results = []
    correct_count = 0
    total_time = 0
    total_memories = 0

    # 按难度分组统计
    difficulty_stats = {'easy': {'correct': 0, 'total': 0},
                       'medium': {'correct': 0, 'total': 0},
                       'hard': {'correct': 0, 'total': 0}}

    # 按类型分组统计
    type_stats = {}

    for i, q in enumerate(TEST_QUESTIONS, 1):
        print(f"  {q['id']}: {q['question']}")
        print(f"  📌 Expected: {q['expected']}")

        start_time = time.time()
        result = await coordinator.process_user_input(q['question'], {})
        elapsed_time = time.time() - start_time

        answer = result.response
        memories_count = len(result.memories_retrieved) if result.memories_retrieved else 0

        # 检查答案是否正确 (支持关键词匹配)
        answer_lower = answer.lower()
        expected_lower = q['expected'].lower()

        is_correct = False
        if expected_lower in answer_lower:
            is_correct = True
        elif 'expected_keywords' in q:
            # 检查是否包含任意关键词
            keywords_found = [kw for kw in q['expected_keywords'] if kw.lower() in answer_lower]
            if keywords_found:
                is_correct = True

        # 记录结果
        result_data = {
            'id': q['id'],
            'question': q['question'],
            'expected': q['expected'],
            'got': answer,
            'correct': is_correct,
            'time': elapsed_time,
            'memories': memories_count,
            'type': q['type'],
            'difficulty': q['difficulty']
        }
        results.append(result_data)

        if is_correct:
            correct_count += 1

        total_time += elapsed_time
        total_memories += memories_count

        # 更新统计
        difficulty_stats[q['difficulty']]['total'] += 1
        if is_correct:
            difficulty_stats[q['difficulty']]['correct'] += 1

        if q['type'] not in type_stats:
            type_stats[q['type']] = {'correct': 0, 'total': 0}
        type_stats[q['type']]['total'] += 1
        if is_correct:
            type_stats[q['type']]['correct'] += 1

        # 打印结果
        status = "✅ CORRECT" if is_correct else "❌ WRONG"
        print(f"  🤖 Got: {answer[:100]}...")
        print(f"  ⏱️  Time: {elapsed_time:.2f}s")
        print(f"  💾 Memories: {memories_count}")
        print(f"  {status}")
        print()

    # 总结报告
    print("=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    print()

    accuracy = (correct_count / len(TEST_QUESTIONS)) * 100
    avg_time = total_time / len(TEST_QUESTIONS)
    avg_memories = total_memories / len(TEST_QUESTIONS)

    print(f"✅ Correct: {correct_count}/{len(TEST_QUESTIONS)}")
    print(f"📈 Accuracy: {accuracy:.1f}%")
    print(f"⏱️  Avg Time: {avg_time:.2f}s")
    print(f"💾 Avg Memories: {avg_memories:.1f}")
    print()

    # 按难度统计
    print("📊 By Difficulty:")
    for difficulty in ['easy', 'medium', 'hard']:
        stats = difficulty_stats[difficulty]
        if stats['total'] > 0:
            acc = (stats['correct'] / stats['total']) * 100
            print(f"  {difficulty.capitalize()}: {stats['correct']}/{stats['total']} ({acc:.1f}%)")
    print()

    # 按类型统计
    print("📊 By Type:")
    for qtype, stats in sorted(type_stats.items()):
        acc = (stats['correct'] / stats['total']) * 100
        print(f"  {qtype}: {stats['correct']}/{stats['total']} ({acc:.1f}%)")
    print()

    # 详细结果
    print("详细结果:")
    for r in results:
        status = "✅" if r['correct'] else "❌"
        print(f"  {status} {r['id']}: {r['question'][:50]}... ({r['time']:.1f}s, {r['memories']} mems)")

    print()
    print("=" * 80)

    await coordinator.stop_system()

    return {
        'total': len(TEST_QUESTIONS),
        'correct': correct_count,
        'accuracy': accuracy,
        'avg_time': avg_time,
        'avg_memories': avg_memories,
        'results': results,
        'difficulty_stats': difficulty_stats,
        'type_stats': type_stats
    }


if __name__ == '__main__':
    asyncio.run(test_locomo_20_questions())
