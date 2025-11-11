#!/usr/bin/env python3
"""
Memory System Metrics Dashboard Example
记忆系统指标仪表板示例

Demonstrates:
- Real-time metrics collection during operation
- Health monitoring and alerting
- Visualization-ready data export
- Long-term storage effectiveness tracking
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.monitoring.memory_metrics import get_metrics_collector, reset_metrics_collector


async def run_simulated_workload():
    """
    Simulate realistic workload to generate metrics
    模拟真实负载以生成指标
    """
    print("=" * 80)
    print("Memory System Metrics Dashboard - Live Demo")
    print("=" * 80)
    print()

    # Initialize system
    print("[1/5] Initializing Brain-Inspired Coordinator...")
    coordinator = BrainInspiredCoordinator()
    metrics = get_metrics_collector(output_dir="metrics")

    # Phase 1: Inject memories (short-term storage)
    print("\n[2/5] Phase 1: Injecting memories into Hippocampus (short-term)...")
    test_memories = [
        "Alice is a researcher at MIT.",
        "Alice published a paper on neural networks.",
        "Alice won the Best Paper Award at NeurIPS 2024.",
        "Bob is a professor at Stanford.",
        "Bob teaches machine learning courses.",
        "Bob supervises 10 PhD students.",
        "Carol works at Google AI.",
        "Carol leads the computer vision team.",
        "Carol developed a new image recognition algorithm.",
        "David is a data scientist at OpenAI.",
    ]

    for i, memory in enumerate(test_memories, 1):
        await coordinator.process_input(memory)
        print(f"  [{i}/{len(test_memories)}] Stored: {memory[:50]}...")

    # Record initial storage distribution
    hippo_count = len(coordinator.hippocampus.memories) if hasattr(coordinator.hippocampus, 'memories') else 0
    temporal_count = len(coordinator.temporal_lobe.memories) if hasattr(coordinator.temporal_lobe, 'memories') else 0
    metrics.record_storage_update('hippocampus', hippo_count, source='phase1_inject')
    metrics.record_storage_update('temporal_lobe', temporal_count, source='phase1_inject')

    print(f"\n  ✓ Hippocampus storage: {hippo_count} memories")
    print(f"  ✓ TemporalLobe storage: {temporal_count} memories")

    # Phase 2: Retrieval (activate brain regions)
    print("\n[3/5] Phase 2: Multi-brain region retrieval...")
    queries = [
        "What is Alice's research about?",
        "Who teaches at Stanford?",
        "What does Carol do?",
        "Tell me about AI researchers.",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n  Query {i}: {query}")
        results = await coordinator.smart_retrieve(query, k=5, strategy='hybrid')
        print(f"    → Retrieved {len(results)} memories")

        # Show source distribution
        sources = {}
        for r in results:
            source = r.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        print(f"    → Sources: {sources}")

    # Phase 3: Consolidation (long-term storage)
    print("\n[4/5] Phase 3: Triggering consolidation (Hippocampus → TemporalLobe/MemorySystem)...")

    # Boost importance to trigger consolidation
    for mem in coordinator.hippocampus.memories:
        mem.importance = 0.9
        mem.access_count = 0

    result = await coordinator.hippocampus.consolidate_memories()
    print(f"  ✓ Consolidation result: {result}")

    # Update storage metrics
    temporal_count_after = len(coordinator.temporal_lobe.memories) if hasattr(coordinator.temporal_lobe, 'memories') else 0
    metrics.record_storage_update('temporal_lobe', temporal_count_after, source='post_consolidation')

    if hasattr(coordinator, 'memory_system') and hasattr(coordinator.memory_system, 'db_manager'):
        memory_system_count = len(coordinator.memory_system.db_manager.get_all_memories())
        metrics.record_storage_update('memory_system', memory_system_count, source='post_consolidation')
        print(f"  ✓ MemorySystem storage: {memory_system_count} memories")

    # Phase 4: Post-consolidation retrieval
    print("\n[5/5] Phase 4: Verifying long-term retrieval...")
    post_query = "What awards has Alice won?"
    results = await coordinator.smart_retrieve(post_query, k=10, strategy='hybrid')

    sources = {}
    for r in results:
        source = r.get('source', 'unknown')
        sources[source] = sources.get(source, 0) + 1

    print(f"  Query: {post_query}")
    print(f"  → Retrieved {len(results)} memories")
    print(f"  → Sources: {sources}")

    # Generate and display metrics
    print("\n" + "=" * 80)
    print("METRICS SUMMARY")
    print("=" * 80)
    print(metrics.generate_summary_report())

    # Save metrics to JSON
    metrics_file = metrics.save_metrics()
    print(f"\n📊 Metrics saved to: {metrics_file}")

    # Generate dashboard-ready data
    dashboard_data = generate_dashboard_data(metrics)
    dashboard_file = Path("metrics") / f"dashboard_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2, ensure_ascii=False)
    print(f"📈 Dashboard data saved to: {dashboard_file}")

    # Check for alerts
    print("\n" + "=" * 80)
    print("HEALTH ALERTS")
    print("=" * 80)
    alerts = check_health_alerts(metrics)
    if alerts:
        for alert in alerts:
            print(f"  {alert['level']} {alert['message']}")
    else:
        print("  ✅ No alerts - system is healthy")

    await coordinator.stop_system()


def generate_dashboard_data(metrics):
    """
    Generate dashboard-ready data structure
    生成仪表板就绪的数据结构
    """
    current_metrics = metrics.get_current_metrics()

    dashboard = {
        'timestamp': current_metrics['timestamp'],
        'session_duration': current_metrics['session_duration_seconds'],

        # Overview panel
        'overview': {
            'total_queries': current_metrics['retrieval_summary']['total_queries'],
            'total_consolidations': current_metrics['consolidation_summary']['total_events'],
            'health_status': current_metrics['health_indicators']['status'],
            'diversity_score': current_metrics['health_indicators']['retrieval_diversity_score']
        },

        # Storage distribution (for pie chart)
        'storage_distribution': {
            'labels': list(current_metrics['storage_distribution'].keys()),
            'values': list(current_metrics['storage_distribution'].values())
        },

        # Retrieval source distribution (for pie chart)
        'retrieval_sources': {
            'labels': list(current_metrics['retrieval_summary']['source_percentages'].keys()),
            'percentages': list(current_metrics['retrieval_summary']['source_percentages'].values()),
            'counts': list(current_metrics['retrieval_summary']['source_distribution'].values())
        },

        # Brain region activity (for bar chart)
        'brain_activity': {
            'labels': list(current_metrics['brain_region_activation'].keys()),
            'values': list(current_metrics['brain_region_activation'].values())
        },

        # Time series data (for line chart)
        'consolidation_events': current_metrics['consolidation_summary']['recent_events'],
        'retrieval_events': current_metrics['retrieval_summary']['recent_events'],

        # Rates
        'rates': {
            'consolidation_per_minute': current_metrics['consolidation_summary']['rate_per_minute'],
            'queries_per_minute': current_metrics['retrieval_summary']['rate_per_minute']
        },

        # Health indicators
        'health': {
            'status': current_metrics['health_indicators']['status'],
            'warnings': current_metrics['health_indicators']['warnings'],
            'long_term_active': current_metrics['health_indicators']['long_term_storage_active'],
            'diversity_score': current_metrics['health_indicators']['retrieval_diversity_score']
        }
    }

    return dashboard


def check_health_alerts(metrics):
    """
    Check for health alerts and generate notifications
    检查健康告警并生成通知
    """
    alerts = []
    current_metrics = metrics.get_current_metrics()
    health = current_metrics['health_indicators']

    # Critical: Long-term storage not active
    if not health['long_term_storage_active']:
        alerts.append({
            'level': '🔴 CRITICAL',
            'message': 'Long-term storage (TemporalLobe/MemorySystem) is not active - system degraded to short-term only',
            'action': 'Verify consolidation triggers and storage APIs'
        })

    # Warning: Low diversity score
    diversity_score = health.get('retrieval_diversity_score', 0)
    if diversity_score < 0.3:
        alerts.append({
            'level': '⚠️  WARNING',
            'message': f'Low retrieval diversity score ({diversity_score:.3f}) - over-reliance on single storage',
            'action': 'Check if consolidation is running and long-term storage is being queried'
        })

    # Warning: System warnings
    for warning in health['warnings']:
        alerts.append({
            'level': '⚠️  WARNING',
            'message': warning,
            'action': 'Review system logs and consolidation configuration'
        })

    # Info: High query rate without consolidations
    consolidation_count = current_metrics['consolidation_summary']['total_events']
    query_count = current_metrics['retrieval_summary']['total_queries']

    if query_count > 20 and consolidation_count == 0:
        alerts.append({
            'level': 'ℹ️  INFO',
            'message': f'{query_count} queries without any consolidations',
            'action': 'Consider triggering manual consolidation or adjusting automatic triggers'
        })

    return alerts


async def main():
    """Main entry point"""
    # Reset metrics for clean run
    reset_metrics_collector()

    # Run demo workload
    await run_simulated_workload()

    print("\n" + "=" * 80)
    print("Demo completed! Check the metrics/ directory for output files.")
    print("\nFiles generated:")
    print("  - memory_system_metrics_YYYYMMDD_HHMMSS.json (full metrics)")
    print("  - dashboard_data_YYYYMMDD_HHMMSS.json (dashboard-ready data)")
    print("\nIntegration suggestions:")
    print("  - Grafana: Import dashboard_data as JSON datasource")
    print("  - Prometheus: Export metrics in Prometheus format")
    print("  - Custom dashboard: Use dashboard_data structure directly")
    print("  - Alerting: Monitor health.warnings and diversity_score")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
