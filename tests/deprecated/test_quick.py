#!/usr/bin/env python3
"""简单的功能测试"""

import asyncio
import sys
sys.path.insert(0, '/Users/liyang/Desktop/testversion/BMAM')

async def test():
    from src.reasoning.capability_analyzer import CapabilityAnalyzer

    print("Testing CapabilityAnalyzer...")
    analyzer = CapabilityAnalyzer()

    # Test 1: Simple fact question
    result = await analyzer.analyze("What did Caroline attend on 8 May 2023?")
    print(f"✅ Test 1: {result.get('capabilities', [])}")

    # Test 2: Temporal question
    result2 = await analyzer.analyze("How many days passed between May 25 and June 3?")
    print(f"✅ Test 2: {result2.get('capabilities', [])}")

    print("\nNow testing CapabilityOrchestrator integration...")
    from src.coordination.brain_coordinator import BrainInspiredCoordinator

    coordinator = BrainInspiredCoordinator()

    # Simple learning
    print("\n📚 Learning fact...")
    r1 = await coordinator.process_input("On 8 May 2023, Caroline attended an LGBTQ support group meeting.")
    print(f"  Stored: {r1.memory_stored}, Mode: {r1.routing_decision.get('mode')}")

    # Simple question
    print("\n❓ Asking question...")
    r2 = await coordinator.process_input("What did Caroline attend on 8 May 2023?")
    print(f"  Mode: {r2.routing_decision.get('mode')}")
    print(f"  Capabilities: {r2.routing_decision.get('capabilities', [])}")
    print(f"  Response: {r2.response}")

    print("\n✅ Test completed!")

if __name__ == '__main__':
    asyncio.run(test())
