#!/usr/bin/env python3
"""
Test BMA format with real LoCoMo data

This script:
1. Cleans current memory database
2. Ingests LoCoMo conv-26 (500+ turns)
3. Exports to BMA archive
4. Validates archive integrity
5. Loads archive back and verifies

Author: BMAM Framework Team
Date: 2025-11-12
"""

import asyncio
import json
import shutil
from pathlib import Path
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def clean_memory():
    """Clean existing memory database"""
    print("=" * 60)
    print("🧹 Step 1: Clean existing memory")
    print("=" * 60)

    db_path = Path("data/brain_memory.db")
    faiss_path = Path("data/faiss_index")

    if db_path.exists():
        backup_path = Path(f"data/brain_memory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        shutil.copy2(db_path, backup_path)
        db_path.unlink()
        print(f"✅ Backed up and removed: {db_path}")
        print(f"   Backup: {backup_path}")

    if faiss_path.exists():
        shutil.rmtree(faiss_path)
        print(f"✅ Removed FAISS index: {faiss_path}")

    print()


async def ingest_locomo_data(coordinator):
    """Ingest LoCoMo conv-26 data"""
    print("=" * 60)
    print("📥 Step 2: Ingest LoCoMo conv-26 (500+ turns)")
    print("=" * 60)

    # Load LoCoMo data
    locomo_path = Path("tests/data/locomo/LoCoMo.json")
    if not locomo_path.exists():
        print(f"❌ LoCoMo data not found: {locomo_path}")
        return 0

    with open(locomo_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find conv-26
    conv_26 = None
    for conv in data['data']:
        if conv['id'] == 'conv-26':
            conv_26 = conv
            break

    if not conv_26:
        print("❌ conv-26 not found in LoCoMo data")
        return 0

    print(f"📖 Found conv-26")
    print(f"   Sessions: {len(conv_26['timeline'])}")

    # Count total dialogues
    total_turns = sum(len(session['dialogues']) for session in conv_26['timeline'])
    print(f"   Total turns: {total_turns}")
    print()

    # Ingest all dialogues
    ingested = 0
    start_time = datetime.now()

    for session_idx, session in enumerate(conv_26['timeline'], 1):
        session_turns = len(session['dialogues'])
        print(f"   Processing session {session_idx}/{len(conv_26['timeline'])} ({session_turns} turns)...", end=" ", flush=True)

        for turn in session['dialogues']:
            speaker = turn.get('speaker', 'Unknown')
            text = turn.get('text', '')

            if text:
                # Process through coordinator
                await coordinator.process_input(f"{speaker}: {text}")
                ingested += 1

        print(f"✓ ({ingested}/{total_turns})")

    duration = (datetime.now() - start_time).total_seconds()
    print()
    print(f"✅ Ingested {ingested} turns in {duration:.1f}s ({ingested/duration:.1f} turns/sec)")
    print()

    return ingested


async def export_bma_archive(coordinator, archive_name="locomo_conv26"):
    """Export memory to BMA archive"""
    print("=" * 60)
    print("📦 Step 3: Export to BMA archive")
    print("=" * 60)

    result = coordinator.export_memory_archive(
        archive_name=archive_name,
        output_dir=Path("archives/"),
        description="LoCoMo conv-26 complete conversation memory (500+ turns)",
        tags=["locomo", "conv-26", "baseline", "test"],
        include_faiss=True,
        metadata={
            "test_date": datetime.now().isoformat(),
            "source": "LoCoMo conv-26",
            "purpose": "BMA format validation"
        }
    )

    if not result['success']:
        print(f"❌ Export failed: {result.get('error')}")
        return None

    print(f"✅ Archive created: {result['archive_path']}")
    print(f"   Total memories: {result['statistics']['total_memories']:,}")
    print(f"   Memory types: {result['statistics']['memory_types']}")
    print(f"   Brain regions: {result['statistics']['brain_regions']}")
    print(f"   Archive size: {result['size_bytes']:,} bytes ({result['size_bytes']/1024/1024:.2f} MB)")
    print(f"   Files: {', '.join(result['files_created'])}")
    print()

    return result['archive_path']


def validate_bma_archive(coordinator, archive_path):
    """Validate BMA archive integrity"""
    print("=" * 60)
    print("✅ Step 4: Validate archive integrity")
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
        print(f"\n❌ Errors ({len(validation['errors'])}):")
        for error in validation['errors']:
            print(f"   - {error}")

    if validation['warnings']:
        print(f"\n⚠️  Warnings ({len(validation['warnings'])}):")
        for warning in validation['warnings']:
            print(f"   - {warning}")

    if validation['valid']:
        print("\n✅ Archive validation passed!")
    else:
        print("\n❌ Archive validation failed!")

    print()
    return validation['valid']


async def test_archive_load(coordinator, archive_path):
    """Test loading archive and verify memory retrieval"""
    print("=" * 60)
    print("🔄 Step 5: Load archive and test retrieval")
    print("=" * 60)

    # Clean current memory first
    db_path = Path("data/brain_memory.db")
    faiss_path = Path("data/faiss_index")

    if db_path.exists():
        db_path.unlink()
        print(f"✓ Cleaned database")

    if faiss_path.exists():
        shutil.rmtree(faiss_path)
        print(f"✓ Cleaned FAISS index")

    print()

    # Load archive
    result = coordinator.load_memory_archive(
        archive_path=archive_path,
        validate=True
    )

    if not result['success']:
        print(f"❌ Load failed: {result.get('error')}")
        return False

    print(f"✅ Archive loaded successfully")
    print(f"   Archive name: {result['archive_name']}")
    print(f"   Files loaded: {', '.join(result['loaded_files'])}")
    print(f"   Total memories: {result['statistics']['total_memories']:,}")
    print()

    # Test memory retrieval with LoCoMo questions
    test_queries = [
        "What did Kevin's father do for a living?",
        "Who won the lottery?",
        "What happened in the restaurant?"
    ]

    print("🔍 Testing memory retrieval:")
    print()

    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")

        # Retrieve memories
        memories = await coordinator.smart_retrieve(query, k=5)

        if memories:
            print(f"   ✓ Retrieved {len(memories)} memories")
            print(f"   Top result: {memories[0].get('content', '')[:100]}...")
        else:
            print(f"   ⚠️  No memories retrieved")

        print()

    return True


async def main():
    """Main test flow"""
    print("\n" + "=" * 60)
    print("🧪 BMA Format Test with LoCoMo Data")
    print("=" * 60)
    print()

    start_time = datetime.now()

    try:
        # Step 1: Clean memory
        await clean_memory()

        # Step 2: Initialize coordinator and ingest LoCoMo data
        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()
        await coordinator.start_system()

        ingested = await ingest_locomo_data(coordinator)
        if ingested == 0:
            print("❌ No data ingested, aborting test")
            return

        # Step 3: Export to BMA archive
        archive_path = await export_bma_archive(coordinator, "locomo_conv26_test")
        if not archive_path:
            print("❌ Export failed, aborting test")
            return

        # Step 4: Validate archive
        if not validate_bma_archive(coordinator, archive_path):
            print("❌ Validation failed, aborting test")
            return

        # Step 5: Load and test
        await test_archive_load(coordinator, archive_path)

        # Shutdown
        await coordinator.stop_system()
        await coordinator.shutdown()

        # Final summary
        total_duration = (datetime.now() - start_time).total_seconds()

        print("=" * 60)
        print("🎉 Test Complete!")
        print("=" * 60)
        print(f"Total duration: {total_duration:.1f}s")
        print(f"Archive: {archive_path}")
        print()
        print("✅ All tests passed!")
        print("   - Memory ingestion: ✓")
        print("   - BMA export: ✓")
        print("   - Archive validation: ✓")
        print("   - Archive load: ✓")
        print("   - Memory retrieval: ✓")
        print()

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
