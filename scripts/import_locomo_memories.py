#!/usr/bin/env python3
"""
LoCoMo Memory Import Script
Import LoCoMo dataset conversations (500+ turns) into BMAM and export BMA v2.0.0 archive

Usage:
    python3 scripts/import_locomo_memories.py [--dataset-path PATH] [--sample-id ID]

目的: 将LoCoMo数据集的第一轮500+回合对话导入BMAM记忆系统
"""

import asyncio
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def download_locomo_dataset():
    """
    Download LoCoMo dataset from HuggingFace
    """
    print("=" * 80)
    print("📥 Downloading LoCoMo Dataset")
    print("=" * 80)

    try:
        from datasets import load_dataset

        print("\n[1/2] Loading LoCoMo dataset from HuggingFace...")
        dataset = load_dataset("Liangzq007/LoCoMo", split="test")

        print(f"   ✅ Loaded {len(dataset)} samples")

        # Save to local file
        output_dir = Path("data/benchmarks/locomo")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "locomo10.json"

        print(f"\n[2/2] Saving dataset to {output_file}...")

        # Convert to list format
        data = []
        for item in dataset:
            data.append(dict(item))

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"   ✅ Saved {len(data)} samples")
        print(f"\n✅ Dataset downloaded successfully!")

        return output_file

    except ImportError:
        print("\n❌ Error: datasets library not installed")
        print("   Install with: pip install datasets")
        return None
    except Exception as e:
        print(f"\n❌ Error downloading dataset: {e}")
        return None


def load_locomo_dataset(dataset_path: Path, sample_id: int = 0):
    """
    Load LoCoMo dataset from local file

    Args:
        dataset_path: Path to locomo10.json
        sample_id: Sample ID to load (default: 0, first conversation)

    Returns:
        Dictionary with conversation sessions and metadata
    """
    print("=" * 80)
    print(f"📁 Loading LoCoMo Dataset Sample {sample_id}")
    print("=" * 80)

    if not dataset_path.exists():
        print(f"\n❌ Dataset not found: {dataset_path}")
        print("   Run with --download to fetch dataset from HuggingFace")
        return None

    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if sample_id >= len(data):
        print(f"\n❌ Sample ID {sample_id} out of range (max: {len(data)-1})")
        return None

    sample = data[sample_id]

    # Extract conversation data (nested under 'conversation' key in some formats)
    conversation = sample.get('conversation', sample)

    # Count total sessions and turns
    session_count = 0
    total_turns = 0

    for key in conversation.keys():
        if key.startswith('session_') and not key.endswith('_date_time'):
            session_count += 1
            session_dialogues = conversation[key]
            if isinstance(session_dialogues, list):
                total_turns += len(session_dialogues)

    print(f"\n📊 Sample Statistics:")
    print(f"   Sample ID: {sample_id}")
    print(f"   Total Sessions: {session_count}")
    print(f"   Total Turns: {total_turns}")
    print(f"   Speaker A: {conversation.get('speaker_a', 'Unknown')}")
    print(f"   Speaker B: {conversation.get('speaker_b', 'Unknown')}")

    return conversation


async def ingest_conversation_to_memory(coordinator: BrainInspiredCoordinator, conversation: dict):
    """
    Ingest LoCoMo conversation into BMAM memory system

    Args:
        coordinator: BrainInspiredCoordinator instance
        conversation: Conversation dictionary with sessions

    Returns:
        Statistics dictionary
    """
    print("\n" + "=" * 80)
    print("📝 Ingesting Conversation into Memory")
    print("=" * 80)

    speaker_a = conversation.get('speaker_a', 'User')
    speaker_b = conversation.get('speaker_b', 'Agent')

    total_ingested = 0
    session_num = 1

    # Process each session
    while f'session_{session_num}' in conversation:
        session_key = f'session_{session_num}'
        session_date = conversation.get(f'{session_key}_date_time', 'Unknown')
        session_dialogues = conversation[session_key]

        if not session_dialogues:
            session_num += 1
            continue

        print(f"\n📅 Session {session_num} ({session_date})")
        print(f"   Turns: {len(session_dialogues)}")

        # Process each turn in the session
        for turn_idx, dialogue in enumerate(session_dialogues, 1):
            # Extract speaker and content
            speaker = dialogue.get('speaker', speaker_a)
            content = dialogue.get('text', dialogue.get('content', ''))

            if not content:
                continue

            # Format as conversational memory
            formatted_text = f"{speaker}: {content}"

            # Process through coordinator
            try:
                await coordinator.process_input(
                    formatted_text,
                    metadata={
                        'session': session_num,
                        'session_date': session_date,
                        'turn': turn_idx,
                        'speaker': speaker,
                        'source': 'locomo_import'
                    }
                )
                total_ingested += 1

                # Progress indicator every 50 turns
                if total_ingested % 50 == 0:
                    print(f"   ... {total_ingested} turns processed")

            except Exception as e:
                print(f"   ⚠️ Error processing turn {turn_idx}: {e}")

        print(f"   ✓ Session {session_num} completed")
        session_num += 1

    print(f"\n✅ Total turns ingested: {total_ingested}")

    return {
        'total_turns': total_ingested,
        'total_sessions': session_num - 1
    }


