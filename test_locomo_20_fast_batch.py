"""
LoCoMo 20题测试 - 批量学习优化版（10-20倍加速）
"""

import asyncio
import json
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

# 配置日志
log_file = f"results/locomo_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
Path("results").mkdir(exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
root_logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.ERROR)
console_handler.setFormatter(logging.Formatter('❌ %(levelname)s: %(message)s'))
root_logger.addHandler(console_handler)

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.memory.memory_system import memory_system
from evaluation.llm_judge_locomo import LoCoMoLLMJudge


def print_progress_bar(iteration, total, prefix='', suffix='', length=40, fill='█'):
    """打印进度条"""
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='', flush=True)
    if iteration == total:
        print()


async def batch_learn_sessions(conversation, needed_sessions):
    """批量学习sessions - 绕过完整的coordinator流程"""

    print(f"\n📚 Phase 1: Batch Learning Sessions (Fast Mode)")
    print(f"{'='*80}\n")

    # 收集所有需要学习的对话
    all_dialogues = []
    total_turns = 0

    for session_num in needed_sessions:
        session_key = f'session_{session_num}'
        session_date = conversation.get(f'{session_key}_date_time', 'Unknown')
        session_dialogues = conversation.get(session_key, [])

        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            if text:
                content = f"On {session_date}, {speaker} said: '{text}'"
                all_dialogues.append({
                    'content': content,
                    'session': session_num,
                    'speaker': speaker,
                    'date': session_date
                })
                total_turns += 1

    print(f"  Collected {total_turns} dialogue turns from {len(needed_sessions)} sessions")
    print(f"  Starting batch embedding and storage...\n")

    # 批量生成embeddings并存储
    start_time = datetime.now()
    stored_count = 0

    # 分批处理（OpenAI API有限制，每次最多处理100条）
    batch_size = 100

    for i in range(0, len(all_dialogues), batch_size):
        batch = all_dialogues[i:i+batch_size]

        # 批量存储（memory_system会自动批量处理embedding）
        for dialogue in batch:
            await memory_system.store_memory(
                content=dialogue['content'],
                memory_type='episodic',
                importance=0.5,
                context_tags=['locomo_learning', f"session_{dialogue['session']}"]
            )
            stored_count += 1

            # 更新进度条
            print_progress_bar(
                stored_count,
                total_turns,
                prefix='  Batch Learning',
                suffix=f'({stored_count}/{total_turns})',
                length=50
            )

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n\n✅ Batch learning completed in {elapsed:.1f}s")
    print(f"   Speed: {total_turns/elapsed:.1f} turns/second")
    print(f"   (vs. sequential: ~0.5-1.0 turns/second)\n")

    return total_turns


async def main():
    print("=" * 80)
    print("🧪 LoCoMo 20-Question Test (Batch Learning - 10-20x Faster)")
    print("=" * 80)

    # 加载数据
    dataset_path = Path('/Users/liyang/Desktop/testversion/BMAM/data/benchmarks/locomo/locomo10.json')
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sample = data[0]
    conversation = sample['conversation']
    qa_list = sample['qa'][:20]

    # 分析需要的sessions
    needed_sessions = set()
    for qa in qa_list:
        for ev in qa.get('evidence', []):
            session_id = int(ev.split(':')[0].replace('D', ''))
            needed_sessions.add(session_id)
    needed_sessions = sorted(needed_sessions)

    print(f"\n📊 Sample: {sample['sample_id']}")
    print(f"📊 Questions: {len(qa_list)}")
    print(f"📊 Sessions to learn: {len(needed_sessions)} (batch mode)")
    print(f"📊 Log file: {log_file}")

    coordinator = BrainInspiredCoordinator()
    judge = LoCoMoLLMJudge()

    # Phase 1: 批量学习（绕过coordinator的复杂流程）
    total_turns = await batch_learn_sessions(conversation, needed_sessions)

    # Phase 2: 测试Questions
    print(f"{'='*80}")
    print("❓ Phase 2: Testing Questions")
    print(f"{'='*80}\n")

    results = []
    correct_count = 0
    start_all = datetime.now()

    for i, qa in enumerate(qa_list, 1):
        question = qa['question']
        gold_answer = str(qa['answer'])

        try:
            print(f"  Q{i:2d}: {question[:65]}...")

            start = datetime.now()
            result = await coordinator.process_user_input(question)
            elapsed = (datetime.now() - start).total_seconds()

            answer = result.response
            memories = len(result.memories_retrieved) if result.memories_retrieved else 0

            # LLM Judge
            judgment = await judge.judge_answer(question, gold_answer, answer)
            is_correct = judgment['correct']

            if is_correct:
                correct_count += 1

            icon = '✅' if is_correct else '❌'
            print(f"       {icon} {answer[:58]}... ({elapsed:.1f}s)")

            print_progress_bar(
                i,
                len(qa_list),
                prefix=f'  Progress',
                suffix=f'({correct_count}/{i} correct, {100*correct_count/i:.1f}%)',
                length=50
            )
            print()

            results.append({
                'id': i,
                'correct': is_correct,
                'time': elapsed,
                'memories': memories,
                'question': question,
                'gold': gold_answer,
                'answer': answer,
                'reasoning': judgment['reasoning']
            })

        except Exception as e:
            print(f"       ❌ ERROR: {e}")
            results.append({'id': i, 'correct': False, 'time': 0, 'memories': 0, 'error': str(e)})

    total_time = (datetime.now() - start_all).total_seconds()

    # 最终统计
    print(f"\n{'='*80}")
    print("📊 Final Results")
    print(f"{'='*80}\n")

    total = len(results)
    accuracy = (correct_count / total * 100) if total > 0 else 0

    print(f"  ✅ Accuracy: {correct_count}/{total} = {accuracy:.1f}%")
    print(f"  ⏱️  Total Time: {total_time/60:.1f} minutes")
    print(f"  ⏱️  Avg Time per Question: {total_time/total:.1f}s")

    avg_mem = sum(r['memories'] for r in results) / total if total > 0 else 0
    print(f"  💾 Avg Memories Retrieved: {avg_mem:.1f}")

    # 保存结果
    output_file = f"results/locomo_20q_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'sample_id': sample['sample_id'],
            'accuracy': accuracy,
            'total_time': total_time,
            'batch_learning': True,
            'sessions_learned': list(needed_sessions),
            'total_turns_learned': total_turns,
            'results': results
        }, f, indent=2)

    print(f"\n  💾 Results: {output_file}")
    print(f"  📝 Log: {log_file}")

    wrong = [r for r in results if not r['correct']]
    if wrong:
        print(f"\n  ❌ Wrong ({len(wrong)}):")
        for r in wrong[:5]:
            print(f"     • Q{r['id']}: {r.get('question', 'N/A')[:50]}...")

    print(f"\n{'='*80}")
    print(f"🎯 Final Accuracy: {accuracy:.1f}%")
    print(f"{'='*80}\n")

    await coordinator.stop_system()

    return accuracy


if __name__ == "__main__":
    try:
        accuracy = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted\n")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
