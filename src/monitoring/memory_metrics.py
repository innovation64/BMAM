"""
Memory System Metrics Collection
记忆系统指标收集模块

Provides comprehensive metrics for monitoring memory system health,
consolidation effectiveness, and multi-brain region collaboration.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemoryMetricsCollector:
    """
    Memory System Metrics Collector
    记忆系统指标收集器

    Tracks:
    - Storage distribution across brain regions
    - Consolidation events and effectiveness
    - Retrieval source distribution
    - Brain region activation counts
    - Performance metrics
    """

    def __init__(self, output_dir: str = "metrics"):
        """
        Initialize metrics collector

        Args:
            output_dir: Directory to store metrics JSON files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Metrics storage
        self.storage_distribution: Dict[str, int] = defaultdict(int)
        self.retrieval_sources: Dict[str, int] = defaultdict(int)
        self.brain_region_activations: Dict[str, int] = defaultdict(int)
        self.consolidation_events: List[Dict[str, Any]] = []
        self.retrieval_events: List[Dict[str, Any]] = []

        # Session info
        self.session_start = datetime.now()
        self.total_queries = 0
        self.total_consolidations = 0

        logger.info(f"MemoryMetricsCollector initialized (output={output_dir})")

    def record_storage_update(
        self,
        brain_region: str,
        count: int,
        source: str = "manual_check"
    ):
        """
        Record storage distribution update

        Args:
            brain_region: 'hippocampus', 'temporal_lobe', 'memory_system'
            count: Current memory count
            source: Source of update
        """
        self.storage_distribution[brain_region] = count
        logger.debug(f"Storage update: {brain_region}={count} (source={source})")

    def record_consolidation_event(
        self,
        trigger: str,
        memories_processed: int,
        patterns_extracted: int,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record consolidation event

        Args:
            trigger: 'manual', 'automatic', 'time_based'
            memories_processed: Number of memories consolidated
            patterns_extracted: Number of patterns extracted
            success: Whether consolidation succeeded
            metadata: Additional metadata
        """
        event = {
            'timestamp': datetime.now().isoformat(),
            'trigger': trigger,
            'memories_processed': memories_processed,
            'patterns_extracted': patterns_extracted,
            'success': success,
            'metadata': metadata or {}
        }
        self.consolidation_events.append(event)
        self.total_consolidations += 1

        logger.info(
            f"Consolidation event: trigger={trigger}, "
            f"processed={memories_processed}, patterns={patterns_extracted}"
        )

    def record_retrieval_event(
        self,
        query: str,
        sources: Dict[str, int],
        total_retrieved: int,
        strategy: str = 'hybrid',
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record retrieval event

        Args:
            query: Query text (truncated)
            sources: {'hippocampus': 5, 'temporal_lobe': 1}
            total_retrieved: Total memories retrieved
            strategy: 'semantic', 'episodic', 'hybrid'
            metadata: Additional metadata
        """
        # Update cumulative source counts
        for source, count in sources.items():
            self.retrieval_sources[source] += count

        # Record event
        event = {
            'timestamp': datetime.now().isoformat(),
            'query': query[:100],  # Truncate long queries
            'sources': sources,
            'total_retrieved': total_retrieved,
            'strategy': strategy,
            'metadata': metadata or {}
        }
        self.retrieval_events.append(event)
        self.total_queries += 1

        logger.debug(
            f"Retrieval event: strategy={strategy}, "
            f"total={total_retrieved}, sources={sources}"
        )

    def record_brain_region_activation(
        self,
        region: str,
        action: str = 'activated'
    ):
        """
        Record brain region activation

        Args:
            region: 'hippocampus', 'prefrontal', 'temporal_lobe', etc.
            action: 'activated', 'queried', 'consolidated'
        """
        key = f"{region}_{action}"
        self.brain_region_activations[key] += 1

    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot

        Returns:
            Dict with all current metrics
        """
        session_duration = (datetime.now() - self.session_start).total_seconds()

        # Calculate rates
        consolidation_rate = self.total_consolidations / (session_duration / 60) if session_duration > 0 else 0
        query_rate = self.total_queries / (session_duration / 60) if session_duration > 0 else 0

        # Calculate source distribution percentages
        total_retrievals = sum(self.retrieval_sources.values())
        source_percentages = {}
        if total_retrievals > 0:
            for source, count in self.retrieval_sources.items():
                source_percentages[source] = round(count / total_retrievals * 100, 2)

        metrics = {
            'timestamp': datetime.now().isoformat(),
            'session_duration_seconds': round(session_duration, 2),

            # Storage distribution
            'storage_distribution': dict(self.storage_distribution),

            # Consolidation metrics
            'consolidation_summary': {
                'total_events': self.total_consolidations,
                'rate_per_minute': round(consolidation_rate, 4),
                'recent_events': self.consolidation_events[-5:]  # Last 5 events
            },

            # Retrieval metrics
            'retrieval_summary': {
                'total_queries': self.total_queries,
                'rate_per_minute': round(query_rate, 4),
                'source_distribution': dict(self.retrieval_sources),
                'source_percentages': source_percentages,
                'recent_events': self.retrieval_events[-5:]  # Last 5 events
            },

            # Brain region activity
            'brain_region_activation': dict(self.brain_region_activations),

            # Health indicators
            'health_indicators': self._calculate_health_indicators()
        }

        return metrics

    def _calculate_health_indicators(self) -> Dict[str, Any]:
        """
        Calculate system health indicators

        Returns:
            Dict with health status and warnings
        """
        warnings = []
        status = 'healthy'

        # Check if long-term storage is being used
        temporal_count = self.storage_distribution.get('temporal_lobe', 0)
        memory_system_count = self.storage_distribution.get('memory_system', 0)

        if temporal_count == 0 and memory_system_count == 0:
            warnings.append('No long-term storage detected - system may be short-term only')
            status = 'warning'

        # Check if retrieval is diversified
        total_retrievals = sum(self.retrieval_sources.values())
        if total_retrievals > 10:
            hippocampus_ratio = self.retrieval_sources.get('hippocampus', 0) / total_retrievals
            if hippocampus_ratio > 0.95:
                warnings.append(f'Over 95% retrievals from hippocampus - long-term storage may not be working')
                status = 'warning'

        # Check consolidation activity
        if self.total_queries > 20 and self.total_consolidations == 0:
            warnings.append('No consolidations despite many queries - check consolidation triggers')
            status = 'warning'

        return {
            'status': status,
            'warnings': warnings,
            'long_term_storage_active': temporal_count > 0 or memory_system_count > 0,
            'retrieval_diversity_score': self._calculate_diversity_score()
        }

    def _calculate_diversity_score(self) -> float:
        """
        Calculate retrieval source diversity score (0-1)

        Returns:
            Diversity score (1 = perfectly distributed, 0 = single source)
        """
        if not self.retrieval_sources:
            return 0.0

        total = sum(self.retrieval_sources.values())
        if total == 0:
            return 0.0

        # Calculate Shannon entropy
        import math
        entropy = 0.0
        for count in self.retrieval_sources.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)

        # Normalize to 0-1 (max entropy = log2(n) where n is number of sources)
        max_entropy = math.log2(len(self.retrieval_sources)) if len(self.retrieval_sources) > 1 else 1
        diversity_score = entropy / max_entropy if max_entropy > 0 else 0.0

        return round(diversity_score, 3)

    def save_metrics(self, filename: Optional[str] = None) -> str:
        """
        Save current metrics to JSON file

        Args:
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"memory_system_metrics_{timestamp}.json"

        filepath = self.output_dir / filename

        metrics = self.get_current_metrics()

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

        logger.info(f"Metrics saved to {filepath}")
        return str(filepath)

    def generate_summary_report(self) -> str:
        """
        Generate human-readable summary report

        Returns:
            Formatted summary string
        """
        metrics = self.get_current_metrics()
        health = metrics['health_indicators']

        report = []
        report.append("=" * 80)
        report.append("Memory System Metrics Summary")
        report.append("=" * 80)
        report.append(f"Timestamp: {metrics['timestamp']}")
        report.append(f"Session Duration: {metrics['session_duration_seconds']:.1f}s")
        report.append("")

        # Health status
        status_emoji = "✅" if health['status'] == 'healthy' else "⚠️"
        report.append(f"Health Status: {status_emoji} {health['status'].upper()}")
        if health['warnings']:
            for warning in health['warnings']:
                report.append(f"  ⚠️  {warning}")
        report.append("")

        # Storage distribution
        report.append("Storage Distribution:")
        for region, count in metrics['storage_distribution'].items():
            report.append(f"  {region}: {count} memories")
        report.append("")

        # Consolidation summary
        cons = metrics['consolidation_summary']
        report.append(f"Consolidation Activity:")
        report.append(f"  Total Events: {cons['total_events']}")
        report.append(f"  Rate: {cons['rate_per_minute']:.4f} events/min")
        report.append("")

        # Retrieval summary
        retr = metrics['retrieval_summary']
        report.append(f"Retrieval Activity:")
        report.append(f"  Total Queries: {retr['total_queries']}")
        report.append(f"  Rate: {retr['rate_per_minute']:.4f} queries/min")
        report.append(f"  Source Distribution:")
        for source, pct in retr['source_percentages'].items():
            count = retr['source_distribution'][source]
            report.append(f"    {source}: {count} ({pct}%)")
        report.append(f"  Diversity Score: {health['retrieval_diversity_score']:.3f}")
        report.append("")

        # Brain region activity
        report.append("Brain Region Activations:")
        for region, count in sorted(metrics['brain_region_activation'].items()):
            report.append(f"  {region}: {count}")
        report.append("=" * 80)

        return "\n".join(report)


# Global metrics collector instance
_global_collector: Optional[MemoryMetricsCollector] = None


def get_metrics_collector(output_dir: str = "metrics") -> MemoryMetricsCollector:
    """
    Get global metrics collector instance (singleton)

    Args:
        output_dir: Directory for metrics output

    Returns:
        Global MemoryMetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MemoryMetricsCollector(output_dir=output_dir)
    return _global_collector


def reset_metrics_collector():
    """Reset global metrics collector (for testing)"""
    global _global_collector
    _global_collector = None
