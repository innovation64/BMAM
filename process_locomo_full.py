"""
Process LoCoMo Full Dataset - 处理LoCoMo完整数据集
塑造记忆 + 检查框架瓶颈

目标:
1. 处理500+条LoCoMo对话
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('locomo_full_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import BMAM
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.memory.memory_version_manager import MemoryVersionManager


class LoCoMoProcessor:
    """LoCoMo数据处理器"""

    def __init__(self):
        self.coordinator = None
        self.version_manager = None
        self.metrics = {
            'total_conversations': 0,
            'total_memories_created': 0,
            'consolidations_performed': 0,
            'forgotten_memories': 0,
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
                auto_save_enabled=True  # 自动保存
            )

            # Auto-load latest state
            await self.version_manager.auto_load()

            logger.info("✅ 框架初始化完成")
            logger.info(f"   - Coordinator: {self.coordinator}")
            logger.info(f"   - Version Manager: 自动保存已启用")

        except Exception as e:
            logger.error(f"❌ 框架初始化失败: {e}")
            raise

    async def load_locomo_data(self, data_path: str) -> List[Dict[str, Any]]:
        """加载LoCoMo数据并提取QA pairs"""
        logger.info(f"\n📥 加载LoCoMo数据: {data_path}")

        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract QA pairs from sessions
            all_qa_pairs = []

            if isinstance(data, list):
                # Each item is a session with 'qa' key
                for session_idx, session in enumerate(data):
                    if 'qa' in session and isinstance(session['qa'], list):
                        for qa in session['qa']:
                            if 'question' in qa and 'answer' in qa:
                                all_qa_pairs.append({
                                    'user': qa['question'],
                                    'assistant': qa['answer'],
                                    'session_id': session_idx,
                                    'metadata': {
                                        'evidence': qa.get('evidence', []),
                                        'category': qa.get('category', None)
                                    }
                                })
                logger.info(f"✅ 加载了 {len(data)} 个sessions，共 {len(all_qa_pairs)} 个QA对")
                return all_qa_pairs
            else:
                # Fallback: treat as direct conversation list
                logger.info(f"✅ 加载了 {len(data)} 条对话")
                return data if isinstance(data, list) else []

        except Exception as e:
            logger.error(f"❌ 加载数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def process_conversations(
        self,
        conversations: List[Dict[str, Any]],
        batch_size: int = 50
    ):
        """处理对话并塑造记忆"""
        logger.info(f"\n🧠 开始处理对话 (共 {len(conversations)} 条)")
        logger.info(f"   批处理大小: {batch_size}")
        logger.info("=" * 60)

        total = len(conversations)
        processed = 0

        for i in range(0, total, batch_size):
            batch = conversations[i:i + batch_size]
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

        for idx, conv in enumerate(batch):
            try:
                # Extract conversation content
                if isinstance(conv, dict):
                    if 'user' in conv and 'assistant' in conv:
                        user_msg = conv['user']
                        assistant_msg = conv['assistant']
                    elif 'question' in conv and 'answer' in conv:
                        user_msg = conv['question']
                        assistant_msg = conv['answer']
                    else:
                        # Skip if format is unknown
                        continue
                else:
                    # Skip non-dict items
                    continue

                # Process through coordinator
                # This will trigger: 记忆存储 → 巩固 → 重塑 → 遗忘
                response = await self.coordinator.process_input(user_msg)

                self.metrics['total_conversations'] += 1

                # Log progress
                if idx % 10 == 0:
                    logger.info(f"      处理中: {idx + 1}/{len(batch)}")

            except Exception as e:
                logger.error(f"      ❌ 处理对话失败: {e}")
                self.metrics['bottlenecks'].append({
                    'batch': batch_num,
                    'conversation': idx,
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
            # psutil not installed
            pass

    async def create_checkpoint(self, name: str):
        """创建检查点"""
        logger.info(f"\n📦 创建检查点: {name}")

        checkpoint = await self.version_manager.create_checkpoint(
            name=name,
            description=f"LoCoMo processing checkpoint - {self.metrics['total_conversations']} conversations processed",
            tags=["locomo", "processing", "auto"]
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
            if hasattr(self.coordinator, 'hippocampus'):
                brain_stats['hippocampus'] = len(self.coordinator.hippocampus.memories)
            if hasattr(self.coordinator, 'temporal_lobe'):
                brain_stats['temporal_lobe'] = len(self.coordinator.temporal_lobe.memories)
            if hasattr(self.coordinator, 'amygdala'):
                brain_stats['amygdala'] = len(self.coordinator.amygdala.memories)

        report = {
            'timestamp': datetime.now().isoformat(),
            'processing': {
                'total_conversations': self.metrics['total_conversations'],
                'total_time_seconds': total_time,
                'average_batch_time': avg_batch_time,
                'conversations_per_second': (
                    self.metrics['total_conversations'] / total_time if total_time > 0 else 0
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
        logger.info(f"   总对话数: {report['processing']['total_conversations']}")
        logger.info(f"   总时间: {report['processing']['total_time_seconds']:.2f}s")
        logger.info(f"   平均批次时间: {report['processing']['average_batch_time']:.2f}s")
        logger.info(f"   处理速度: {report['processing']['conversations_per_second']:.2f} 对话/秒")

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
        report_path = Path(f"locomo_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"\n📄 报告已保存: {report_path}")

        return report


async def main():
    """主函数"""
    print("╔" + "=" * 58 + "╗")
    print("║  LoCoMo完整数据集处理 - Memory Shaping & Bottleneck Test   ║")
    print("╚" + "=" * 58 + "╝")

    processor = LoCoMoProcessor()

    try:
        # Step 1: Initialize
        await processor.initialize()

        # Step 2: Load data
        # Try to find LoCoMo data file
        possible_paths = [
            "data/locomo/locomo10.json",
            "/Users/liyang/Desktop/testversion/BMAM/data/locomo/locomo10.json",
            "BMAM/data/locomo/locomo10.json",
            "BMAM/data/locomo_medium_20251030_115927_final.json",
            "BMAM/data/locomo_small_20251028_162319_final.json",
            "data/locomo_data.json",
        ]

        conversations = []
        for path in possible_paths:
            if Path(path).exists():
                conversations = await processor.load_locomo_data(path)
                if conversations:
                    break

        if not conversations:
            logger.error("❌ 未找到LoCoMo数据文件")
            logger.info("请提供数据文件路径...")
            return

        # Step 3: Create initial checkpoint
        await processor.create_checkpoint("before_locomo_processing")

        # Step 4: Process conversations
        await processor.process_conversations(conversations, batch_size=50)

        # Step 5: Create final checkpoint
        await processor.create_checkpoint("after_locomo_processing")

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
