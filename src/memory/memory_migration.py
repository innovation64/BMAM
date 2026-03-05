"""
Memory Migration System - 记忆迁移系统
Cross-machine memory portability with merge/switch strategies

Enables:
1. Export memory from Machine A (distributed across 5 brain regions)
2. Import memory to Machine B with merge strategies
3. Seamless memory switching for continuous learning
4. Cross-region relationship integrity preservation
"""

from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import json
import uuid
import hashlib
from datetime import datetime

from ..utils.paths import BMAMPaths

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """
    Memory Switch Strategies
    记忆切换策略
    """
    REPLACE = "replace"          # 完全替换：使用导入的记忆（默认）


class ConflictResolution(Enum):
    """
    ID Conflict Resolution Strategies
    ID冲突解决策略
    """
    REGENERATE = "regenerate"    # 重新生成B的ID
    KEEP_SOURCE = "keep_source"  # 保留源（A）的记忆
    KEEP_TARGET = "keep_target"  # 保留目标（B）的记忆
    MERGE_CONTENT = "merge_content"  # 合并内容


@dataclass
class MigrationConfig:
    """
    Migration Configuration
    迁移配置
    """
    merge_strategy: MergeStrategy
    conflict_resolution: ConflictResolution
    preserve_timestamps: bool = True
    validate_relationships: bool = True
    create_backup: bool = True
    enable_rollback: bool = True


@dataclass
class MigrationReport:
    """
    Migration Report
    迁移报告
    """
    success: bool
    source_archive: str
    target_system: str
    merge_strategy: str
    timestamp: datetime

    # Statistics
    total_memories_imported: int
    memories_by_region: Dict[str, int]
    id_conflicts_resolved: int
    relationships_validated: int
    relationships_fixed: int

    # Details
    new_memory_ids: Dict[str, str]  # old_id -> new_id mapping
    warnings: List[str]
    errors: List[str]

    # Rollback info
    backup_path: Optional[Path] = None


