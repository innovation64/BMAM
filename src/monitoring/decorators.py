"""
Metrics Decorators for Brain Region Agents
脑区指标装饰器

Provides easy-to-use decorators for automatic metrics tracking.
"""

import time
import functools
from typing import Callable, Optional, Any
from .brain_region_metrics import get_global_metrics_collector


def track_brain_region_activation(
    region: str,
    operation: Optional[str] = None,
    input_source: str = "user_query",
    output_type: str = "default"
):
    """
    装饰器：自动追踪脑区激活

    Usage:
        @track_brain_region_activation('hippocampus', operation='retrieve')
        async def retrieve_memories(self, query: str):
            ...

    Args:
        region: 脑区名称
        operation: 操作名称（默认使用函数名）
        input_source: 输入来源
        output_type: 输出类型
    """
    def decorator(func: Callable) -> Callable:
        op_name = operation or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_global_metrics_collector()
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)

                # 计算处理时间
                processing_time_ms = (time.time() - start_time) * 1000

                # 记录激活 (use async version to avoid blocking event loop)
                metadata = {
                    'success': True,
                    'result_type': type(result).__name__
                }
                if isinstance(result, (list, dict)):
                    metadata['result_count'] = len(result)

                await collector.async_record_activation(
                    region=region,
                    operation=op_name,
                    input_source=input_source,
                    output_type=output_type,
                    processing_time_ms=processing_time_ms,
                    metadata=metadata
                )

                return result

            except Exception as e:
                # 即使失败也记录
                processing_time_ms = (time.time() - start_time) * 1000
                await collector.async_record_activation(
                    region=region,
                    operation=op_name,
                    input_source=input_source,
                    output_type='error',
                    processing_time_ms=processing_time_ms,
                    metadata={'success': False, 'error': str(e)}
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = get_global_metrics_collector()
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                processing_time_ms = (time.time() - start_time) * 1000

                metadata = {
                    'success': True,
                    'result_type': type(result).__name__
                }
                if isinstance(result, (list, dict)):
                    metadata['result_count'] = len(result)

                collector.record_activation(
                    region=region,
                    operation=op_name,
                    input_source=input_source,
                    output_type=output_type,
                    processing_time_ms=processing_time_ms,
                    metadata=metadata
                )

                return result

            except Exception as e:
                processing_time_ms = (time.time() - start_time) * 1000
                collector.record_activation(
                    region=region,
                    operation=op_name,
                    input_source=input_source,
                    output_type='error',
                    processing_time_ms=processing_time_ms,
                    metadata={'success': False, 'error': str(e)}
                )
                raise

        # 根据函数类型返回不同的wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def track_collaboration(*regions: str):
    """
    装饰器：追踪多个脑区的协作

    Usage:
        @track_collaboration('hippocampus', 'prefrontal')
        async def complex_reasoning(self, query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            collector = get_global_metrics_collector()

            # 记录协作开始 (use async version to avoid blocking event loop)
            for region in regions:
                await collector.async_record_activation(
                    region=region,
                    operation=f'collaboration_{func.__name__}',
                    input_source='collaboration',
                    output_type='collaborative_result'
                )

            # 执行函数
            result = await func(*args, **kwargs)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            collector = get_global_metrics_collector()

            for region in regions:
                collector.record_activation(
                    region=region,
                    operation=f'collaboration_{func.__name__}',
                    input_source='collaboration',
                    output_type='collaborative_result'
                )

            result = func(*args, **kwargs)
            return result

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
