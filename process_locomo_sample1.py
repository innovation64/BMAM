"""
Process LoCoMo Sample 1 - 处理第1个sample的对话
塑造记忆 + 检查框架瓶颈

目标:
1. 处理第1个sample的所有对话轮次 (~419个)
2. 自动巩固/重塑/遗忘
3. 检测框架瓶颈（性能、记忆）
4. 生成记忆塑造报告
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('locomo_sample1_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.memory.memory_version_manager import MemoryVersionManager


class LoCoMoSample1Processor:
    """LoCoMo Sample 1 处理器"""

    def __init__(self):
        self.coordinator = None
        self.version_manager = None
        self.metrics = {
            'total_dialogs': 0,
            'total_memories_created': 0,
            'processing_times': [],
            'memory_usage': [],
            'bottlenecks': []
        }

    async def initialize(self):
        """初始化框架"""
        logger.info("=" * 60)
        logger.info("初始化BMAM框架...")
        logger.info("=" * 60)

        try:
            # Initialize coordinator
            self.coordinator = BrainInspiredCoordinator()

            # Initialize version manager
            self.version_manager = MemoryVersionManager(
                coordinator=self.coordinator,
                auto_save_enabled=True
            )

            # Auto-load latest state
            await self.version_manager.auto_load()

            logger.info("✅ 框架初始化完成")

        except Exception as e:
            logger.error(f"❌ 框架初始化失败: {e}")
            raise

    async def load_sample1_dialogs(self, data_path: str) -> List[Dict[str, Any]]:
        """加载Sample 1的所有对话轮次"""
        logger.info(f"\n📥 加载LoCoMo Sample 1: {data_path}")

        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract dialog turns from first sample
            sample = data[0]  # First sample only
            dialogs = []

            if 'conversation' in sample:
                conv = sample['conversation']
                # Extract all sessions
                for key, value in conv.items():
                    if key.startswith('session_') and not key.endswith('_date_time'):
                        if isinstance(value, list):
                            for dialog in value:
                                if 'text' in dialog:
                                    dialogs.append({
                                        'text': dialog['text'],
                                        'speaker': dialog.get('speaker', 'Unknown'),
                                        'dia_id': dialog.get('dia_id', ''),
                                        'session': key
                                    })

            logger.info(f"✅ 提取了 {len(dialogs)} 个对话轮次")
            return dialogs

        except Exception as e:
            logger.error(f"❌ 加载数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def process_dialogs(
        self,
        dialogs: List[Dict[str, Any]],
        batch_size: int = 50
    ):
        """处理对话并塑造记忆"""
        logger.info(f"\n🧠 开始处理对话 (共 {len(dialogs)} 轮)")
        logger.info(f"   批处理大小: {batch_size}")
        logger.info("=" * 60)

        total = len(dialogs)
        processed = 0

        for i in range(0, total, batch_size):
            batch = dialogs[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(f"\n📦 处理批次 {batch_num}/{total_batches}")

            # Process batch
            await self._process_batch(batch, batch_num)

            processed += len(batch)
            progress = (processed / total) * 100

            logger.info(f"   进度: {processed}/{total} ({progress:.1f}%)")

            # Auto-save after each batch
            logger.info(f"   💾 自动保存...")
            await self.version_manager.auto_save()

            # Check memory usage
            self._check_memory_usage()

        logger.info(f"\n✅ 所有对话处理完成!")

    async def _process_batch(self, batch: List[Dict[str, Any]], batch_num: int):
        """处理一批对话"""
        start_time = time.time()

        for idx, dialog in enumerate(batch):
            try:
                # Process dialog text through coordinator
                # This will trigger: 记忆存储 → 巩固 → 重塑 → 遗忘
                response = await self.coordinator.process_input(dialog['text'])

                self.metrics['total_dialogs'] += 1

                # Log progress
                if idx % 10 == 0:
                    logger.info(f"      处理中: {idx + 1}/{len(batch)}")

            except Exception as e:
                logger.error(f"      ❌ 处理对话失败: {e}")
                self.metrics['bottlenecks'].append({
                    'batch': batch_num,
                    'dialog': idx,
                    'error': str(e)
                })

        # Batch processing time
        elapsed = time.time() - start_time
        self.metrics['processing_times'].append(elapsed)

        logger.info(f"   ⏱️  批次处理时间: {elapsed:.2f}s")

    def _check_memory_usage(self):
        """检查内存使用情况"""
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024

            self.metrics['memory_usage'].append(memory_mb)

            if memory_mb > 1000:  # > 1GB
                logger.warning(f"   ⚠️  内存使用较高: {memory_mb:.1f} MB")

        except ImportError:
            pass

    async def create_checkpoint(self, name: str):
        """创建检查点"""
        logger.info(f"\n📦 创建检查点: {name}")

        checkpoint = await self.version_manager.create_checkpoint(
            name=name,
            description=f"LoCoMo Sample 1 - {self.metrics['total_dialogs']} dialogs processed",
            tags=["locomo", "sample1", "auto"]
        )

        if checkpoint:
            logger.info(f"✅ 检查点已创建: {checkpoint.archive_path}")
        else:
            logger.error(f"❌ 检查点创建失败")

    def generate_report(self) -> Dict[str, Any]:
        """生成处理报告"""
        logger.info("\n" + "=" * 60)
        logger.info("生成处理报告...")
        logger.info("=" * 60)

        # Calculate statistics
        total_time = sum(self.metrics['processing_times'])
        avg_batch_time = (
            sum(self.metrics['processing_times']) / len(self.metrics['processing_times'])
            if self.metrics['processing_times'] else 0
        )

        avg_memory = (
            sum(self.metrics['memory_usage']) / len(self.metrics['memory_usage'])
            if self.metrics['memory_usage'] else 0
        )

        max_memory = max(self.metrics['memory_usage']) if self.metrics['memory_usage'] else 0

        # Get brain region stats
        brain_stats = {}
        if self.coordinator:
            if hasattr(self.coordinator, 'hippocampus') and self.coordinator.hippocampus:
                brain_stats['hippocampus'] = len(self.coordinator.hippocampus.memories)
            if hasattr(self.coordinator, 'temporal_lobe') and self.coordinator.temporal_lobe:
                brain_stats['temporal_lobe'] = len(self.coordinator.temporal_lobe.memories)
            if hasattr(self.coordinator, 'amygdala') and self.coordinator.amygdala:
                brain_stats['amygdala'] = len(self.coordinator.amygdala.memories)

        report = {
            'timestamp': datetime.now().isoformat(),
            'processing': {
                'total_dialogs': self.metrics['total_dialogs'],
                'total_time_seconds': total_time,
                'average_batch_time': avg_batch_time,
                'dialogs_per_second': (
                    self.metrics['total_dialogs'] / total_time if total_time > 0 else 0
                )
            },
            'memory_usage': {
                'average_mb': avg_memory,
                'peak_mb': max_memory
            },
            'brain_regions': brain_stats,
            'bottlenecks': self.metrics['bottlenecks']
        }

        # Print report
        logger.info(f"\n📊 处理统计:")
        logger.info(f"   总对话轮次: {report['processing']['total_dialogs']}")
        logger.info(f"   总时间: {report['processing']['total_time_seconds']:.2f}s")
        logger.info(f"   平均批次时间: {report['processing']['average_batch_time']:.2f}s")
        logger.info(f"   处理速度: {report['processing']['dialogs_per_second']:.2f} 对话/秒")

        logger.info(f"\n💾 内存使用:")
        logger.info(f"   平均: {report['memory_usage']['average_mb']:.1f} MB")
        logger.info(f"   峰值: {report['memory_usage']['peak_mb']:.1f} MB")

        logger.info(f"\n🧠 脑区记忆:")
        for region, count in brain_stats.items():
            logger.info(f"   {region}: {count} 条记忆")

        if self.metrics['bottlenecks']:
            logger.warning(f"\n⚠️  发现 {len(self.metrics['bottlenecks'])} 个瓶颈:")
            for bottleneck in self.metrics['bottlenecks'][:5]:  # Show first 5
                logger.warning(f"   - Batch {bottleneck['batch']}: {bottleneck['error']}")

        # Save report to file
        report_path = Path(f"locomo_sample1_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"\n📄 报告已保存: {report_path}")

        return report


async def main():
    """主函数"""
    print("╔" + "=" * 58 + "╗")
    print("║  LoCoMo Sample 1 处理 - Memory Shaping & Bottleneck Test  ║")
    print("╚" + "=" * 58 + "╝")

    processor = LoCoMoSample1Processor()

    try:
        # Step 1: Initialize
        await processor.initialize()

        # Step 2: Load Sample 1 dialogs
        data_path = "data/locomo/locomo10.json"
        dialogs = await processor.load_sample1_dialogs(data_path)

        if not dialogs:
            logger.error("❌ 未找到对话数据")
            return

        # Step 3: Create initial checkpoint
        await processor.create_checkpoint("before_sample1_processing")

        # Step 4: Process dialogs
        await processor.process_dialogs(dialogs, batch_size=50)

        # Step 5: Create final checkpoint
        await processor.create_checkpoint("after_sample1_processing")

        # Step 6: Generate report
        report = processor.generate_report()

        logger.info("\n" + "=" * 60)
        logger.info("✅ 处理完成!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ 处理过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
