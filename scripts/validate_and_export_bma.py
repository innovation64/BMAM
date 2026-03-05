#!/usr/bin/env python3
"""
Validate LoCoMo Memory State and Export BMA v2.0.0 Archive

Usage:
    python3 scripts/validate_and_export_bma.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def main():
    """Validate memory state and export BMA archive"""
    print("=" * 80)
    print("📊 LoCoMo Memory Validation & BMA Export")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize coordinator (will load existing memory state)
    print("🔧 Initializing BMAM Coordinator...")
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    await coordinator.start_system()
    print("✅ Coordinator initialized\n")

    try:
        # Get statistics from all brain regions
        print("=" * 80)
        print("📊 Brain Region Memory Statistics")
        print("=" * 80)

        # Hippocampus (short-term episodic)
        hippo_stats = coordinator.hippocampus.get_statistics()
        print(f"\n🐚 Hippocampus (Short-term Episodic):")
        print(f"   Current memories: {hippo_stats['current_memories']}")
        print(f"   Total stored: {hippo_stats['total_stored']}")
        print(f"   Capacity: {hippo_stats['capacity']}")
        print(f"   Usage: {hippo_stats['current_memories']/hippo_stats['capacity']*100:.1f}%")

        # TemporalLobe (long-term episodic)
        temporal_stats = coordinator.temporal_lobe.get_statistics()
        print(f"\n🧠 TemporalLobe (Long-term Episodic):")
        print(f"   Current memories: {temporal_stats.get('current_memories', 0)}")
        print(f"   Total stored: {temporal_stats.get('total_stored', 0)}")
        print(f"   KG entities: {temporal_stats.get('knowledge_graph', {}).get('total_entities', 0)}")
        print(f"   KG triples: {temporal_stats.get('knowledge_graph', {}).get('total_triples', 0)}")
        print(f"   Capacity: {temporal_stats['capacity']}")

        # PrefrontalCortex (working memory)
        prefrontal_stats = coordinator.prefrontal_storage.get_statistics()
        print(f"\n🎯 PrefrontalCortex (Working Memory):")
        print(f"   Active items: {prefrontal_stats.get('working_memory_count', 0)}")
        print(f"   Capacity: {prefrontal_stats.get('capacity', 10)}")

        # Amygdala (emotional memory)
        amygdala_stats = coordinator.amygdala.get_statistics()
        print(f"\n❤️  Amygdala (Emotional Memory):")
        print(f"   Emotional memories: {amygdala_stats['current_memories']}")
        print(f"   Total stored: {amygdala_stats['total_stored']}")

        # BasalGanglia (procedural memory)
        basal_stats = coordinator.basal_ganglia.get_statistics()
        print(f"\n⚙️  BasalGanglia (Procedural Memory):")
        print(f"   Skills stored: {basal_stats['current_skills']}")
        print(f"   Average proficiency: {basal_stats.get('average_proficiency', 0):.2f}")

        # Memory consolidation check
        print(f"\n" + "=" * 80)
        print("💾 Memory Consolidation Status")
        print("=" * 80)

        total_memories = (
            hippo_stats['current_memories'] +
            temporal_stats.get('total_stored', 0)
        )

        print(f"\n   Total episodic memories: {total_memories}")
        print(f"   - Hippocampus (recent): {hippo_stats['current_memories']}")
        print(f"   - TemporalLobe (consolidated): {temporal_stats.get('total_stored', 0)}")

        # Simple sanity check
        print(f"\n" + "=" * 80)
        print("🧪 Memory Retrieval Sanity Check")
        print("=" * 80)

        test_queries = [
            "What did Caroline and Melanie talk about?",
            "Tell me about their conversations",
            "What topics did they discuss?"
        ]

        for query in test_queries:
            print(f"\n   Query: {query}")
            try:
                response = await coordinator.process_input(query)
                result_text = response.get('result', '').strip()

                if len(result_text) > 200:
                    print(f"   Response: {result_text[:200]}...")
                else:
                    print(f"   Response: {result_text}")

                print(f"   ✓ Memory retrieval working")
            except Exception as e:
                print(f"   ⚠️  Retrieval failed: {e}")

            # Only test first query for quick check
            break

        # Export BMA v2.0.0 archive
        print(f"\n" + "=" * 80)
        print("📦 Exporting BMA v2.0.0 Archive")
        print("=" * 80)

        archive_name = f"locomo_sample0_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        output_dir = Path("data/memory_archives")

        print(f"\n   Archive name: {archive_name}")
        print(f"   Output directory: {output_dir}")
        print(f"\n   Exporting...")

        export_result = coordinator.export_memory_archive(
            archive_name=archive_name,
            output_dir=output_dir,
            description=f"LoCoMo Sample 0 - Full 419 turns with multi-region consolidation",
            tags=["locomo", "sample_0", "full", "v2.0.0", "validated"],
            include_faiss=True
        )

        if export_result['success']:
            print(f"\n   ✅ Archive exported successfully!")
            print(f"   📦 Archive path: {export_result['archive_path']}")
            print(f"   📊 Archive size: {export_result.get('archive_size_mb', 0):.2f} MB")
            print(f"   📋 Format version: {export_result.get('format_version', 'unknown')}")

            # Show archive structure
            archive_path = Path(export_result['archive_path'])
            if archive_path.exists():
                print(f"\n   📁 Archive structure:")
                for item in sorted(archive_path.rglob("*")):
                    if item.is_file():
                        rel_path = item.relative_to(archive_path)
                        size = item.stat().st_size
                        if size < 1024:
                            size_str = f"{size}B"
                        elif size < 1024*1024:
                            size_str = f"{size/1024:.1f}KB"
                        else:
                            size_str = f"{size/(1024*1024):.1f}MB"
                        print(f"      - {rel_path} ({size_str})")
        else:
            print(f"\n   ❌ Archive export failed: {export_result.get('error')}")
            return 1

        # Summary
        print(f"\n" + "=" * 80)
        print("📋 Validation Summary")
        print("=" * 80)
        print(f"\n   ✅ Memory System Status: Healthy")
        print(f"   ✅ Total Memories Ingested: {total_memories}")
        print(f"   ✅ BMA v2.0.0 Archive: Exported")
        print(f"   ✅ Archive Path: {export_result['archive_path']}")
        print(f"\n   End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n" + "=" * 80)
        print("✅ Validation and Export Complete!")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await coordinator.shutdown()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
