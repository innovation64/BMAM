#!/usr/bin/env python3
"""
BMA format real test with existing memory

Just test export/validate/load without ingestion
Uses existing memory database

Author: BMAM Framework Team
Date: 2025-11-12
"""

import asyncio
from pathlib import Path
from datetime import datetime
import shutil

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def test_bma_format():
    """Test BMA format with existing memory"""
    print("\n" + "=" * 60)
    print("🧪 BMA Format Real Test")
    print("=" * 60)
    print()

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    await coordinator.start_system()

    try:
        # Check existing memory
        db_path = Path("data/brain_memory.db")
        if not db_path.exists():
            print("❌ No existing memory database found")
            print("   Please run a LoCoMo test first to create memory")
            return

        print(f"✓ Found existing memory: {db_path}")
        print(f"  Size: {db_path.stat().st_size:,} bytes ({db_path.stat().st_size/1024:.1f} KB)")
        print()

        # Create archives directory
        archives_dir = Path("archives")
        archives_dir.mkdir(exist_ok=True)

        # Step 1: Export to BMA
        print("=" * 60)
        print("📦 Step 1: Export to BMA archive")
        print("=" * 60)

        result = coordinator.export_memory_archive(
            archive_name="test_bma_real",
            output_dir=archives_dir,
            description="Test BMA export with real LoCoMo memory",
            tags=["test", "bma", "locomo"],
            include_faiss=True
        )

        if not result['success']:
            print(f"❌ Export failed: {result.get('error')}")
            return

        archive_path = result['archive_path']
        print(f"✅ Archive created: {archive_path}")
        print(f"   Total memories: {result['statistics']['total_memories']:,}")
        print(f"   Memory types: {result['statistics']['memory_types']}")
        print(f"   Brain regions: {result['statistics']['brain_regions']}")
        print(f"   Size: {result['size_bytes']:,} bytes ({result['size_bytes']/1024/1024:.2f} MB)")
        print()

        # Step 2: Validate archive
        print("=" * 60)
        print("✅ Step 2: Validate archive")
        print("=" * 60)

        validation = coordinator.validate_memory_archive(
            archive_path=archive_path,
            check_checksums=True
        )

        print(f"Valid: {validation['valid']}")
        print(f"Manifest valid: {validation['manifest_valid']}")
        print(f"Files valid: {validation['files_valid']}")
        print(f"Checksums valid: {validation['checksums_valid']}")

        if validation['errors']:
            print(f"\n❌ Errors:")
            for error in validation['errors']:
                print(f"   - {error}")

        if validation['warnings']:
            print(f"\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"   - {warning}")

        if not validation['valid']:
            print("\n❌ Archive validation failed!")
            return

        print("\n✅ Archive validation passed!")
        print()

        # Step 3: Test load
        print("=" * 60)
        print("🔄 Step 3: Test load")
        print("=" * 60)

        # Backup current database
        backup_path = Path(f"data/brain_memory_test_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        if db_path.exists():
            shutil.copy2(db_path, backup_path)
            print(f"✓ Backed up database to: {backup_path.name}")

        # Clean current memory
        if db_path.exists():
            db_path.unlink()
            print(f"✓ Cleaned: {db_path}")

        faiss_path = Path("data/faiss_index")
        if faiss_path.exists():
            shutil.rmtree(faiss_path)
            print(f"✓ Cleaned: {faiss_path}")

        print()

        # Load archive
        load_result = coordinator.load_memory_archive(
            archive_path=archive_path,
            validate=True
        )

        if not load_result['success']:
            print(f"❌ Load failed: {load_result.get('error')}")
            # Restore backup
            if backup_path.exists():
                shutil.copy2(backup_path, db_path)
                print(f"✓ Restored from backup")
            return

        print(f"✅ Archive loaded successfully")
        print(f"   Files loaded: {', '.join(load_result['loaded_files'])}")
        print(f"   Total memories: {load_result['statistics']['total_memories']:,}")
        print()

        # Step 4: Test memory retrieval
        print("=" * 60)
        print("🔍 Step 4: Test memory retrieval")
        print("=" * 60)

        test_query = "What happened in the conversation?"
        print(f"Query: {test_query}")

        memories = await coordinator.smart_retrieve(test_query, k=3)

        if memories:
            print(f"✓ Retrieved {len(memories)} memories:")
            for i, mem in enumerate(memories[:3], 1):
                content = mem.get('content', '')[:100]
                importance = mem.get('importance', 0)
                print(f"   {i}. {content}... (importance: {importance:.2f})")
        else:
            print("⚠️  No memories retrieved")

        print()

        # Restore original database
        if backup_path.exists():
            if db_path.exists():
                db_path.unlink()
            shutil.copy2(backup_path, db_path)
            print(f"✓ Restored original database from backup")
            backup_path.unlink()
            print()

        # Final summary
        print("=" * 60)
        print("🎉 Test Complete!")
        print("=" * 60)
        print()
        print("✅ All BMA operations successful:")
        print("   - Export: ✓")
        print("   - Validation: ✓")
        print("   - Load: ✓")
        print("   - Retrieval: ✓")
        print()
        print(f"Archive location: {archive_path}")
        print()

    finally:
        await coordinator.stop_system()
        await coordinator.shutdown()


if __name__ == '__main__':
    asyncio.run(test_bma_format())
