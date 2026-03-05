#!/usr/bin/env python3
"""
快速测试评估系统是否正常工作
Quick test for benchmark evaluation system
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def test_basic_evaluation():
    """测试基础评估功能"""

    print("=" * 60)
    print("🧪 BMAM Benchmark System Quick Test")
    print("=" * 60)

    # Test 1: Import modules
    print("\n📦 Test 1: Importing modules...")
    try:
        from evaluation.benchmark_comparison import BenchmarkComparison
        from evaluation.benchmark_datasets import BenchmarkDatasets
        print("✅ Imports successful")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

    # Test 2: Initialize without loading datasets
    print("\n⚙️  Test 2: Initializing benchmark system...")
    try:
        comparator = BenchmarkComparison()
        print(f"✅ BenchmarkComparison initialized")
        print(f"   BMAM path: {comparator.bmam_path}")
        print(f"   MemOS path: {comparator.memos_path}")
        print(f"   MemOS exists: {comparator.memos_path.exists()}")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

    # Test 3: Check MemOS baseline availability (should fail without real data)
    print("\n📊 Test 3: Checking MemOS baseline data availability...")
    baseline_status = comparator.check_memos_baseline_availability("locomo")
    locomo_status = baseline_status["locomo"]

    print(f"   Path exists: {'✅' if locomo_status['path_exists'] else '❌'}")
    print(f"   Results available: {'✅' if locomo_status['available'] else '❌'}")

    if locomo_status['available']:
        print(f"   ✅ MemOS baseline data ready for comparison")
        print(f"   Result files: {locomo_status['result_count']}")

        # Try loading the actual results
        try:
            memos_results = comparator.load_memos_results("locomo")
            print(f"   Successfully loaded baseline results")
        except Exception as e:
            print(f"   ❌ Failed to load results: {e}")
            return False
    else:
        print(f"   ⚠️  MemOS baseline not available")
        print(f"   This is CORRECT - no mock data is used")
        print(f"   To run real comparison, generate MemOS baseline first")

        # Verify that loading fails properly (no mock data)
        try:
            memos_results = comparator.load_memos_results("locomo")
            if 'error' not in memos_results:
                print(f"   ❌ ERROR: Mock data detected! This should not happen.")
                return False
        except FileNotFoundError as e:
            print(f"   ✅ Correctly raises error without real data")
        except Exception as e:
            print(f"   ⚠️  Unexpected error type: {e}")

    # Test 4: Test dataset info (without heavy IO)
    print("\n📂 Test 4: Checking dataset configurations...")
    try:
        datasets = BenchmarkDatasets()

        # Just list configurations without checking files
        print(f"✅ Available benchmarks:")
        for name, config in datasets.datasets.items():
            print(f"   - {name}: {config['description']}")
            print(f"     Local path: {config['local_path']}")
            exists = config['local_path'].exists()
            print(f"     Cached: {'✅' if exists else '❌'}")
    except Exception as e:
        print(f"❌ Dataset check failed: {e}")
        return False

    # Test 5: Test BMAM coordinator initialization
    print("\n🧠 Test 5: Testing BMAM coordinator...")
    try:
        from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

        coordinator = BrainInspiredCoordinator()
        print(f"✅ Coordinator created")
        print(f"   Agents: {len(coordinator.agents)}")

        # Test a simple query
        print("\n   Testing simple query...")
        result = await coordinator.process_user_input("Hello, this is a test.")

        if result.success:
            print(f"   ✅ Query processed successfully")
            print(f"   Response length: {len(result.response)} chars")
            print(f"   Agents involved: {len(result.agents_involved)}")
        else:
            print(f"   ⚠️  Query failed: {result.error}")

        await coordinator.stop_system()

    except Exception as e:
        print(f"❌ BMAM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("=" * 60)

    return True


async def main():
    """主函数"""
    try:
        success = await test_basic_evaluation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())