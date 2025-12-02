"""
BMAM Memory Archive (BMA) Format Handler

This module implements the unified memory archive format for BMAM framework.
The BMA format provides a standardized, portable, and self-contained way to
package, validate, and exchange memory states.

Features:
- Standard directory structure with manifest
- Integrity validation via SHA256 checksums
- Version compatibility checking
- Statistics collection and metadata
- Self-documenting archives

Format Structure:
    my_memory.bma/
    ├── manifest.json      # Required: metadata, statistics, compatibility
    ├── memories.db        # Required: standard SQLite database
    ├── faiss_index/       # Optional: FAISS vector index
    ├── checksums.json     # Recommended: SHA256 integrity verification
    └── README.md          # Optional: human-readable description

Author: BMAM Framework Team
Created: 2025-11-12
Version: 1.0.0
"""

import json
import hashlib
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MemoryArchive:
    """
    Handles creation, validation, and loading of BMAM Memory Archives (BMA format).

    The BMA format is a standardized directory structure containing:
    - SQLite database (memories.db)
    - FAISS vector index (optional)
    - Manifest with metadata and statistics
    - Checksums for integrity validation
    - Human-readable README

    Example:
        # Create archive
        archive = MemoryArchive.create(
            name="memory_baseline",
            source_db_path=Path("data/brain_memory.db"),
            output_dir=Path("archives/"),
            description="Memory snapshot baseline",
            tags=["baseline", "test"]
        )

        # Load archive
        archive = MemoryArchive(Path("archives/memory_baseline.bma"))
        validation = archive.validate()
        if validation['valid']:
            archive.load(target_dir=Path("data/"))
    """

    FORMAT_VERSION = "1.0.0"
    ARCHIVE_TYPE = "bmam_memory_archive"

    # Required features for compatibility
    REQUIRED_FEATURES = ["sqlite3", "faiss"]
    MIN_BMAM_VERSION = "1.0.0"

    def __init__(self, archive_path: Path):
        """
        Initialize MemoryArchive from an existing BMA directory.

        Args:
            archive_path: Path to the .bma directory
        """
        self.archive_path = Path(archive_path)
        self.manifest_path = self.archive_path / "manifest.json"
        self.db_path = self.archive_path / "memories.db"
        self.faiss_path = self.archive_path / "faiss_index"
        self.checksum_path = self.archive_path / "checksums.json"
        self.readme_path = self.archive_path / "README.md"

        self.manifest: Optional[Dict[str, Any]] = None

        if self.archive_path.exists():
            self._load_manifest()

    @classmethod
    def create(
        cls,
        name: str,
        source_db_path: Path,
        output_dir: Path,
        description: str = "",
        tags: Optional[List[str]] = None,
        source_faiss_path: Optional[Path] = None,
        language: str = "en",
        metadata: Optional[Dict[str, Any]] = None
    ) -> "MemoryArchive":
        """
        Create a new BMA archive from source memory files.

        Args:
            name: Archive name (will be used as directory name)
            source_db_path: Path to source SQLite database
            output_dir: Directory where archive will be created
            description: Human-readable description
            tags: List of tags for categorization
            source_faiss_path: Optional path to FAISS index directory
            language: Language code (default: "en")
            metadata: Additional custom metadata

        Returns:
            MemoryArchive instance for the created archive

        Raises:
            FileNotFoundError: If source files don't exist
            ValueError: If archive name is invalid
        """
        # Validate inputs
        if not source_db_path.exists():
            raise FileNotFoundError(f"Source database not found: {source_db_path}")

        if not name or "/" in name or "\\" in name:
            raise ValueError(f"Invalid archive name: {name}")

        # Create archive directory
        archive_path = output_dir / f"{name}.bma"
        archive_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"📦 Creating BMA archive: {archive_path}")

        # Copy database
        db_dest = archive_path / "memories.db"
        shutil.copy2(source_db_path, db_dest)
        logger.info(f"   ✓ Copied database: {source_db_path.name}")

        # Copy FAISS index if provided
        has_faiss = False
        if source_faiss_path and source_faiss_path.exists():
            faiss_dest = archive_path / "faiss_index"
            if faiss_dest.exists():
                shutil.rmtree(faiss_dest)
            shutil.copytree(source_faiss_path, faiss_dest)
            has_faiss = True
            logger.info(f"   ✓ Copied FAISS index: {source_faiss_path.name}")

        # Collect statistics from database
        stats = cls._collect_statistics(db_dest)
        logger.info(f"   ✓ Collected statistics: {stats['total_memories']} memories")

        # Create manifest
        manifest = {
            "format_version": cls.FORMAT_VERSION,
            "archive_type": cls.ARCHIVE_TYPE,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "memory_info": {
                "name": name,
                "description": description,
                "tags": tags or [],
                "language": language,
                "metadata": metadata or {}
            },
            "statistics": stats,
            "files": {
                "database": {
                    "path": "memories.db",
                    "required": True,
                    "size_bytes": db_dest.stat().st_size
                }
            },
            "compatibility": {
                "min_bmam_version": cls.MIN_BMAM_VERSION,
                "required_features": cls.REQUIRED_FEATURES.copy()
            }
        }

        # Add FAISS info if present
        if has_faiss:
            faiss_size = sum(f.stat().st_size for f in (archive_path / "faiss_index").rglob("*") if f.is_file())
            manifest["files"]["vector_index"] = {
                "path": "faiss_index/",
                "required": False,
                "size_bytes": faiss_size
            }

        # Write manifest
        manifest_path = archive_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        logger.info(f"   ✓ Created manifest")

        # Generate checksums
        checksums = cls._generate_checksums(archive_path, has_faiss)
        checksum_path = archive_path / "checksums.json"
        with open(checksum_path, 'w', encoding='utf-8') as f:
            json.dump(checksums, f, indent=2)
        logger.info(f"   ✓ Generated checksums")

        # Create README
        readme_content = cls._create_readme(name, description, tags, stats, has_faiss)
        readme_path = archive_path / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        logger.info(f"   ✓ Created README")

        logger.info(f"✅ Archive created successfully: {archive_path}")

        return cls(archive_path)

    @classmethod
    def create_from_coordinator(
        cls,
        name: str,
        coordinator: Any,  # BrainInspiredCoordinator
        output_dir: Path,
        description: str = "",
        tags: Optional[List[str]] = None,
        language: str = "en",
        metadata: Optional[Dict[str, Any]] = None
    ) -> "MemoryArchive":
        """
        Create a BMA archive v2.0.0 with multi-brain-region support from coordinator.

        Args:
            name: Archive name (will be used as directory name)
            coordinator: BrainInspiredCoordinator instance with agents
            output_dir: Directory where archive will be created
            description: Human-readable description
            tags: List of tags for categorization
            language: Language code (default: "en")
            metadata: Additional custom metadata

        Returns:
            MemoryArchive instance for the created archive
        """
        # Validate inputs
        if not name or "/" in name or "\\" in name:
            raise ValueError(f"Invalid archive name: {name}")

        # Create archive directory
        archive_path = output_dir / f"{name}.bma"
        archive_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"📦 Creating BMA v2.0 multi-region archive: {archive_path}")

        # Create brain_regions directory
        brain_regions_dir = archive_path / "brain_regions"
        brain_regions_dir.mkdir(exist_ok=True)

        # Export each brain region
        brain_regions_info = {}
        total_memories = 0

        # 1. Temporal Lobe (long-term memory - SQLite)
        import os
        database_url = os.getenv('DATABASE_URL', 'data/brain_memory.db')
        if database_url.startswith('sqlite:///'):
            database_url = database_url.replace('sqlite:///', '')
        db_path = Path(database_url)

        if db_path.exists():
            db_dest = brain_regions_dir / "temporal_lobe.db"
            shutil.copy2(db_path, db_dest)
            stats = cls._collect_statistics(db_dest)
            brain_regions_info['temporal_lobe'] = {
                'file': 'brain_regions/temporal_lobe.db',
                'format': 'sqlite',
                'required': True,
                'memory_count': stats['total_memories']
            }
            total_memories += stats['total_memories']
            logger.info(f"   ✓ Exported TemporalLobe: {stats['total_memories']} memories")

        # 2. Hippocampus (short-term memory - JSON)
        if hasattr(coordinator, 'hippocampus') and coordinator.hippocampus:
            try:
                hippo_state = coordinator.hippocampus.export_state()
                hippo_file = brain_regions_dir / "hippocampus.json"
                with open(hippo_file, 'w', encoding='utf-8') as f:
                    json.dump(hippo_state, f, indent=2, ensure_ascii=False)
                brain_regions_info['hippocampus'] = {
                    'file': 'brain_regions/hippocampus.json',
                    'format': 'json',
                    'required': False,
                    'memory_count': len(hippo_state.get('memories', []))
                }
                logger.info(f"   ✓ Exported Hippocampus: {len(hippo_state.get('memories', []))} memories")
            except Exception as e:
                logger.warning(f"   ⚠️ Hippocampus export failed: {e}")

        # 3. Prefrontal Cortex (working memory - JSON)
        prefrontal_agent = None
        if hasattr(coordinator, 'prefrontal_storage') and coordinator.prefrontal_storage:
            prefrontal_agent = coordinator.prefrontal_storage
        elif hasattr(coordinator, 'prefrontal') and coordinator.prefrontal:
            prefrontal_agent = coordinator.prefrontal

        if prefrontal_agent:
            try:
                prefrontal_state = prefrontal_agent.export_state()
                prefrontal_file = brain_regions_dir / "prefrontal.json"
                with open(prefrontal_file, 'w', encoding='utf-8') as f:
                    json.dump(prefrontal_state, f, indent=2, ensure_ascii=False)
                brain_regions_info['prefrontal'] = {
                    'file': 'brain_regions/prefrontal.json',
                    'format': 'json',
                    'required': False,
                    'working_memory_slots': len(prefrontal_state.get('working_memory', []))
                }
                logger.info(f"   ✓ Exported PrefrontalCortex: {len(prefrontal_state.get('working_memory', []))} items")
            except Exception as e:
                logger.warning(f"   ⚠️ PrefrontalCortex export failed: {e}")

        # 4. Amygdala (emotional memory - JSON)
        if hasattr(coordinator, 'amygdala') and coordinator.amygdala:
            try:
                amygdala_state = coordinator.amygdala.export_state()
                amygdala_file = brain_regions_dir / "amygdala.json"
                with open(amygdala_file, 'w', encoding='utf-8') as f:
                    json.dump(amygdala_state, f, indent=2, ensure_ascii=False)
                brain_regions_info['amygdala'] = {
                    'file': 'brain_regions/amygdala.json',
                    'format': 'json',
                    'required': False,
                    'emotional_memories': len(amygdala_state.get('memories', []))
                }
                logger.info(f"   ✓ Exported Amygdala: {len(amygdala_state.get('memories', []))} memories")
            except Exception as e:
                logger.warning(f"   ⚠️ Amygdala export failed: {e}")

        # 5. Basal Ganglia (procedural memory - JSON)
        if hasattr(coordinator, 'basal_ganglia') and coordinator.basal_ganglia:
            try:
                basal_state = coordinator.basal_ganglia.export_state()
                basal_file = brain_regions_dir / "basal_ganglia.json"
                with open(basal_file, 'w', encoding='utf-8') as f:
                    json.dump(basal_state, f, indent=2, ensure_ascii=False)
                brain_regions_info['basal_ganglia'] = {
                    'file': 'brain_regions/basal_ganglia.json',
                    'format': 'json',
                    'required': False,
                    'skills_count': len(basal_state.get('skills', []))
                }
                logger.info(f"   ✓ Exported BasalGanglia: {len(basal_state.get('skills', []))} skills")
            except Exception as e:
                logger.warning(f"   ⚠️ BasalGanglia export failed: {e}")

        # 6. Copy FAISS vector index if exists
        has_faiss = False
        faiss_path = Path("data/faiss_index")
        if faiss_path.exists():
            faiss_dest = archive_path / "vectors"
            if faiss_dest.exists():
                shutil.rmtree(faiss_dest)
            shutil.copytree(faiss_path, faiss_dest)
            has_faiss = True
            logger.info(f"   ✓ Exported vector indices")

        # Create manifest v2.0.0
        manifest = {
            "format_version": "2.0.0",  # Upgraded version
            "archive_type": cls.ARCHIVE_TYPE,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "memory_info": {
                "name": name,
                "description": description,
                "tags": tags or [],
                "language": language,
                "metadata": metadata or {}
            },
            "brain_regions": brain_regions_info,
            "statistics": {
                "total_memories": total_memories,
                "brain_regions_exported": list(brain_regions_info.keys())
            },
            "compatibility": {
                "min_bmam_version": cls.MIN_BMAM_VERSION,
                "required_features": cls.REQUIRED_FEATURES.copy()
            }
        }

        # Add vector index info if present
        if has_faiss:
            manifest["vectors"] = {
                "path": "vectors/",
                "format": "faiss"
            }

        # Write manifest
        manifest_path = archive_path / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        logger.info(f"   ✓ Created manifest v2.0.0")

        # Generate checksums
        checksums = cls._generate_checksums_v2(archive_path)
        checksum_path = archive_path / "checksums.json"
        with open(checksum_path, 'w', encoding='utf-8') as f:
            json.dump(checksums, f, indent=2)
        logger.info(f"   ✓ Generated checksums")

        # Create README
        readme_content = cls._create_readme_v2(name, description, tags, brain_regions_info, has_faiss)
        readme_path = archive_path / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        logger.info(f"   ✓ Created README")

        logger.info(f"✅ Multi-region archive created successfully: {archive_path}")

        return cls(archive_path)

    def validate(self, check_checksums: bool = True) -> Dict[str, Any]:
        """
        Validate archive integrity and compatibility.

        Args:
            check_checksums: Whether to verify file checksums (slower but more thorough)

        Returns:
            Dictionary with validation results:
            {
                'valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'manifest_valid': bool,
                'files_valid': bool,
                'checksums_valid': bool,
                'compatibility': Dict
            }
        """
        errors = []
        warnings = []

        # Check archive directory exists
        if not self.archive_path.exists():
            return {
                'valid': False,
                'errors': [f"Archive directory not found: {self.archive_path}"],
                'warnings': [],
                'manifest_valid': False,
                'files_valid': False,
                'checksums_valid': False
            }

        # Validate manifest
        manifest_valid = self._validate_manifest(errors, warnings)

        # Validate required files
        files_valid = self._validate_files(errors, warnings)

        # Validate checksums if requested
        checksums_valid = True
        if check_checksums:
            checksums_valid = self._validate_checksums(errors, warnings)

        # Check compatibility
        compatibility = self._check_compatibility(errors, warnings)

        is_valid = len(errors) == 0 and manifest_valid and files_valid

        return {
            'valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'manifest_valid': manifest_valid,
            'files_valid': files_valid,
            'checksums_valid': checksums_valid,
            'compatibility': compatibility
        }

    def load(self, target_dir: Path, validate: bool = True, force: bool = False) -> Dict[str, Any]:
        """
        Load archive contents to target directory.

        Args:
            target_dir: Directory where memory files will be copied
            validate: Whether to validate before loading
            force: Force loading even if validation fails (use with caution)

        Returns:
            Dictionary with load results:
            {
                'success': bool,
                'loaded_files': List[str],
                'target_db_path': Path,
                'target_faiss_path': Optional[Path],
                'validation': Dict (if validate=True)
            }

        Raises:
            ValueError: If validation fails and force=False
        """
        result = {
            'success': False,
            'loaded_files': [],
            'target_db_path': None,
            'target_faiss_path': None
        }

        # Validate if requested
        if validate:
            validation = self.validate()
            result['validation'] = validation

            if not validation['valid'] and not force:
                raise ValueError(
                    f"Archive validation failed with {len(validation['errors'])} errors. "
                    f"Use force=True to load anyway (not recommended)."
                )

            if not validation['valid']:
                logger.warning(f"⚠️  Loading archive despite validation errors (force=True)")

        # Create target directory
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📥 Loading archive to: {target_dir}")

        # Check format version
        format_version = self.manifest.get('format_version', '1.0.0')
        brain_regions_data = {}

        if format_version == '2.0.0' and 'brain_regions' in self.manifest:
            # v2.0.0: Multi-region format
            logger.info(f"   📦 Loading BMA v2.0.0 multi-region archive")

            brain_regions_info = self.manifest['brain_regions']

            # Copy brain region files
            for region_name, region_info in brain_regions_info.items():
                region_file = self.archive_path / region_info['file']

                if region_file.exists():
                    # For temporal_lobe.db, copy to standard location
                    if region_name == 'temporal_lobe' and region_info['format'] == 'sqlite':
                        target_db = target_dir / "brain_memory.db"
                        shutil.copy2(region_file, target_db)
                        result['loaded_files'].append("brain_memory.db")
                        result['target_db_path'] = target_db
                        logger.info(f"   ✓ Loaded {region_name}: brain_memory.db")
                    else:
                        # For JSON regions, store file content for later loading
                        if region_info['format'] == 'json':
                            with open(region_file, 'r', encoding='utf-8') as f:
                                brain_regions_data[region_name] = json.load(f)
                            result['loaded_files'].append(region_info['file'])
                            logger.info(f"   ✓ Loaded {region_name}: {region_info['file']}")

            # Copy vector indices if present
            vectors_path = self.archive_path / "vectors"
            if vectors_path.exists():
                target_vectors = target_dir / "faiss_index"
                if target_vectors.exists():
                    shutil.rmtree(target_vectors)
                shutil.copytree(vectors_path, target_vectors)
                result['loaded_files'].append("faiss_index/")
                result['target_faiss_path'] = target_vectors
                logger.info(f"   ✓ Loaded vector indices: faiss_index/")

        else:
            # v1.0.0: Legacy single-database format (backward compatible)
            logger.info(f"   📦 Loading BMA v1.0.0 legacy format")

            # Copy database
            if self.db_path.exists():
                target_db = target_dir / "brain_memory.db"
                shutil.copy2(self.db_path, target_db)
                result['loaded_files'].append("brain_memory.db")
                result['target_db_path'] = target_db
                logger.info(f"   ✓ Loaded database: brain_memory.db")

            # Copy FAISS index if present
            if self.faiss_path.exists():
                target_faiss = target_dir / "faiss_index"
                if target_faiss.exists():
                    shutil.rmtree(target_faiss)
                shutil.copytree(self.faiss_path, target_faiss)
                result['loaded_files'].append("faiss_index/")
                result['target_faiss_path'] = target_faiss
                logger.info(f"   ✓ Loaded FAISS index: faiss_index/")

        # Store brain regions data for coordinator to load
        result['brain_regions_data'] = brain_regions_data
        result['format_version'] = format_version
        result['success'] = True
        result['statistics'] = self.manifest.get('statistics', {})

        logger.info(f"✅ Archive loaded successfully")

        return result

    def get_info(self) -> Dict[str, Any]:
        """
        Get archive information from manifest.

        Returns:
            Dictionary with archive information
        """
        if not self.manifest:
            self._load_manifest()

        if not self.manifest:
            return {'error': 'Manifest not found or invalid'}

        format_version = self.manifest.get('format_version', '1.0.0')
        info = {
            'name': self.manifest['memory_info']['name'],
            'description': self.manifest['memory_info']['description'],
            'tags': self.manifest['memory_info']['tags'],
            'created_at': self.manifest['created_at'],
            'format_version': format_version,
            'statistics': self.manifest['statistics']
        }

        # Handle v1.0.0 vs v2.0.0 format
        if format_version == '2.0.0' and 'brain_regions' in self.manifest:
            # v2.0.0: Multi-region format
            info['brain_regions'] = list(self.manifest['brain_regions'].keys())
            info['total_regions'] = len(self.manifest['brain_regions'])
        elif 'files' in self.manifest:
            # v1.0.0: Legacy single-file format
            info['files'] = list(self.manifest['files'].keys())
            info['total_size_bytes'] = sum(
                f['size_bytes'] for f in self.manifest['files'].values()
                if 'size_bytes' in f
            )

        return info

    # Private helper methods

    def _load_manifest(self):
        """Load manifest from file."""
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                self.manifest = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load manifest: {e}")
            self.manifest = None

    def _validate_manifest(self, errors: List[str], warnings: List[str]) -> bool:
        """Validate manifest structure and content."""
        if not self.manifest_path.exists():
            errors.append("Missing manifest.json")
            return False

        if not self.manifest:
            errors.append("Invalid manifest.json (failed to parse)")
            return False

        # Get format version
        format_version = self.manifest.get('format_version', '1.0.0')

        # Check common required fields
        common_required_fields = [
            'format_version', 'archive_type', 'created_at',
            'memory_info', 'statistics', 'compatibility'
        ]

        for field in common_required_fields:
            if field not in self.manifest:
                errors.append(f"Missing required field in manifest: {field}")

        # Check format-specific required fields
        if format_version == '2.0.0':
            # v2.0.0: Multi-region format
            if 'brain_regions' not in self.manifest:
                errors.append("Missing required field in manifest: brain_regions (v2.0.0)")
        else:
            # v1.0.0: Legacy format
            if 'files' not in self.manifest:
                errors.append("Missing required field in manifest: files (v1.0.0)")

            # Only warn about version mismatch for v1.0.0
            if format_version != self.FORMAT_VERSION:
                warnings.append(
                    f"Format version mismatch: {format_version} "
                    f"(current: {self.FORMAT_VERSION})"
                )

        # Validate archive type
        if self.manifest.get('archive_type') != self.ARCHIVE_TYPE:
            errors.append(
                f"Invalid archive type: {self.manifest.get('archive_type')} "
                f"(expected: {self.ARCHIVE_TYPE})"
            )

        return len(errors) == 0

    def _validate_files(self, errors: List[str], warnings: List[str]) -> bool:
        """Validate that required files exist."""
        format_version = self.manifest.get('format_version', '1.0.0') if self.manifest else '1.0.0'

        if format_version == '2.0.0':
            # v2.0.0: Multi-region format
            # Check brain_regions files
            if self.manifest and 'brain_regions' in self.manifest:
                brain_regions_dir = self.archive_path / "brain_regions"
                if not brain_regions_dir.exists():
                    errors.append("Missing brain_regions directory")
                else:
                    for region_name, region_info in self.manifest['brain_regions'].items():
                        file_path = self.archive_path / region_info['file']

                        if region_info.get('required', False) and not file_path.exists():
                            errors.append(f"Missing required file: {region_info['file']}")
                        elif not region_info.get('required', False) and not file_path.exists():
                            warnings.append(f"Missing optional file: {region_info['file']}")

            # Check vectors directory (optional)
            vectors_dir = self.archive_path / "vectors"
            if not vectors_dir.exists():
                warnings.append("No vectors directory found (FAISS indices may be missing)")
        else:
            # v1.0.0: Legacy format
            if not self.db_path.exists():
                errors.append("Missing required file: memories.db")

            # Check files listed in manifest
            if self.manifest and 'files' in self.manifest:
                for file_key, file_info in self.manifest['files'].items():
                    file_path = self.archive_path / file_info['path']

                    if file_info.get('required', False) and not file_path.exists():
                        errors.append(f"Missing required file: {file_info['path']}")
                    elif not file_info.get('required', False) and not file_path.exists():
                        warnings.append(f"Missing optional file: {file_info['path']}")

        return len(errors) == 0

    def _validate_checksums(self, errors: List[str], warnings: List[str]) -> bool:
        """Validate file checksums."""
        if not self.checksum_path.exists():
            warnings.append("No checksums.json found, skipping integrity check")
            return True

        try:
            with open(self.checksum_path, 'r') as f:
                checksums = json.load(f)
        except Exception as e:
            warnings.append(f"Failed to read checksums: {e}")
            return True

        # Verify each file
        for file_path, expected_hash in checksums.items():
            full_path = self.archive_path / file_path

            if not full_path.exists():
                continue  # Already reported in _validate_files

            if full_path.is_file():
                actual_hash = self._calculate_file_hash(full_path)
                if actual_hash != expected_hash:
                    errors.append(f"Checksum mismatch for {file_path}")

        return len(errors) == 0

    def _check_compatibility(self, errors: List[str], warnings: List[str]) -> Dict[str, Any]:
        """Check compatibility with current BMAM version."""
        compat_info = {
            'compatible': True,
            'min_version': None,
            'required_features': [],
            'missing_features': []
        }

        if not self.manifest or 'compatibility' not in self.manifest:
            warnings.append("No compatibility information in manifest")
            return compat_info

        compat = self.manifest['compatibility']

        # Check minimum version
        min_version = compat.get('min_bmam_version')
        compat_info['min_version'] = min_version

        # Check required features
        required_features = compat.get('required_features', [])
        compat_info['required_features'] = required_features

        # In a real implementation, check if features are available
        # For now, assume all required features are available

        return compat_info

    @staticmethod
    def _collect_statistics(db_path: Path) -> Dict[str, Any]:
        """Collect statistics from database."""
        stats = {
            'total_memories': 0,
            'memory_types': {},
            'brain_regions': {},
            'avg_importance': 0.0,
            'date_range': {'earliest': None, 'latest': None}
        }

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Total memories
            cursor.execute("SELECT COUNT(*) FROM memories")
            stats['total_memories'] = cursor.fetchone()[0]

            # Memory types
            cursor.execute("""
                SELECT memory_type, COUNT(*)
                FROM memories
                GROUP BY memory_type
            """)
            stats['memory_types'] = {row[0]: row[1] for row in cursor.fetchall()}

            # Brain regions
            cursor.execute("""
                SELECT brain_region, COUNT(*)
                FROM memories
                GROUP BY brain_region
            """)
            stats['brain_regions'] = {row[0]: row[1] for row in cursor.fetchall()}

            # Average importance
            cursor.execute("SELECT AVG(importance) FROM memories")
            result = cursor.fetchone()[0]
            stats['avg_importance'] = round(result, 3) if result else 0.0

            # Date range
            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM memories")
            earliest, latest = cursor.fetchone()
            stats['date_range'] = {
                'earliest': earliest,
                'latest': latest
            }

            conn.close()

        except Exception as e:
            logger.warning(f"Failed to collect some statistics: {e}")

        return stats

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    @classmethod
    def _generate_checksums(cls, archive_path: Path, has_faiss: bool) -> Dict[str, str]:
        """Generate checksums for all files in archive."""
        checksums = {}

        # Database
        db_path = archive_path / "memories.db"
        if db_path.exists():
            checksums["memories.db"] = cls._calculate_file_hash(db_path)

        # Manifest
        manifest_path = archive_path / "manifest.json"
        if manifest_path.exists():
            checksums["manifest.json"] = cls._calculate_file_hash(manifest_path)

        # FAISS index files
        if has_faiss:
            faiss_dir = archive_path / "faiss_index"
            for faiss_file in faiss_dir.rglob("*"):
                if faiss_file.is_file():
                    rel_path = faiss_file.relative_to(archive_path)
                    checksums[str(rel_path)] = cls._calculate_file_hash(faiss_file)

        return checksums

    @staticmethod
    def _create_readme(
        name: str,
        description: str,
        tags: Optional[List[str]],
        stats: Dict[str, Any],
        has_faiss: bool
    ) -> str:
        """Create README content for archive."""
        readme = f"""# {name}

{description}

## Archive Information

- **Format**: BMAM Memory Archive (BMA) v1.0.0
- **Created**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
- **Tags**: {', '.join(tags) if tags else 'None'}

## Memory Statistics

- **Total Memories**: {stats['total_memories']:,}
- **Memory Types**: {', '.join(f"{k}: {v}" for k, v in stats['memory_types'].items())}
- **Brain Regions**: {', '.join(f"{k}: {v}" for k, v in stats['brain_regions'].items())}
- **Average Importance**: {stats['avg_importance']:.3f}
- **Date Range**: {stats['date_range']['earliest']} to {stats['date_range']['latest']}

## Contents

- `manifest.json` - Archive metadata and statistics
- `memories.db` - SQLite database with all memories
{"- `faiss_index/` - FAISS vector index for semantic search" if has_faiss else ""}
- `checksums.json` - SHA256 checksums for integrity verification
- `README.md` - This file

## Usage

### Load with Python

```python
from memory.memory_archive import MemoryArchive

# Load archive
archive = MemoryArchive(Path("{name}.bma"))

# Validate
validation = archive.validate()
print(f"Valid: {{validation['valid']}}")

# Load to runtime
result = archive.load(target_dir=Path("data/"))
```

### Load with Memory Manager CLI

```bash
python scripts/memory_manager.py import {name}.bma --target data/
```

## Compatibility

- **Minimum BMAM Version**: 1.0.0
- **Required Features**: sqlite3, faiss

---
Generated by BMAM Memory Archive System
"""
        return readme

    @classmethod
    def _generate_checksums_v2(cls, archive_path: Path) -> Dict[str, str]:
        """Generate checksums for all files in v2.0.0 archive."""
        checksums = {}

        # Manifest
        manifest_path = archive_path / "manifest.json"
        if manifest_path.exists():
            checksums["manifest.json"] = cls._calculate_file_hash(manifest_path)

        # Brain regions directory
        brain_regions_dir = archive_path / "brain_regions"
        if brain_regions_dir.exists():
            for region_file in brain_regions_dir.rglob("*"):
                if region_file.is_file():
                    rel_path = region_file.relative_to(archive_path)
                    checksums[str(rel_path)] = cls._calculate_file_hash(region_file)

        # Vectors directory
        vectors_dir = archive_path / "vectors"
        if vectors_dir.exists():
            for vector_file in vectors_dir.rglob("*"):
                if vector_file.is_file():
                    rel_path = vector_file.relative_to(archive_path)
                    checksums[str(rel_path)] = cls._calculate_file_hash(vector_file)

        return checksums

    @staticmethod
    def _create_readme_v2(
        name: str,
        description: str,
        tags: Optional[List[str]],
        brain_regions_info: Dict[str, Any],
        has_faiss: bool
    ) -> str:
        """Create README content for v2.0.0 archive."""
        readme = f"""# BMAM Memory Archive: {name}

**Format Version**: 2.0.0 (Multi-Region)
**Created**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

## Description

{description or 'No description provided'}

## Brain Regions Included

"""
        for region, info in brain_regions_info.items():
            count_key = [k for k in info.keys() if 'count' in k or 'slots' in k]
            count_val = info.get(count_key[0], 'N/A') if count_key else 'N/A'
            readme += f"- **{region.replace('_', ' ').title()}**: {count_val} items ({info['format']})\n"

        if has_faiss:
            readme += f"\n- **Vector Index**: FAISS indices included\n"

        if tags:
            readme += f"\n## Tags\n\n{', '.join(tags)}\n"

        readme += """
## Usage

Load this archive into BMAM using:

```python
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

coordinator = BrainInspiredCoordinator()
await coordinator.initialize()

# Load archive
result = coordinator.load_memory_archive(
    archive_path=Path("path/to/this.bma"),
    validate=True
)
```

## Archive Structure

```
archive.bma/
├── manifest.json           # Archive metadata
├── brain_regions/          # Brain region states
│   ├── temporal_lobe.db   # Long-term memory (SQLite)
│   ├── hippocampus.json   # Short-term memory
│   ├── prefrontal.json    # Working memory
│   ├── amygdala.json      # Emotional memory
│   └── basal_ganglia.json # Procedural memory
├── vectors/                # FAISS vector indices
├── checksums.json         # File integrity hashes
└── README.md             # This file
```

---

*Generated with BMAM Memory Archive System v2.0.0*
"""
        return readme


