#!/usr/bin/env python3
"""
单样本测试脚本 - 用于快速验证修复效果
"""
import sys
import asyncio
from pathlib import Path

# Use relative path instead of hardcoded absolute path
_BMAM_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(_BMAM_ROOT))

from tests.test_locomo_10samples_full import (
    load_locomo_data,
    test_single_sample,
    clear_all_memory_files,
    LLM_JUDGE_AVAILABLE
)
from pathlib import Path
from datetime import datetime
import json
import os

async def main():
    sample_idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    print("="*60)
    print(f"Single Sample Test: Index {sample_idx}")
    print(f"  LLM Judge: {'✓' if LLM_JUDGE_AVAILABLE else '✗ (fallback)'}")
    print("="*60)

    # 清空记忆
    print("\n[1/4] 清空记忆文件...")
    clear_all_memory_files()

    # LLM Judge
    llm_client = None
    if LLM_JUDGE_AVAILABLE:
        try:
            from openai import AsyncOpenAI
            from dotenv import load_dotenv
            load_dotenv()
            llm_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL")
            )
        except Exception as e:
            print(f"  ⚠️ LLM Judge init failed: {e}")

    # 加载数据
    print("[2/4] 加载数据...")
    data = load_locomo_data()
    sample = data[sample_idx]
    sample_id = sample.get('sample_id', f'sample-{sample_idx}')
    print(f"  Sample: {sample_id}, QA: {len(sample.get('qa', []))} questions")

    # 运行测试
    print(f"[3/4] 运行测试 (塑造 + QA)...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = await test_single_sample(sample_idx, sample, llm_client, timestamp)

    # 结果
    print("\n" + "="*60)
    print("[4/4] 测试结果")
    print("="*60)

    qa = result['qa']
    print(f"\n📊 Overall: {qa['correct']}/{qa['total']} = {qa['accuracy']*100:.1f}%")

    print("\n📈 Category Breakdown:")
    for cat, stats in sorted(result['categories'].items()):
        pct = stats['correct']/stats['total']*100 if stats['total'] > 0 else 0
        bar = '█' * int(pct/5) + '░' * (20 - int(pct/5))
        print(f"  {cat}: {stats['correct']:3d}/{stats['total']:3d} ({pct:5.1f}%) |{bar}|")

    # 保存结果
    metrics_dir = Path(__file__).parent.parent / 'metrics' / 'locomo_bmam_full'
    metrics_dir.mkdir(parents=True, exist_ok=True)
    result_file = metrics_dir / f'single_sample_{sample_id}_{timestamp}.json'
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n💾 Results saved: {result_file.name}")


if __name__ == '__main__':
    asyncio.run(main())
