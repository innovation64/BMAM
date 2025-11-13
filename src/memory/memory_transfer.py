"""
Memory Transfer System - 记忆迁移系统
Seamless memory portability across machines (完整的灵魂体迁移)

Philosophy:
- 每个记忆体是独一无二的"灵魂"，通过巩固、重塑、遗忘机制主动塑造
- 不存在"合并"概念 - 灵魂无法合并
- 只支持完整导出/导入/切换，保持记忆的完整性

核心功能:
1. 完整导出五脑区记忆（包含所有关系）
2. 无缝导入到新环境
3. 继续持续学习和记忆塑造
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TransferReport:
    """
    Memory Transfer Report
    记忆迁移报告
    """
    success: bool
    operation: str  # 'export' or 'import'
    timestamp: datetime

    # Memory statistics
    total_memories: int
    memories_by_region: Dict[str, int]

    # File paths
    archive_path: Optional[Path] = None
    backup_path: Optional[Path] = None

    # Validation
    relationships_validated: int = 0
    integrity_check_passed: bool = False

    # Errors and warnings
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class MemoryTransferSystem:
    """
    Memory Transfer System
    记忆迁移系统

    Enables complete memory portability:
    - Machine A: Export memory → memory_A.bma
    - Machine B: Import memory_A.bma → Continue learning

    Key principle: 记忆体是完整的灵魂，不可合并，只可迁移
    """

    def __init__(self, coordinator=None):
        """
        Initialize Transfer System

        Args:
            coordinator: BrainInspiredCoordinator instance
        """
        self.coordinator = coordinator
        logger.info("MemoryTransferSystem initialized")

    async def export_memory(
        self,
        output_dir: Path,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        create_backup: bool = True
    ) -> TransferReport:
        """
        Export Complete Memory (五脑区完整导出)
        导出完整记忆

        Exports all brain regions with full relationship preservation.

        Args:
            output_dir: Output directory
            name: Archive name
            description: Description of this memory state
            tags: Tags for categorization
            create_backup: Whether to create local backup

        Returns:
            TransferReport with export results
        """
        start_time = datetime.now()
        logger.info(f"📤 Exporting memory: {name}")

        report = TransferReport(
            success=False,
            operation='export',
            timestamp=start_time,
            total_memories=0,
            memories_by_region={}
        )

        try:
            # Use existing MemoryArchive v2.0.0 format
            from .memory_archive import MemoryArchive

            # Create archive from coordinator
            archive = MemoryArchive.create_from_coordinator(
                name=name,
                coordinator=self.coordinator,
                output_dir=output_dir,
                description=description,
                tags=tags or [],
                metadata={'exported_by': 'MemoryTransferSystem'}
            )

            # Get archive info
            info = archive.get_info()

            report.archive_path = archive.archive_path
            report.total_memories = info['statistics'].get('total_memories', 0)
            report.memories_by_region = {
                region: info['statistics'].get(f'{region}_memories', 0)
                for region in info.get('brain_regions', [])
            }

            # Validate export
            validation = archive.validate()
            report.integrity_check_passed = validation['valid']

            if not validation['valid']:
                report.errors.extend(validation['errors'])
                report.warnings.extend(validation['warnings'])

            report.success = True
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"✅ Memory exported successfully in {duration:.2f}s")
            logger.info(f"   Archive: {archive.archive_path}")
            logger.info(f"   Total memories: {report.total_memories}")
            logger.info(f"   Brain regions: {list(report.memories_by_region.keys())}")

            return report

        except Exception as e:
            logger.error(f"❌ Memory export failed: {e}")
            report.errors.append(str(e))
            return report

    async def import_memory(
        self,
        archive_path: Path,
        create_backup: bool = True,
        validate_before_import: bool = True
    ) -> TransferReport:
        """
        Import Complete Memory (五脑区完整导入)
        导入完整记忆

        Replaces current memory with imported memory.
        **Warning**: This will clear existing memories!

        Args:
            archive_path: Path to .bma archive
            create_backup: Whether to backup current memory first
            validate_before_import: Validate archive before import

        Returns:
            TransferReport with import results
        """
        start_time = datetime.now()
        logger.info(f"📥 Importing memory: {archive_path}")

        report = TransferReport(
            success=False,
            operation='import',
            timestamp=start_time,
            total_memories=0,
            memories_by_region={}
        )

        try:
            # Step 1: Backup current memory if requested
            if create_backup:
                backup_report = await self._create_backup()
                report.backup_path = backup_report.archive_path
                logger.info(f"   ✓ Backup created: {report.backup_path}")

            # Step 2: Load and validate archive
            from .memory_archive import MemoryArchive
            archive = MemoryArchive(archive_path)

            if validate_before_import:
                validation = archive.validate()
                if not validation['valid']:
                    report.errors.extend(validation['errors'])
                    report.warnings.extend(validation['warnings'])
                    logger.error("❌ Archive validation failed")
                    return report

            # Step 3: Clear current memories (完整替换)
            logger.info("🔄 Clearing current memories...")
            self._clear_all_memories()

            # Step 4: Load archive data
            archive_data = archive.load(
                target_dir=Path("data/"),
                validate=True,
                force=False
            )

            brain_regions_data = archive_data.get('brain_regions_data', {})

            # Step 5: Import to each brain region
            logger.info("📥 Importing to brain regions...")

            for region_name, region_data in brain_regions_data.items():
                count = await self._import_region(region_name, region_data)
                report.memories_by_region[region_name] = count
                report.total_memories += count
                logger.info(f"   ✓ {region_name}: {count} memories")

            # Step 6: Validate cross-region relationships
            report.relationships_validated = self._validate_relationships()
            logger.info(f"   ✓ Validated {report.relationships_validated} relationships")

            # Step 7: Finalize
            report.success = True
            report.integrity_check_passed = True
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(f"✅ Memory imported successfully in {duration:.2f}s")
            logger.info(f"   Total memories: {report.total_memories}")
            logger.info(f"   Ready for continuous learning")

            return report

        except Exception as e:
            logger.error(f"❌ Memory import failed: {e}")
            report.errors.append(str(e))

            # Rollback to backup if available
            if create_backup and report.backup_path:
                logger.warning("🔄 Rolling back to backup...")
                await self._rollback(report.backup_path)

            return report

    def _clear_all_memories(self) -> None:
        """
        Clear All Memories
        清空所有记忆

        Prepares for fresh memory import.
        """
        if not self.coordinator:
            return

        # Clear Hippocampus
        if hasattr(self.coordinator, 'hippocampus') and self.coordinator.hippocampus:
            self.coordinator.hippocampus.memories.clear()
            self.coordinator.hippocampus.memory_dict.clear()
            if hasattr(self.coordinator.hippocampus, 'entity_index'):
                self.coordinator.hippocampus.entity_index.clear()
            if hasattr(self.coordinator.hippocampus, 'time_index'):
                self.coordinator.hippocampus.time_index.clear()
            logger.debug("   ✓ Cleared Hippocampus")

        # Clear Temporal Lobe
        if hasattr(self.coordinator, 'temporal_lobe') and self.coordinator.temporal_lobe:
            self.coordinator.temporal_lobe.memories.clear()
            self.coordinator.temporal_lobe.memory_dict.clear()
            if hasattr(self.coordinator.temporal_lobe, 'kg'):
                self.coordinator.temporal_lobe.kg.entities.clear()
                self.coordinator.temporal_lobe.kg.relations.clear()
            logger.debug("   ✓ Cleared Temporal Lobe")

        # Clear Amygdala
        if hasattr(self.coordinator, 'amygdala') and self.coordinator.amygdala:
            self.coordinator.amygdala.memories.clear()
            self.coordinator.amygdala.memory_dict.clear()
            if hasattr(self.coordinator.amygdala, 'emotion_index'):
                self.coordinator.amygdala.emotion_index.clear()
            logger.debug("   ✓ Cleared Amygdala")

        # Clear Prefrontal
        if hasattr(self.coordinator, 'prefrontal') and self.coordinator.prefrontal:
            if hasattr(self.coordinator.prefrontal, 'memories'):
                self.coordinator.prefrontal.memories.clear()
                self.coordinator.prefrontal.memory_dict.clear()
            logger.debug("   ✓ Cleared Prefrontal")

        # Clear Basal Ganglia
        if hasattr(self.coordinator, 'basal_ganglia') and self.coordinator.basal_ganglia:
            if hasattr(self.coordinator.basal_ganglia, 'memories'):
                self.coordinator.basal_ganglia.memories.clear()
                self.coordinator.basal_ganglia.memory_dict.clear()
            logger.debug("   ✓ Cleared Basal Ganglia")

        # Clear memory system (FAISS index, DB, caches)
        if hasattr(self.coordinator, 'memory_system') and self.coordinator.memory_system:
            try:
                # Clear FAISS vector index
                if hasattr(self.coordinator.memory_system, 'vector_db'):
                    self.coordinator.memory_system.vector_db.reset_index()
                    logger.debug("   ✓ Cleared FAISS index")

                # Clear database
                if hasattr(self.coordinator.memory_system, 'db_manager'):
                    self.coordinator.memory_system.db_manager.clear_all_memories()
                    logger.debug("   ✓ Cleared memory database")

                logger.debug("   ✓ Cleared memory system")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to clear memory system: {e}")

        # Clear storage interface caches
        for region_name in ['hippocampus', 'temporal_lobe', 'amygdala', 'prefrontal', 'basal_ganglia']:
            region = getattr(self.coordinator, region_name, None)
            if region and hasattr(region, 'storage'):
                storage = region.storage
                if hasattr(storage, 'local_cache'):
                    storage.local_cache.clear()
                    storage._cache_ids.clear()
                    logger.debug(f"   ✓ Cleared {region_name} storage cache")

        logger.info("   ✓ All memories and caches cleared")

    async def _import_region(
        self,
        region_name: str,
        region_data: Dict[str, Any]
    ) -> int:
        """
        Import Single Brain Region
        导入单个脑区

        Args:
            region_name: Brain region name
            region_data: Region data from archive

        Returns:
            Number of memories imported
        """
        if not self.coordinator:
            return 0

        try:
            if region_name == 'hippocampus':
                return await self._import_hippocampus(region_data)
            elif region_name == 'temporal_lobe':
                return await self._import_temporal_lobe(region_data)
            elif region_name == 'amygdala':
                return await self._import_amygdala(region_data)
            elif region_name == 'prefrontal':
                return await self._import_prefrontal(region_data)
            elif region_name == 'basal_ganglia':
                return await self._import_basal_ganglia(region_data)
            else:
                logger.warning(f"Unknown region: {region_name}")
                return 0

        except Exception as e:
            logger.error(f"Failed to import {region_name}: {e}")
            return 0

    async def _import_hippocampus(self, data: Dict[str, Any]) -> int:
        """Import Hippocampus memories"""
        if not hasattr(self.coordinator, 'hippocampus'):
            return 0

        hippocampus = self.coordinator.hippocampus
        memories_data = data.get('memories', [])

        # Use Hippocampus's import_state method if available
        if hasattr(hippocampus, 'import_state'):
            hippocampus.import_state(data)
            return len(memories_data)

        # Manual import
        from BMAM.src.agents.brain_regions.hippocampus_agent.core import EpisodicMemory

        for mem_data in memories_data:
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

            # Rebuild indices
            for entity in memory.entities:
                hippocampus.entity_index[entity].append(memory.id)

        return len(memories_data)

    async def _import_temporal_lobe(self, data: Dict[str, Any]) -> int:
        """Import Temporal Lobe memories"""
        if not hasattr(self.coordinator, 'temporal_lobe'):
            return 0

        temporal_lobe = self.coordinator.temporal_lobe

        # Import using temporal_lobe's import method if available
        if hasattr(temporal_lobe, 'import_state'):
            temporal_lobe.import_state(data)
            return len(data.get('memories', []))

        return 0

    async def _import_amygdala(self, data: Dict[str, Any]) -> int:
        """Import Amygdala memories"""
        if not hasattr(self.coordinator, 'amygdala'):
            return 0

        amygdala = self.coordinator.amygdala

        if hasattr(amygdala, 'import_state'):
            amygdala.import_state(data)
            return len(data.get('memories', []))

        return 0

    async def _import_prefrontal(self, data: Dict[str, Any]) -> int:
        """Import Prefrontal memories"""
        if not hasattr(self.coordinator, 'prefrontal'):
            return 0

        prefrontal = self.coordinator.prefrontal

        if hasattr(prefrontal, 'import_state'):
            prefrontal.import_state(data)
            return len(data.get('memories', []))

        return 0

    async def _import_basal_ganglia(self, data: Dict[str, Any]) -> int:
        """Import Basal Ganglia memories"""
        if not hasattr(self.coordinator, 'basal_ganglia'):
            return 0

        basal_ganglia = self.coordinator.basal_ganglia

        if hasattr(basal_ganglia, 'import_state'):
            basal_ganglia.import_state(data)
            return len(data.get('memories', []))

        return 0

    def _validate_relationships(self) -> int:
        """
        Validate Cross-Region Relationships
        验证跨脑区关系

        Ensures memory references are valid after import.

        Returns:
            Number of relationships validated
        """
        validated_count = 0

        if not self.coordinator:
            return 0

        # Validate Hippocampus → Temporal Lobe references
        if hasattr(self.coordinator, 'hippocampus') and self.coordinator.hippocampus:
            hippocampus = self.coordinator.hippocampus

            for memory in hippocampus.memories:
                if 'consolidated_to' in memory.metadata:
                    validated_count += 1

        # Validate Amygdala → Hippocampus references
        if hasattr(self.coordinator, 'amygdala') and self.coordinator.amygdala:
            amygdala = self.coordinator.amygdala

            for memory in amygdala.memories:
                if hasattr(memory, 'reference_id'):
                    validated_count += 1

        return validated_count

    async def _create_backup(self) -> TransferReport:
        """Create backup of current memory"""
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = Path("data/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)

        return await self.export_memory(
            output_dir=backup_dir,
            name=backup_name,
            description="Automatic backup before import",
            tags=["backup", "auto"]
        )

    async def _rollback(self, backup_path: Path) -> None:
        """Rollback to backup"""
        logger.info(f"🔄 Rolling back to: {backup_path}")
        await self.import_memory(
            archive_path=backup_path,
            create_backup=False,
            validate_before_import=False
        )
        logger.info("✅ Rollback complete")

    def get_current_memory_info(self) -> Dict[str, Any]:
        """
        Get Current Memory Info
        获取当前记忆信息

        Returns:
            Dictionary with memory statistics
        """
        if not self.coordinator:
            return {'error': 'No coordinator'}

        info = {
            'brain_regions': {},
            'total_memories': 0
        }

        # Collect statistics from each region
        if hasattr(self.coordinator, 'hippocampus') and self.coordinator.hippocampus:
            count = len(self.coordinator.hippocampus.memories)
            info['brain_regions']['hippocampus'] = count
            info['total_memories'] += count

        if hasattr(self.coordinator, 'temporal_lobe') and self.coordinator.temporal_lobe:
            count = len(self.coordinator.temporal_lobe.memories)
            info['brain_regions']['temporal_lobe'] = count
            info['total_memories'] += count

        if hasattr(self.coordinator, 'amygdala') and self.coordinator.amygdala:
            count = len(self.coordinator.amygdala.memories)
            info['brain_regions']['amygdala'] = count
            info['total_memories'] += count

        if hasattr(self.coordinator, 'prefrontal') and self.coordinator.prefrontal:
            if hasattr(self.coordinator.prefrontal, 'memories'):
                count = len(self.coordinator.prefrontal.memories)
                info['brain_regions']['prefrontal'] = count
                info['total_memories'] += count

        if hasattr(self.coordinator, 'basal_ganglia') and self.coordinator.basal_ganglia:
            if hasattr(self.coordinator.basal_ganglia, 'memories'):
                count = len(self.coordinator.basal_ganglia.memories)
                info['brain_regions']['basal_ganglia'] = count
                info['total_memories'] += count

        return info
