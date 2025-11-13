#!/usr/bin/env python3
"""
Migrate old memory snapshots to unified BMA format

This script converts legacy snapshot formats to the new standardized
BMA (BMAM Memory Archive) format.

Old format (memory_manager.py snapshots):
    data/snapshots/{snapshot_id}_{name}/
    ├── brain_memory.db
    ├── faiss_index/
    └── metadata.json

New format (BMA):
    archives/{name}.bma/
    ├── manifest.json      # Standardized metadata
    ├── memories.db        # Standard database name
    ├── faiss_index/       # Vector index
    ├── checksums.json     # Integrity verification
    └── README.md          # Human-readable info

Usage:
    # Migrate single snapshot
    python scripts/migrate_snapshots_to_bma.py --snapshot data/snapshots/abc123_baseline

    # Migrate all snapshots
    python scripts/migrate_snapshots_to_bma.py --all

    # Dry run (no changes)
    python scripts/migrate_snapshots_to_bma.py --all --dry-run

    # Specify output directory
    python scripts/migrate_snapshots_to_bma.py --all --output archives/migrated

Author: BMAM Framework Team
Created: 2025-11-12
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.memory_archive import MemoryArchive


class SnapshotMigrator:
    """Migrates old snapshot format to BMA format"""

    def __init__(self, output_dir: Path = Path("archives/"), dry_run: bool = False):
        """
        Initialize migrator

        Args:
            output_dir: Directory for BMA archives
            dry_run: If True, only simulate migration without creating files
        """
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

    def detect_snapshot_format(self, snapshot_path: Path) -> Optional[str]:
        """
        Detect snapshot format

        Returns:
            'legacy' for old memory_manager.py format
            'bma' for new BMA format
            None if unrecognized
        """
        snapshot_path = Path(snapshot_path)

        if not snapshot_path.exists():
            return None

        # Check for BMA format (manifest.json)
        if (snapshot_path / "manifest.json").exists():
            return 'bma'

        # Check for legacy format (metadata.json + brain_memory.db or memories.db)
        has_metadata = (snapshot_path / "metadata.json").exists()
        has_db = (snapshot_path / "brain_memory.db").exists() or (snapshot_path / "memories.db").exists()

        if has_metadata and has_db:
            return 'legacy'

        # Check for simple format (just database without metadata)
        if has_db:
            return 'simple'

        return None

    def parse_legacy_metadata(self, metadata_path: Path) -> Dict[str, Any]:
        """
        Parse legacy metadata.json

        Returns:
            Dict with parsed metadata
        """
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            return metadata
        except Exception as e:
            print(f"⚠️  Failed to parse metadata: {e}")
            return {}

    def extract_snapshot_name(self, snapshot_path: Path, metadata: Dict[str, Any]) -> str:
        """
        Extract snapshot name from directory or metadata

        Legacy format: {snapshot_id}_{name}
        Extract the name part
        """
        # Try to get name from metadata
        if 'name' in metadata:
            return metadata['name']

        # Extract from directory name
        dir_name = snapshot_path.name

        # Remove .bma extension if present
        if dir_name.endswith('.bma'):
            dir_name = dir_name[:-4]

        # Try to split on underscore (legacy format: id_name)
        parts = dir_name.split('_', 1)
        if len(parts) > 1:
            # Remove ID prefix, keep name
            return parts[1]

        return dir_name

    def migrate_snapshot(self, snapshot_path: Path) -> Dict[str, Any]:
        """
        Migrate a single snapshot to BMA format

        Args:
            snapshot_path: Path to legacy snapshot directory

        Returns:
            Dict with migration results
        """
        snapshot_path = Path(snapshot_path)
        self.stats['total'] += 1

        print(f"\n📦 Processing: {snapshot_path}")

        # Detect format
        format_type = self.detect_snapshot_format(snapshot_path)

        if format_type is None:
            print(f"   ⚠️  Unrecognized format, skipping")
            self.stats['skipped'] += 1
            return {'success': False, 'reason': 'unrecognized_format'}

        if format_type == 'bma':
            print(f"   ✓ Already in BMA format, skipping")
            self.stats['skipped'] += 1
            return {'success': False, 'reason': 'already_bma'}

        # Parse metadata
        metadata_path = snapshot_path / "metadata.json"
        metadata = {}
        if metadata_path.exists():
            metadata = self.parse_legacy_metadata(metadata_path)

        # Find database file
        db_path = snapshot_path / "brain_memory.db"
        if not db_path.exists():
            db_path = snapshot_path / "memories.db"

        if not db_path.exists():
            print(f"   ❌ No database found")
            self.stats['failed'] += 1
            return {'success': False, 'reason': 'no_database'}

        # Extract snapshot name
        snapshot_name = self.extract_snapshot_name(snapshot_path, metadata)

        # Check for FAISS index
        faiss_path = snapshot_path / "faiss_index"
        has_faiss = faiss_path.exists() and faiss_path.is_dir()

        # Extract metadata fields
        description = metadata.get('description', f'Migrated from {snapshot_path.name}')
        tags = metadata.get('tags', ['migrated'])
        created_at = metadata.get('timestamp', metadata.get('created_at'))

        # Add migration tag
        if 'migrated' not in tags:
            tags.append('migrated')

        print(f"   Name: {snapshot_name}")
        print(f"   Description: {description}")
        print(f"   Tags: {', '.join(tags)}")
        print(f"   Database: {db_path.name}")
        print(f"   FAISS: {'Yes' if has_faiss else 'No'}")

        if self.dry_run:
            print(f"   [DRY RUN] Would create: {self.output_dir / f'{snapshot_name}.bma'}")
            self.stats['success'] += 1
            return {'success': True, 'dry_run': True}

        # Create BMA archive
        try:
            archive = MemoryArchive.create(
                name=snapshot_name,
                source_db_path=db_path,
                output_dir=self.output_dir,
                description=description,
                tags=tags,
                source_faiss_path=faiss_path if has_faiss else None,
                metadata={
                    'migrated_from': str(snapshot_path),
                    'migration_date': datetime.utcnow().isoformat() + 'Z',
                    'original_created_at': created_at,
                    'original_metadata': metadata
                }
            )

            print(f"   ✅ Migrated to: {archive.archive_path}")
            self.stats['success'] += 1

            return {
                'success': True,
                'archive_path': archive.archive_path,
                'snapshot_name': snapshot_name
            }

        except Exception as e:
            print(f"   ❌ Migration failed: {e}")
            self.stats['failed'] += 1
            return {'success': False, 'error': str(e)}

    def migrate_all(self, snapshots_dir: Path = Path("data/snapshots")) -> List[Dict[str, Any]]:
        """
        Migrate all snapshots in directory

        Args:
            snapshots_dir: Directory containing snapshots

        Returns:
            List of migration results
        """
        snapshots_dir = Path(snapshots_dir)

        if not snapshots_dir.exists():
            print(f"❌ Snapshots directory not found: {snapshots_dir}")
            return []

        # Find all snapshot directories
        snapshot_dirs = [d for d in snapshots_dir.iterdir() if d.is_dir()]

        if not snapshot_dirs:
            print(f"⚠️  No snapshots found in {snapshots_dir}")
            return []

        print(f"🔍 Found {len(snapshot_dirs)} snapshots")

        results = []
        for snapshot_dir in sorted(snapshot_dirs):
            result = self.migrate_snapshot(snapshot_dir)
            results.append({
                'snapshot_path': snapshot_dir,
                **result
            })

        return results

    def print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 60)
        print("📊 Migration Summary")
        print("=" * 60)
        print(f"Total snapshots:     {self.stats['total']}")
        print(f"✅ Successfully migrated: {self.stats['success']}")
        print(f"⏭️  Skipped:              {self.stats['skipped']}")
        print(f"❌ Failed:               {self.stats['failed']}")
        print("=" * 60)

        if self.dry_run:
            print("\n💡 This was a dry run. Use --no-dry-run to perform actual migration.")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate legacy memory snapshots to BMA format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate single snapshot
  python scripts/migrate_snapshots_to_bma.py --snapshot data/snapshots/abc123_baseline

  # Migrate all snapshots
  python scripts/migrate_snapshots_to_bma.py --all

  # Dry run (preview without changes)
  python scripts/migrate_snapshots_to_bma.py --all --dry-run

  # Specify output directory
  python scripts/migrate_snapshots_to_bma.py --all --output archives/migrated
        """
    )

    parser.add_argument(
        '--snapshot',
        type=str,
        help='Path to single snapshot to migrate'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Migrate all snapshots in data/snapshots directory'
    )

    parser.add_argument(
        '--snapshots-dir',
        type=str,
        default='data/snapshots',
        help='Directory containing snapshots (default: data/snapshots)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='archives',
        help='Output directory for BMA archives (default: archives)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate migration without creating files'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.snapshot and not args.all:
        parser.error('Must specify either --snapshot or --all')

    # Create migrator
    migrator = SnapshotMigrator(
        output_dir=Path(args.output),
        dry_run=args.dry_run
    )

    # Ensure output directory exists
    if not args.dry_run:
        Path(args.output).mkdir(parents=True, exist_ok=True)

    print("🚀 BMAM Snapshot Migration Tool")
    print(f"   Output directory: {args.output}")
    print(f"   Dry run: {args.dry_run}")
    print()

    # Migrate
    if args.snapshot:
        # Migrate single snapshot
        result = migrator.migrate_snapshot(Path(args.snapshot))
        migrator.print_summary()

        if result['success']:
            sys.exit(0)
        else:
            sys.exit(1)

    elif args.all:
        # Migrate all snapshots
        results = migrator.migrate_all(Path(args.snapshots_dir))
        migrator.print_summary()

        if migrator.stats['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == '__main__':
    main()
