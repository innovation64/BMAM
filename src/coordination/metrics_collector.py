"""
Metrics Collector Module
Handles metrics collection, statistics tracking, and performance monitoring
"""

from typing import Dict, Any, List
from datetime import datetime

from ..utils.config import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Collects and manages system metrics and statistics"""

    def __init__(self):
        """Initialize Metrics Collector"""
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'agent_activations': {},
            'memory_operations': 0,
            'kg_operations': 0,
            'consolidation_operations': 0,
            'forgetting_operations': 0
        }

        self.performance_metrics = {
            'average_response_time': 0.0,
            'total_processing_time': 0.0,
            'request_count': 0
        }


    def record_request(self, success: bool, processing_time: float = None):
        """
        Record a request completion

        Args:
            success: Whether request was successful
            processing_time: Time taken to process (seconds)
        """
        self.processing_stats['total_requests'] += 1

        if success:
            self.processing_stats['successful_requests'] += 1
        else:
            self.processing_stats['failed_requests'] += 1

        if processing_time is not None:
            self._update_performance_metrics(processing_time)

    def _update_performance_metrics(self, processing_time: float):
        """Update performance metrics with new timing"""
        self.performance_metrics['total_processing_time'] += processing_time
        self.performance_metrics['request_count'] += 1

        # Calculate moving average
        self.performance_metrics['average_response_time'] = (
            self.performance_metrics['total_processing_time'] /
            self.performance_metrics['request_count']
        )

    def record_agent_activation(self, agent_id: str):
        """
        Record agent activation

        Args:
            agent_id: Agent identifier
        """
        if agent_id not in self.processing_stats['agent_activations']:
            self.processing_stats['agent_activations'][agent_id] = 0

        self.processing_stats['agent_activations'][agent_id] += 1

    def record_memory_operation(self):
        """Record a memory operation"""
        self.processing_stats['memory_operations'] += 1

    def record_kg_operation(self):
        """Record a KG operation"""
        self.processing_stats['kg_operations'] += 1

    def record_consolidation_operation(self):
        """Record a consolidation operation"""
        self.processing_stats['consolidation_operations'] += 1

    def record_forgetting_operation(self):
        """Record a forgetting operation"""
        self.processing_stats['forgetting_operations'] += 1

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current statistics

        Returns:
            Statistics dict
        """
        return {
            'processing_stats': self.processing_stats.copy(),
            'performance_metrics': self.performance_metrics.copy(),
            'timestamp': datetime.now().isoformat()
        }

    def get_agent_statistics(self) -> Dict[str, int]:
        """
        Get agent activation statistics

        Returns:
            Dict mapping agent_id to activation count
        """
        return self.processing_stats['agent_activations'].copy()

    def get_success_rate(self) -> float:
        """
        Calculate success rate

        Returns:
            Success rate (0.0-1.0)
        """
        total = self.processing_stats['total_requests']
        if total == 0:
            return 0.0

        successful = self.processing_stats['successful_requests']
        return successful / total

    def get_average_response_time(self) -> float:
        """
        Get average response time

        Returns:
            Average response time in seconds
        """
        return self.performance_metrics['average_response_time']

    def get_most_active_agents(self, top_n: int = 5) -> List[tuple]:
        """
        Get most active agents

        Args:
            top_n: Number of top agents to return

        Returns:
            List of (agent_id, activation_count) tuples
        """
        activations = self.processing_stats['agent_activations']
        sorted_agents = sorted(
            activations.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_agents[:top_n]

    def log_memory_source_summary(self, memories: List[Dict[str, Any]]) -> None:
        """
        Log memory source distribution

        Args:
            memories: List of memories to analyze
        """
        if not memories:
            return

        source_counts = {}
        for mem in memories:
            source = mem.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1


    def log_plasticity_adjustments(
        self,
        agent_from: str,
        agent_to: str,
        old_weight: float,
        new_weight: float
    ) -> None:
        """
        Log plasticity weight adjustment

        Args:
            agent_from: Source agent
            agent_to: Target agent
            old_weight: Old weight value
            new_weight: New weight value
        """
        change = new_weight - old_weight
        logger.info(
            f"🔧 Plasticity: {agent_from}→{agent_to} "
            f"weight {old_weight:.3f}→{new_weight:.3f} "
            f"(Δ{change:+.3f})"
        )

    def log_kg_surfacing_stats(self, memories: List[Dict[str, Any]]) -> None:
        """
        Log KG fact surfacing statistics

        Args:
            memories: List of memories to analyze
        """
        kg_count = sum(1 for m in memories if m.get('kg_enhanced', False))
        total_count = len(memories)

        if kg_count > 0:
            percentage = (kg_count / total_count * 100) if total_count > 0 else 0
            logger.info(
                f"📊 KG Surfacing: {kg_count}/{total_count} "
                f"({percentage:.1f}%) memories are KG-enhanced"
            )

    def reset_statistics(self):
        """Reset all statistics to initial state"""
        self.processing_stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'agent_activations': {},
            'memory_operations': 0,
            'kg_operations': 0,
            'consolidation_operations': 0,
            'forgetting_operations': 0
        }

        self.performance_metrics = {
            'average_response_time': 0.0,
            'total_processing_time': 0.0,
            'request_count': 0
        }


    def export_metrics(self) -> Dict[str, Any]:
        """
        Export all metrics in structured format

        Returns:
            Complete metrics export dict
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'processing_stats': self.processing_stats.copy(),
            'performance_metrics': self.performance_metrics.copy(),
            'derived_metrics': {
                'success_rate': self.get_success_rate(),
                'average_response_time': self.get_average_response_time(),
                'most_active_agents': self.get_most_active_agents()
            }
        }

    def get_system_status(self, agents: Dict[str, Any], is_running: bool) -> Dict[str, Any]:
        """
        Get comprehensive system status

        Args:
            agents: Dict of agent instances
            is_running: Whether system is running

        Returns:
            System status dict
        """
        return {
            'is_running': is_running,
            'agent_count': len(agents),
            'statistics': self.get_statistics(),
            'success_rate': self.get_success_rate(),
            'average_response_time': self.get_average_response_time(),
            'most_active_agents': self.get_most_active_agents(),
            'timestamp': datetime.now().isoformat()
        }
