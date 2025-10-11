"""
LoCoMo完整测试 - 加载完整对话历史再测试QA
"""

import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')
os.environ['USE_BRAIN_NETWORK'] = 'true'

from src.coordination.brain_coordinator import BrainInspiredCoordinator


def load_caroline_dialogues():
    """从LoCoMo数据集加载Caroline的完整对话"""
    locomo_path = '/Users/liyang/Desktop/testversion/MemOS/evaluation/data/locomo/locomo10.json'

    with open(locomo_path) as f:
        data = json.load(f)

    # 找到Caroline相关的conversation
    for item in data:
        if 'conversation' in item:
            conv = item['conversation']
            # 检查speaker_a或speaker_b是否是Caroline
            if conv.get('speaker_a') == 'Caroline' or conv.get('speaker_b') == 'Caroline':
                # 提取所有sessions的Caroline对话
                all_dialogues = []
                for i in range(1, 36):  # session_1 到 session_35
                    session_key = f'session_{i}'
                    if session_key in conv:
                        session_dialogues = conv[session_key]
                        # 只提取Caroline说的话
                        for dia in session_dialogues:
                            if dia.get('speaker') == 'Caroline':
                                all_dialogues.append(dia)
                return all_dialogues

    return []


def load_caroline_questions():
    """从LoCoMo数据集加载Caroline相关的问题"""
    locomo_path = '/Users/liyang/Desktop/testversion/MemOS/evaluation/data/locomo/locomo10.json'

    with open(locomo_path) as f:
        data = json.load(f)

    # 找到Caroline相关的问题
    caroline_qa = []
    for item in data:
        if 'qa' in item:
            for qa in item['qa']:
                question = qa.get('question', '')
                answer = qa.get('answer', '')
                # 只选择Caroline相关的问题
                if 'Caroline' in question or 'caroline' in question.lower():
                    caroline_qa.append((question, answer))

    return caroline_qa


async def main():
    print("=" * 80)
    print("🧪 LoCoMo Complete Test - Full Dialogue History")
    print("=" * 80)

    # 加载数据
    print("\n📂 Loading Caroline's dialogues from LoCoMo...")
    dialogues = load_caroline_dialogues()
    print(f"✅ Loaded {len(dialogues)} dialogues")

    print("\n📂 Loading Caroline's questions...")
    questions = load_caroline_questions()
    print(f"✅ Loaded {len(questions)} questions")

    # 按session分组
    sessions = {}
    for dia in dialogues:
        dia_id = dia.get('dia_id', '?')
        session = dia_id.split(':')[0] if ':' in dia_id else 'Unknown'
        if session not in sessions:
            sessions[session] = []
        sessions[session].append(dia)

    print(f"\n📊 Dialogue sessions: {sorted(sessions.keys())}")
    for session in sorted(sessions.keys()):
        print(f"   {session}: {len(sessions[session])} turns")

    # 初始化coordinator
    coordinator = BrainInspiredCoordinator()

    # Phase 1: 学习所有对话
    print("\n" + "=" * 80)
    print("📚 Phase 1: Learning All Dialogues")
    print("=" * 80)

    dialogue_count = 0
    for session in sorted(sessions.keys()):
        print(f"\n📅 Session {session} ({len(sessions[session])} turns):")

        for dia in sessions[session]:
            dia_id = dia.get('dia_id', '?')
            text = dia.get('text', '')

            # 格式化为记忆系统输入
            memory_input = f"Caroline said: '{text}'"

            # 显示进度
            if dialogue_count % 10 == 0:
                print(f"  Processing dialogue {dialogue_count+1}/{len(dialogues)}... [{dia_id}]")

            # 存储到记忆系统
            await coordinator.process_user_input(memory_input)
            dialogue_count += 1

    print(f"\n✅ Learning complete - {dialogue_count} dialogues stored")

    # Phase 2: 测试前5个Caroline问题
    print("\n" + "=" * 80)
    print("❓ Phase 2: Testing Questions")
    print("=" * 80)

    results = []
    test_questions = questions[:5]  # 先测试前5个

    for i, (question, expected_answer) in enumerate(test_questions, 1):
        print(f"\n  Q{i}: {question}")
        print(f"  📌 Expected: {expected_answer}")

        start_time = datetime.now()
        result = await coordinator.process_user_input(question)
        elapsed = (datetime.now() - start_time).total_seconds()

        answer = result.response
        print(f"  🤖 Got: {answer[:100]}...")
        print(f"  ⏱️  Time: {elapsed:.2f}s")
        print(f"  💾 Memories: {len(result.memories_retrieved)}")

        # 判断正确性
        expected_lower = str(expected_answer).lower()
        answer_lower = answer.lower()
        correct = expected_lower in answer_lower

        results.append({
            'question': question,
            'expected': expected_answer,
            'got': answer,
            'correct': correct,
            'time': elapsed,
            'memories': len(result.memories_retrieved)
        })

        print(f"  {'✅' if correct else '❌'} {('CORRECT' if correct else 'WRONG')}")

    # 统计结果
    print("\n" + "=" * 80)
    print("📊 Test Summary")
    print("=" * 80)

    correct_count = sum(1 for r in results if r['correct'])
    total_count = len(results)
    accuracy = correct_count / total_count * 100 if total_count > 0 else 0

    print(f"\n✅ Correct: {correct_count}/{total_count}")
    print(f"📈 Accuracy: {accuracy:.1f}%")
    print(f"⏱️  Avg Time: {sum(r['time'] for r in results) / len(results):.2f}s")
    print(f"💾 Avg Memories: {sum(r['memories'] for r in results) / len(results):.1f}")

    print("\n详细结果:")
    for i, r in enumerate(results, 1):
        status = '✅' if r['correct'] else '❌'
        print(f"  {status} Q{i}: {r['question'][:50]}...")
        print(f"      Expected: {r['expected']}")
        print(f"      Got: {r['got'][:80]}...")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
