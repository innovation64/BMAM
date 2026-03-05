"""
Performance Profiler for BMAM System
性能分析工具

用于追踪和分析系统各组件的性能指标
"""

import time
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TimingRecord:
    """单次操作的计时记录"""
    operation: str
    start_time: float
    end_time: float
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationStats:
    """操作统计信息"""
    operation: str
    count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0

    def update(self, duration_ms: float):
        """更新统计信息"""
        self.count += 1
        self.total_duration_ms += duration_ms
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        self.avg_duration_ms = self.total_duration_ms / self.count

    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation': self.operation,
            'count': self.count,
            'total_ms': round(self.total_duration_ms, 2),
            'avg_ms': round(self.avg_duration_ms, 2),
            'min_ms': round(self.min_duration_ms, 2),
            'max_ms': round(self.max_duration_ms, 2),
        }


class PerformanceProfiler:
    """
    性能分析器

    用法:
        profiler = PerformanceProfiler()

        # 方式1: 使用上下文管理器
        with profiler.track("operation_name"):
            # do something

        # 方式2: 手动记录
        profiler.start("operation_name")
        # do something
        profiler.end("operation_name")

        # 获取报告
        report = profiler.get_report()
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.records: List[TimingRecord] = []
        self.stats: Dict[str, OperationStats] = defaultdict(lambda: OperationStats(""))
        self.active_timers: Dict[str, float] = {}
        self.session_start = time.time()

        # 特殊计数器
        self.counters: Dict[str, int] = defaultdict(int)

    def start(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """开始计时"""
        if not self.enabled:
            return operation

        timer_key = f"{operation}_{id(metadata) if metadata else ''}"
        self.active_timers[timer_key] = time.time()
        return timer_key

    def end(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        """结束计时并记录"""
        if not self.enabled:
            return 0.0

        timer_key = f"{operation}_{id(metadata) if metadata else ''}"
        if timer_key not in self.active_timers:
            logger.warning(f"⚠️  Timer not found for operation: {operation}")
            return 0.0

        start_time = self.active_timers.pop(timer_key)
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000

        # 记录详细信息
        record = TimingRecord(
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        self.records.append(record)

        # 更新统计信息
        if operation not in self.stats:
            self.stats[operation] = OperationStats(operation)
        self.stats[operation].update(duration_ms)

        return duration_ms

    def track(self, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """上下文管理器方式追踪性能"""
        return _TimerContext(self, operation, metadata)

    def increment(self, counter_name: str, value: int = 1):
        """增加计数器"""
        if self.enabled:
            self.counters[counter_name] += value

    def get_counter(self, counter_name: str) -> int:
        """获取计数器值"""
        return self.counters.get(counter_name, 0)

    def get_stats(self, operation: Optional[str] = None) -> Dict[str, OperationStats]:
        """获取统计信息"""
        if operation:
            return {operation: self.stats.get(operation, OperationStats(operation))}
        return dict(self.stats)

    def get_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        total_duration = (time.time() - self.session_start) * 1000

        # 按总耗时排序
        sorted_stats = sorted(
            self.stats.values(),
            key=lambda x: x.total_duration_ms,
            reverse=True
        )

        return {
            'session': {
                'start_time': datetime.fromtimestamp(self.session_start).isoformat(),
                'total_duration_ms': round(total_duration, 2),
                'total_records': len(self.records),
            },
            'operations': [s.to_dict() for s in sorted_stats],
            'counters': dict(self.counters),
            'top_bottlenecks': self._identify_bottlenecks(sorted_stats[:10]),
        }

    def _identify_bottlenecks(self, top_stats: List[OperationStats]) -> List[Dict[str, Any]]:
        """识别性能瓶颈"""
        bottlenecks = []
        total_time = sum(s.total_duration_ms for s in self.stats.values())

        for stat in top_stats:
            percentage = (stat.total_duration_ms / total_time * 100) if total_time > 0 else 0
            bottlenecks.append({
                'operation': stat.operation,
                'total_ms': round(stat.total_duration_ms, 2),
                'percentage': round(percentage, 2),
                'count': stat.count,
                'avg_ms': round(stat.avg_duration_ms, 2),
            })

        return bottlenecks

    def save_report(self, filepath: str):
        """保存报告到文件"""
        report = self.get_report()
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"📊 Performance report saved to: {filepath}")

    def print_summary(self):
        """打印性能摘要"""
        report = self.get_report()
        print("\n" + "="*80)
        print("📊 PERFORMANCE SUMMARY")
        print("="*80)

        print(f"\n⏱️  Session Duration: {report['session']['total_duration_ms']:.2f} ms")
        print(f"📝 Total Records: {report['session']['total_records']}")

        print("\n🔥 Top 10 Bottlenecks:")
        print(f"{'Operation':<40} {'Total (ms)':<12} {'%':<8} {'Count':<8} {'Avg (ms)':<10}")
        print("-"*80)
        for bottleneck in report['top_bottlenecks'][:10]:
            print(f"{bottleneck['operation']:<40} {bottleneck['total_ms']:<12.2f} "
                  f"{bottleneck['percentage']:<8.2f} {bottleneck['count']:<8} "
                  f"{bottleneck['avg_ms']:<10.2f}")

        if report['counters']:
            print("\n📊 Counters:")
            for name, value in sorted(report['counters'].items()):
                print(f"   {name}: {value}")

        print("="*80 + "\n")

    def reset(self):
        """重置所有统计信息"""
        self.records.clear()
        self.stats.clear()
        self.active_timers.clear()
        self.counters.clear()
        self.session_start = time.time()


class _TimerContext:
    """计时器上下文管理器"""

    def __init__(self, profiler: PerformanceProfiler, operation: str, metadata: Optional[Dict[str, Any]] = None):
        self.profiler = profiler
        self.operation = operation
        self.metadata = metadata
        self.timer_key = None

    def __enter__(self):
        self.timer_key = self.profiler.start(self.operation, self.metadata)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.end(self.operation, self.metadata)


# 全局性能分析器实例
_global_profiler: Optional[PerformanceProfiler] = None


def get_profiler() -> PerformanceProfiler:
    """获取全局性能分析器"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler(enabled=True)
    return _global_profiler


def enable_profiling():
    """启用性能分析"""
    get_profiler().enabled = True


def disable_profiling():
    """禁用性能分析"""
    get_profiler().enabled = False


def reset_profiler():
    """重置全局性能分析器"""
    global _global_profiler
    _global_profiler = None


def profile(operation_name: Optional[str] = None):
    """
    Decorator to automatically profile a function/method

    Usage:
        @profile("my_operation")
        async def my_function():
            pass

        # Or auto-detect name
        @profile()
        async def my_function():
            pass
    """
    import functools

    def decorator(func):
        nonlocal operation_name
        if operation_name is None:
            operation_name = f"{func.__module__}.{func.__qualname__}"

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            profiler = get_profiler()
            with profiler.track(operation_name):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            profiler = get_profiler()
            with profiler.track(operation_name):
                return func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
