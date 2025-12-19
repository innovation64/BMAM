#!/usr/bin/env python3
"""
LoCoMo 评估脚本

封装现有的 LoCoMo 测试脚本，提供统一的评估接口

原始脚本位置: experiments/benchmarks/locomo/test_sequential.py

使用:
  python eval_locomo.py --groups 10         # 测试10组
  python eval_locomo.py --groups 1          # 快速测试1组
  python eval_locomo.py --questions 20      # 每组只测20题
"""

import asyncio
import json
import os
import sys
import argparse
import time
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
import logging
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
LOCOMO_DATA = DATA_DIR / 'locomo' / 'locomo10.json'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'locomo'


def clear_memory():
    """清空记忆文件"""
    files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
             'amygdala_state.json', 'brain_memory.db', 'temporal_lobe.db', 'working_memory.db',
             'story_arc_state.json', 'tom_state.json', 'kv_value_store.db']
    for f in files:
        p = DATA_DIR / f
        if p.exists():
            p.unlink()
    for d in ['embedding_cache', 'knowledge_graph', 'faiss_index']:
        p = DATA_DIR / d
        if p.exists():
            shutil.rmtree(p)


def parse_date(s: str) -> datetime:
    """解析日期字符串"""
    if not s:
        return datetime.now()
    try:
        from dateutil import parser
        return parser.parse(s, fuzzy=True)
    except:
        return datetime.now()


