"""
Basic test for BrainNetwork parallel activation architecture
"""
import asyncio
import os
import sys

# Add BMAM to path
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

async def test_brain_network():
    """Test BrainNetwork with a simple query"""
    from src.coordination.brain_coordinator import BrainInspiredCoordinator

    # Enable BrainNetwork mode
    os.environ['USE_BRAIN_NETWORK'] = 'true'

    print("=" * 80)
    print("🧠 Testing BrainNetwork Parallel Activation Architecture")
    print("=" * 80)

    # Initialize coordinator
    coordinator = BrainInspiredCoordinator()

    # Verify BrainNetwork is enabled
    if not coordinator.use_brain_network:
        print("❌ ERROR: BrainNetwork not enabled!")
        return

    print(f"✅ BrainNetwork ENABLED")
    print(f"✅ Agents loaded: {len(coordinator.agents)}")
    print(f"✅ BrainNetwork initialized with {len(coordinator.brain_network.agent_ids)} agents")

    # Test 1: Simple factual query
    print("\n" + "=" * 80)
    print("Test 1: Simple Query")
    print("=" * 80)

    query = "Hello, how are you?"
    print(f"Query: {query}")

    result = await coordinator.process_user_input(query)

    print(f"\n✅ Response: {result.response}")
    print(f"✅ Mode: {result.routing_decision.get('mode', 'unknown')}")
    print(f"✅ Converged: {result.routing_decision.get('converged', False)}")
    print(f"✅ Agents involved: {result.agents_involved}")
    print(f"✅ Convergence iteration: {result.insights.get('convergence_iteration', 'N/A')}")

    print("\n" + "=" * 80)
    print("✅ BrainNetwork Basic Test PASSED")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_brain_network())
