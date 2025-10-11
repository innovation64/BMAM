"""
LoCoMo Session-Based Learning - 按会话学习，模拟真实记忆形成过程
"""

import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')
os.environ['USE_BRAIN_NETWORK'] = 'true'

from src.coordination.brain_coordinator import BrainInspiredCoordinator


def load_caroline_sessions():
    """
    从LoCoMo数据集按Session加载Caroline的对话
    返回：按session分组的对话列表
    """
    locomo_path = '/Users/liyang/Desktop/testversion/MemOS/evaluation/data/locomo/locomo10.json'

    with open(locomo_path) as f:
        data = json.load(f)

    # 找到Caroline的conversation
    for item in data:
        if 'conversation' in item:
            conv = item['conversation']
            if conv.get('speaker_a') == 'Caroline' or conv.get('speaker_b') == 'Caroline':
                sessions = []

                # 提取前4个session (D1-D4，包含5个问题所需的信息)
                for i in range(1, 5):
                    session_key = f'session_{i}'
                    session_date_key = f'session_{i}_date_time'

                    if session_key in conv:
                        session_info = {
                            'session_id': i,
                            'date_time': conv.get(session_date_key, 'Unknown'),
                            'dialogues': conv[session_key],
                            'speaker_a': conv.get('speaker_a'),
                            'speaker_b': conv.get('speaker_b')
                        }
                        sessions.append(session_info)

                return sessions

    return []


def load_caroline_questions():
    """加载Caroline相关的问题"""
    locomo_path = '/Users/liyang/Desktop/testversion/MemOS/evaluation/data/locomo/locomo10.json'

    with open(locomo_path) as f:
        data = json.load(f)

    # 找到前5个Caroline相关的问题
    caroline_qa = []
    for item in data:
        if 'qa' in item:
            for qa in item['qa']:
                question = qa.get('question', '')
                answer = qa.get('answer', '')
                if 'Caroline' in question or 'caroline' in question.lower():
                    caroline_qa.append((question, answer))
                    if len(caroline_qa) >= 5:  # 只取前5个
                        return caroline_qa

    return caroline_qa


async def learn_session(coordinator, session):
    """
    学习一个完整的Session
    保留对话的上下文和时序关系
    """
    session_id = session['session_id']
    date_time = session['date_time']
    dialogues = session['dialogues']

    print(f"\n📅 Session {session_id} ({date_time})")
    print(f"   {len(dialogues)} dialogues")

    # 构建Session上下文
    session_context = f"On {date_time}, {session['speaker_a']} and {session['speaker_b']} had a conversation."

    # 存储Session开始标记
    await coordinator.process_user_input(session_context)

    # 逐条处理对话，保留对话流
    caroline_dialogue_count = 0
    for dia in dialogues:
        speaker = dia.get('speaker', '')
        text = dia.get('text', '')
        dia_id = dia.get('dia_id', '')

        # 只存储Caroline说的话（因为问题都是关于Caroline的）
        if speaker == 'Caroline':
            # 保留对话上下文：谁说的、在哪个session
            memory_input = f"{speaker} said: '{text}'"
            await coordinator.process_user_input(memory_input)
            caroline_dialogue_count += 1

    print(f"   ✅ Stored {caroline_dialogue_count} Caroline dialogues")

    # Session结束 - 可以触发记忆巩固（未来优化）
    # await coordinator.consolidate_memories(session_id)


async def main():
    print("=" * 80)
    print("🧪 LoCoMo Session-Based Learning Test")
    print("=" * 80)

    # 加载数据
    print("\n📂 Loading Caroline's sessions...")
    sessions = load_caroline_sessions()
    print(f"✅ Loaded {len(sessions)} sessions")

    print("\n📂 Loading Caroline's questions...")
    questions = load_caroline_questions()
    print(f"✅ Loaded {len(questions)} questions")

    # 显示Session概览
    print("\n📊 Session Overview:")
    for session in sessions:
        total_dialogues = len(session['dialogues'])
        caroline_dialogues = sum(1 for d in session['dialogues'] if d.get('speaker') == 'Caroline')
        print(f"   Session {session['session_id']}: {total_dialogues} total, {caroline_dialogues} Caroline")

    # 初始化coordinator
    coordinator = BrainInspiredCoordinator()

    # Phase 1: 按Session学习
    print("\n" + "=" * 80)
    print("📚 Phase 1: Learning Sessions (Session-Based)")
    print("=" * 80)

    for session in sessions:
        await learn_session(coordinator, session)

    print("\n✅ All sessions learned")

    # Phase 2: 测试5个问题
    print("\n" + "=" * 80)
    print("❓ Phase 2: Testing Questions")
    print("=" * 80)

    results = []
    for i, (question, expected_answer) in enumerate(questions, 1):
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
