#!/usr/bin/env python3
"""
Test Brain Region Activation - Corrected Implementation
验证修复后的脑区激活和自动持久化

测试内容:
1. Amygdala emotion tagging (通过正确API)
2. PrefrontalCortex working memory (通过正确API)
3. BasalGanglia skill learning (通过正确API)
4. 自动持久化验证 (检查state files)
"""

import os
import sys
import json
import logging
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from coordination.brain_coordinator_refactored import BrainCoordinator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Test corrected brain region activation"""

    print("\n" + "=" * 80)
    print("🧠 BMAM Brain Region Activation Test - Corrected Implementation")
    print("=" * 80 + "\n")

    # Initialize BrainCoordinator
    print("📌 Step 1: Initialize BrainCoordinator")
    coordinator = BrainCoordinator(enable_llm=False)
    print("✅ BrainCoordinator initialized\n")

    # Test conversations with emotional content and actions
    test_conversations = [
        # Emotional content - should trigger Amygdala
        ("I'm so happy today! I won the lottery!", "That's wonderful news!"),
        ("I'm feeling really stressed about the deadline.", "I understand that pressure."),
        ("My grandmother passed away yesterday.", "I'm so sorry for your loss."),

        # Action patterns - should trigger BasalGanglia
        ("I clicked the button and opened the file.", "The file is now open."),
        ("I need to search for information.", "What would you like to search for?"),
        ("I'm going to create a new project.", "Great! Let's get started."),

        # Complex reasoning - should trigger PrefrontalCortex
        ("How can we solve climate change?", "This requires multiple approaches."),
        ("What's the best strategy for learning?", "Active recall and spaced repetition."),
    ]

    print("📌 Step 2: Process test conversations")
    print(f"Processing {len(test_conversations)} conversations...\n")

    for i, (user_input, response) in enumerate(test_conversations, 1):
        print(f"Conversation {i}/{len(test_conversations)}:")
        print(f"  User: {user_input[:60]}...")
        print(f"  Bot: {response[:60]}...")

        try:
            result = await coordinator.process_user_input(
                user_input=user_input,
                session_id=f"test_session_{i}",
                context={'test_id': i},
                use_reasoning_chain=True
            )
            print(f"  ✅ Processed (memory_id: {result.get('memory_id', 'N/A')[:8]}...)\n")
        except Exception as e:
            print(f"  ❌ Error: {e}\n")

    print("\n" + "=" * 80)
    print("📌 Step 3: Check Brain Region Statistics")
    print("=" * 80 + "\n")

    # Check Hippocampus
    hippo_stats = coordinator.hippocampus.get_statistics()
    print(f"🐴 Hippocampus (Episodic Memory):")
    print(f"  - Stored: {hippo_stats['current_events']}/{hippo_stats['capacity']}")
    print(f"  - Usage: {hippo_stats['usage_percent']:.1f}%\n")

    # Check TemporalLobe
    temporal_stats = coordinator.temporal_lobe.get_statistics()
    print(f"📚 TemporalLobe (Semantic Memory):")
    print(f"  - Facts: {temporal_stats['fact_count']}")
    print(f"  - KG Nodes: {temporal_stats.get('kg_node_count', 0)}")
    print(f"  - KG Edges: {temporal_stats.get('kg_edge_count', 0)}\n")

    # Check Amygdala
    amygdala_stats = coordinator.amygdala.get_statistics()
    print(f"🎭 Amygdala (Emotional Memory):")
    print(f"  - Emotions: {amygdala_stats['current_emotions']}/{amygdala_stats['capacity']}")
    print(f"  - Total Stored: {amygdala_stats['total_stored']}")
    print(f"  - Usage: {amygdala_stats['usage_percent']:.1f}%\n")

    # Check PrefrontalCortex
    prefrontal_stats = coordinator.prefrontal_agent.get_statistics()
    print(f"🧠 PrefrontalCortex (Working Memory):")
    print(f"  - Items: {prefrontal_stats['current_items']}/{prefrontal_stats['capacity']}")
    print(f"  - Total Stored: {prefrontal_stats['total_stored']}")
    print(f"  - Tasks Coordinated: {prefrontal_stats['total_tasks_coordinated']}")
    print(f"  - Reflections: {prefrontal_stats['total_reflections']}\n")

    # Check BasalGanglia
    basal_stats = coordinator.basal_ganglia.get_statistics()
    print(f"🎯 BasalGanglia (Procedural Memory):")
    print(f"  - Skills: {basal_stats['current_skills']}/{basal_stats['capacity']}")
    print(f"  - Total Stored: {basal_stats['total_stored']}")
    print(f"  - Avg Proficiency: {basal_stats['average_proficiency']:.2f}")
    print(f"  - Total Practices: {basal_stats['total_practices']}\n")

    print("=" * 80)
    print("📌 Step 4: Verify Auto-Persistence (Check State Files)")
    print("=" * 80 + "\n")

    state_files = {
        'hippocampus': 'data/hippocampus_state.json',
        'temporal_lobe': 'data/temporal_lobe.db',
        'amygdala': 'data/amygdala_state.json',
        'prefrontal': 'data/prefrontal_state.json',
        'basal_ganglia': 'data/basal_ganglia_state.json'
    }

    for name, filepath in state_files.items():
        path = Path(filepath)
        if path.exists():
            size = path.stat().st_size
            print(f"✅ {name:20} {filepath:40} ({size:,} bytes)")
        else:
            print(f"❌ {name:20} {filepath:40} (NOT FOUND)")

    print("\n" + "=" * 80)
    print("📌 Step 5: Detailed Inspection of Persisted Data")
    print("=" * 80 + "\n")

    # Inspect Amygdala state
    amygdala_path = Path('data/amygdala_state.json')
    if amygdala_path.exists():
        with amygdala_path.open('r') as f:
            amygdala_data = json.load(f)
        print(f"🎭 Amygdala State File:")
        print(f"  - Emotions Count: {len(amygdala_data)}")
        if amygdala_data:
            print(f"  - Sample Emotion: {amygdala_data[0].get('emotion_tags', [])} "
                  f"(intensity={amygdala_data[0].get('emotion_intensity', 0):.2f})")
    else:
        print(f"❌ Amygdala state file not found\n")

    # Inspect PrefrontalCortex state
    prefrontal_path = Path('data/prefrontal_state.json')
    if prefrontal_path.exists():
        with prefrontal_path.open('r') as f:
            prefrontal_data = json.load(f)
        print(f"\n🧠 PrefrontalCortex State File:")
        print(f"  - Working Memory Count: {len(prefrontal_data.get('working_memory', []))}")
        if prefrontal_data.get('working_memory'):
            print(f"  - Sample Item: {prefrontal_data['working_memory'][0].get('task_type', 'N/A')}")
    else:
        print(f"❌ PrefrontalCortex state file not found\n")

    # Inspect BasalGanglia state
    basal_path = Path('data/basal_ganglia_state.json')
    if basal_path.exists():
        with basal_path.open('r') as f:
            basal_data = json.load(f)
        print(f"\n🎯 BasalGanglia State File:")
        print(f"  - Skills Count: {len(basal_data)}")
        if basal_data:
            print(f"  - Sample Skill: {basal_data[0].get('skill_name', 'N/A')} "
                  f"(proficiency={basal_data[0].get('proficiency_level', 0):.2f}, "
                  f"practice_count={basal_data[0].get('practice_count', 0)})")
    else:
        print(f"❌ BasalGanglia state file not found\n")

    print("\n" + "=" * 80)
    print("🎯 Test Summary")
    print("=" * 80 + "\n")

    # Check if all critical brain regions were activated
    success_count = 0
    total_checks = 3

    if amygdala_stats['total_stored'] > 0:
        print("✅ Amygdala: Emotion tagging ACTIVE")
        success_count += 1
    else:
        print("❌ Amygdala: No emotions stored")

    if prefrontal_stats['total_stored'] > 0:
        print("✅ PrefrontalCortex: Working memory ACTIVE")
        success_count += 1
    else:
        print("❌ PrefrontalCortex: No working memory items")

    if basal_stats['total_stored'] > 0:
        print("✅ BasalGanglia: Skill learning ACTIVE")
        success_count += 1
    else:
        print("❌ BasalGanglia: No skills learned")

    print(f"\n🎯 Brain Region Activation: {success_count}/{total_checks} regions active")

    # Check persistence
    files_exist = sum(1 for path in state_files.values() if Path(path).exists())
    print(f"💾 Auto-Persistence: {files_exist}/{len(state_files)} state files created")

    if success_count == total_checks and files_exist == len(state_files):
        print("\n🎉 ALL TESTS PASSED - Brain regions properly activated and persisted!")
        return True
    else:
        print("\n⚠️ SOME TESTS FAILED - Check implementation")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
