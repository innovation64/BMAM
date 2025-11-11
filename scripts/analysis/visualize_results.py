#!/usr/bin/env python3
"""
Visualization Script for KG Comparison Results
可视化 KG 对比实验结果（可选功能，需要 matplotlib）
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import argparse

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Install with: pip install matplotlib")


def load_comparison_results(results_dir: str) -> Dict[str, Any]:
    """Load comparison results from directory"""
    results_path = Path(results_dir)

    # Find latest comparison results
    result_files = list(results_path.glob("comparison_results_*.json"))
    if not result_files:
        print(f"Error: No comparison results found in {results_dir}")
        sys.exit(1)

    latest_file = max(result_files, key=lambda p: p.stat().st_mtime)

    with open(latest_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_learning_log_analysis(analysis_path: str) -> Dict[str, Any]:
    """Load learning log analysis"""
    if not Path(analysis_path).exists():
        print(f"Error: Analysis file not found: {analysis_path}")
        sys.exit(1)

    with open(analysis_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def plot_accuracy_comparison(results: Dict[str, Any], output_file: str):
    """Plot accuracy comparison bar chart"""
    if not HAS_MATPLOTLIB:
        print("Skipping accuracy plot (matplotlib not installed)")
        return

    configs = list(results.keys())
    accuracies = [results[cfg].get('accuracy', 0) * 100 for cfg in configs]
    corrects = [results[cfg].get('correct', 0) for cfg in configs]
    totals = [results[cfg].get('total', 0) for cfg in configs]

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
    bars = ax.bar(configs, accuracies, color=colors[:len(configs)])

    # Add value labels on bars
    for i, (bar, correct, total) in enumerate(zip(bars, corrects, totals)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{height:.1f}%\n({correct}/{total})',
               ha='center', va='bottom', fontsize=10)

    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title('KG Configuration Comparison - Accuracy', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Accuracy comparison saved to: {output_file}")
    plt.close()


def plot_strategy_distribution(analysis: Dict[str, Any], output_file: str):
    """Plot strategy distribution pie chart"""
    if not HAS_MATPLOTLIB:
        print("Skipping strategy plot (matplotlib not installed)")
        return

    strategy_dist = analysis.get('strategy_distribution', {})
    overall = strategy_dist.get('overall_distribution', {})

    if not overall:
        print("No strategy distribution data available")
        return

    strategies = list(overall.keys())
    counts = list(overall.values())

    fig, ax = plt.subplots(figsize=(10, 7))

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
    explode = [0.05] * len(strategies)

    wedges, texts, autotexts = ax.pie(
        counts,
        labels=strategies,
        autopct='%1.1f%%',
        colors=colors[:len(strategies)],
        explode=explode,
        startangle=90
    )

    # Beautify text
    for text in texts:
        text.set_fontsize(11)

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')

    ax.set_title('Retrieval Strategy Distribution', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Strategy distribution saved to: {output_file}")
    plt.close()


def plot_plasticity_distribution(analysis: Dict[str, Any], output_file: str):
    """Plot plasticity value distribution"""
    if not HAS_MATPLOTLIB:
        print("Skipping plasticity plot (matplotlib not installed)")
        return

    plasticity_trends = analysis.get('plasticity_trends', {})
    overall_stats = plasticity_trends.get('overall_stats', {})

    if not overall_stats:
        print("No plasticity data available")
        return

    mean = overall_stats.get('mean', 0)
    median = overall_stats.get('median', 0)
    min_val = overall_stats.get('min', 0)
    max_val = overall_stats.get('max', 0)
    std_dev = overall_stats.get('std_dev', 0)

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create a simple visualization
    metrics = ['Min', 'Mean', 'Median', 'Max']
    values = [min_val, mean, median, max_val]

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A']
    bars = ax.bar(metrics, values, color=colors)

    # Add value labels
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{val:.4f}',
               ha='center', va='bottom', fontsize=10)

    ax.set_ylabel('Plasticity Value', fontsize=12)
    ax.set_title('Memory Plasticity Distribution', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Add std dev annotation
    ax.text(0.98, 0.98, f'Std Dev: {std_dev:.4f}',
           transform=ax.transAxes,
           ha='right', va='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
           fontsize=10)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Plasticity distribution saved to: {output_file}")
    plt.close()


def plot_kg_reflection_triggers(analysis: Dict[str, Any], output_file: str):
    """Plot KG and reflection trigger rates"""
    if not HAS_MATPLOTLIB:
        print("Skipping trigger rates plot (matplotlib not installed)")
        return

    kg_data = analysis.get('kg_triggering', {})
    reflection_data = analysis.get('reflection_triggering', {})

    kg_rate = kg_data.get('trigger_rate', 0) * 100
    reflection_rate = reflection_data.get('trigger_rate', 0) * 100

    fig, ax = plt.subplots(figsize=(10, 6))

    mechanisms = ['KG Triggering', 'Reflection Triggering']
    rates = [kg_rate, reflection_rate]
    colors = ['#4ECDC4', '#FF6B6B']

    bars = ax.bar(mechanisms, rates, color=colors)

    # Add value labels
    for bar, rate in zip(bars, rates):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{rate:.1f}%',
               ha='center', va='bottom', fontsize=12, fontweight='bold')

    ax.set_ylabel('Trigger Rate (%)', fontsize=12)
    ax.set_title('KG and Reflection Trigger Rates', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 100)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Trigger rates saved to: {output_file}")
    plt.close()


def generate_all_visualizations(
    comparison_results_dir: str,
    learning_log_analysis: str,
    output_dir: str = "results/visualizations"
):
    """Generate all visualizations"""
    if not HAS_MATPLOTLIB:
        print("\n⚠️  matplotlib not installed. Visualizations skipped.")
        print("Install with: pip install matplotlib")
        return

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("Generating Visualizations")
    print("=" * 60 + "\n")

    # Load data
    print("Loading data...")
    comparison_results = load_comparison_results(comparison_results_dir)
    analysis = load_learning_log_analysis(learning_log_analysis)

    # Generate plots
    print("\nGenerating plots...")

    plot_accuracy_comparison(
        comparison_results,
        str(output_path / "accuracy_comparison.png")
    )

    plot_strategy_distribution(
        analysis,
        str(output_path / "strategy_distribution.png")
    )

    plot_plasticity_distribution(
        analysis,
        str(output_path / "plasticity_distribution.png")
    )

    plot_kg_reflection_triggers(
        analysis,
        str(output_path / "trigger_rates.png")
    )

    print("\n" + "=" * 60)
    print(f"✅ All visualizations saved to: {output_path}")
    print("=" * 60 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Visualize KG comparison and learning log results"
    )
    parser.add_argument(
        "--comparison-dir",
        type=str,
        default="results/kg_comparison",
        help="Directory containing comparison results"
    )
    parser.add_argument(
        "--analysis",
        type=str,
        default="results/learning_log_analysis.json",
        help="Path to learning log analysis JSON"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/visualizations",
        help="Output directory for visualizations"
    )

    args = parser.parse_args()

    generate_all_visualizations(
        args.comparison_dir,
        args.analysis,
        args.output
    )


if __name__ == "__main__":
    main()
