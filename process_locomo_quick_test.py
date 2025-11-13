"""
Quick LoCoMo Processing Test - 快速测试
Process only first 100 QA pairs to verify memory shaping
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import sys

sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def quick_test():
    """Quick test: Process first 100 QA pairs"""
    print("=" * 60)
    print("LoCoMo Quick Test - 处理前100个QA对")
    print("=" * 60)

    # Initialize coordinator
    print("\n✅ 初始化框架...")
    coordinator = BrainInspiredCoordinator()

    # Load data
    print("✅ 加载数据...")
    with open('data/locomo/locomo10.json', 'r') as f:
        data = json.load(f)

    # Extract first 100 QA pairs
    qa_pairs = []
    for session in data:
        if 'qa' in session:
            for qa in session['qa']:
                if 'question' in qa and 'answer' in qa:
                    qa_pairs.append(qa)
                    if len(qa_pairs) >= 100:
                        break
        if len(qa_pairs) >= 100:
            break

    print(f"✅ 提取了 {len(qa_pairs)} 个QA对")

    # Process
    print("\n🧠 开始处理...")
    start_time = time.time()
    processed_count = 0

    for idx, qa in enumerate(qa_pairs):
        try:
            # Process question through coordinator
            response = await coordinator.process_input(qa['question'])
            processed_count += 1

            if (idx + 1) % 10 == 0:
                elapsed = time.time() - start_time
                speed = processed_count / elapsed if elapsed > 0 else 0
                print(f"   进度: {idx + 1}/100 ({speed:.2f} QA/秒)")

        except Exception as e:
            print(f"   ERROR at {idx}: {e}")

    # Report
    elapsed = time.time() - start_time
    print(f"\n✅ 处理完成!")
    print(f"   处理数: {processed_count}/100")
    print(f"   总时间: {elapsed:.2f}秒")
    print(f"   速度: {processed_count / elapsed:.2f} QA/秒")

    # Check memory distribution
    print(f"\n🧠 记忆分布:")
    if hasattr(coordinator, 'hippocampus') and coordinator.hippocampus:
        print(f"   Hippocampus: {len(coordinator.hippocampus.memories)} 条记忆")
    if hasattr(coordinator, 'temporal_lobe') and coordinator.temporal_lobe:
        print(f"   TemporalLobe: {len(coordinator.temporal_lobe.memories)} 条记忆")
    if hasattr(coordinator, 'amygdala') and coordinator.amygdala:
        print(f"   Amygdala: {len(coordinator.amygdala.memories)} 条记忆")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(quick_test())
