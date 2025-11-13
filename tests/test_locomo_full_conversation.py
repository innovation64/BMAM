#!/usr/bin/env python3
"""
LoCoMo Full Conversation Test - 真实完整测试
直接测试目标:
1. 喂入 locomo10 的完整对话 (500+ 回合)
2. 按 session 顺序调用 process_input()
3. 用实际 QA 检索和生成回答
4. 记录真实准确率

Author: Claude Code
Date: 2025-11-11
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


LOCOMO_DATA_PATH = '/Users/liyang/Desktop/testversion/archived/MemOS/evaluation/data/locomo/locomo10.json'


def load_locomo_data(sample_idx=0):
    """加载 LoCoMo 数据"""
    with open(LOCOMO_DATA_PATH, 'r') as f:
        data = json.load(f)
    return data[sample_idx]


async def phase_1_ingest_conversation(sample):
    """
    Phase 1: 喂入完整对话
    """
    print("\n" + "="*80)
    print("PHASE 1: Ingesting Full Conversation")
    print("="*80)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    conversation = sample['conversation']
    speaker_a = conversation['speaker_a']
    speaker_b = conversation['speaker_b']

    print(f"Speakers: {speaker_a} <-> {speaker_b}")

    # 统计总turns
    total_turns = 0
    session_num = 1

    # 遍历所有sessions
    while f'session_{session_num}' in conversation:
        session_key = f'session_{session_num}'
        session_date = conversation.get(f'{session_key}_date_time', 'Unknown')
        session_dialogues = conversation.get(session_key, [])

        if not session_dialogues:
            session_num += 1
            continue

        print(f"\nSession {session_num} ({session_date}): {len(session_dialogues)} turns")

        # 处理每个turn
        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')

            if not text:
                continue

            # 直接调用 process_input - 最简单直接
            await coordinator.process_input(f"{speaker}: {text}")

            total_turns += 1

            if total_turns % 50 == 0:
                print(f"  Processed {total_turns} turns...")

        session_num += 1

    print(f"\n✓ Total turns processed: {total_turns}")

    # 保存状态
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_full'
    metrics_dir.mkdir(parents=True, exist_ok=True)

    phase1_state = {
        'sample_id': sample['sample_id'],
        'total_turns': total_turns,
        'sessions': session_num - 1,
        'timestamp': datetime.now().isoformat()
    }

    with open(metrics_dir / 'phase1_ingest.json', 'w') as f:
        json.dump(phase1_state, f, indent=2)

    return total_turns


async def phase_2_qa_testing(sample, num_questions=20):
    """
    Phase 2: QA 测试
    使用前 N 个问题进行测试
    """
    print("\n" + "="*80)
    print(f"PHASE 2: QA Testing ({num_questions} questions)")
    print("="*80)

    # 新建 coordinator - Fresh start
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    qa_pairs = sample['qa'][:num_questions]

    results = []
    correct_count = 0

    for i, qa in enumerate(qa_pairs, 1):
        question = qa['question']
        expected_answer = qa['answer']

        print(f"\n[{i}/{num_questions}] Q: {question}")
        print(f"  Expected: {expected_answer}")

        # 检索记忆
        if hasattr(coordinator, 'memory_coordinator'):
            memories = await coordinator.memory_coordinator.smart_retrieve(
                query=question,
                top_k=5
            )
        else:
            memories = []

        print(f"  Retrieved: {len(memories)} memories")

        # 生成回答 (直接用 process_user_input)
        result = await coordinator.process_user_input(question)
        actual_answer = result.response if hasattr(result, 'response') else str(result)

        print(f"  Actual: {actual_answer[:100]}...")

        # 简单判断: 预期答案是否在实际答案中
        is_correct = expected_answer.lower() in actual_answer.lower()

        if is_correct:
            correct_count += 1
            print(f"  ✅ CORRECT")
        else:
            print(f"  ❌ INCORRECT")

        results.append({
            'question': question,
            'expected': expected_answer,
            'actual': actual_answer,
            'correct': is_correct,
            'memories_retrieved': len(memories)
        })

    accuracy = (correct_count / num_questions) * 100

    print("\n" + "="*80)
    print("PHASE 2 RESULTS")
    print("="*80)
    print(f"Questions tested: {num_questions}")
    print(f"Correct: {correct_count}")
    print(f"Accuracy: {accuracy:.1f}%")

    # 保存结果
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_full'
    phase2_state = {
        'sample_id': sample['sample_id'],
        'num_questions': num_questions,
        'correct_count': correct_count,
        'accuracy': accuracy,
        'results': results,
        'timestamp': datetime.now().isoformat()
    }

    with open(metrics_dir / 'phase2_qa_results.json', 'w') as f:
        json.dump(phase2_state, f, indent=2)

    return accuracy


async def main():
    """主测试流程"""
    print("\n" + "="*80)
    print("LoCoMo Full Conversation Test")
    print("="*80)

    try:
        # 加载数据
        print("\n📁 Loading LoCoMo data...")
        sample = load_locomo_data(sample_idx=0)
        print(f"✓ Loaded sample: {sample['sample_id']}")
        print(f"✓ QA pairs available: {len(sample['qa'])}")

        # Phase 1: 喂入完整对话
        total_turns = await phase_1_ingest_conversation(sample)

        print("\n⏳ Waiting for memory consolidation...")
        await asyncio.sleep(5)

        # Phase 2: QA 测试 (先测试 20 个问题)
        accuracy = await phase_2_qa_testing(sample, num_questions=20)

        # Final summary
        print("\n" + "="*80)
        print("FINAL SUMMARY")
        print("="*80)
        print(f"Sample: {sample['sample_id']}")
        print(f"Total turns ingested: {total_turns}")
        print(f"QA accuracy: {accuracy:.1f}%")

        threshold = 50.0  # 50% 作为初始阈值
        if accuracy >= threshold:
            print(f"\n✅ TEST PASSED (accuracy ≥ {threshold}%)")
            sys.exit(0)
        else:
            print(f"\n⚠️  Accuracy below threshold ({accuracy:.1f}% < {threshold}%)")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
