#!/usr/bin/env python3
"""
BMAM 消融实验脚本 v2.0

支持脑区级别和功能模块级别消融，验证类脑多智能体协作的优越性。

消融类型:
1. 脑区消融 (验证五脑区协作):
   - no_hippocampus: 禁用海马体 (情景记忆编码)
   - no_temporal_lobe: 禁用颞叶 (语义记忆 + KG)
   - no_amygdala: 禁用杏仁核 (显著性标记)
   - no_prefrontal: 禁用前额叶 (工作记忆控制)
   - no_basal_ganglia: 禁用基底神经节 (程序性记忆)

2. 功能模块消融:
   - no_story_arc: 禁用时间线索引
   - no_temporal_reasoning: 禁用时间推理
   - no_kg: 禁用知识图谱
   - no_hybrid_retrieval: 禁用混合检索
   - no_consolidation: 禁用记忆巩固
   - no_hrm: 禁用层次记忆管理

3. 成对组合消融 (验证协同效应):
   - no_prefrontal_temporal: 禁用前额叶+颞叶
   - no_hippocampus_amygdala: 禁用海马体+杏仁核
   - no_hippocampus_temporal: 禁用海马体+颞叶
   - no_amygdala_prefrontal: 禁用杏仁核+前额叶
   - no_kg_story_arc: 禁用KG+StoryArc

4. 极端消融 (基线对比):
   - hippocampus_only: 仅保留海马体基础记忆
   - vector_only: 仅向量检索 (类RAG基线)

使用:
  python run_ablation.py                              # 运行全部消融
  python run_ablation.py --ablations full no_story_arc no_kg  # 指定消融
  python run_ablation.py --brain-regions             # 仅脑区消融
  python run_ablation.py --components                 # 仅功能模块消融
  python run_ablation.py --pairwise                   # 仅成对组合消融 (验证协同)
  python run_ablation.py --groups 1                   # 测试1组 (快速验证)
  python run_ablation.py --groups 3                   # 测试3组 (平衡)
  python run_ablation.py --groups 10                  # 测试全部10组
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
from dataclasses import dataclass, asdict

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

# Import ablation config
from src.config.ablation_config import (
    AblationConfig, get_ablation_config, set_active_ablation,
    list_ablation_configs, ABLATION_PRESETS
)

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
MEMORY_DIR = DATA_DIR / 'memory'
STATE_DIR = DATA_DIR / 'state'
CACHE_DIR = DATA_DIR / 'cache'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'ablation'

# LoCoMo dataset path
_locomo_env = os.getenv('LOCOMO_DATASET_PATH')
LOCOMO_PATH = Path(_locomo_env) if _locomo_env else DATA_DIR / 'datasets' / 'locomo' / 'locomo10.json'


def clear_memory():
    """清空记忆文件"""
    # 数据库文件
    db_files = ['brain_memory.db', 'temporal_lobe.db', 'working_memory.db', 'kv_value_store.db',
                'memory_vectors.index', 'memory_vectors_mappings.json']
    for f in db_files:
        p = MEMORY_DIR / f
        if p.exists():
            p.unlink()

    # Memory checkpoints
    checkpoint_dir = MEMORY_DIR / 'checkpoints'
    if checkpoint_dir.exists():
        for f in checkpoint_dir.glob('*.json'):
            f.unlink()

    # 状态文件
    state_files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
                   'amygdala_state.json', 'story_arc_state.json', 'calibration_state.json']
    for f in state_files:
        p = STATE_DIR / f
        if p.exists():
            p.unlink()

    # 用户画像
    for f in ['value_profiles.json', 'user_portraits.json']:
        p = DATA_DIR / f
        if p.exists():
            p.unlink()

    # 缓存目录
    for d in ['embedding', 'knowledge_graph', 'faiss_index']:
        p = CACHE_DIR / d
        if p.exists():
            shutil.rmtree(p)

    # 旧版缓存路径
    for d in ['embedding_cache', 'knowledge_graph', 'faiss_index']:
        p = MEMORY_DIR / d
        if p.exists():
            shutil.rmtree(p)

    # 重置 StoryArc 单例
    try:
        from src.memory.story_arc import reset_story_arc_manager
        reset_story_arc_manager()
    except ImportError:
        pass


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

    # 应用消融配置到环境变量
    set_active_ablation(config)

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


# LoCoMo category mapping
CATEGORY_NAMES = {
    1: 'single-hop',
    2: 'multi-hop',
    3: 'temporal',
    4: 'open-domain',
    5: 'adversarial'
}


async def run_locomo_ablation(
    config: AblationConfig,
    data: List[Dict],
    llm_client: Optional[AsyncOpenAI],
    max_groups: int = 1
) -> Dict[str, Any]:
    """在 LoCoMo 数据集上运行消融实验"""

    samples = data[:max_groups]
    results = []
    correct_total = 0
    question_total = 0

    # 按类别统计
    category_stats = {cat: {'correct': 0, 'total': 0} for cat in CATEGORY_NAMES.values()}

    for sample_idx, sample in enumerate(samples):
        print(f"  [{sample_idx+1}/{len(samples)}] {sample['sample_id']}", end='', flush=True)

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

                # 存储对话
                for t in dialogs:
                    if t.get('text'):
                        await coord.store_memory_with_timestamp(
                            f"{t['speaker']}: {t['text']}", ts, t['speaker'], 0.6
                        )

                # 存储观察事件
                for spk, items in ob.items():
                    for it in items:
                        if isinstance(it, list) and it:
                            await coord.store_memory_with_timestamp(
                                f"[Event] {spk}: {it[0]}", ts, spk, 0.8
                            )

            # 🔥 2026-03-31: 显式触发巩固（而非等后台循环）
            # 将海马体记忆巩固到颞叶（语义+KG），确保答题时颞叶有知识
            try:
                await coord.trigger_consolidation(strategy='batch', batch_size=100)
            except Exception as e:
                logging.getLogger(__name__).debug(f"Pre-QA consolidation: {e}")

            # 测试 QA
            sample_correct = 0
            sample_results = []

            for qa in sample['qa']:
                q, gold = qa['question'], qa.get('answer', '')
                cat_id = qa.get('category', 1)
                cat_name = CATEGORY_NAMES.get(cat_id, 'unknown')

                context = {'skip_memory_store': True, 'evaluation_mode': True}
                r = await coord.process_user_input(q, context=context)
                gen = r.response if hasattr(r, 'response') else str(r)

                if llm_client:
                    ok = await llm_judge(llm_client, q, gold, gen)
                else:
                    ok = str(gold).lower() in str(gen).lower()

                if ok:
                    sample_correct += 1
                    category_stats[cat_name]['correct'] += 1

                category_stats[cat_name]['total'] += 1

                sample_results.append({
                    'question': q,
                    'gold': str(gold),
                    'generated': gen,
                    'correct': ok,
                    'category': cat_name
                })

            correct_total += sample_correct
            question_total += len(sample['qa'])

            acc = sample_correct / len(sample['qa']) * 100 if sample['qa'] else 0
            print(f" → {sample_correct}/{len(sample['qa'])} ({acc:.1f}%)", flush=True)

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

    # 计算各类别准确率
    category_accuracy = {}
    for cat_name, stats in category_stats.items():
        if stats['total'] > 0:
            category_accuracy[cat_name] = {
                'correct': stats['correct'],
                'total': stats['total'],
                'accuracy': stats['correct'] / stats['total']
            }

    return {
        'config': config.name,
        'description': config.description,
        'overall': {
            'correct': correct_total,
            'total': question_total,
            'accuracy': accuracy
        },
        'by_category': category_accuracy,
        'samples': results
    }


def print_results_table(all_results: List[Dict], full_acc: float):
    """打印结果表格"""
    print("\n" + "=" * 80)
    print("消融实验结果汇总")
    print("=" * 80)

    # Overall accuracy
    print(f"\n{'配置':<25} {'总精度':>10} {'Δ':>8} {'正确/总数':>15}")
    print("-" * 60)

    for result in all_results:
        acc = result['overall']['accuracy'] * 100
        diff = (result['overall']['accuracy'] - full_acc) * 100 if result['config'] != 'full' else 0
        diff_str = f"{diff:+.2f}%" if result['config'] != 'full' else '--'
        print(f"{result['config']:<25} {acc:>9.2f}% {diff_str:>8} "
              f"{result['overall']['correct']:>6}/{result['overall']['total']:<6}")

    # Per-category breakdown (if available)
    if all_results and 'by_category' in all_results[0] and all_results[0]['by_category']:
        categories = list(all_results[0]['by_category'].keys())
        print(f"\n{'配置':<20}", end='')
        for cat in categories:
            print(f" {cat[:8]:>10}", end='')
        print()
        print("-" * (20 + len(categories) * 11))

        for result in all_results:
            print(f"{result['config']:<20}", end='')
            for cat in categories:
                if cat in result['by_category']:
                    acc = result['by_category'][cat]['accuracy'] * 100
                    print(f" {acc:>9.1f}%", end='')
                else:
                    print(f" {'--':>10}", end='')
            print()


async def main():
    parser = argparse.ArgumentParser(description='BMAM 消融实验 v2.0')
    parser.add_argument('--ablations', nargs='+', default=None,
                       help='要运行的消融配置 (默认全部)')
    parser.add_argument('--brain-regions', action='store_true',
                       help='仅运行脑区消融')
    parser.add_argument('--components', action='store_true',
                       help='仅运行功能模块消融')
    parser.add_argument('--pairwise', action='store_true',
                       help='仅运行成对组合消融 (验证组件协同效应)')
    parser.add_argument('--groups', type=int, default=1,
                       help='测试组数 (1-10)')
    parser.add_argument('--list', action='store_true',
                       help='列出所有可用消融配置')
    parser.add_argument('--output', type=str, default=None,
                       help='输出文件路径')
    args = parser.parse_args()

    # 列出配置
    if args.list:
        print("可用消融配置:")
        print("-" * 60)
        for name, desc in list_ablation_configs().items():
            print(f"  {name:<25} {desc}")
        return

    print("=" * 80)
    print("BMAM 消融实验 v2.0 - 验证类脑多智能体协作优越性")
    print("=" * 80)

    # 确定要运行的消融配置
    if args.ablations:
        configs_to_run = [get_ablation_config(name) for name in args.ablations]
    elif args.brain_regions:
        configs_to_run = [
            get_ablation_config('full'),
            get_ablation_config('no_hippocampus'),
            get_ablation_config('no_temporal_lobe'),
            get_ablation_config('no_amygdala'),
            get_ablation_config('no_prefrontal'),
            get_ablation_config('no_basal_ganglia'),
        ]
    elif args.components:
        configs_to_run = [
            get_ablation_config('full'),
            get_ablation_config('no_story_arc'),
            get_ablation_config('no_temporal_reasoning'),
            get_ablation_config('no_kg'),
            get_ablation_config('no_hybrid_retrieval'),
            get_ablation_config('no_consolidation'),
        ]
    elif args.pairwise:
        configs_to_run = [
            get_ablation_config('full'),
            get_ablation_config('no_prefrontal_temporal'),
            get_ablation_config('no_hippocampus_amygdala'),
            get_ablation_config('no_hippocampus_temporal'),
            get_ablation_config('no_amygdala_prefrontal'),
            get_ablation_config('no_kg_story_arc'),
        ]
    else:
        # 默认: 完整 + 主要消融
        configs_to_run = [
            get_ablation_config('full'),
            get_ablation_config('no_story_arc'),
            get_ablation_config('no_kg'),
            get_ablation_config('no_temporal_reasoning'),
            get_ablation_config('hippocampus_only'),
        ]

    print(f"\n将运行 {len(configs_to_run)} 个消融配置 (每个 {args.groups} 组):")
    for cfg in configs_to_run:
        print(f"  • {cfg.name}: {cfg.description}")

    # 加载数据
    if not LOCOMO_PATH.exists():
        print(f"\n错误: 数据集文件不存在: {LOCOMO_PATH}")
        sys.exit(1)

    with open(LOCOMO_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\n✓ 加载 LoCoMo 数据集: {len(data)} 组")

    # LLM Client
    llm_client = None
    if LLM_AVAILABLE:
        llm_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )
        print("✓ LLM Judge 已启用")

    # 运行消融实验
    all_results = []
    start_time = datetime.now()

    for config in configs_to_run:
        print(f"\n{'='*80}")
        print(f"运行: {config.name}")
        print(f"描述: {config.description}")
        print(f"{'='*80}")

        result = await run_locomo_ablation(config, data, llm_client, args.groups)
        all_results.append(result)

        print(f"\n  → 总精度: {result['overall']['accuracy']*100:.2f}% "
              f"({result['overall']['correct']}/{result['overall']['total']})")

    elapsed = (datetime.now() - start_time).total_seconds()

    # 获取 full 配置的准确率作为基准
    full_acc = next((r['overall']['accuracy'] for r in all_results if r['config'] == 'full'), 0)

    # 打印结果表格
    print_results_table(all_results, full_acc)

    print(f"\n总耗时: {elapsed/60:.1f} 分钟")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = args.output or (RESULTS_DIR / f"ablation_{args.groups}g_{ts}.json")

    output_data = {
        'meta': {
            'timestamp': datetime.now().isoformat(),
            'groups': args.groups,
            'ablations': [cfg.name for cfg in configs_to_run],
            'elapsed_seconds': elapsed
        },
        'summary': {
            r['config']: {
                'accuracy': r['overall']['accuracy'],
                'correct': r['overall']['correct'],
                'total': r['overall']['total'],
                'delta': r['overall']['accuracy'] - full_acc if r['config'] != 'full' else 0,
                'by_category': r.get('by_category', {})
            } for r in all_results
        },
        'full_results': all_results
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
