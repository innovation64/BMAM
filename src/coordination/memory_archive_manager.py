"""
Memory Archive Manager - 记忆归档操作管理器

负责 BMA (BMAM Memory Archive) 格式的导出、加载和验证操作。
从 brain_coordinator_refactored.py 提取，遵循委托模式。

Usage:
    archive_manager = MemoryArchiveManager(coordinator)
    result = archive_manager.export_archive("my_snapshot", tags=["test"])
    result = archive_manager.load_archive(Path("archives/my_snapshot.bma"))
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional, TYPE_CHECKING

from ..utils.config import get_logger
from ..utils.paths import BMAMPaths

if TYPE_CHECKING:
    from .brain_coordinator_refactored import BrainInspiredCoordinator

logger = get_logger(__name__)


class MemoryArchiveManager:
    """
    管理 BMA 格式记忆归档的导出、加载和验证。

    BMA (BMAM Memory Archive) 格式 v2.0.0 支持:
    - 多脑区状态保存 (Hippocampus, Prefrontal, Amygdala, BasalGanglia)
    - FAISS 向量索引
    - Embedding 缓存
    - 完整性校验 (checksums)
    """

    def __init__(self, coordinator: "BrainInspiredCoordinator"):
        self.coordinator = coordinator

    def export_archive(
        self,
        archive_name: str,
        output_dir: Path = Path("archives/"),
        description: str = "",
        tags: Optional[List[str]] = None,
        include_faiss: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Export current memory state to BMA format.

        Args:
            archive_name: Name for the archive (creates {name}.bma directory)
            output_dir: Directory where archive will be created
            description: Human-readable description
            tags: List of tags for categorization
            include_faiss: Whether to include FAISS vector index
            metadata: Additional custom metadata

        Returns:
            Dict with export results including 'success', 'archive_path', 'statistics'
        """
        try:
            from ..memory.memory_archive import MemoryArchive

            # Resolve database path
            database_url = os.getenv('DATABASE_URL', str(BMAMPaths.BRAIN_MEMORY_DB))
            if database_url.startswith('sqlite:///'):
                database_url = database_url.replace('sqlite:///', '')

            db_path = Path(database_url)
            if not db_path.exists():
                return {
                    'success': False,
                    'error': f'Memory database not found: {db_path}',
                    'archive_path': None
                }

            # Get FAISS index path if requested
            faiss_path = None
            if include_faiss:
                faiss_path = BMAMPaths.FAISS_INDEX_DIR
                if not faiss_path.exists():
                    logger.warning(f"FAISS index not found at {faiss_path}, skipping")
                    faiss_path = None

            # Create archive v2.0.0 with multi-region support
            logger.info(f"Exporting multi-region memory archive: {archive_name}")
            archive = MemoryArchive.create_from_coordinator(
                name=archive_name,
                coordinator=self.coordinator,
                output_dir=output_dir,
                description=description,
                tags=tags,
                metadata=metadata
            )

            # Get archive info
            info = archive.get_info()

            result = {
                'success': True,
                'archive_path': archive.archive_path,
                'statistics': info['statistics'],
                'info': info
            }

            # Add format-specific fields
            if 'total_size_bytes' in info:
                result['size_bytes'] = info['total_size_bytes']
            if 'files' in info:
                result['files_created'] = info['files']
            if 'brain_regions' in info:
                result['brain_regions'] = info['brain_regions']
                result['total_regions'] = info.get('total_regions', len(info['brain_regions']))

            return result

        except Exception as e:
            logger.error(f"Failed to export memory archive: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'archive_path': None
            }

    def load_archive(
        self,
        archive_path: Path,
        target_dir: Path = None,
        validate: bool = True,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Load memory archive to current instance.

        WARNING: This replaces current memory database and FAISS index.

        Args:
            archive_path: Path to .bma archive directory
            target_dir: Target directory for loading (default: data/)
            validate: Whether to validate archive before loading
            force: Force loading even if validation fails

        Returns:
            Dict with load results including 'success', 'loaded_files', 'statistics'
        """
        try:
            from ..memory.memory_archive import MemoryArchive

            archive_path = Path(archive_path)

            if not archive_path.exists():
                return {
                    'success': False,
                    'error': f'Archive not found: {archive_path}',
                    'loaded_files': []
                }

            logger.info(f"Loading memory archive: {archive_path}")

            if target_dir is None:
                target_dir = BMAMPaths.DATA_DIR

            # Create archive instance and load
            archive = MemoryArchive(archive_path)
            result = archive.load(
                target_dir=target_dir,
                validate=validate,
                force=force
            )

            # Get archive statistics
            info = archive.get_info()
            result['statistics'] = info.get('statistics', {})
            result['archive_name'] = info.get('name', archive_path.name)

            if result['success']:
                logger.info(f"Successfully loaded memory archive: {info.get('name')}")
                logger.info(f"   Total memories: {info['statistics'].get('total_memories', 0):,}")

                # Load brain region states if v2.0.0
                self._load_brain_region_states(result.get('brain_regions_data', {}))
                logger.info("Memory system will reload on next operation")

            return result

        except Exception as e:
            logger.error(f"Failed to load memory archive: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'loaded_files': []
            }

    def _load_brain_region_states(self, brain_regions_data: Dict[str, Any]) -> None:
        """Load brain region states from archive data."""
        if not brain_regions_data:
            return

        logger.info("Loading brain region states...")
        coord = self.coordinator

        # Hippocampus
        if 'hippocampus' in brain_regions_data and hasattr(coord, 'hippocampus'):
            self._try_load_region_state(
                coord.hippocampus,
                brain_regions_data['hippocampus'],
                "Hippocampus"
            )

        # Prefrontal
        prefrontal_agent = getattr(coord, 'prefrontal_storage', None) or getattr(coord, 'prefrontal_agent', None)
        if 'prefrontal' in brain_regions_data and prefrontal_agent:
            self._try_load_region_state(
                prefrontal_agent,
                brain_regions_data['prefrontal'],
                "PrefrontalCortex"
            )

        # Amygdala
        if 'amygdala' in brain_regions_data and hasattr(coord, 'amygdala'):
            self._try_load_region_state(
                coord.amygdala,
                brain_regions_data['amygdala'],
                "Amygdala"
            )

        # BasalGanglia
        if 'basal_ganglia' in brain_regions_data and hasattr(coord, 'basal_ganglia'):
            self._try_load_region_state(
                coord.basal_ganglia,
                brain_regions_data['basal_ganglia'],
                "BasalGanglia"
            )

        logger.info("All brain regions loaded successfully")

    def _try_load_region_state(self, agent, state_data: Dict, region_name: str) -> bool:
        """Try to load state for a brain region agent."""
        try:
            success = agent.load_state(state_data)
            if success:
                logger.info(f"   {region_name} state restored")
            else:
                logger.warning(f"   {region_name} state load failed")
            return success
        except Exception as e:
            logger.error(f"   {region_name} load error: {e}")
            return False

    def validate_archive(
        self,
        archive_path: Path,
        check_checksums: bool = True
    ) -> Dict[str, Any]:
        """
        Validate memory archive integrity and compatibility.

        Args:
            archive_path: Path to .bma archive directory
            check_checksums: Whether to verify file checksums

        Returns:
            Dict with validation results including 'valid', 'errors', 'warnings'
        """
        try:
            from ..memory.memory_archive import MemoryArchive

            archive_path = Path(archive_path)

            if not archive_path.exists():
                return {
                    'valid': False,
                    'errors': [f'Archive not found: {archive_path}'],
                    'warnings': [],
                    'manifest_valid': False,
                    'files_valid': False,
                    'checksums_valid': False
                }

            archive = MemoryArchive(archive_path)
            return archive.validate(check_checksums=check_checksums)

        except Exception as e:
            logger.error(f"Failed to validate archive: {e}", exc_info=True)
            return {
                'valid': False,
                'errors': [f'Validation failed: {str(e)}'],
                'warnings': [],
                'manifest_valid': False,
                'files_valid': False,
                'checksums_valid': False
            }
