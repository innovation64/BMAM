#!/usr/bin/env python3
"""
Checkpoint Manager for Long-Running Evaluations
评测检查点管理器 - 支持断点续跑

🔥 2025-12-26: 应对网络不稳定导致的测试中断

功能:
1. 定期保存进度
2. 崩溃后从上次检查点恢复
3. 支持任意评测脚本
4. 自动备份，防止checkpoint损坏

使用示例:
    from evaluation.checkpoint_manager import CheckpointManager

    checkpoint = CheckpointManager("locomo_test")

    # 检查是否有未完成的checkpoint
    if checkpoint.has_checkpoint():
        completed_ids = checkpoint.load()
        print(f"✅ 从checkpoint恢复，已完成 {len(completed_ids)} 题")
    else:
        completed_ids = set()

    # 处理每个题目
    for sample in samples:
        if sample['id'] in completed_ids:
            print(f"⏭️  跳过已完成: {sample['id']}")
            continue

        # 处理题目...
        result = process_sample(sample)

        # 保存checkpoint（每题都保存）
        completed_ids.add(sample['id'])
        checkpoint.save(completed_ids)

    # 完成后清理checkpoint
    checkpoint.clear()
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, Any, Optional


class CheckpointManager:
    """评测检查点管理器"""

    def __init__(self, test_name: str, checkpoint_dir: Optional[Path] = None):
        """
        初始化checkpoint管理器

        Args:
            test_name: 测试名称 (e.g., "locomo_20251226", "longmemeval")
            checkpoint_dir: checkpoint保存目录（默认：evaluation/checkpoints/）
        """
        if checkpoint_dir is None:
            # 默认目录
            project_root = Path(__file__).parent.parent
            checkpoint_dir = project_root / 'evaluation' / 'checkpoints'

        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.test_name = test_name
        self.checkpoint_file = self.checkpoint_dir / f"{test_name}_checkpoint.json"
        self.backup_file = self.checkpoint_dir / f"{test_name}_checkpoint.backup.json"

    def has_checkpoint(self) -> bool:
        """检查是否存在checkpoint"""
        return self.checkpoint_file.exists()

    def load(self) -> Set[str]:
        """
        加载checkpoint

        Returns:
            已完成的sample ID集合
        """
        if not self.has_checkpoint():
            return set()

        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            completed_ids = set(data.get('completed_ids', []))
            metadata = data.get('metadata', {})

            print(f"📂 加载checkpoint: {self.test_name}")
            print(f"   已完成: {len(completed_ids)} 题")
            print(f"   保存时间: {metadata.get('last_updated', 'unknown')}")
            print(f"   总耗时: {metadata.get('elapsed_time', 'unknown')}")

            return completed_ids

        except Exception as e:
            print(f"⚠️  加载checkpoint失败: {e}")

            # 尝试从备份恢复
            if self.backup_file.exists():
                try:
                    with open(self.backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    completed_ids = set(data.get('completed_ids', []))
                    print(f"✅ 从备份恢复: {len(completed_ids)} 题")
                    return completed_ids
                except Exception as backup_error:
                    print(f"❌ 备份文件也损坏: {backup_error}")

            return set()

    def save(self, completed_ids: Set[str], metadata: Optional[Dict[str, Any]] = None):
        """
        保存checkpoint

        Args:
            completed_ids: 已完成的sample ID集合
            metadata: 额外的元数据（如总题数、当前精度等）
        """
        try:
            # 备份旧checkpoint
            if self.checkpoint_file.exists():
                import shutil
                shutil.copy2(self.checkpoint_file, self.backup_file)

            # 构建checkpoint数据
            checkpoint_data = {
                'test_name': self.test_name,
                'completed_ids': sorted(list(completed_ids)),  # 排序便于查看
                'total_completed': len(completed_ids),
                'metadata': metadata or {},
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            # 写入checkpoint
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️  保存checkpoint失败: {e}")

    def clear(self):
        """清理checkpoint（测试完成后调用）"""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                print(f"🗑️  清理checkpoint: {self.test_name}")

            if self.backup_file.exists():
                self.backup_file.unlink()
        except Exception as e:
            print(f"⚠️  清理checkpoint失败: {e}")

    def get_progress(self, total: int) -> Dict[str, Any]:
        """
        获取进度信息

        Args:
            total: 总题数

        Returns:
            进度信息字典
        """
        completed = len(self.load()) if self.has_checkpoint() else 0
        return {
            'completed': completed,
            'total': total,
            'progress': f"{completed}/{total}",
            'percentage': f"{100 * completed / total:.1f}%" if total > 0 else "0%"
        }
