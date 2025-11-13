#!/usr/bin/env python3
"""Simple test to verify brain region activation and auto-persistence"""

import sys
import os
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from coordination.brain_coordinator_refactored import BrainCoordinator


async def test_simple():
    """Test simple brain activation"""

    print("\n=== Testing Brain Region Activation ===\n")

    # Clear old state files
    for f in ["data/hippocampus_state.json", "data/temporal_lobe.db",
              "data/amygdala_state.json", "data/prefrontal_state.json",
              "data/basal_ganglia_state.json"]:
        if Path(f).exists():
            Path(f).unlink()
            print(f"✅ Cleared {f}")

    # Initialize coordinator
    print("\n📌 Initializing BrainCoordinator...")
    coordinator = BrainCoordinator(enable_llm=False)
    print("✅ BrainCoordinator initialized\n")

    # Test conversations
    test_inputs = [
        "I'm so happy today! Won the lottery!",
        "Feeling very stressed about deadline.",
        "I clicked the button to save the file.",
        "Need to search for information online.",
    ]

    print("📌 Processing test inputs...")
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n{i}. Processing: {user_input[:50]}...")
        result = await coordinator.process_user_input(
            user_input=user_input,
            session_id=f"test_{i}",
            context={},
            use_reasoning_chain=True
        )
        print(f"   ✅ Memory stored: {result.get('memory_id', 'N/A')[:8]}...")

    # Check statistics
    print("\n\n=== Brain Region Statistics ===\n")

    amygdala_stats = coordinator.amygdala.get_statistics()
    print(f"🎭 Amygdala:")
    print(f"   Emotions: {amygdala_stats['current_emotions']}")
    print(f"   Total Stored: {amygdala_stats['total_stored']}")

    prefrontal_stats = coordinator.prefrontal_agent.get_statistics()
    print(f"\n🧠 PrefrontalCortex:")
    print(f"   Items: {prefrontal_stats['current_items']}")
    print(f"   Total Stored: {prefrontal_stats['total_stored']}")

    basal_stats = coordinator.basal_ganglia.get_statistics()
    print(f"\n🎯 BasalGanglia:")
    print(f"   Skills: {basal_stats['current_skills']}")
    print(f"   Total Stored: {basal_stats['total_stored']}")
    print(f"   Total Practices: {basal_stats['total_practices']}")

    # Check state files
    print("\n\n=== State Files ===\n")
    state_files = [
        "data/hippocampus_state.json",
        "data/temporal_lobe.db",
        "data/amygdala_state.json",
        "data/prefrontal_state.json",
        "data/basal_ganglia_state.json"
    ]

    created_files = 0
    for filepath in state_files:
        if Path(filepath).exists():
            size = Path(filepath).stat().st_size
            print(f"✅ {filepath:40} ({size:,} bytes)")
            created_files += 1
        else:
            print(f"❌ {filepath:40} (NOT FOUND)")

    # Summary
    print("\n\n=== Test Summary ===\n")

    if amygdala_stats['total_stored'] > 0:
        print("✅ Amygdala: ACTIVE (emotions tagged)")
    else:
        print("❌ Amygdala: NOT ACTIVE")

    if prefrontal_stats['total_stored'] > 0:
        print("✅ PrefrontalCortex: ACTIVE (working memory)")
    else:
        print("❌ PrefrontalCortex: NOT ACTIVE")

    if basal_stats['total_stored'] > 0:
        print("✅ BasalGanglia: ACTIVE (skills learned)")
    else:
        print("❌ BasalGanglia: NOT ACTIVE")

    if created_files == len(state_files):
        print(f"✅ Auto-Persistence: ALL {created_files} files created")
    else:
        print(f"⚠️ Auto-Persistence: Only {created_files}/{len(state_files)} files created")

    print("\n")


if __name__ == "__main__":
    asyncio.run(test_simple())
