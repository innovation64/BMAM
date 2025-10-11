"""
LoCoMo 20题测试 - 最终版
保留完整的记忆重塑流程，优化进度显示
"""

import asyncio
import json
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

# 配置日志：ERROR到命令行，其他到文件
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
from evaluation.llm_judge_locomo import LoCoMoLLMJudge


def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    """打印进度条"""
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='', flush=True)
    if iteration == total:
        print()


async def main():
    print("=" * 80)
    print("🧪 LoCoMo 20-Question Test")
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
    print(f"📊 Sessions: {len(needed_sessions)} (with memory reshaping)")
    print(f"📊 Log: {log_file}")

    coordinator = BrainInspiredCoordinator()
    judge = LoCoMoLLMJudge()

    # ============================================================================
    # Phase 1: 学习Sessions（包含记忆重塑、巩固、神经可塑性更新）
    # ============================================================================
    print(f"\n{'='*80}")
    print("📚 Phase 1: Learning with Memory Reshaping")
    print(f"{'='*80}")
    print("\n  ℹ️  Each dialogue goes through:")
    print("     • Memory encoding & embedding")
    print("     • Distributed memory allocation (brain regions)")
    print("     • Neural plasticity updates")
    print("     • This ensures proper memory consolidation\n")

    total_turns = 0
    turns_learned = 0

    # 预计算总turns
    for session_num in needed_sessions:
        session_key = f'session_{session_num}'
        session_dialogues = conversation.get(session_key, [])
        total_turns += len([t for t in session_dialogues if t.get('text')])

    print(f"  Total turns to learn: {total_turns}")
    print(f"  Estimated time: {total_turns * 0.8:.0f}-{total_turns * 1.2:.0f} seconds ({total_turns * 0.8/60:.1f}-{total_turns * 1.2/60:.1f} min)\n")

    start_learn = datetime.now()

    for session_num in needed_sessions:
        session_key = f'session_{session_num}'
        session_date = conversation.get(f'{session_key}_date_time', 'Unknown')
        session_dialogues = conversation.get(session_key, [])

        for turn in session_dialogues:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')
            if text:
                context_text = f"On {session_date}, {speaker} said: '{text}'"
                await coordinator.process_user_input(context_text)
                turns_learned += 1

                # 更新进度条
                elapsed = (datetime.now() - start_learn).total_seconds()
                speed = turns_learned / elapsed if elapsed > 0 else 0
                eta = (total_turns - turns_learned) / speed if speed > 0 else 0

                print_progress_bar(
                    turns_learned,
                    total_turns,
                    prefix='  Learning',
                    suffix=f'{turns_learned}/{total_turns} | {speed:.1f} turns/s | ETA: {eta:.0f}s',
                    length=45
                )

    learn_time = (datetime.now() - start_learn).total_seconds()
    print(f"\n✅ Learning completed in {learn_time:.1f}s ({learn_time/60:.1f} min)")
    print(f"   Speed: {turns_learned/learn_time:.2f} turns/second\n")

    # ============================================================================
    # Phase 2: 测试Questions
    # ============================================================================
    print(f"{'='*80}")
    print("❓ Phase 2: Testing Questions")
    print(f"{'='*80}\n")

    results = []
    correct_count = 0
    start_test = datetime.now()

    for i, qa in enumerate(qa_list, 1):
        question = qa['question']
        gold_answer = str(qa['answer'])

        try:
            print(f"  Q{i:2d}: {question[:63]}...")

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
            print(f"       {icon} {answer[:56]}... ({elapsed:.1f}s, {memories}mem)")

            # 进度条
            test_elapsed = (datetime.now() - start_test).total_seconds()
            avg_time = test_elapsed / i
            eta = avg_time * (len(qa_list) - i)

            print_progress_bar(
                i,
                len(qa_list),
                prefix=f'  Testing',
                suffix=f'{correct_count}/{i} correct ({100*correct_count/i:.0f}%) | ETA: {eta:.0f}s',
                length=45
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

    test_time = (datetime.now() - start_test).total_seconds()
    total_time = learn_time + test_time

    # ============================================================================
    # 最终统计
    # ============================================================================
    print(f"\n{'='*80}")
    print("📊 Final Results")
    print(f"{'='*80}\n")

    total = len(results)
    accuracy = (correct_count / total * 100) if total > 0 else 0

    print(f"  ✅ Accuracy: {correct_count}/{total} = {accuracy:.1f}%")
    print(f"  ⏱️  Learning Time: {learn_time/60:.1f} min")
    print(f"  ⏱️  Testing Time: {test_time/60:.1f} min")
    print(f"  ⏱️  Total Time: {total_time/60:.1f} min")

    avg_mem = sum(r['memories'] for r in results) / total if total > 0 else 0
    print(f"  💾 Avg Memories: {avg_mem:.1f}")

    # 保存结果
    output_file = f"results/locomo_20q_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'sample_id': sample['sample_id'],
            'accuracy': accuracy,
            'learn_time': learn_time,
            'test_time': test_time,
            'total_time': total_time,
            'sessions_learned': list(needed_sessions),
            'turns_learned': turns_learned,
            'results': results
        }, f, indent=2)

    print(f"\n  💾 Results: {output_file}")
    print(f"  📝 Log: {log_file}")

    # 错误分析
    wrong = [r for r in results if not r['correct']]
    if wrong:
        print(f"\n  ❌ Wrong Answers ({len(wrong)}):")
        for r in wrong[:5]:
            print(f"     • Q{r['id']}: {r.get('question', 'N/A')[:48]}...")

    print(f"\n{'='*80}")
    print(f"🎯 Final Accuracy: {accuracy:.1f}%")
    print(f"{'='*80}\n")

    await coordinator.stop_system()

    return accuracy


if __name__ == "__main__":
    try:
        accuracy = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user\n")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