def load_locomo_data() -> List[Dict]:
    """加载 LoCoMo 数据集"""
    if not LOCOMO_DATA.exists():
        # 尝试备用路径
        alt_path = PROJECT_ROOT / 'datasets' / 'locomo' / 'locomo10.json'
        if alt_path.exists():
            with open(alt_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        print(f"❌ 数据集不存在: {LOCOMO_DATA}")
        print(f"   也未找到备用路径: {alt_path}")
        return []

    with open(LOCOMO_DATA, 'r', encoding='utf-8') as f:
        return json.load(f)


async def llm_judge(client: AsyncOpenAI, question: str, gold: str, generated: str) -> bool:
    """使用 LLM 评判答案正确性"""
    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {question}
Gold answer: {gold}
Generated answer: {generated}

Be generous: same meaning = CORRECT. Same date different format = CORRECT.
Return JSON: {{"label": "CORRECT" or "WRONG"}}"""

    try:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert grader"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        result = json.loads(r.choices[0].message.content)
        return result.get("label", "").upper() == "CORRECT"
    except:
        # Fallback: 字符串匹配
        return str(gold).lower() in str(generated).lower()


async def ingest_conversation(coord: HRMCoordinatorWrapper, sample: Dict) -> None:
    """将对话塑造为记忆"""
    conv = sample.get('conversation', [])

    for turn in conv:
        speaker = turn.get('speaker', 'User')
        text = turn.get('text', '')
        ts_str = turn.get('timestamp', '')
        ts = parse_date(ts_str)

        # 计算重要性
        importance = 0.7
        if any(k in text.lower() for k in ['important', 'remember', 'birthday', 'anniversary']):
            importance = 0.9
        elif any(k in text.lower() for k in ['prefer', 'like', 'love', 'hate']):
            importance = 0.8

        await coord.store_memory_with_timestamp(
            f"{speaker}: {text}",
            ts,
            speaker,
            importance
        )


async def run_locomo_evaluation(num_groups: int = 10,
                                  max_questions: Optional[int] = None,
                                  llm_client: Optional[AsyncOpenAI] = None) -> Dict[str, Any]:
    """
    运行 LoCoMo 评估

    Args:
        num_groups: 测试的组数 (最多10组)
        max_questions: 每组最大问题数
        llm_client: LLM 客户端用于评判
    """
    print("=" * 70)
    print("LoCoMo 评估")
    print("=" * 70)

    # 加载数据
    data = load_locomo_data()
    if not data:
        return {'error': 'Failed to load dataset'}

    print(f"✓ 加载 {len(data)} 个 sessions")
    print(f"✓ 测试 {min(num_groups, len(data))} 组")

    all_results = []
    results_by_category = {}

    start_time = time.time()

    for group_idx, sample in enumerate(data[:num_groups]):
        print(f"\n{'='*50}")
        print(f"组 {group_idx + 1}/{num_groups}: {sample.get('conversation_id', f'conv-{group_idx}')}")
        print(f"{'='*50}")

        # 清空记忆
        clear_memory()

        # 初始化
        base_coord = BrainInspiredCoordinator()
        hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
        coord = HRMCoordinatorWrapper(base_coord, hrm_config)
        await coord.start_system()

        try:
            # 塑造对话记忆
            print("  塑造记忆...")
            await ingest_conversation(coord, sample)
            await asyncio.sleep(1)

            # 获取问题
            questions = sample.get('questions', [])
            if max_questions:
                questions = questions[:max_questions]

            print(f"  测试 {len(questions)} 个问题...")

            group_results = []

            for q_idx, q in enumerate(tqdm(questions, desc="  问题", leave=False)):
                question_text = q.get('question', '')
                gold_answer = q.get('answer', '')
                category = q.get('category', 'other')

                if not question_text:
                    continue

                # 查询
                context = {'skip_memory_store': True, 'evaluation_mode': True}
                result = await coord.process_user_input(question_text, context=context)

                if hasattr(result, 'response'):
                    generated = result.response
                elif isinstance(result, dict):
                    generated = result.get('response', str(result))
                else:
                    generated = str(result)

                # 评判
                if llm_client:
                    is_correct = await llm_judge(llm_client, question_text, gold_answer, generated)
                else:
                    is_correct = gold_answer.lower() in generated.lower()

                q_result = {
                    'group': group_idx,
                    'question': question_text,
                    'gold': gold_answer,
                    'generated': generated,
                    'category': category,
                    'is_correct': is_correct
                }

                group_results.append(q_result)
                all_results.append(q_result)

                # 按类别统计
                if category not in results_by_category:
                    results_by_category[category] = {'correct': 0, 'total': 0}
                results_by_category[category]['total'] += 1
                if is_correct:
                    results_by_category[category]['correct'] += 1

            # 组统计
            group_correct = sum(1 for r in group_results if r['is_correct'])
            group_total = len(group_results)
            group_acc = group_correct / group_total if group_total > 0 else 0

            print(f"  组准确率: {group_acc*100:.1f}% ({group_correct}/{group_total})")

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    elapsed = time.time() - start_time

    # 总体统计
    total_correct = sum(1 for r in all_results if r['is_correct'])
    total_questions = len(all_results)
    overall_acc = total_correct / total_questions if total_questions > 0 else 0

    print("\n" + "=" * 70)
    print("LoCoMo 评估结果")
    print("=" * 70)

    print(f"\n总体准确率: {overall_acc*100:.2f}% ({total_correct}/{total_questions})")

    print("\n按类别准确率:")
    for cat, stats in sorted(results_by_category.items()):
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {cat:>20}: {acc*100:.1f}% ({stats['correct']}/{stats['total']})")

    print(f"\n耗时: {elapsed/60:.1f} 分钟")

    return {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'num_groups': num_groups,
            'max_questions': max_questions
        },
        'summary': {
            'overall_accuracy': overall_acc,
            'correct': total_correct,
            'total': total_questions
        },
        'by_category': {
            cat: {
                'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0,
                **stats
            }
            for cat, stats in results_by_category.items()
        },
        'elapsed_seconds': elapsed,
        'detailed_results': all_results
    }


async def main():
    parser = argparse.ArgumentParser(description='LoCoMo 评估')
    parser.add_argument('--groups', type=int, default=10,
                       help='测试组数 (默认10)')
    parser.add_argument('--questions', type=int, default=None,
                       help='每组最大问题数')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM Judge 已启用")

    results = await run_locomo_evaluation(
        num_groups=args.groups,
        max_questions=args.questions,
        llm_client=llm_client
    )

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"locomo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    # 移除详细结果以减小文件大小
    results_to_save = {k: v for k, v in results.items() if k != 'detailed_results'}

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results_to_save, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