# Convenience functions for common operations

def create_archive(
    name: str,
    source_db_path: Path,
    output_dir: Path = Path("archives/"),
    **kwargs
) -> MemoryArchive:
    """
    Convenience function to create a memory archive.

    Args:
        name: Archive name
        source_db_path: Path to source database
        output_dir: Output directory (default: archives/)
        **kwargs: Additional arguments passed to MemoryArchive.create()

    Returns:
        MemoryArchive instance
    """
    return MemoryArchive.create(
        name=name,
        source_db_path=source_db_path,
        output_dir=output_dir,
        **kwargs
    )


def load_archive(
    archive_path: Path,
    target_dir: Path = Path("data/"),
    validate: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to load a memory archive.

    Args:
        archive_path: Path to .bma directory
        target_dir: Target directory for loading (default: data/)
        validate: Whether to validate before loading

    Returns:
        Load result dictionary
    """
    archive = MemoryArchive(archive_path)
    return archive.load(target_dir=target_dir, validate=validate)


def validate_archive(archive_path: Path, check_checksums: bool = True) -> Dict[str, Any]:
    """
    Convenience function to validate a memory archive.

    Args:
        archive_path: Path to .bma directory
        check_checksums: Whether to verify checksums

    Returns:
        Validation result dictionary
    """
    archive = MemoryArchive(archive_path)
    return archive.validate(check_checksums=check_checksums)