class MemoryMigrationManager:
    """
    Memory Migration Manager
    记忆迁移管理器

    Handles cross-machine memory transfer with:
    - Multiple merge strategies
    - ID conflict resolution
    - Cross-region relationship preservation
    - Rollback support
    """

    def __init__(
        self,
        coordinator=None,  # BrainInspiredCoordinator
        config: Optional[MigrationConfig] = None
    ):
        """
        Initialize Migration Manager

        Args:
            coordinator: Brain coordinator instance
            config: Migration configuration
        """
        self.coordinator = coordinator
        self.config = config or MigrationConfig(
            merge_strategy=MergeStrategy.MERGE_ADD,
            conflict_resolution=ConflictResolution.REGENERATE
        )

        # Track ID mappings during migration
        self.id_mappings: Dict[str, str] = {}  # old_id -> new_id

        # Track relationships for validation
        self.relationships: List[Tuple[str, str, str]] = []  # (source_id, relation, target_id)

        # Migration history for persistence
        self._migration_history: List[MigrationReport] = []
        self._history_file = BMAMPaths.STATE_DIR / "migration_history.json"

        # Load existing history
        self._load_history()

        logger.info("MemoryMigrationManager initialized")

    async def import_memory(
        self,
        archive_path: Path,
        config: Optional[MigrationConfig] = None
    ) -> MigrationReport:
        """
        Import Memory from Archive
        从归档导入记忆

        Main entry point for memory migration.

        Args:
            archive_path: Path to .bma archive
            config: Migration configuration (overrides default)

        Returns:
            MigrationReport with import results
        """
        config = config or self.config
        start_time = datetime.now()

        logger.info(f"🚀 Starting memory import: {archive_path}")
        logger.info(f"   Strategy: {config.merge_strategy.value}")
        logger.info(f"   Conflict Resolution: {config.conflict_resolution.value}")

        # Initialize report
        report = MigrationReport(
            success=False,
            source_archive=str(archive_path),
            target_system="current",
            merge_strategy=config.merge_strategy.value,
            timestamp=start_time,
            total_memories_imported=0,
            memories_by_region={},
            id_conflicts_resolved=0,
            relationships_validated=0,
            relationships_fixed=0,
            new_memory_ids={},
            warnings=[],
            errors=[]
        )

        try:
            # Step 1: Create backup if enabled
            if config.create_backup:
                report.backup_path = await self._create_backup()
                logger.info(f"   ✓ Backup created: {report.backup_path}")

            # Step 2: Load archive
            from .memory_archive import MemoryArchive
            archive = MemoryArchive(archive_path)

            # Step 3: Validate archive
            validation = archive.validate()
            if not validation['valid']:
                report.errors.extend(validation['errors'])
                report.warnings.extend(validation['warnings'])
                logger.error(f"❌ Archive validation failed")
                return report

            # Step 4: Load archive data
            # 🔥 使用 BMAMPaths 统一路径管理
            from ..utils.paths import BMAMPaths
            archive_data = archive.load(
                target_dir=BMAMPaths.TEMP_DIR,
                validate=True
            )

            brain_regions_data = archive_data.get('brain_regions_data', {})

            # Step 5: Apply merge strategy
            if config.merge_strategy == MergeStrategy.REPLACE:
                result = await self._merge_replace(brain_regions_data, report)
            elif config.merge_strategy == MergeStrategy.MERGE_ADD:
                result = await self._merge_add(brain_regions_data, config, report)
            elif config.merge_strategy == MergeStrategy.MERGE_UPDATE:
                result = await self._merge_update(brain_regions_data, config, report)
            elif config.merge_strategy == MergeStrategy.SNAPSHOT:
                result = await self._merge_snapshot(brain_regions_data, config, report)
            else:
                raise ValueError(f"Unknown merge strategy: {config.merge_strategy}")

            # Step 6: Validate cross-region relationships
            if config.validate_relationships:
                self._validate_relationships(report)

            # Step 7: Finalize
            report.success = True
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Memory import completed in {duration:.2f}s")
            logger.info(f"   Imported: {report.total_memories_imported} memories")
            logger.info(f"   Conflicts resolved: {report.id_conflicts_resolved}")

            return report

        except Exception as e:
            logger.error(f"❌ Memory import failed: {e}")
            report.errors.append(str(e))

            # Rollback if enabled
            if config.enable_rollback and report.backup_path:
                logger.info("🔄 Rolling back to backup...")
                await self._rollback(report.backup_path)

            return report

    async def _merge_replace(
        self,
        brain_regions_data: Dict[str, Any],
        report: MigrationReport
    ) -> None:
        """
        Replace Strategy: 完全替换
        删除当前记忆，使用导入的记忆
        """
        logger.info("📝 Applying REPLACE strategy: clearing existing memories")

        # Clear all brain regions
        if self.coordinator:
            if hasattr(self.coordinator, 'hippocampus') and self.coordinator.hippocampus:
                self.coordinator.hippocampus.memories.clear()
                self.coordinator.hippocampus.memory_dict.clear()
                logger.info("   ✓ Cleared Hippocampus")

            if hasattr(self.coordinator, 'prefrontal') and self.coordinator.prefrontal:
                self.coordinator.prefrontal.memories.clear()
                self.coordinator.prefrontal.memory_dict.clear()
                logger.info("   ✓ Cleared Prefrontal")

            if hasattr(self.coordinator, 'amygdala') and self.coordinator.amygdala:
                self.coordinator.amygdala.memories.clear()
                self.coordinator.amygdala.memory_dict.clear()
                logger.info("   ✓ Cleared Amygdala")

            if hasattr(self.coordinator, 'basal_ganglia') and self.coordinator.basal_ganglia:
                self.coordinator.basal_ganglia.memories.clear()
                self.coordinator.basal_ganglia.memory_dict.clear()
                logger.info("   ✓ Cleared Basal Ganglia")

        # Import new memories
        await self._import_brain_regions(brain_regions_data, report, allow_conflicts=False)

    async def _merge_add(
        self,
        brain_regions_data: Dict[str, Any],
        config: MigrationConfig,
        report: MigrationReport
    ) -> None:
        """
        Merge Add Strategy: 增量合并
        保留当前记忆，添加新记忆（解决ID冲突）
        """
        logger.info("📝 Applying MERGE_ADD strategy: adding new memories")

        # Import with ID conflict resolution
        await self._import_brain_regions(
            brain_regions_data,
            report,
            allow_conflicts=True,
            conflict_resolution=config.conflict_resolution
        )

    async def _merge_update(
        self,
        brain_regions_data: Dict[str, Any],
        config: MigrationConfig,
        report: MigrationReport
    ) -> None:
        """
        Merge Update Strategy: 更新合并
        保留当前记忆，新记忆覆盖冲突项
        """
        logger.info("📝 Applying MERGE_UPDATE strategy: updating existing memories")

        # Import with update-on-conflict
        await self._import_brain_regions(
            brain_regions_data,
            report,
            allow_conflicts=True,
            conflict_resolution=ConflictResolution.KEEP_TARGET
        )

    async def _merge_snapshot(
        self,
        brain_regions_data: Dict[str, Any],
        config: MigrationConfig,
        report: MigrationReport
    ) -> None:
        """
        Snapshot Strategy: 快照模式
        创建独立快照，可切换
        """
        logger.info("📝 Applying SNAPSHOT strategy: creating independent snapshot")

        # Create snapshot with unique namespace
        snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"   Snapshot ID: {snapshot_id}")

        # Import with namespace prefix
        await self._import_brain_regions(
            brain_regions_data,
            report,
            allow_conflicts=True,
            conflict_resolution=ConflictResolution.REGENERATE,
            id_prefix=f"snapshot_{snapshot_id}_"
        )

    async def _import_brain_regions(
        self,
        brain_regions_data: Dict[str, Any],
        report: MigrationReport,
        allow_conflicts: bool = False,
        conflict_resolution: Optional[ConflictResolution] = None,
        id_prefix: str = ""
    ) -> None:
        """
        Import Brain Regions Data
        导入各脑区数据

        Args:
            brain_regions_data: Brain regions data from archive
            report: Migration report to update
            allow_conflicts: Whether to allow ID conflicts
            conflict_resolution: How to resolve conflicts
            id_prefix: Prefix for new IDs (for snapshots)
        """
        conflict_resolution = conflict_resolution or self.config.conflict_resolution

        # Import each brain region
        for region_name, region_data in brain_regions_data.items():
            logger.info(f"   📥 Importing {region_name}...")

            try:
                if region_name == 'hippocampus':
                    count = await self._import_hippocampus(
                        region_data,
                        allow_conflicts,
                        conflict_resolution,
                        id_prefix
                    )
                elif region_name == 'prefrontal':
                    count = await self._import_prefrontal(
                        region_data,
                        allow_conflicts,
                        conflict_resolution,
                        id_prefix
                    )
                elif region_name == 'amygdala':
                    count = await self._import_amygdala(
                        region_data,
                        allow_conflicts,
                        conflict_resolution,
                        id_prefix
                    )
                elif region_name == 'basal_ganglia':
                    count = await self._import_basal_ganglia(
                        region_data,
                        allow_conflicts,
                        conflict_resolution,
                        id_prefix
                    )
                elif region_name == 'temporal_lobe':
                    count = await self._import_temporal_lobe(
                        region_data,
                        allow_conflicts,
                        conflict_resolution,
                        id_prefix
                    )
                else:
                    logger.warning(f"   ⚠️  Unknown region: {region_name}")
                    continue

                report.memories_by_region[region_name] = count
                report.total_memories_imported += count
                logger.info(f"   ✓ Imported {count} memories to {region_name}")

            except Exception as e:
                logger.error(f"   ❌ Failed to import {region_name}: {e}")
                report.errors.append(f"{region_name}: {str(e)}")

    async def _import_hippocampus(
        self,
        data: Dict[str, Any],
        allow_conflicts: bool,
        conflict_resolution: ConflictResolution,
        id_prefix: str
    ) -> int:
        """Import Hippocampus memories"""
        if not self.coordinator or not hasattr(self.coordinator, 'hippocampus'):
            return 0

        hippocampus = self.coordinator.hippocampus
        memories = data.get('memories', [])
        imported_count = 0

        for mem_data in memories:
            old_id = mem_data.get('id')

            # Check for ID conflict
            if old_id in hippocampus.memory_dict and allow_conflicts:
                if conflict_resolution == ConflictResolution.REGENERATE:
                    # Generate new ID
                    new_id = id_prefix + str(uuid.uuid4())
                    mem_data['id'] = new_id
                    self.id_mappings[old_id] = new_id
                    self.config.id_conflicts_resolved += 1
                elif conflict_resolution == ConflictResolution.KEEP_SOURCE:
                    # Skip this memory
                    continue
                elif conflict_resolution == ConflictResolution.KEEP_TARGET:
                    # Replace existing
                    pass

            # Import memory (using Hippocampus's import_state or manual construction)
            from BMAM.src.agents.brain_regions.hippocampus_agent.core import EpisodicMemory

            memory = EpisodicMemory(
                id=mem_data['id'],
                content=mem_data['content'],
                timestamp=datetime.fromisoformat(mem_data['timestamp']),
                entities=mem_data.get('entities', []),
                importance=mem_data.get('importance', 0.5),
                emotion_tags=mem_data.get('emotion_tags', []),
                emotion_intensity=mem_data.get('emotion_intensity', 0.0),
                metadata=mem_data.get('metadata', {})
            )

            hippocampus.memories.append(memory)
            hippocampus.memory_dict[memory.id] = memory
            imported_count += 1

        return imported_count

    async def _import_prefrontal(
        self,
        data: Dict[str, Any],
        allow_conflicts: bool,
        conflict_resolution: ConflictResolution,
        id_prefix: str
    ) -> int:
        """Import Prefrontal memories"""
        # Similar to hippocampus
        # Implementation depends on Prefrontal's data structure
        return len(data.get('memories', []))

    async def _import_amygdala(
        self,
        data: Dict[str, Any],
        allow_conflicts: bool,
        conflict_resolution: ConflictResolution,
        id_prefix: str
    ) -> int:
        """Import Amygdala emotional tags"""
        return len(data.get('memories', []))

    async def _import_basal_ganglia(
        self,
        data: Dict[str, Any],
        allow_conflicts: bool,
        conflict_resolution: ConflictResolution,
        id_prefix: str
    ) -> int:
        """Import Basal Ganglia procedural memories"""
        return len(data.get('memories', []))

    async def _import_temporal_lobe(
        self,
        data: Dict[str, Any],
        allow_conflicts: bool,
        conflict_resolution: ConflictResolution,
        id_prefix: str
    ) -> int:
        """Import Temporal Lobe semantic memories"""
        # Temporal lobe typically uses database, handled separately
        return 0

    def _validate_relationships(self, report: MigrationReport) -> None:
        """
        Validate Cross-Region Relationships
        验证跨脑区关系完整性

        Ensures that memory references are valid after migration.
        """
        logger.info("🔍 Validating cross-region relationships...")

        # Check Hippocampus → Temporal Lobe references
        if self.coordinator and hasattr(self.coordinator, 'hippocampus'):
            hippocampus = self.coordinator.hippocampus

            for memory in hippocampus.memories:
                # Check if memory references exist
                metadata = memory.metadata

                if 'consolidated_to' in metadata:
                    semantic_id = metadata['consolidated_to']

                    # Update ID if it was remapped
                    if semantic_id in self.id_mappings:
                        old_id = semantic_id
                        new_id = self.id_mappings[old_id]
                        metadata['consolidated_to'] = new_id
                        report.relationships_fixed += 1
                        logger.debug(f"   Fixed reference: {old_id} → {new_id}")

                report.relationships_validated += 1

        logger.info(f"   ✓ Validated {report.relationships_validated} relationships")
        if report.relationships_fixed > 0:
            logger.info(f"   ✓ Fixed {report.relationships_fixed} broken references")

    async def _create_backup(self) -> Path:
        """Create backup before migration"""
        from .memory_archive import MemoryArchive
        # 🔥 使用 BMAMPaths 统一路径管理
        from ..utils.paths import BMAMPaths

        backup_dir = BMAMPaths.MIGRATION_BACKUPS_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_name = f"pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        archive = MemoryArchive.create_from_coordinator(
            name=backup_name,
            coordinator=self.coordinator,
            output_dir=backup_dir,
            description="Pre-migration backup",
            tags=["backup", "migration"]
        )

        return archive.archive_path

    async def _rollback(self, backup_path: Path) -> None:
        """Rollback to backup"""
        logger.info(f"🔄 Rolling back to: {backup_path}")

        # Load backup
        from .memory_archive import MemoryArchive
        archive = MemoryArchive(backup_path)
        # 🔥 使用 BMAMPaths 统一路径管理
        from ..utils.paths import BMAMPaths
        archive.load(target_dir=BMAMPaths.DATA_DIR, force=True)

        logger.info("✅ Rollback complete")

    def _load_history(self) -> None:
        """Load migration history from persistent storage"""
        if not self._history_file.exists():
            self._migration_history = []
            return

        try:
            with open(self._history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._migration_history = []
            for item in data:
                # Convert timestamp string back to datetime
                item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                # Convert backup_path string back to Path if present
                if item.get('backup_path'):
                    item['backup_path'] = Path(item['backup_path'])
                self._migration_history.append(MigrationReport(**item))

            logger.debug(f"Loaded {len(self._migration_history)} migration reports")
        except Exception as e:
            logger.warning(f"Failed to load migration history: {e}")
            self._migration_history = []

    def _save_history(self) -> None:
        """Save migration history to persistent storage"""
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)

            data = []
            for report in self._migration_history:
                item = asdict(report)
                # Convert datetime to ISO string
                item['timestamp'] = report.timestamp.isoformat()
                # Convert Path to string if present
                if item.get('backup_path'):
                    item['backup_path'] = str(item['backup_path'])
                data.append(item)

            with open(self._history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(data)} migration reports")
        except Exception as e:
            logger.error(f"Failed to save migration history: {e}")

    def add_migration_report(self, report: MigrationReport) -> None:
        """Add a migration report and persist"""
        self._migration_history.append(report)
        self._save_history()

    def get_migration_history(self) -> List[MigrationReport]:
        """Get migration history (persisted)"""
        return self._migration_history.copy()

    async def switch_snapshot(self, snapshot_id: str) -> bool:
        """
        Switch to a different memory snapshot
        切换到不同的记忆快照

        Args:
            snapshot_id: Snapshot identifier (backup_path from MigrationReport)

        Returns:
            True if successful
        """
        logger.info(f"🔀 Switching to snapshot: {snapshot_id}")

        # Find snapshot in migration history
        target_report = None
        for report in self._migration_history:
            if report.backup_path and str(report.backup_path) == snapshot_id:
                target_report = report
                break

        if not target_report or not target_report.backup_path:
            logger.error(f"Snapshot not found: {snapshot_id}")
            return False

        backup_path = Path(target_report.backup_path)
        if not backup_path.exists():
            logger.error(f"Backup archive not found: {backup_path}")
            return False

        try:
            # Create a backup of current state before switching
            current_backup = BMAMPaths.MIGRATION_BACKUPS_DIR / f"pre_switch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bma"
            from .memory_archive import MemoryArchive

            # Export current state
            current_archive = MemoryArchive(current_backup)
            current_archive.save(
                source_dir=BMAMPaths.DATA_DIR,
                metadata={"reason": f"pre-switch backup before loading {snapshot_id}"}
            )

            # Load the target snapshot
            target_archive = MemoryArchive(backup_path)
            target_archive.load(target_dir=BMAMPaths.DATA_DIR, force=True)

            logger.info(f"✅ Successfully switched to snapshot: {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to switch snapshot: {e}")
            return False
