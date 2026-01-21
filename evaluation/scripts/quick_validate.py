#!/usr/bin/env python3
"""
快速验证脚本 - 用于修复后的快速回归测试
每个数据集只测试少量样本，总共 ~5-10 分钟

使用:
    python evaluation/scripts/quick_validate.py           # 默认每个数据集5个样本
    python evaluation/scripts/quick_validate.py --samples 10  # 每个数据集10个样本
    python evaluation/scripts/quick_validate.py --only prefeval  # 只测试 PrefEval
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 禁用日志噪音
import warnings
warnings.filterwarnings('ignore')
import logging
logging.getLogger().setLevel(logging.CRITICAL)
for name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss']:
    logging.getLogger(name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


async def test_longmemeval(samples: int = 5) -> dict:
    """快速测试 LongMemEval"""
    print(f"\n{'='*50}")
    print(f"LongMemEval (快速测试 {samples} 样本)")
    print(f"{'='*50}")

    try:
        from evaluation.benchmarks.longmemeval.test_longmemeval import (
            clear_memory, ingest_sample, test_sample, ORACLE_PATH
        )
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
        from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig
        from openai import AsyncOpenAI
        from dotenv import load_dotenv
        load_dotenv()

        # 加载数据
        with open(ORACLE_PATH, 'r') as f:
            data = json.load(f)[:samples]
        print(f"✓ 加载 {len(data)} 样本")

        client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        correct = 0
        for i, sample in enumerate(data):
            print(f"\n[{i+1}/{len(data)}] {sample['question_id']} ({sample['question_type']})")

            # 每个样本都需要清理内存并重新塑造
            clear_memory()
            base_coord = BrainInspiredCoordinator()
            hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
            coord = HRMCoordinatorWrapper(base_coord, hrm_config)
            await coord.start_system()

            # 塑造会话历史
            await ingest_sample(coord, sample)
            await asyncio.sleep(0.5)  # 短暂巩固

            # 测试
            ok, _ = await test_sample(coord, sample, client)
            if ok:
                correct += 1
                print(f"  ✓ 正确")
            else:
                print(f"  ✗ 错误")

        acc = correct / len(data) * 100
        print(f"\n结果: {correct}/{len(data)} = {acc:.1f}%")
        return {'name': 'LongMemEval', 'correct': correct, 'total': len(data), 'acc': acc}

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return {'name': 'LongMemEval', 'error': str(e)}


async def test_prefeval(samples: int = 5) -> dict:
    """快速测试 PrefEval"""
    print(f"\n{'='*50}")
    print(f"PrefEval (快速测试 {samples} 样本)")
    print(f"{'='*50}")

    try:
        from evaluation.benchmarks.prefeval.test_prefeval import (
            load_data, test_sample, clear_memory
        )
        from openai import AsyncOpenAI
        from dotenv import load_dotenv
        load_dotenv()

        data = load_data(samples)
        print(f"✓ 加载 {len(data)} 样本")

        client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        personalized = 0
        for i, sample in enumerate(data):
            result = await test_sample(None, sample, client, i, len(data))
            if result['error_type'] == 'Personalized Response':
                personalized += 1

        rate = personalized / len(data) * 100
        print(f"\n结果: {personalized}/{len(data)} = {rate:.1f}% 个性化回答")
        return {'name': 'PrefEval', 'personalized': personalized, 'total': len(data), 'rate': rate}

    except Exception as e:
        print(f"❌ 错误: {e}")
        return {'name': 'PrefEval', 'error': str(e)}


async def test_personamem(samples: int = 5, users: int = 1) -> dict:
    """快速测试 PersonaMem"""
    print(f"\n{'='*50}")
    print(f"PersonaMem (快速测试 {users} 用户, ~{samples} 题)")
    print(f"{'='*50}")

    try:
        from evaluation.benchmarks.personamem.test_personamem import (
            load_data, ingest_context, consolidate_and_synthesize_portrait,
            test_questions, clear_memory
        )
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
        from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig
        from openai import AsyncOpenAI
        from dotenv import load_dotenv
        load_dotenv()

        questions, contexts = load_data()
        print(f"✓ 加载 {len(questions)} 题, {len(contexts)} 上下文")

        # 只取前 N 个用户的上下文
        context_ids = list(contexts.keys())[:users]
        questions = [q for q in questions if q.get('shared_context_id') in context_ids][:samples]

        client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        clear_memory()
        base_coord = BrainInspiredCoordinator()
        hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
        coord = HRMCoordinatorWrapper(base_coord, hrm_config)
        await coord.start_system()

        # 塑造用户上下文
        shaped_user_ids = []
        for i, ctx_id in enumerate(context_ids):
            messages = contexts[ctx_id]
            print(f"\n[用户 {i+1}/{len(context_ids)}] {ctx_id[:16]}...")
            # 使用正确的函数名
            await ingest_context(coord, messages, max_messages=50, user_id=ctx_id)
            # 巩固阶段
            print("  ⏳ 巩固...", end='', flush=True)
            await consolidate_and_synthesize_portrait(coord, user_id=ctx_id)
            print(" done")
            shaped_user_ids.append(ctx_id)

        # 测试问题
        correct, results, _, _, tested = await test_questions(
            coord, questions, client, question_type=None, user_ids=shaped_user_ids
        )

        acc = correct / tested * 100 if tested > 0 else 0
        print(f"\n结果: {correct}/{tested} = {acc:.1f}%")
        return {'name': 'PersonaMem', 'correct': correct, 'total': tested, 'acc': acc}

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return {'name': 'PersonaMem', 'error': str(e)}


async def test_locomo(samples: int = 5) -> dict:
    """快速测试 LoCoMo (只测试1组对话)"""
    print(f"\n{'='*50}")
    print(f"LoCoMo (快速测试 1 组对话)")
    print(f"{'='*50}")

    try:
        from evaluation.benchmarks.locomo.test_sequential import (
            load_locomo_data, test_group, clear_memory
        )
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
        from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig
        from openai import AsyncOpenAI
        from dotenv import load_dotenv
        load_dotenv()

        groups = load_locomo_data()[:1]  # 只取1组
        print(f"✓ 加载 {len(groups)} 组对话")

        client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL")
        )

        clear_memory()
        base_coord = BrainInspiredCoordinator()
        hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
        coord = HRMCoordinatorWrapper(base_coord, hrm_config)
        await coord.start_system()

        group = groups[0]
        correct, total, results = await test_group(coord, client, group, 0, 1)

        acc = correct / total * 100 if total > 0 else 0
        print(f"\n结果: {correct}/{total} = {acc:.1f}%")
        return {'name': 'LoCoMo', 'correct': correct, 'total': total, 'acc': acc}

    except Exception as e:
        print(f"❌ 错误: {e}")
        return {'name': 'LoCoMo', 'error': str(e)}


async def main():
    parser = argparse.ArgumentParser(description='快速验证脚本')
    parser.add_argument('--samples', type=int, default=5, help='每个数据集的样本数')
    parser.add_argument('--only', type=str, choices=['longmemeval', 'prefeval', 'personamem', 'locomo'],
                        help='只测试指定数据集')
    args = parser.parse_args()

    print("=" * 60)
    print("BMAM 快速验证")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"样本数: {args.samples}")
    print("=" * 60)

    results = []

    if args.only:
        # 只测试指定数据集
        if args.only == 'longmemeval':
            results.append(await test_longmemeval(args.samples))
        elif args.only == 'prefeval':
            results.append(await test_prefeval(args.samples))
        elif args.only == 'personamem':
            results.append(await test_personamem(args.samples, users=1))
        elif args.only == 'locomo':
            results.append(await test_locomo(args.samples))
    else:
        # 测试全部 (顺序: 快 → 慢)
        results.append(await test_longmemeval(args.samples))
        results.append(await test_prefeval(args.samples))
        results.append(await test_personamem(args.samples, users=1))
        # LoCoMo 太慢，默认跳过
        # results.append(await test_locomo(args.samples))

    # 汇总
    print("\n" + "=" * 60)
    print("汇总结果")
    print("=" * 60)

    for r in results:
        name = r['name']
        if 'error' in r:
            print(f"  {name}: ❌ {r['error']}")
        elif 'rate' in r:
            print(f"  {name}: {r['rate']:.1f}% ({r['personalized']}/{r['total']})")
        else:
            print(f"  {name}: {r['acc']:.1f}% ({r['correct']}/{r['total']})")

    # 保存结果
    results_dir = PROJECT_ROOT / 'evaluation' / 'results' / 'quick_validate'
    results_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(results_dir / f'result_{ts}.json', 'w') as f:
        json.dump({
            'timestamp': ts,
            'samples': args.samples,
            'results': results
        }, f, indent=2)

    print(f"\n结果已保存到: {results_dir / f'result_{ts}.json'}")


if __name__ == '__main__':
    asyncio.run(main())
