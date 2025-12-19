#!/usr/bin/env python3
"""
BMAM 消融实验脚本

测试各个模块对系统性能的贡献:
- Full: 完整系统
- -StoryArc: 移除时间线模块
- -ToM: 移除心智理论模块
- -KG: 移除知识图谱
- -Emotion: 移除情绪模块
- -HRM: 移除层次记忆管理

使用:
  python run_ablation.py                           # 在 LoCoMo 上运行全部消融
  python run_ablation.py --dataset longmemeval     # 在 LongMemEval 上运行
  python run_ablation.py --ablations story_arc tom # 只测试特定消融
  python run_ablation.py --samples 50              # 限制样本数
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
from dataclasses import dataclass

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
import logging
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
for name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss']:
    logging.getLogger(name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'ablation'


@dataclass
class AblationConfig:
    """消融配置"""
    name: str
    description: str
    enable_story_arc: bool = True
    enable_tom: bool = True
    enable_kg: bool = True
    enable_emotion: bool = True
    enable_hrm: bool = True


# 消融配置列表
ABLATION_CONFIGS = {
    'full': AblationConfig(
        name='full',
        description='完整系统 (Full BMAM)',
        enable_story_arc=True, enable_tom=True, enable_kg=True,
        enable_emotion=True, enable_hrm=True
    ),
    'no_story_arc': AblationConfig(
        name='no_story_arc',
        description='移除 StoryArc (- StoryArc)',
        enable_story_arc=False, enable_tom=True, enable_kg=True,
        enable_emotion=True, enable_hrm=True
    ),
    'no_tom': AblationConfig(
        name='no_tom',
        description='移除 Theory of Mind (- ToM)',
        enable_story_arc=True, enable_tom=False, enable_kg=True,
        enable_emotion=True, enable_hrm=True
    ),
    'no_kg': AblationConfig(
        name='no_kg',
        description='移除知识图谱 (- KG)',
        enable_story_arc=True, enable_tom=True, enable_kg=False,
        enable_emotion=True, enable_hrm=True
    ),
    'no_emotion': AblationConfig(
        name='no_emotion',
        description='移除情绪模块 (- Emotion)',
        enable_story_arc=True, enable_tom=True, enable_kg=True,
        enable_emotion=False, enable_hrm=True
    ),
    'no_hrm': AblationConfig(
        name='no_hrm',
        description='移除层次记忆管理 (- HRM)',
        enable_story_arc=True, enable_tom=True, enable_kg=True,
        enable_emotion=True, enable_hrm=False
    ),
    'hippocampus_only': AblationConfig(
        name='hippocampus_only',
        description='仅使用 Hippocampus',
        enable_story_arc=False, enable_tom=False, enable_kg=False,
        enable_emotion=False, enable_hrm=False
    ),
}


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
    if not s:
        return datetime.now()
    try:
        from dateutil import parser
        return parser.parse(s, fuzzy=True)
    except:
        return datetime.now()


async def create_coordinator(config: AblationConfig):
    """根据消融配置创建 coordinator"""

    # 设置环境变量控制模块
    os.environ['BMAM_DISABLE_STORY_ARC'] = 'true' if not config.enable_story_arc else 'false'
    os.environ['BMAM_DISABLE_TOM'] = 'true' if not config.enable_tom else 'false'
    os.environ['BMAM_DISABLE_KG'] = 'true' if not config.enable_kg else 'false'
    os.environ['BMAM_DISABLE_EMOTION'] = 'true' if not config.enable_emotion else 'false'

    from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

    base_coord = BrainInspiredCoordinator()

    if config.enable_hrm:
        from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig
        hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
        coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    else:
        coord = base_coord

    await coord.start_system()
    return coord


async def llm_judge(client: AsyncOpenAI, q: str, gold: str, gen: str) -> bool:
    """LLM 评判"""
    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {q}
Gold answer: {gold}
Generated answer: {gen}

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
        return json.loads(r.choices[0].message.content).get("label", "").upper() == "CORRECT"
    except:
        return str(gold).lower() in str(gen).lower()


async def run_locomo_ablation(config: AblationConfig, data: List[Dict],
                               llm_client: Optional[AsyncOpenAI],
                               max_samples: Optional[int] = None) -> Dict[str, Any]:
    """在 LoCoMo 数据集上运行消融实验"""

    samples = data[:max_samples] if max_samples else data
    results = []
    correct_total = 0
    question_total = 0

    for sample_idx, sample in enumerate(tqdm(samples, desc=f"  {config.name}")):
        # 清空记忆
        clear_memory()

        # 创建 coordinator
        coord = await create_coordinator(config)

        try:
            # 塑造记忆
            conv = sample['conversation']
            obs = sample.get('observation', {})
            sessions = []
            i = 1
            while f'session_{i}' in conv:
                sessions.append((
                    conv[f'session_{i}'],
                    conv.get(f'session_{i}_date_time', ''),
                    obs.get(f'session_{i}_observation', {})
                ))
                i += 1

            for idx, (dialogs, date, ob) in enumerate(sessions):
                ts = parse_date(date)
                for t in dialogs:
                    if t.get('text'):
                        await coord.store_memory_with_timestamp(
                            f"{t['speaker']}: {t['text']}", ts, t['speaker'], 0.6
                        )
                for spk, items in ob.items():
                    for it in items:
                        if isinstance(it, list) and it:
                            await coord.store_memory_with_timestamp(
                                f"[Event] {spk}: {it[0]}", ts, spk, 0.8
                            )

            # 等待巩固
            await asyncio.sleep(2)

            # 测试 QA
            sample_correct = 0
            sample_results = []

            for qa in sample['qa']:
                q, gold, cat = qa['question'], qa.get('answer', ''), qa.get('category', 0)

                context = {'skip_memory_store': True, 'evaluation_mode': True}
                r = await coord.process_user_input(q, context=context)
                gen = r.response if hasattr(r, 'response') else str(r)

                if llm_client:
                    ok = await llm_judge(llm_client, q, gold, gen)
                else:
                    ok = str(gold).lower() in str(gen).lower()

                if ok:
                    sample_correct += 1

                sample_results.append({
                    'question': q,
                    'gold': str(gold),
                    'generated': gen,
                    'correct': ok,
                    'category': cat
                })

            correct_total += sample_correct
            question_total += len(sample['qa'])

            results.append({
                'sample_id': sample['sample_id'],
                'correct': sample_correct,
                'total': len(sample['qa']),
                'accuracy': sample_correct / len(sample['qa']) if sample['qa'] else 0,
                'results': sample_results
            })

        finally:
            if hasattr(coord, 'stop_system'):
                try:
                    await coord.stop_system()
                except:
                    pass

    accuracy = correct_total / question_total if question_total > 0 else 0

    # 按类别统计
    category_stats = {}
    for sample_result in results:
        for qa_result in sample_result['results']:
            cat = qa_result['category']
            if cat not in category_stats:
                category_stats[cat] = {'correct': 0, 'total': 0}
            category_stats[cat]['total'] += 1
            if qa_result['correct']:
                category_stats[cat]['correct'] += 1

    for cat in category_stats:
        stats = category_stats[cat]
        stats['accuracy'] = stats['correct'] / stats['total'] if stats['total'] > 0 else 0

    return {
        'config': config.name,
        'description': config.description,
        'overall': {
            'correct': correct_total,
            'total': question_total,
            'accuracy': accuracy
        },
        'by_category': category_stats,
        'samples': results
    }


async def main():
    parser = argparse.ArgumentParser(description='BMAM 消融实验')
    parser.add_argument('--dataset', type=str, default='locomo',
                       choices=['locomo'],
                       help='数据集')
    parser.add_argument('--ablations', nargs='+', default=None,
                       help='要运行的消融配置 (默认全部)')
    parser.add_argument('--samples', type=int, default=None,
                       help='样本数量限制')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    print("=" * 70)
    print("BMAM 消融实验")
    print("=" * 70)
    print(f"数据集: {args.dataset}")

    # 加载数据
    if args.dataset == 'locomo':
        dataset_path = DATA_DIR / 'locomo' / 'locomo10.json'
        if not dataset_path.exists():
            print(f"错误: 数据集文件不存在: {dataset_path}")
            sys.exit(1)
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"加载 {len(data)} 组数据")

    # 确定要运行的消融配置
    if args.ablations:
        configs_to_run = [ABLATION_CONFIGS[name] for name in args.ablations if name in ABLATION_CONFIGS]
    else:
        configs_to_run = list(ABLATION_CONFIGS.values())

    print(f"\n将运行 {len(configs_to_run)} 个消融配置:")
    for cfg in configs_to_run:
        print(f"  - {cfg.name}: {cfg.description}")

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("\n✓ LLM Judge 已启用")

    # 运行消融实验
    all_results = []
    start_time = datetime.now()

    for config in configs_to_run:
        print(f"\n{'='*70}")
        print(f"运行消融: {config.name}")
        print(f"描述: {config.description}")
        print(f"{'='*70}")

        if args.dataset == 'locomo':
            result = await run_locomo_ablation(config, data, llm_client, args.samples)

        all_results.append(result)

        print(f"\n  结果: {result['overall']['accuracy']*100:.2f}% "
              f"({result['overall']['correct']}/{result['overall']['total']})")

    elapsed = (datetime.now() - start_time).total_seconds()

    # 打印汇总
    print("\n" + "=" * 70)
    print("消融实验汇总")
    print("=" * 70)
    print(f"{'配置':<20} {'准确率':>10} {'正确/总数':>15}")
    print("-" * 50)
    for result in all_results:
        print(f"{result['config']:<20} {result['overall']['accuracy']*100:>9.2f}% "
              f"{result['overall']['correct']:>6}/{result['overall']['total']:<6}")

    # 计算各模块贡献
    print("\n模块贡献分析:")
    full_acc = next((r['overall']['accuracy'] for r in all_results if r['config'] == 'full'), None)
    if full_acc:
        for result in all_results:
            if result['config'] != 'full':
                diff = (full_acc - result['overall']['accuracy']) * 100
                print(f"  {result['config']}: {diff:+.2f}% "
                      f"({'正贡献' if diff > 0 else '负贡献/无影响'})")

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_file = args.output or (RESULTS_DIR / f"ablation_{args.dataset}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    output_data = {
        'config': {
            'dataset': args.dataset,
            'samples': args.samples,
            'ablations': [cfg.name for cfg in configs_to_run],
            'timestamp': datetime.now().isoformat()
        },
        'summary': {
            cfg['config']: {
                'accuracy': cfg['overall']['accuracy'],
                'correct': cfg['overall']['correct'],
                'total': cfg['overall']['total']
            } for cfg in all_results
        },
        'results': all_results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
