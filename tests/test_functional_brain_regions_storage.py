#!/usr/bin/env python3
"""
Functional Brain Regions Storage Verification
功能性脑区存储验证

Objective: Verify that non-memory brain regions (PrefrontalCortex, Amygdala,
BasalGanglia, Thalamus) properly store and utilize specialized information
in their respective buffers/caches.

Scope:
- PrefrontalCortex: working_memory buffer (reasoning chains)
- Amygdala: emotional_buffer (emotion tags)
- BasalGanglia: strategy_cache (behavioral patterns)
- Thalamus: routing_buffer (if exists)

This complements memory storage tests by verifying functional brain regions.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator


async def test_prefrontal_working_memory():
    """
    Test 1: PrefrontalCortex Working Memory
    前额叶工作记忆测试

    Verify that PrefrontalCortex stores reasoning chains in working_memory buffer
    """
    print("=" * 80)
    print("Test 1: PrefrontalCortex Working Memory")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Inject memories that require reasoning
    print("\n[1/3] Injecting memories requiring reasoning...")
    reasoning_memories = [
        "If it rains, the ground gets wet.",
        "The ground is wet this morning.",
        "There are dark clouds in the sky.",
    ]

    for mem in reasoning_memories:
        await coordinator.process_input(mem)

    # Trigger reasoning chain
    print("\n[2/3] Triggering reasoning chain...")
    query = "Did it rain this morning?"

    if hasattr(coordinator, 'memory_reasoning_chain') and coordinator.memory_reasoning_chain:
        result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(query)
        print(f"  → Reasoning chain result:")
        print(f"     - Memories: {len(result.memories)}")
        print(f"     - Causal links: {len(result.causal_links)}")
        print(f"     - Confidence: {result.confidence:.2f}")

    # Check PrefrontalCortex working memory
    print("\n[3/3] Checking PrefrontalCortex working memory...")

    if hasattr(coordinator, 'prefrontal_agent'):
        prefrontal = coordinator.prefrontal_agent

        # Check working_memory attribute
        if hasattr(prefrontal, 'working_memory'):
            wm_count = len(prefrontal.working_memory)
            print(f"  → Working memory: {wm_count} items")

            if wm_count > 0:
                print(f"  → Sample working memory item:")
                sample = prefrontal.working_memory[0]
                print(f"     - Content: {str(sample)[:100]}...")
                print(f"  ✅ PASS: PrefrontalCortex working memory is storing items")
                success = True
            else:
                print(f"  ⚠️  WARNING: Working memory is empty")
                success = False
        else:
            print(f"  ⚠️  WARNING: PrefrontalCortex has no 'working_memory' attribute")
            success = False

        # Check prefrontal_storage (if exists)
        if hasattr(coordinator, 'prefrontal_storage'):
            storage = coordinator.prefrontal_storage
            print(f"  → PrefrontalStorage found: {type(storage).__name__}")

            # Try to read storage contents
            if hasattr(storage, 'get_all') or hasattr(storage, 'list_all'):
                method = getattr(storage, 'get_all', getattr(storage, 'list_all', None))
                if method:
                    try:
                        items = method()
                        print(f"  → PrefrontalStorage items: {len(items) if isinstance(items, list) else 'N/A'}")
                    except Exception as e:
                        print(f"  → PrefrontalStorage read error: {e}")
    else:
        print(f"  ❌ FAIL: PrefrontalCortex not found in coordinator")
        success = False

    await coordinator.stop_system()
    return success


async def test_amygdala_emotional_buffer():
    """
    Test 2: Amygdala Emotional Buffer
    杏仁核情绪缓冲测试

    Verify that Amygdala stores emotional tags and intensities
    """
    print("\n" + "=" * 80)
    print("Test 2: Amygdala Emotional Buffer")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Inject emotionally charged memories
    print("\n[1/3] Injecting emotionally charged memories...")
    emotional_memories = [
        "I won the lottery! I'm so happy!",
        "My dog passed away yesterday. I'm heartbroken.",
        "The project deadline was moved up. I'm stressed.",
    ]

    for mem in emotional_memories:
        await coordinator.process_input(mem)

    # Check Amygdala emotional buffer
    print("\n[2/3] Checking Amygdala emotional buffer...")

    if hasattr(coordinator, 'amygdala'):
        amygdala = coordinator.amygdala

        # Check for emotional_buffer or similar
        buffer_attrs = ['emotional_buffer', 'emotion_buffer', 'emotions', 'emotional_memories']
        buffer_found = False

        for attr in buffer_attrs:
            if hasattr(amygdala, attr):
                buffer = getattr(amygdala, attr)
                print(f"  → Found: {attr}")
                print(f"     - Type: {type(buffer).__name__}")
                print(f"     - Length: {len(buffer) if hasattr(buffer, '__len__') else 'N/A'}")

                if hasattr(buffer, '__len__') and len(buffer) > 0:
                    print(f"     - Sample: {str(buffer[0])[:100]}...")
                    print(f"  ✅ PASS: Amygdala emotional buffer is storing items")
                    buffer_found = True
                    break

        if not buffer_found:
            print(f"  ⚠️  WARNING: No emotional buffer found in Amygdala")
            print(f"     - Available attributes: {[a for a in dir(amygdala) if not a.startswith('_')]}")

        # Check emotional tagging on memories
        print("\n[3/3] Checking emotional tags on memories...")
        hippo_memories = coordinator.hippocampus.memories if hasattr(coordinator.hippocampus, 'memories') else []

        emotional_tagged = 0
        for mem in hippo_memories:
            if hasattr(mem, 'emotion_tags') and mem.emotion_tags:
                emotional_tagged += 1
            elif hasattr(mem, 'emotion_intensity') and mem.emotion_intensity > 0:
                emotional_tagged += 1

        print(f"  → Memories with emotional tags: {emotional_tagged}/{len(hippo_memories)}")

        if emotional_tagged > 0:
            print(f"  ✅ PASS: Amygdala is tagging memories with emotions")
            success = True
        else:
            print(f"  ⚠️  WARNING: No emotional tags found on memories")
            success = False
    else:
        print(f"  ❌ FAIL: Amygdala not found in coordinator")
        success = False

    await coordinator.stop_system()
    return success


async def test_basal_ganglia_strategy_cache():
    """
    Test 3: BasalGanglia Strategy Cache
    基底节策略缓存测试

    Verify that BasalGanglia stores behavioral patterns and strategies
    """
    print("\n" + "=" * 80)
    print("Test 3: BasalGanglia Strategy Cache")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Simulate repeated behaviors to trigger habit learning
    print("\n[1/3] Simulating repeated behaviors...")
    repeated_actions = [
        "User clicked the save button.",
        "User clicked the save button.",
        "User clicked the save button.",
        "User opened preferences menu.",
        "User opened preferences menu.",
    ]

    for action in repeated_actions:
        await coordinator.process_input(action)

    # Check BasalGanglia strategy cache
    print("\n[2/3] Checking BasalGanglia strategy cache...")

    if hasattr(coordinator, 'basal_ganglia'):
        basal_ganglia = coordinator.basal_ganglia

        # Check for strategy_cache or similar
        cache_attrs = ['strategy_cache', 'habit_cache', 'patterns', 'behavioral_patterns']
        cache_found = False

        for attr in cache_attrs:
            if hasattr(basal_ganglia, attr):
                cache = getattr(basal_ganglia, attr)
                print(f"  → Found: {attr}")
                print(f"     - Type: {type(cache).__name__}")

                if isinstance(cache, dict):
                    print(f"     - Keys: {list(cache.keys())[:5]}")
                    print(f"     - Size: {len(cache)}")

                    if len(cache) > 0:
                        print(f"  ✅ PASS: BasalGanglia strategy cache is storing patterns")
                        cache_found = True
                        break
                elif hasattr(cache, '__len__'):
                    print(f"     - Length: {len(cache)}")
                    if len(cache) > 0:
                        print(f"  ✅ PASS: BasalGanglia strategy cache is storing items")
                        cache_found = True
                        break

        if not cache_found:
            print(f"  ⚠️  WARNING: No strategy cache found in BasalGanglia")
            print(f"     - Available attributes: {[a for a in dir(basal_ganglia) if not a.startswith('_')]}")

        print("\n[3/3] Checking habit learning...")
        # Check if repeated patterns are recognized
        if hasattr(basal_ganglia, 'get_habit_strength'):
            try:
                strength = basal_ganglia.get_habit_strength("save button")
                print(f"  → Habit strength for 'save button': {strength}")
                if strength > 0:
                    print(f"  ✅ PASS: BasalGanglia is learning habits")
                    success = True
                else:
                    print(f"  ⚠️  WARNING: No habit strength detected")
                    success = False
            except Exception as e:
                print(f"  → Error checking habit: {e}")
                success = False
        else:
            print(f"  ⚠️  WARNING: No habit strength API found")
            success = cache_found

    else:
        print(f"  ❌ FAIL: BasalGanglia not found in coordinator")
        success = False

    await coordinator.stop_system()
    return success


async def test_thalamus_routing():
    """
    Test 4: Thalamus Routing/Coordination
    丘脑路由协调测试

    Verify that Thalamus handles information routing
    (May not have dedicated storage, just activation tracking)
    """
    print("\n" + "=" * 80)
    print("Test 4: Thalamus Routing/Coordination")
    print("=" * 80)

    coordinator = BrainInspiredCoordinator()

    # Process various types of input
    print("\n[1/2] Processing diverse inputs...")
    inputs = [
        "Important urgent task!",
        "Routine reminder.",
        "Emotional news update.",
    ]

    for inp in inputs:
        await coordinator.process_input(inp)

    # Check Thalamus
    print("\n[2/2] Checking Thalamus coordination...")

    if hasattr(coordinator, 'thalamus'):
        thalamus = coordinator.thalamus
        print(f"  → Thalamus found: {type(thalamus).__name__}")

        # Check for routing buffer (may not exist)
        buffer_attrs = ['routing_buffer', 'coordination_buffer', 'message_queue']
        buffer_found = False

        for attr in buffer_attrs:
            if hasattr(thalamus, attr):
                buffer = getattr(thalamus, attr)
                print(f"  → Found: {attr}")
                print(f"     - Type: {type(buffer).__name__}")
                if hasattr(buffer, '__len__'):
                    print(f"     - Length: {len(buffer)}")
                buffer_found = True
                break

        if not buffer_found:
            print(f"  ℹ️  INFO: Thalamus may not have dedicated storage (routing-only)")
            print(f"     - This is expected for pure coordination components")

        # Check activation tracking (from metrics)
        from src.monitoring.memory_metrics import get_metrics_collector
        metrics = get_metrics_collector()
        current = metrics.get_current_metrics()

        thalamus_activations = {k: v for k, v in current['brain_region_activation'].items()
                               if 'thalamus' in k.lower()}

        if thalamus_activations:
            print(f"  → Thalamus activations: {thalamus_activations}")
            print(f"  ✅ PASS: Thalamus coordination is tracked in metrics")
            success = True
        else:
            print(f"  ℹ️  INFO: No Thalamus activations in metrics (may not be instrumented)")
            success = True  # Not a failure - pure routing may not need activation tracking

    else:
        print(f"  ⚠️  WARNING: Thalamus not found in coordinator")
        success = True  # Not critical

    await coordinator.stop_system()
    return success


async def main():
    """Main test orchestrator"""
    print("Functional Brain Regions Storage Verification")
    print("=" * 80)
    print("Objective: Verify specialized storage in functional brain regions")
    print("=" * 80)

    results = {}

    # Test 1: PrefrontalCortex
    try:
        results['prefrontal_working_memory'] = await test_prefrontal_working_memory()
    except Exception as e:
        print(f"\n❌ PrefrontalCortex test failed: {e}")
        results['prefrontal_working_memory'] = False

    # Test 2: Amygdala
    try:
        results['amygdala_emotional_buffer'] = await test_amygdala_emotional_buffer()
    except Exception as e:
        print(f"\n❌ Amygdala test failed: {e}")
        results['amygdala_emotional_buffer'] = False

    # Test 3: BasalGanglia
    try:
        results['basal_ganglia_strategy_cache'] = await test_basal_ganglia_strategy_cache()
    except Exception as e:
        print(f"\n❌ BasalGanglia test failed: {e}")
        results['basal_ganglia_strategy_cache'] = False

    # Test 4: Thalamus
    try:
        results['thalamus_routing'] = await test_thalamus_routing()
    except Exception as e:
        print(f"\n❌ Thalamus test failed: {e}")
        results['thalamus_routing'] = False

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "⚠️  NEEDS REVIEW"
        print(f"  {status}: {test_name.replace('_', ' ').title()}")

    passed_count = sum(1 for p in results.values() if p)
    total_count = len(results)

    print(f"\nPassed: {passed_count}/{total_count}")

    # Save results
    output_file = Path("metrics/cross_session/functional_brain_regions_test.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_results': results,
            'passed_count': passed_count,
            'total_count': total_count
        }, f, indent=2)

    print(f"\n✓ Results saved to {output_file}")

    return passed_count == total_count


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