async def consolidate_and_export(coordinator: BrainInspiredCoordinator, sample_id: int):
    """
    Trigger memory consolidation and export BMA v2.0.0 archive

    Args:
        coordinator: BrainInspiredCoordinator instance
        sample_id: Sample ID for archive naming

    Returns:
        Export result dictionary
    """
    print("\n" + "=" * 80)
    print("💾 Consolidating and Exporting Memory")
    print("=" * 80)

    # Trigger consolidation
    print("\n[1/2] Triggering memory consolidation...")
    try:
        consolidation_result = coordinator.trigger_consolidation(force=True)
        print(f"   ✅ Consolidation completed")
        print(f"   Hippocampus → TemporalLobe: {consolidation_result.get('consolidated_count', 0)} memories")
    except Exception as e:
        print(f"   ⚠️ Consolidation error: {e}")

    # Export BMA v2.0.0 archive
    print("\n[2/2] Exporting BMA v2.0.0 archive...")
    archive_name = f"locomo_sample{sample_id}_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = Path("data/memory_archives")

    export_result = coordinator.export_memory_archive(
        archive_name=archive_name,
        output_dir=output_dir,
        description=f"LoCoMo Sample {sample_id} - Baseline Memory State (500+ turns)",
        tags=["locomo", f"sample_{sample_id}", "baseline", "v2.0.0"],
        include_faiss=True
    )

    if export_result['success']:
        print(f"   ✅ Archive exported successfully!")
        print(f"   📦 Archive path: {export_result['archive_path']}")
        print(f"   📊 Archive size: {export_result.get('archive_size_mb', 0):.2f} MB")
        print(f"   Format: {export_result.get('format_version', 'unknown')}")
    else:
        print(f"   ❌ Export failed: {export_result.get('error')}")

    return export_result


async def validate_memory_state(coordinator: BrainInspiredCoordinator):
    """
    Validate memory state and run sanity checks

    Args:
        coordinator: BrainInspiredCoordinator instance

    Returns:
        Validation result dictionary
    """
    print("\n" + "=" * 80)
    print("🔍 Validating Memory State")
    print("=" * 80)

    # Get statistics from all brain regions
    print("\n📊 Brain Region Statistics:")

    # Hippocampus (short-term)
    hippo_stats = coordinator.hippocampus.get_statistics()
    print(f"\n   🐚 Hippocampus (Short-term Episodic):")
    print(f"      Current memories: {hippo_stats['current_memories']}")
    print(f"      Total stored: {hippo_stats['total_stored']}")
    print(f"      Capacity: {hippo_stats['capacity']}")

    # TemporalLobe (long-term)
    temporal_stats = await coordinator.temporal_lobe.get_statistics()
    print(f"\n   🧠 TemporalLobe (Long-term Episodic):")
    print(f"      Total memories: {temporal_stats['total_memories']}")
    print(f"      Semantic network nodes: {temporal_stats['knowledge_graph_size']}")

    # Amygdala (emotional)
    amygdala_stats = coordinator.amygdala.get_statistics()
    print(f"\n   ❤️ Amygdala (Emotional):")
    print(f"      Emotional memories: {amygdala_stats['current_memories']}")

    # BasalGanglia (procedural)
    basal_stats = coordinator.basal_ganglia.get_statistics()
    print(f"\n   ⚙️ BasalGanglia (Procedural):")
    print(f"      Skills stored: {basal_stats['current_skills']}")

    # Simple sanity check
    print("\n🧪 Sanity Check:")
    test_query = "What did the speakers talk about?"
    print(f"   Query: {test_query}")

    try:
        response = await coordinator.process_input(test_query)
        result_text = response.get('result', '').strip()[:200]
        print(f"   Response preview: {result_text}...")
        print(f"   ✓ Memory retrieval working")
    except Exception as e:
        print(f"   ⚠️ Sanity check failed: {e}")

    print("\n✅ Validation complete")

    return {
        'hippocampus': hippo_stats,
        'temporal_lobe': temporal_stats,
        'amygdala': amygdala_stats,
        'basal_ganglia': basal_stats
    }


async def main():
    """Main import workflow"""
    parser = argparse.ArgumentParser(description="Import LoCoMo dataset into BMAM memory")
    parser.add_argument('--dataset-path', type=str,
                       default='data/benchmarks/locomo/locomo10.json',
                       help='Path to LoCoMo dataset JSON file')
    parser.add_argument('--sample-id', type=int, default=0,
                       help='Sample ID to import (default: 0)')
    parser.add_argument('--download', action='store_true',
                       help='Download dataset from HuggingFace first')

    args = parser.parse_args()

    print("=" * 80)
    print("🚀 LoCoMo Memory Import Script")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Step 1: Download dataset if requested
    if args.download:
        dataset_path = await download_locomo_dataset()
        if not dataset_path:
            return 1
    else:
        dataset_path = Path(args.dataset_path)

    # Step 2: Load dataset
    conversation = load_locomo_dataset(dataset_path, args.sample_id)
    if not conversation:
        return 1

    # Step 3: Initialize coordinator
    print("\n" + "=" * 80)
    print("🔧 Initializing BMAM Coordinator")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    await coordinator.start_system()
    print("✅ Coordinator ready")

    try:
        # Step 4: Ingest conversation
        ingest_stats = await ingest_conversation_to_memory(coordinator, conversation)

        # Step 5: Consolidate and export
        export_result = await consolidate_and_export(coordinator, args.sample_id)

        # Step 6: Validate
        validation_stats = await validate_memory_state(coordinator)

        # Summary
        print("\n" + "=" * 80)
        print("📋 Import Summary")
        print("=" * 80)
        print(f"   Total turns imported: {ingest_stats['total_turns']}")
        print(f"   Total sessions: {ingest_stats['total_sessions']}")
        print(f"   Archive exported: {export_result['success']}")
        if export_result['success']:
            print(f"   Archive path: {export_result['archive_path']}")
        print(f"\n   End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n✅ LoCoMo memory import complete!")
        print("=" * 80)

        return 0

    except Exception as e:
        print(f"\n❌ Import failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        await coordinator.shutdown()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
