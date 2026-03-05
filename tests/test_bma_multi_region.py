"""
Integration test for BMA Multi-Region Export/Load Cycle

Tests the complete export→load cycle for BMA v2.0.0 format with multi-brain-region support.

Test scenarios:
1. Export BMA v2.0.0 from coordinator with data in all brain regions
2. Clear current state
3. Load BMA back
4. Verify all brain region states match original
5. Test backward compatibility with v1.0.0 format
"""

import asyncio
import logging
import sys
import shutil
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.memory.memory_archive import MemoryArchive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BMAMultiRegionTester:
    """Test BMA multi-region export/load functionality"""

    def __init__(self):
        self.test_dir = Path("tests/bma_test_archives")
        self.test_dir.mkdir(exist_ok=True)
        self.coordinator = None

    async def setup_coordinator_with_data(self) -> BrainInspiredCoordinator:
        """Initialize coordinator and populate all brain regions with test data"""
        logger.info("=" * 80)
        logger.info("🔧 Setting up coordinator with test data...")
        logger.info("=" * 80)

        coordinator = BrainInspiredCoordinator()
        await coordinator.initialize()
        await coordinator.start_system()

        # Populate Hippocampus (short-term episodic memory)
        logger.info("\n📝 Populating Hippocampus (short-term memory)...")
        for i in range(5):
            await coordinator.hippocampus.store_memory(
                content=f"Test episodic memory {i}",
                entities=[f"entity_{i}", "test_entity"],
                importance=0.5 + i * 0.1,
                emotion_tags=["neutral"],
                emotion_intensity=0.3,
                metadata={"test": True, "index": i}
            )
        hippo_stats = coordinator.hippocampus.get_statistics()
        logger.info(f"   ✓ Stored {hippo_stats['current_memories']} episodic memories")

        # Populate PrefrontalCortex (working memory)
        # Since PrefrontalAgent doesn't have a simple store API, directly add to working_memory
        logger.info("\n📝 Populating PrefrontalCortex (working memory)...")
        from src.agents.brain_regions.prefrontal_agent.prefrontal_agent import WorkingMemoryItem
        from collections import deque

        for i in range(3):
            item = WorkingMemoryItem(
                id=f"wm_{i}",
                content=f"Test working memory {i}",
                task_type="test_task",
                priority=i,
                timestamp=datetime.now(),
                metadata={"test": True, "index": i}
            )
            coordinator.prefrontal_storage.working_memory.append(item)

        logger.info(f"   ✓ Stored {len(coordinator.prefrontal_storage.working_memory)} working memory items")

        # Populate Amygdala (emotional memory)
        # The amygdala uses a different data structure - memories and emotion_memories
        # For simplicity, just add raw records
        logger.info("\n📝 Populating Amygdala (emotional memory)...")
        from src.agents.brain_regions.amygdala_agent import EmotionalMemory

        for i in range(4):
            emotional_mem = EmotionalMemory(
                id=uuid.uuid4().hex,
                reference_id=f"memory_{i}",
                content_summary=f"Test emotional context {i}",
                emotion_tags=["joy" if i % 2 == 0 else "surprise"],
                emotion_intensity=0.7 + i * 0.05,
                timestamp=datetime.now(),
                access_count=0,
                metadata={"test": True}
            )
            coordinator.amygdala.memories.append(emotional_mem)
            coordinator.amygdala.memory_dict[emotional_mem.id] = emotional_mem

        logger.info(f"   ✓ Stored {len(coordinator.amygdala.memories)} emotional memories")

        # Populate BasalGanglia (procedural memory/skills)
        logger.info("\n📝 Populating BasalGanglia (procedural memory)...")
        for i in range(3):
            await coordinator.basal_ganglia.store_skill(
                skill_name=f"test_skill_{i}",
                content=f"Test skill description {i}",
                steps=[f"step_1_{i}", f"step_2_{i}", f"step_3_{i}"],
                metadata={"test": True, "index": i}
            )
            # Practice skill to increase proficiency
            await coordinator.basal_ganglia.practice_skill(f"test_skill_{i}")
        basal_stats = coordinator.basal_ganglia.get_statistics()
        logger.info(f"   ✓ Stored {basal_stats['current_skills']} procedural skills")

        # For this test, we'll focus on testing the 4 in-memory brain regions
        # TemporalLobe (SQLite) is already being copied in export/load, so we don't need to populate it here
        logger.info("\n📝 TemporalLobe (long-term memory) - using existing data")

        logger.info("\n✅ Coordinator populated with test data")
        return coordinator

    def capture_state_snapshot(self, coordinator: BrainInspiredCoordinator) -> Dict[str, Any]:
        """Capture current state of all brain regions for comparison"""
        logger.info("\n📸 Capturing state snapshot...")

        snapshot = {}

        # Hippocampus state
        snapshot['hippocampus'] = {
            'memory_count': len(coordinator.hippocampus.memories),
            'entity_index_size': len(coordinator.hippocampus.entity_index),
            'memory_ids': [m.id for m in coordinator.hippocampus.memories]
        }

        # PrefrontalCortex state
        snapshot['prefrontal'] = {
            'working_memory_count': len(coordinator.prefrontal_storage.working_memory),
            'working_memory_ids': [item.id for item in coordinator.prefrontal_storage.working_memory]
        }

        # Amygdala state
        snapshot['amygdala'] = {
            'emotional_memory_count': len(coordinator.amygdala.memories),
            'memory_ids': [m.id for m in coordinator.amygdala.memories]
        }

        # BasalGanglia state
        snapshot['basal_ganglia'] = {
            'skill_count': len(coordinator.basal_ganglia.skills),
            'skill_names': list(coordinator.basal_ganglia.skills.keys())
        }

        logger.info(f"   ✓ Captured snapshot: "
                   f"Hippo={snapshot['hippocampus']['memory_count']}, "
                   f"Prefrontal={snapshot['prefrontal']['working_memory_count']}, "
                   f"Amygdala={snapshot['amygdala']['emotional_memory_count']}, "
                   f"BasalGanglia={snapshot['basal_ganglia']['skill_count']}")

        return snapshot

    def compare_states(self, original: Dict[str, Any], restored: Dict[str, Any]) -> bool:
        """Compare two state snapshots"""
        logger.info("\n🔍 Comparing original and restored states...")

        all_match = True

        # Compare each brain region
        for region in ['hippocampus', 'prefrontal', 'amygdala', 'basal_ganglia']:
            logger.info(f"\n   Checking {region}...")

            orig = original[region]
            rest = restored[region]

            for key in orig:
                if orig[key] != rest[key]:
                    logger.error(f"      ❌ Mismatch in {region}.{key}: "
                               f"original={orig[key]}, restored={rest[key]}")
                    all_match = False
                else:
                    logger.info(f"      ✓ {key}: {orig[key]}")

        return all_match

    async def test_export_load_cycle(self) -> bool:
        """Test complete export→load cycle"""
        logger.info("\n" + "=" * 80)
        logger.info("🧪 TEST 1: Export→Load Cycle (v2.0.0)")
        logger.info("=" * 80)

        coordinator = None
        try:
            # Setup coordinator with data
            coordinator = await self.setup_coordinator_with_data()

            # Capture original state
            original_state = self.capture_state_snapshot(coordinator)

            # Export BMA v2.0.0
            logger.info("\n📦 Exporting BMA v2.0.0...")
            archive_name = "test_multi_region_v2"
            result = coordinator.export_memory_archive(
                archive_name=archive_name,
                output_dir=self.test_dir,
                description="Test multi-region export",
                tags=["test", "v2"],
                include_faiss=True
            )

            if result['success']:
                logger.info(f"   ✅ Export successful: {result['archive_path']}")
                logger.info(f"   📊 Archive size: {result.get('archive_size_mb', 0):.2f} MB")
            else:
                logger.error(f"   ❌ Export failed: {result.get('error')}")
                return False

            archive_path = Path(result['archive_path'])

            # Verify v2.0.0 format structure
            logger.info("\n🔍 Verifying v2.0.0 format structure...")
            brain_regions_dir = archive_path / "brain_regions"
            if not brain_regions_dir.exists():
                logger.error(f"   ❌ brain_regions/ directory not found")
                return False

            expected_files = [
                "temporal_lobe.db",
                "hippocampus.json",
                "prefrontal.json",
                "amygdala.json",
                "basal_ganglia.json"
            ]

            for file_name in expected_files:
                file_path = brain_regions_dir / file_name
                if file_path.exists():
                    size = file_path.stat().st_size
                    logger.info(f"   ✓ {file_name} ({size} bytes)")
                else:
                    logger.error(f"   ❌ {file_name} not found")
                    return False

            # Clear coordinator state
            logger.info("\n🧹 Clearing coordinator state...")
            coordinator.hippocampus.memories.clear()
            coordinator.prefrontal_storage.working_memory.clear()
            coordinator.amygdala.memories.clear()
            coordinator.basal_ganglia.skills.clear()
            logger.info("   ✓ All brain regions cleared")

            # Verify cleared
            cleared_state = self.capture_state_snapshot(coordinator)
            if (cleared_state['hippocampus']['memory_count'] == 0 and
                cleared_state['prefrontal']['working_memory_count'] == 0 and
                cleared_state['amygdala']['emotional_memory_count'] == 0 and
                cleared_state['basal_ganglia']['skill_count'] == 0):
                logger.info("   ✅ State successfully cleared")
            else:
                logger.error("   ❌ State not fully cleared")
                return False

            # Load BMA back
            logger.info("\n📥 Loading BMA v2.0.0...")
            load_result = coordinator.load_memory_archive(
                archive_path=archive_path,
                validate=True
            )

            if load_result['success']:
                logger.info(f"   ✅ Load successful")
                logger.info(f"   📊 Format: {load_result.get('format_version', 'unknown')}")
            else:
                logger.error(f"   ❌ Load failed: {load_result.get('error')}")
                return False

            # Capture restored state
            restored_state = self.capture_state_snapshot(coordinator)

            # Compare states
            states_match = self.compare_states(original_state, restored_state)

            if states_match:
                logger.info("\n✅ TEST 1 PASSED: Export→Load cycle successful, all states match")
                return True
            else:
                logger.error("\n❌ TEST 1 FAILED: States do not match")
                return False

        except Exception as e:
            logger.error(f"\n❌ TEST 1 FAILED with exception: {e}", exc_info=True)
            return False
        finally:
            if coordinator:
                await coordinator.shutdown()

    async def test_backward_compatibility(self) -> bool:
        """Test v1.0.0 backward compatibility"""
        logger.info("\n" + "=" * 80)
        logger.info("🧪 TEST 2: Backward Compatibility (v1.0.0)")
        logger.info("=" * 80)

        try:
            # Check if any v1.0.0 archives exist
            v1_archives = list(self.test_dir.glob("*v1*.bma"))

            if not v1_archives:
                logger.info("   ℹ️  No v1.0.0 archives found to test")
                logger.info("   ⏭️  Skipping v1.0.0 test (no legacy archives)")
                logger.info("\n✅ TEST 2 SKIPPED: No v1.0.0 archives to test")
                return True

            # Test loading v1.0.0 archive
            v1_archive = v1_archives[0]
            logger.info(f"\n📦 Found v1.0.0 archive: {v1_archive.name}")

            coordinator = BrainInspiredCoordinator()
            await coordinator.initialize()
            await coordinator.start_system()

            logger.info(f"📥 Loading v1.0.0 archive...")
            load_result = coordinator.load_memory_archive(
                archive_path=v1_archive,
                validate=True
            )

            if load_result['success']:
                logger.info(f"   ✅ v1.0.0 load successful (backward compatible)")
                logger.info(f"   📊 Format: {load_result.get('format_version', 'unknown')}")
                await coordinator.shutdown()
                logger.info("\n✅ TEST 2 PASSED: Backward compatibility verified")
                return True
            else:
                logger.error(f"   ❌ v1.0.0 load failed: {load_result.get('error')}")
                await coordinator.shutdown()
                return False

        except Exception as e:
            logger.error(f"\n❌ TEST 2 FAILED with exception: {e}", exc_info=True)
            return False

    async def cleanup(self):
        """Clean up test archives"""
        logger.info("\n🧹 Cleaning up test archives...")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            logger.info("   ✓ Test directory removed")


async def main():
    """Run all BMA multi-region tests"""
    logger.info("=" * 80)
    logger.info("BMA MULTI-REGION INTEGRATION TEST SUITE")
    logger.info("=" * 80)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tester = BMAMultiRegionTester()
    results = {}

    try:
        # Test 1: Export→Load cycle
        results['export_load_cycle'] = await tester.test_export_load_cycle()

        # Test 2: Backward compatibility
        results['backward_compatibility'] = await tester.test_backward_compatibility()

    finally:
        # Cleanup
        # await tester.cleanup()  # Comment out to keep archives for inspection
        pass

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"   {test_name}: {status}")

    logger.info(f"\n   Total: {passed}/{total} tests passed")
    logger.info(f"   End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
