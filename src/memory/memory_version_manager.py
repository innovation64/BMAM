"""
Memory Version Manager - 记忆版本管理系统
Unified memory persistence with checkpoint management

工作流程:
┌─────────────────────────────────────────────────────────────┐
│  运行中: 输入 → 处理 → 巩固/重塑/遗忘 → 自动保存到最新版本  │
│           ↓                                                  │
│  断开/重启 → 自动加载最新版本 → 继续塑造                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  用户操作:                                                   │
│  1. 手动归档 → checkpoint_day30.bma (稳定快照)              │
│  2. 继续运行 → 最新版本继续演化                             │
│  3. 发现问题 → 从归档回溯 → 替换最新版本 → 继续塑造         │
└─────────────────────────────────────────────────────────────┘
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class MemoryCheckpoint:
    """
    Memory Checkpoint
    记忆检查点
    """
    name: str
    archive_path: Path
    created_at: datetime
    description: str
    tags: List[str]
    memory_count: int
    is_current: bool  # 是否是当前活跃版本


class MemoryVersionManager:
    """
    Memory Version Manager
    记忆版本管理器

    职责:
    1. 自动持久化 - 每次处理后自动保存最新状态
    2. 断点续传 - 程序重启时自动加载最新状态
    3. 手动归档 - 用户创建稳定检查点
    4. 回溯恢复 - 从检查点恢复为最新版本

    文件结构:
    data/
    ├── current/                    # 最新版本（自动保存）
    │   ├── hippocampus_state.json
    │   ├── temporal_lobe.db
    │   ├── amygdala_state.json
    │   ├── prefrontal_state.json
    │   └── basal_ganglia_state.json
    └── checkpoints/                # 用户归档
        ├── checkpoint_day30.bma
        ├── checkpoint_stable.bma
        └── checkpoints.index.json  # 检查点索引
    """

    def __init__(
        self,
        coordinator=None,
        data_dir: Path = None,
        auto_save_enabled: bool = True
    ):
        """
        Initialize Version Manager

        Args:
            coordinator: BrainInspiredCoordinator instance
            data_dir: Data directory (default: BMAMPaths.DATA_DIR)
            auto_save_enabled: Enable auto-save after each processing
        """
        # 🔥 使用 BMAMPaths 统一路径管理
        from ..utils.paths import BMAMPaths
        if data_dir is None:
            data_dir = BMAMPaths.DATA_DIR
        self.coordinator = coordinator
        self.data_dir = Path(data_dir)
        self.auto_save_enabled = auto_save_enabled

        # Directories
        self.current_dir = self.data_dir / "current"
        self.checkpoints_dir = self.data_dir / "checkpoints"
        self.checkpoints_index_path = self.checkpoints_dir / "checkpoints.index.json"

        # Ensure directories exist
        self.current_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Load checkpoints index
        self.checkpoints: List[MemoryCheckpoint] = self._load_checkpoints_index()

        logger.info(f"MemoryVersionManager initialized (auto_save={auto_save_enabled})")

    async def auto_save(self) -> bool:
        """
        Auto Save Current Memory State
        自动保存当前记忆状态

        Called after each information processing.
        Saves to data/current/ directory.

        Returns:
            True if successful
        """
        if not self.auto_save_enabled:
            return True

        try:
            logger.debug("🔄 Auto-saving current memory state...")

            # Save each brain region to current/ directory
            success_count = 0

            # Hippocampus
            if hasattr(self.coordinator, 'hippocampus') and self.coordinator.hippocampus:
                hippocampus = self.coordinator.hippocampus
                if hasattr(hippocampus, '_save_state_to_file'):
                    hippocampus._save_state_to_file()
                    success_count += 1

            # Temporal Lobe
            if hasattr(self.coordinator, 'temporal_lobe') and self.coordinator.temporal_lobe:
                temporal_lobe = self.coordinator.temporal_lobe
                if hasattr(temporal_lobe, '_save_state_to_file'):
                    temporal_lobe._save_state_to_file()
                    success_count += 1

            # Amygdala
            if hasattr(self.coordinator, 'amygdala') and self.coordinator.amygdala:
                amygdala = self.coordinator.amygdala
                if hasattr(amygdala, '_save_state_to_file'):
                    amygdala._save_state_to_file()
                    success_count += 1

            # Prefrontal
            if hasattr(self.coordinator, 'prefrontal') and self.coordinator.prefrontal:
                prefrontal = self.coordinator.prefrontal
                if hasattr(prefrontal, '_save_state_to_file'):
                    prefrontal._save_state_to_file()
                    success_count += 1

            # Basal Ganglia
            if hasattr(self.coordinator, 'basal_ganglia') and self.coordinator.basal_ganglia:
                basal_ganglia = self.coordinator.basal_ganglia
                if hasattr(basal_ganglia, '_save_state_to_file'):
                    basal_ganglia._save_state_to_file()
                    success_count += 1

            logger.debug(f"✅ Auto-saved {success_count} brain regions to current/")
            return True

        except Exception as e:
            logger.error(f"❌ Auto-save failed: {e}")
            return False

    async def auto_load(self) -> bool:
        """
        Auto Load Latest Memory State
        自动加载最新记忆状态

        Called on program startup.
        Loads from data/current/ directory.

        Returns:
            True if successful
        """
        try:
            logger.info("📥 Auto-loading latest memory state...")

            # Check if current/ directory has data
            if not any(self.current_dir.iterdir()):
                logger.info("   No existing state found, starting fresh")
                return False

            # Load each brain region from current/ directory
            success_count = 0

            # Hippocampus
            if hasattr(self.coordinator, 'hippocampus') and self.coordinator.hippocampus:
                hippocampus = self.coordinator.hippocampus
                if hasattr(hippocampus, '_load_state_from_file'):
                    hippocampus._load_state_from_file()
                    success_count += 1

            # Temporal Lobe
            if hasattr(self.coordinator, 'temporal_lobe') and self.coordinator.temporal_lobe:
                temporal_lobe = self.coordinator.temporal_lobe
                if hasattr(temporal_lobe, '_load_state_from_file'):
                    temporal_lobe._load_state_from_file()
                    success_count += 1

            # Amygdala
            if hasattr(self.coordinator, 'amygdala') and self.coordinator.amygdala:
                amygdala = self.coordinator.amygdala
                if hasattr(amygdala, '_load_state_from_file'):
                    amygdala._load_state_from_file()
                    success_count += 1

            # Prefrontal
            if hasattr(self.coordinator, 'prefrontal') and self.coordinator.prefrontal:
                prefrontal = self.coordinator.prefrontal
                if hasattr(prefrontal, '_load_state_from_file'):
                    prefrontal._load_state_from_file()
                    success_count += 1

            # Basal Ganglia
            if hasattr(self.coordinator, 'basal_ganglia') and self.coordinator.basal_ganglia:
                basal_ganglia = self.coordinator.basal_ganglia
                if hasattr(basal_ganglia, '_load_state_from_file'):
                    basal_ganglia._load_state_from_file()
                    success_count += 1

            logger.info(f"✅ Auto-loaded {success_count} brain regions from current/")
            return True

        except Exception as e:
            logger.error(f"❌ Auto-load failed: {e}")
            return False

    async def create_checkpoint(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Optional[MemoryCheckpoint]:
        """
        Create Manual Checkpoint
        创建手动检查点

        User-triggered action to archive current memory state.

        Args:
            name: Checkpoint name (e.g., "stable_day30", "before_experiment")
            description: Human-readable description
            tags: Tags for categorization

        Returns:
            MemoryCheckpoint if successful

        Example:
            >>> checkpoint = await manager.create_checkpoint(
            ...     name="stable_day30",
            ...     description="Stable personality after 30 days",
            ...     tags=["stable", "milestone"]
            ... )
        """
        logger.info(f"📦 Creating checkpoint: {name}")

        try:
            # Use MemoryArchive to export current state
            from .memory_archive import MemoryArchive

            archive = MemoryArchive.create_from_coordinator(
                name=name,
                coordinator=self.coordinator,
                output_dir=self.checkpoints_dir,
                description=description,
                tags=tags or [],
                metadata={
                    'checkpoint_type': 'manual',
                    'created_by': 'user'
                }
            )

            # Get archive info
            info = archive.get_info()

            # Create checkpoint record
            checkpoint = MemoryCheckpoint(
                name=name,
                archive_path=archive.archive_path,
                created_at=datetime.now(),
                description=description,
                tags=tags or [],
                memory_count=info['statistics'].get('total_memories', 0),
                is_current=False  # Checkpoint is not current
            )

            # Add to index
            self.checkpoints.append(checkpoint)
            self._save_checkpoints_index()

            logger.info(f"✅ Checkpoint created: {archive.archive_path}")
            logger.info(f"   Total memories: {checkpoint.memory_count}")

            return checkpoint

        except Exception as e:
            logger.error(f"❌ Failed to create checkpoint: {e}")
            return None

    async def restore_from_checkpoint(
        self,
        checkpoint_name: str,
        create_backup: bool = True
    ) -> bool:
        """
        Restore from Checkpoint
        从检查点恢复

        Restores checkpoint as the latest/current version.
        After restore, program continues with checkpoint's memory state.

        Args:
            checkpoint_name: Checkpoint name to restore
            create_backup: Create backup of current state before restore

        Returns:
            True if successful

        Example:
            >>> # Restore from stable checkpoint
            >>> success = await manager.restore_from_checkpoint("stable_day30")
            >>> # Now program continues with day30 memory, continues shaping
        """
        logger.info(f"🔄 Restoring from checkpoint: {checkpoint_name}")

        try:
            # Find checkpoint
            checkpoint = self._find_checkpoint(checkpoint_name)
            if not checkpoint:
                logger.error(f"❌ Checkpoint not found: {checkpoint_name}")
                return False

            # Create backup of current state if requested
            if create_backup:
                backup_name = f"backup_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                await self.create_checkpoint(
                    name=backup_name,
                    description=f"Auto-backup before restoring {checkpoint_name}",
                    tags=["backup", "auto"]
                )
                logger.info(f"   ✓ Created backup: {backup_name}")

            # Load checkpoint
            from .memory_archive import MemoryArchive
            archive = MemoryArchive(checkpoint.archive_path)

            # Import to current/ directory (replaces latest version)
            archive_data = archive.load(
                target_dir=self.current_dir,
                validate=True
            )

            # Load into coordinator
            brain_regions_data = archive_data.get('brain_regions_data', {})

            for region_name, region_data in brain_regions_data.items():
                if region_name == 'hippocampus' and hasattr(self.coordinator, 'hippocampus'):
                    self.coordinator.hippocampus.import_state(region_data)

                elif region_name == 'temporal_lobe' and hasattr(self.coordinator, 'temporal_lobe'):
                    if hasattr(self.coordinator.temporal_lobe, 'import_state'):
                        self.coordinator.temporal_lobe.import_state(region_data)

                elif region_name == 'amygdala' and hasattr(self.coordinator, 'amygdala'):
                    if hasattr(self.coordinator.amygdala, 'import_state'):
                        self.coordinator.amygdala.import_state(region_data)

                elif region_name == 'prefrontal' and hasattr(self.coordinator, 'prefrontal'):
                    if hasattr(self.coordinator.prefrontal, 'import_state'):
                        self.coordinator.prefrontal.import_state(region_data)

                elif region_name == 'basal_ganglia' and hasattr(self.coordinator, 'basal_ganglia'):
                    if hasattr(self.coordinator.basal_ganglia, 'import_state'):
                        self.coordinator.basal_ganglia.import_state(region_data)

            # Auto-save to update current/ files
            await self.auto_save()

            # Mark checkpoint as current
            for cp in self.checkpoints:
                cp.is_current = (cp.name == checkpoint_name)
            self._save_checkpoints_index()

            logger.info(f"✅ Restored from checkpoint: {checkpoint_name}")
            logger.info(f"   Memory state now matches checkpoint")
            logger.info(f"   Program will continue shaping from this state")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to restore from checkpoint: {e}")
            return False

    def list_checkpoints(self) -> List[MemoryCheckpoint]:
        """
        List All Checkpoints
        列出所有检查点

        Returns:
            List of checkpoints, sorted by creation time (newest first)
        """
        return sorted(
            self.checkpoints,
            key=lambda cp: cp.created_at,
            reverse=True
        )

    def get_current_checkpoint(self) -> Optional[MemoryCheckpoint]:
        """
        Get Current Checkpoint
        获取当前检查点

        Returns:
            Current checkpoint if exists
        """
        for cp in self.checkpoints:
            if cp.is_current:
                return cp
        return None

    def delete_checkpoint(self, checkpoint_name: str) -> bool:
        """
        Delete Checkpoint
        删除检查点

        Args:
            checkpoint_name: Checkpoint name to delete

        Returns:
            True if successful
        """
        try:
            checkpoint = self._find_checkpoint(checkpoint_name)
            if not checkpoint:
                logger.error(f"Checkpoint not found: {checkpoint_name}")
                return False

            # Don't allow deleting current checkpoint
            if checkpoint.is_current:
                logger.error(f"Cannot delete current checkpoint: {checkpoint_name}")
                return False

            # Delete archive directory
            import shutil
            if checkpoint.archive_path.exists():
                shutil.rmtree(checkpoint.archive_path)

            # Remove from index
            self.checkpoints = [cp for cp in self.checkpoints if cp.name != checkpoint_name]
            self._save_checkpoints_index()

            logger.info(f"✅ Deleted checkpoint: {checkpoint_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to delete checkpoint: {e}")
            return False

    # Private methods

    def _find_checkpoint(self, name: str) -> Optional[MemoryCheckpoint]:
        """Find checkpoint by name"""
        for cp in self.checkpoints:
            if cp.name == name:
                return cp
        return None

    def _load_checkpoints_index(self) -> List[MemoryCheckpoint]:
        """Load checkpoints index from file"""
        if not self.checkpoints_index_path.exists():
            return []

        try:
            with open(self.checkpoints_index_path, 'r') as f:
                data = json.load(f)

            checkpoints = []
            for cp_data in data.get('checkpoints', []):
                checkpoint = MemoryCheckpoint(
                    name=cp_data['name'],
                    archive_path=Path(cp_data['archive_path']),
                    created_at=datetime.fromisoformat(cp_data['created_at']),
                    description=cp_data.get('description', ''),
                    tags=cp_data.get('tags', []),
                    memory_count=cp_data.get('memory_count', 0),
                    is_current=cp_data.get('is_current', False)
                )
                checkpoints.append(checkpoint)

            return checkpoints

        except Exception as e:
            logger.error(f"Failed to load checkpoints index: {e}")
            return []

    def _save_checkpoints_index(self) -> None:
        """Save checkpoints index to file"""
        try:
            data = {
                'version': '1.0.0',
                'checkpoints': [
                    {
                        'name': cp.name,
                        'archive_path': str(cp.archive_path),
                        'created_at': cp.created_at.isoformat(),
                        'description': cp.description,
                        'tags': cp.tags,
                        'memory_count': cp.memory_count,
                        'is_current': cp.is_current
                    }
                    for cp in self.checkpoints
                ]
            }

            with open(self.checkpoints_index_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save checkpoints index: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get Version Manager Status
        获取版本管理器状态

        Returns:
            Status dictionary
        """
        current_checkpoint = self.get_current_checkpoint()

        return {
            'auto_save_enabled': self.auto_save_enabled,
            'current_dir': str(self.current_dir),
            'checkpoints_dir': str(self.checkpoints_dir),
            'total_checkpoints': len(self.checkpoints),
            'current_checkpoint': current_checkpoint.name if current_checkpoint else None,
            'recent_checkpoints': [
                {
                    'name': cp.name,
                    'created_at': cp.created_at.isoformat(),
                    'memory_count': cp.memory_count,
                    'is_current': cp.is_current
                }
                for cp in self.list_checkpoints()[:5]  # Latest 5
            ]
        }
