#!/usr/bin/env python3
"""
Brain Region Memory Swapper

Allows selective loading and swapping of individual brain region memories from BMA archives.
This enables modular memory management where you can mix and match brain regions from different sources.

Features:
- Load only specific brain regions from a BMA archive
- Swap out individual brain regions (e.g., replace Hippocampus but keep Temporal Lobe)
- Combine brain regions from multiple BMA archives
- Export specific brain regions to standalone files

Example Use Cases:
1. Test different short-term memory states (Hippocampus) with same long-term memory (Temporal Lobe)
2. Compare emotional responses (Amygdala) across different conversation contexts
3. Isolate and test individual brain region contributions
"""

import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import logging

from ..utils.paths import BMAMPaths

logger = logging.getLogger(__name__)


class BrainRegionSwapper:
    """
    Manages selective loading and swapping of brain region memories.

    Brain Regions Supported:
    - temporal_lobe: Long-term memory (SQLite database)
    - hippocampus: Short-term memory (JSON)
    - prefrontal: Working memory (JSON)
    - amygdala: Emotional memory (JSON)
    - basal_ganglia: Procedural memory (JSON)
    """

    # NOTE: BRAIN_REGIONS will be populated dynamically using BMAMPaths
    @classmethod
    def _get_brain_regions(cls) -> Dict[str, Dict[str, Any]]:
        """Get brain regions config using unified paths"""
        return {
            'temporal_lobe': {'file': 'temporal_lobe.db', 'format': 'sqlite', 'target': str(BMAMPaths.BRAIN_MEMORY_DB)},
            'hippocampus': {'file': 'hippocampus.json', 'format': 'json', 'target': str(BMAMPaths.HIPPOCAMPUS_STATE)},
            'prefrontal': {'file': 'prefrontal.json', 'format': 'json', 'target': str(BMAMPaths.PREFRONTAL_STATE)},
            'amygdala': {'file': 'amygdala.json', 'format': 'json', 'target': str(BMAMPaths.AMYGDALA_STATE)},
            'basal_ganglia': {'file': 'basal_ganglia.json', 'format': 'json', 'target': str(BMAMPaths.BASAL_GANGLIA_STATE)}
        }

    # Legacy support - will be dynamically populated
    BRAIN_REGIONS = {}

    def __init__(self, bmam_root: Optional[Path] = None):
        """
        Args:
            bmam_root: Root directory of BMAM framework (default: auto-detect)
        """
        # Use BMAMPaths for unified path management
        self.bmam_root = Path(bmam_root) if bmam_root else BMAMPaths.BMAM_ROOT
        self.data_dir = BMAMPaths.DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Populate BRAIN_REGIONS dynamically
        self.__class__.BRAIN_REGIONS = self._get_brain_regions()

    def load_regions(
        self,
        archive_path: Path,
        regions: List[str],
        force: bool = False,
        backup: bool = True
    ) -> Dict[str, Any]:
        """
        Load specific brain regions from a BMA archive.

        Args:
            archive_path: Path to .bma archive directory
            regions: List of brain region names to load (e.g., ['hippocampus', 'amygdala'])
            force: Overwrite existing brain region states without backup
            backup: Create backup of existing states before overwriting

        Returns:
            Dictionary with load results:
            {
                'success': bool,
                'loaded_regions': List[str],
                'skipped_regions': List[str],
                'backups_created': List[str]
            }

        Example:
            # Load only Hippocampus and Amygdala from an archive
            swapper = BrainRegionSwapper()
            result = swapper.load_regions(
                archive_path=Path("archives/memory_baseline.bma"),
                regions=['hippocampus', 'amygdala']
            )
        """
        archive_path = Path(archive_path)
        result = {
            'success': False,
            'loaded_regions': [],
            'skipped_regions': [],
            'backups_created': []
        }

        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        # Load manifest
        manifest_path = archive_path / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Archive manifest not found: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        brain_regions_dir = archive_path / "brain_regions"
        if not brain_regions_dir.exists():
            raise FileNotFoundError(f"No brain_regions directory in archive: {archive_path}")

        logger.info(f"📦 Loading {len(regions)} brain regions from {archive_path.name}")

        # Load each requested region
        for region_name in regions:
            if region_name not in self.BRAIN_REGIONS:
                logger.warning(f"   ⚠️  Unknown region '{region_name}', skipping")
                result['skipped_regions'].append(region_name)
                continue

            region_config = self.BRAIN_REGIONS[region_name]
            source_file = brain_regions_dir / region_config['file']

            if not source_file.exists():
                logger.warning(f"   ⚠️  Region '{region_name}' not found in archive, skipping")
                result['skipped_regions'].append(region_name)
                continue

            target_file = self.bmam_root / region_config['target']

            # Backup existing state if requested
            if backup and target_file.exists() and not force:
                backup_path = self._create_backup(target_file)
                result['backups_created'].append(str(backup_path))
                logger.info(f"   💾 Backed up existing {region_name} to {backup_path.name}")

            # Copy region file to target location
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_file)
            result['loaded_regions'].append(region_name)
            logger.info(f"   ✅ Loaded {region_name} from archive")

        result['success'] = len(result['loaded_regions']) > 0
        logger.info(f"📊 Loaded {len(result['loaded_regions'])} regions, skipped {len(result['skipped_regions'])}")

        return result

    def swap_region(
        self,
        region_name: str,
        source_archive: Path,
        backup: bool = True
    ) -> Dict[str, Any]:
        """
        Swap a single brain region from an archive.

        Args:
            region_name: Name of brain region to swap (e.g., 'hippocampus')
            source_archive: Path to BMA archive to load from
            backup: Create backup before swapping

        Returns:
            Swap result dictionary

        Example:
            # Replace Hippocampus with another archive version while keeping other regions
            swapper = BrainRegionSwapper()
            swapper.swap_region(
                region_name='hippocampus',
                source_archive=Path("archives/memory_full.bma")
            )
        """
        logger.info(f"🔄 Swapping {region_name} from {source_archive.name}")
        return self.load_regions(
            archive_path=source_archive,
            regions=[region_name],
            backup=backup
        )

    def combine_archives(
        self,
        region_sources: Dict[str, Path],
        backup: bool = True
    ) -> Dict[str, Any]:
        """
        Combine brain regions from multiple archives.

        Args:
            region_sources: Mapping of region name to archive path
                Example: {
                    'temporal_lobe': Path("longterm_archive.bma"),
                    'hippocampus': Path("full_archive.bma"),
                    'amygdala': Path("truncated_archive.bma")
                }
            backup: Create backups before combining

        Returns:
            Combined load results

        Example:
            # Create hybrid memory: long-term from one archive + short-term from another
            swapper = BrainRegionSwapper()
            swapper.combine_archives({
                'temporal_lobe': Path("archives/longterm_archive.bma"),
                'hippocampus': Path("archives/full_archive.bma"),
                'prefrontal': Path("archives/full_archive.bma"),
                'amygdala': Path("archives/full_archive.bma")
            })
        """
        logger.info(f"🧩 Combining {len(region_sources)} brain regions from multiple archives")

        all_results = {
            'success': True,
            'loaded_regions': [],
            'skipped_regions': [],
            'backups_created': []
        }

        for region_name, archive_path in region_sources.items():
            result = self.load_regions(
                archive_path=archive_path,
                regions=[region_name],
                backup=backup
            )

            all_results['loaded_regions'].extend(result['loaded_regions'])
            all_results['skipped_regions'].extend(result['skipped_regions'])
            all_results['backups_created'].extend(result['backups_created'])

            if not result['success']:
                all_results['success'] = False

        logger.info(f"✅ Combined regions: {', '.join(all_results['loaded_regions'])}")
        return all_results

    def export_region(
        self,
        region_name: str,
        output_path: Path,
        create_manifest: bool = True
    ) -> Path:
        """
        Export a single brain region to a standalone file.

        Args:
            region_name: Name of brain region to export
            output_path: Where to save the exported file
            create_manifest: Also create a manifest file with metadata

        Returns:
            Path to exported file

        Example:
            # Export just the Hippocampus for sharing
            swapper = BrainRegionSwapper()
            exported = swapper.export_region(
                region_name='hippocampus',
                output_path=Path("exports/hippocampus_mode4.json")
            )
        """
        if region_name not in self.BRAIN_REGIONS:
            raise ValueError(f"Unknown brain region: {region_name}")

        region_config = self.BRAIN_REGIONS[region_name]
        source_file = self.bmam_root / region_config['target']

        if not source_file.exists():
            raise FileNotFoundError(f"Brain region state not found: {source_file}")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_file, output_path)
        logger.info(f"📤 Exported {region_name} to {output_path}")

        if create_manifest:
            manifest = {
                "brain_region": region_name,
                "format": region_config['format'],
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "source_file": str(source_file.relative_to(self.bmam_root)),
                "file_size_bytes": output_path.stat().st_size
            }

            manifest_path = output_path.parent / f"{output_path.stem}_manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            logger.info(f"   📄 Created manifest: {manifest_path.name}")

        return output_path

    def list_available_regions(self, archive_path: Path) -> Dict[str, Any]:
        """
        List all brain regions available in a BMA archive.

        Args:
            archive_path: Path to .bma archive directory

        Returns:
            Dictionary with region information

        Example:
            swapper = BrainRegionSwapper()
            regions = swapper.list_available_regions(
                Path("archives/conversation_baseline.bma")
            )
            print(f"Available regions: {list(regions['regions'].keys())}")
        """
        archive_path = Path(archive_path)
        manifest_path = archive_path / "manifest.json"

        if not manifest_path.exists():
            raise FileNotFoundError(f"Archive manifest not found: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        result = {
            'archive_name': manifest['memory_info']['name'],
            'format_version': manifest.get('format_version', 'unknown'),
            'regions': {}
        }

        if 'brain_regions' in manifest:
            for region_name, region_info in manifest['brain_regions'].items():
                region_file = archive_path / region_info['file']
                result['regions'][region_name] = {
                    'available': region_file.exists(),
                    'format': region_info.get('format', 'unknown'),
                    'file': region_info['file']
                }

                # Add memory counts if available
                for key in region_info:
                    if 'count' in key or 'slots' in key:
                        result['regions'][region_name][key] = region_info[key]

        return result

    def _create_backup(self, file_path: Path) -> Path:
        """Create a timestamped backup of a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = file_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
        shutil.copy2(file_path, backup_path)

        return backup_path


# Convenience functions

def swap_brain_region(region_name: str, source_archive: Path, backup: bool = True):
    """
    Quick function to swap a single brain region.

    Args:
        region_name: Brain region to swap ('hippocampus', 'temporal_lobe', etc.)
        source_archive: Path to BMA archive
        backup: Create backup before swapping

    Example:
        swap_brain_region('hippocampus', Path("archives/conversation_full.bma"))
    """
    swapper = BrainRegionSwapper()
    return swapper.swap_region(region_name, source_archive, backup)


def combine_brain_regions(region_sources: Dict[str, Path], backup: bool = True):
    """
    Quick function to combine brain regions from multiple archives.

    Args:
        region_sources: Mapping of region name to archive path
        backup: Create backups before combining

    Example:
        combine_brain_regions({
            'temporal_lobe': Path("longterm_archive.bma"),
            'hippocampus': Path("full_archive.bma")
        })
    """
    swapper = BrainRegionSwapper()
    return swapper.combine_archives(region_sources, backup)
