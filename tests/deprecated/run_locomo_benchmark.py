#!/usr/bin/env python3
"""
运行BMAM vs MemOS的LoCoMo基准测试
Run LoCoMo Benchmark Comparison between BMAM and MemOS
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from evaluation.benchmark_comparison import BenchmarkComparison


async def main():
    print("=" * 80)
    print("🧠 BMAM vs MemOS LoCoMo Benchmark Comparison")
    print("=" * 80)
    print()

    # Initialize comparison framework
    comparator = BenchmarkComparison()

    # Step 1: Check MemOS baseline availability
    print("📊 Step 1: Checking MemOS baseline availability...")
    print("-" * 80)

    status = comparator.check_memos_baseline_availability("locomo")
    locomo_status = status.get("locomo", {})

    print(f"MemOS Path: {comparator.memos_path}")
    print(f"Data Path Exists: {locomo_status.get('path_exists', False)}")
    print(f"Baseline Available: {locomo_status.get('available', False)}")

    if locomo_status.get("result_files"):
        print(f"Found {len(locomo_status['result_files'])} baseline file(s)")
        print(f"Latest: {locomo_status.get('latest_result', 'N/A')}")
    else:
        print("⚠️  No MemOS baseline results found")
        print()
        print(locomo_status.get('instructions', 'No instructions available'))
        print()
        print("Continuing with BMAM-only evaluation...")

    print()

    # Step 2: Run BMAM evaluation on LoCoMo
    print("🚀 Step 2: Running BMAM evaluation on LoCoMo benchmark...")
    print("-" * 80)
    print("This will test BMAM on:")
    print("  • Multi-hop reasoning")
    print("  • Temporal reasoning")
    print("  • Open domain questions")
    print("  • Single-hop recall")
    print()

    try:
        bmam_results = await comparator.run_bmam_evaluation("locomo")

        print("✅ BMAM Evaluation Complete")
        print(f"   Total Questions: {bmam_results.get('total_questions', 0)}")
        print(f"   Correct Answers: {bmam_results.get('correct_answers', 0)}")
        print(f"   Overall Score: {bmam_results.get('overall_score', 0):.2%}")
        print()

        # Show category breakdown
        if bmam_results.get('categories'):
            print("Category Performance:")
            for category, data in bmam_results['categories'].items():
                accuracy = data.get('accuracy', data.get('correct', 0) / max(data.get('total', 1), 1))
                avg_score = data.get('avg_llm_score', 0)
                print(f"  • {category:20s}: {accuracy:.2%} (LLM Score: {avg_score:.2f})")
        print()

    except Exception as e:
        print(f"❌ BMAM evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Load or skip MemOS baseline
    memos_results = None
    if locomo_status.get('available'):
        print("📖 Step 3: Loading MemOS baseline results...")
        print("-" * 80)

        try:
            memos_results = comparator.load_memos_results("locomo")
            print("✅ MemOS Baseline Loaded")
            print(f"   Overall Score: {memos_results.get('overall_score', 0):.2%}")
            print()
        except Exception as e:
            print(f"⚠️  Failed to load MemOS baseline: {e}")
            print("Continuing with BMAM-only results...")
            print()
    else:
        print("⏭️  Step 3: Skipping MemOS baseline (not available)")
        print()

    # Step 4: Generate comparison report
    if memos_results:
        print("📊 Step 4: Generating comparison report...")
        print("-" * 80)

        comparison = await comparator.generate_comparison_report(
            bmam_results,
            memos_results,
            "locomo"
        )

        # Print report
        report = comparator.generate_comparison_report_text(comparison)
        print(report)

        # Save results
        comparator.save_comparison_results(comparison, "locomo")
        print()
        print(f"✅ Results saved to: {comparator.results_dir}")
    else:
        print("📊 Step 4: Saving BMAM-only results...")
        print("-" * 80)

        # Save BMAM results only
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        results_file = comparator.results_dir / f"locomo_bmam_only_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(bmam_results, f, indent=2, default=str)

        print(f"✅ BMAM results saved to: {results_file}")
        print()
        print("💡 To run full comparison:")
        print("   1. Navigate to MemOS directory")
        print("   2. Run: python evaluation/scripts/run_locomo.py")
        print("   3. Re-run this script")

    print()
    print("=" * 80)
    print("✨ Benchmark Comparison Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())