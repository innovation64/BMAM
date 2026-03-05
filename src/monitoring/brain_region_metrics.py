"""
Brain Region Metrics Collector
多脑区指标收集器

Tracks activation counts, source ratios, and collaboration patterns
across all brain region agents.

脑区监控指标：
1. 海马体 (Hippocampus) - 情景记忆存储与检索
2. 颞叶 (Temporal Lobe) - 语义记忆与知识图谱
3. 前额叶 (Prefrontal Cortex) - 执行控制与推理
4. 杏仁核 (Amygdala) - 情绪标注与压力响应
5. 基底节 (Basal Ganglia) - 习惯与程序性记忆
6. 丘脑 (Thalamus) - 信息路由与协调
7. 前扣带回 (Anterior Cingulate) - 冲突检测与自适应控制
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import threading


@dataclass
class BrainRegionActivation:
    """单次脑区激活记录"""
    region: str
    timestamp: float
    operation: str  # e.g., "retrieve", "store", "reason", "tag_emotion"
    input_source: str  # e.g., "user_query", "memory_consolidation", "collaboration"
    output_type: str  # e.g., "memories", "inference", "emotion_tags"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BrainRegionStats:
    """脑区统计信息"""
    total_activations: int = 0
    activations_by_operation: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    activations_by_source: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    activations_by_output: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    collaboration_count: int = 0  # 协作次数
    solo_count: int = 0  # 独立工作次数
    avg_processing_time_ms: float = 0.0
    total_processing_time_ms: float = 0.0
    last_activation_timestamp: Optional[float] = None


@dataclass
class MetricsSnapshot:
    """指标快照"""
    timestamp: str
    session_id: str
    total_queries: int
    brain_regions: Dict[str, BrainRegionStats]
    collaboration_patterns: Dict[str, int]  # e.g., "hippocampus+prefrontal": 5
    source_ratio: Dict[str, float]  # 来源占比
    activation_timeline: List[BrainRegionActivation]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'timestamp': self.timestamp,
            'session_id': self.session_id,
            'total_queries': self.total_queries,
            'brain_regions': {
                region: {
                    'total_activations': stats.total_activations,
                    'activations_by_operation': dict(stats.activations_by_operation),
                    'activations_by_source': dict(stats.activations_by_source),
                    'activations_by_output': dict(stats.activations_by_output),
                    'collaboration_count': stats.collaboration_count,
                    'solo_count': stats.solo_count,
                    'avg_processing_time_ms': stats.avg_processing_time_ms,
                    'total_processing_time_ms': stats.total_processing_time_ms,
                    'last_activation_timestamp': stats.last_activation_timestamp
                }
                for region, stats in self.brain_regions.items()
            },
            'collaboration_patterns': self.collaboration_patterns,
            'source_ratio': self.source_ratio,
            'activation_timeline': [
                {
                    'region': act.region,
                    'timestamp': act.timestamp,
                    'operation': act.operation,
                    'input_source': act.input_source,
                    'output_type': act.output_type,
                    'metadata': act.metadata
                }
                for act in self.activation_timeline[-100:]  # 只保留最近100条
            ]
        }


class BrainRegionMetricsCollector:
    """
    多脑区指标收集器

    Features:
    - 实时追踪各脑区激活次数
    - 统计操作类型分布
    - 分析输入来源占比
    - 识别协作模式
    - 导出JSON格式报告
    """

    BRAIN_REGIONS = [
        'hippocampus',      # 海马体
        'temporal_lobe',    # 颞叶
        'prefrontal',       # 前额叶
        'amygdala',         # 杏仁核
        'basal_ganglia',    # 基底节
        'thalamus',         # 丘脑
        'anterior_cingulate'  # 前扣带回
    ]

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"session_{int(time.time())}"
        self.stats: Dict[str, BrainRegionStats] = {
            region: BrainRegionStats() for region in self.BRAIN_REGIONS
        }
        self.activation_timeline: List[BrainRegionActivation] = []
        self.collaboration_patterns: Dict[str, int] = defaultdict(int)
        self.total_queries = 0
        self.current_query_activations: List[str] = []
        self._lock = threading.Lock()
        self._async_lock = None  # Lazy init for async lock

    def _get_async_lock(self) -> asyncio.Lock:
        """Lazy initialization of async lock (must be called in async context)"""
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    def _record_activation_unsafe(
        self,
        region: str,
        operation: str,
        input_source: str = "user_query",
        output_type: str = "default",
        processing_time_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Core activation recording logic (must be called while holding lock)"""
        if region not in self.BRAIN_REGIONS:
            # 动态添加新脑区
            if region not in self.stats:
                self.stats[region] = BrainRegionStats()

        # 记录激活
        activation = BrainRegionActivation(
            region=region,
            timestamp=time.time(),
            operation=operation,
            input_source=input_source,
            output_type=output_type,
            metadata=metadata or {}
        )
        self.activation_timeline.append(activation)

        # 更新统计
        stats = self.stats[region]
        stats.total_activations += 1
        stats.activations_by_operation[operation] += 1
        stats.activations_by_source[input_source] += 1
        stats.activations_by_output[output_type] += 1
        stats.last_activation_timestamp = activation.timestamp

        # 更新处理时间
        if processing_time_ms > 0:
            stats.total_processing_time_ms += processing_time_ms
            stats.avg_processing_time_ms = (
                stats.total_processing_time_ms / stats.total_activations
            )

        # 追踪当前查询的激活
        if region not in self.current_query_activations:
            self.current_query_activations.append(region)

    def record_activation(
        self,
        region: str,
        operation: str,
        input_source: str = "user_query",
        output_type: str = "default",
        processing_time_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录脑区激活 (sync, thread-safe)

        Args:
            region: 脑区名称
            operation: 操作类型 (e.g., "retrieve", "store", "reason")
            input_source: 输入来源 (e.g., "user_query", "consolidation", "collaboration")
            output_type: 输出类型 (e.g., "memories", "inference", "tags")
            processing_time_ms: 处理时间（毫秒）
            metadata: 额外元数据
        """
        with self._lock:
            self._record_activation_unsafe(
                region, operation, input_source, output_type,
                processing_time_ms, metadata
            )

    async def async_record_activation(
        self,
        region: str,
        operation: str,
        input_source: str = "user_query",
        output_type: str = "default",
        processing_time_ms: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        记录脑区激活 (async, for use in async contexts)

        Args:
            region: 脑区名称
            operation: 操作类型 (e.g., "retrieve", "store", "reason")
            input_source: 输入来源 (e.g., "user_query", "consolidation", "collaboration")
            output_type: 输出类型 (e.g., "memories", "inference", "tags")
            processing_time_ms: 处理时间（毫秒）
            metadata: 额外元数据
        """
        async with self._get_async_lock():
            self._record_activation_unsafe(
                region, operation, input_source, output_type,
                processing_time_ms, metadata
            )

    def _start_new_query_unsafe(self):
        """Core start new query logic (must be called while holding lock)"""
        # 分析上一个查询的协作模式
        if len(self.current_query_activations) > 1:
            # 多个脑区协作
            pattern = '+'.join(sorted(self.current_query_activations))
            self.collaboration_patterns[pattern] += 1

            for region in self.current_query_activations:
                self.stats[region].collaboration_count += 1
        elif len(self.current_query_activations) == 1:
            # 单个脑区独立工作
            region = self.current_query_activations[0]
            self.stats[region].solo_count += 1

        # 重置当前查询
        self.current_query_activations = []
        self.total_queries += 1

    def start_new_query(self):
        """开始新查询 (sync)"""
        with self._lock:
            self._start_new_query_unsafe()

    async def async_start_new_query(self):
        """开始新查询 (async)"""
        async with self._get_async_lock():
            self._start_new_query_unsafe()

    def _get_snapshot_unsafe(self) -> MetricsSnapshot:
        """Core snapshot logic (must be called while holding lock)"""
        # 计算来源占比
        total_activations = sum(
            stats.total_activations for stats in self.stats.values()
        )

        source_ratio = defaultdict(float)
        for stats in self.stats.values():
            for source, count in stats.activations_by_source.items():
                source_ratio[source] += count

        if total_activations > 0:
            source_ratio = {
                source: count / total_activations
                for source, count in source_ratio.items()
            }

        return MetricsSnapshot(
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            total_queries=self.total_queries,
            brain_regions=dict(self.stats),
            collaboration_patterns=dict(self.collaboration_patterns),
            source_ratio=dict(source_ratio),
            activation_timeline=self.activation_timeline.copy()
        )

    def get_snapshot(self) -> MetricsSnapshot:
        """获取当前指标快照 (sync)"""
        with self._lock:
            return self._get_snapshot_unsafe()

    async def async_get_snapshot(self) -> MetricsSnapshot:
        """获取当前指标快照 (async)"""
        async with self._get_async_lock():
            return self._get_snapshot_unsafe()

    def export_to_json(self, filepath: str):
        """导出为JSON文件 (sync)"""
        snapshot = self.get_snapshot()

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot.to_dict(), f, indent=2, ensure_ascii=False)

    async def async_export_to_json(self, filepath: str):
        """导出为JSON文件 (async)"""
        snapshot = await self.async_get_snapshot()

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(snapshot.to_dict(), f, indent=2, ensure_ascii=False)

    def get_summary_report(self) -> str:
        """生成文本摘要报告 (sync)"""
        snapshot = self.get_snapshot()
        return self._build_summary_report(snapshot)

    async def async_get_summary_report(self) -> str:
        """生成文本摘要报告 (async)"""
        snapshot = await self.async_get_snapshot()
        return self._build_summary_report(snapshot)

    def _build_summary_report(self, snapshot: MetricsSnapshot) -> str:
        """Build summary report string from a snapshot."""
        lines = [
            "=" * 80,
            "多脑区激活指标报告 | Brain Region Activation Metrics",
            "=" * 80,
            f"Session ID: {self.session_id}",
            f"Timestamp: {snapshot.timestamp}",
            f"Total Queries: {self.total_queries}",
            "",
            "脑区激活统计 | Brain Region Activation Statistics:",
            "-" * 80
        ]

        # 按激活次数排序
        sorted_regions = sorted(
            snapshot.brain_regions.items(),
            key=lambda x: x[1].total_activations,
            reverse=True
        )

        for region, stats in sorted_regions:
            lines.append(f"\n【{region.upper()}】")
            lines.append(f"  总激活次数: {stats.total_activations}")
            lines.append(f"  协作次数: {stats.collaboration_count}")
            lines.append(f"  独立次数: {stats.solo_count}")
            lines.append(f"  平均处理时间: {stats.avg_processing_time_ms:.2f}ms")

            if stats.activations_by_operation:
                lines.append("  操作分布:")
                for op, count in sorted(
                    stats.activations_by_operation.items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    lines.append(f"    - {op}: {count}")

            if stats.activations_by_source:
                lines.append("  来源分布:")
                for source, count in sorted(
                    stats.activations_by_source.items(),
                    key=lambda x: x[1],
                    reverse=True
                ):
                    lines.append(f"    - {source}: {count}")

        lines.append("\n" + "-" * 80)
        lines.append("协作模式 | Collaboration Patterns:")
        lines.append("-" * 80)

        for pattern, count in sorted(
            snapshot.collaboration_patterns.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"  {pattern}: {count} 次")

        lines.append("\n" + "-" * 80)
        lines.append("输入来源占比 | Input Source Ratio:")
        lines.append("-" * 80)

        for source, ratio in sorted(
            snapshot.source_ratio.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            lines.append(f"  {source}: {ratio * 100:.1f}%")

        lines.append("\n" + "=" * 80)

        return '\n'.join(lines)

    def reset(self):
        """重置所有指标 (sync)"""
        with self._lock:
            self._reset_unsafe()

    async def async_reset(self):
        """重置所有指标 (async)"""
        async with self._get_async_lock():
            self._reset_unsafe()

    def _reset_unsafe(self):
        """Core reset logic (must be called while holding lock)"""
        self.stats = {
            region: BrainRegionStats() for region in self.BRAIN_REGIONS
        }
        self.activation_timeline = []
        self.collaboration_patterns = defaultdict(int)
        self.total_queries = 0
        self.current_query_activations = []


# 全局单例
_global_collector: Optional[BrainRegionMetricsCollector] = None
_collector_lock = threading.Lock()


def get_global_metrics_collector() -> BrainRegionMetricsCollector:
    """获取全局指标收集器"""
    global _global_collector

    if _global_collector is None:
        with _collector_lock:
            if _global_collector is None:
                _global_collector = BrainRegionMetricsCollector()

    return _global_collector
