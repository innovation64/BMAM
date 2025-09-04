"""
性能监控系统
Performance Monitoring System

实时监控系统性能和健康状态
Real-time monitoring of system performance and health
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque, defaultdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(
        self,
        sampling_interval: float = 1.0,  # 采样间隔（秒）
        history_size: int = 1000,  # 历史记录大小
        alert_thresholds: Dict[str, float] = None
    ):
        self.sampling_interval = sampling_interval
        self.history_size = history_size
        
        # 警报阈值
        self.alert_thresholds = alert_thresholds or {
            'cpu_percent': 80.0,
            'memory_percent': 85.0,
            'response_time': 5.0,  # 秒
            'error_rate': 0.1,  # 10%
            'api_failure_rate': 0.2  # 20%
        }
        
        # 性能指标历史
        self.metrics_history = {
            'cpu': deque(maxlen=history_size),
            'memory': deque(maxlen=history_size),
            'response_times': deque(maxlen=history_size),
            'request_counts': deque(maxlen=history_size),
            'error_counts': deque(maxlen=history_size),
            'cache_hits': deque(maxlen=history_size),
            'api_calls': deque(maxlen=history_size)
        }
        
        # 实时指标
        self.current_metrics = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_mb': 0,
            'active_requests': 0,
            'total_requests': 0,
            'total_errors': 0,
            'avg_response_time': 0,
            'cache_hit_rate': 0,
            'api_success_rate': 0
        }
        
        # 智能体性能
        self.agent_metrics = defaultdict(lambda: {
            'calls': 0,
            'errors': 0,
            'total_time': 0,
            'avg_time': 0
        })
        
        # 警报状态
        self.alerts = []
        self.alert_history = deque(maxlen=100)
        
        # 监控任务
        self.monitoring_task = None
        self.is_running = False
        
        logger.info("Performance monitor initialized")
    
    async def start(self):
        """启动监控"""
        if not self.is_running:
            self.is_running = True
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Performance monitoring started")
    
    async def stop(self):
        """停止监控"""
        if self.is_running:
            self.is_running = False
            if self.monitoring_task:
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
            logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self.is_running:
            try:
                # 收集系统指标
                self._collect_system_metrics()
                
                # 检查警报条件
                self._check_alerts()
                
                # 等待下次采样
                await asyncio.sleep(self.sampling_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    def _collect_system_metrics(self):
        """收集系统指标"""
        timestamp = datetime.now()
        
        # CPU和内存使用
        self.current_metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        self.current_metrics['memory_percent'] = memory.percent
        self.current_metrics['memory_mb'] = memory.used / 1024 / 1024
        
        # 记录历史
        self.metrics_history['cpu'].append({
            'timestamp': timestamp,
            'value': self.current_metrics['cpu_percent']
        })
        self.metrics_history['memory'].append({
            'timestamp': timestamp,
            'value': self.current_metrics['memory_percent']
        })
    
    def _check_alerts(self):
        """检查并触发警报"""
        current_time = datetime.now()
        new_alerts = []
        
        # CPU警报
        if self.current_metrics['cpu_percent'] > self.alert_thresholds['cpu_percent']:
            new_alerts.append({
                'type': 'HIGH_CPU',
                'severity': 'warning',
                'message': f"CPU usage is {self.current_metrics['cpu_percent']:.1f}%",
                'timestamp': current_time,
                'value': self.current_metrics['cpu_percent']
            })
        
        # 内存警报
        if self.current_metrics['memory_percent'] > self.alert_thresholds['memory_percent']:
            new_alerts.append({
                'type': 'HIGH_MEMORY',
                'severity': 'warning',
                'message': f"Memory usage is {self.current_metrics['memory_percent']:.1f}%",
                'timestamp': current_time,
                'value': self.current_metrics['memory_percent']
            })
        
        # 响应时间警报
        if self.current_metrics['avg_response_time'] > self.alert_thresholds['response_time']:
            new_alerts.append({
                'type': 'SLOW_RESPONSE',
                'severity': 'error',
                'message': f"Average response time is {self.current_metrics['avg_response_time']:.2f}s",
                'timestamp': current_time,
                'value': self.current_metrics['avg_response_time']
            })
        
        # 错误率警报
        if self.current_metrics['total_requests'] > 0:
            error_rate = self.current_metrics['total_errors'] / self.current_metrics['total_requests']
            if error_rate > self.alert_thresholds['error_rate']:
                new_alerts.append({
                    'type': 'HIGH_ERROR_RATE',
                    'severity': 'critical',
                    'message': f"Error rate is {error_rate:.1%}",
                    'timestamp': current_time,
                    'value': error_rate
                })
        
        # 更新警报
        self.alerts = new_alerts
        for alert in new_alerts:
            self.alert_history.append(alert)
            logger.warning(f"Alert: {alert['message']}")
    
    def record_request(
        self,
        duration: float,
        success: bool = True,
        agent: str = None,
        cached: bool = False
    ):
        """记录请求指标"""
        timestamp = datetime.now()
        
        # 更新总计数
        self.current_metrics['total_requests'] += 1
        if not success:
            self.current_metrics['total_errors'] += 1
        
        # 记录响应时间
        self.metrics_history['response_times'].append({
            'timestamp': timestamp,
            'duration': duration,
            'success': success,
            'cached': cached
        })
        
        # 更新平均响应时间
        recent_times = [
            m['duration'] for m in self.metrics_history['response_times']
            if m['success'] and not m['cached']
        ]
        if recent_times:
            self.current_metrics['avg_response_time'] = sum(recent_times) / len(recent_times)
        
        # 记录智能体性能
        if agent:
            self.agent_metrics[agent]['calls'] += 1
            if not success:
                self.agent_metrics[agent]['errors'] += 1
            self.agent_metrics[agent]['total_time'] += duration
            self.agent_metrics[agent]['avg_time'] = \
                self.agent_metrics[agent]['total_time'] / self.agent_metrics[agent]['calls']
    
    def record_cache_access(self, hit: bool):
        """记录缓存访问"""
        timestamp = datetime.now()
        self.metrics_history['cache_hits'].append({
            'timestamp': timestamp,
            'hit': hit
        })
        
        # 计算缓存命中率
        recent_hits = [m['hit'] for m in self.metrics_history['cache_hits']]
        if recent_hits:
            self.current_metrics['cache_hit_rate'] = sum(recent_hits) / len(recent_hits)
    
    def record_api_call(self, success: bool, service: str = 'openai'):
        """记录API调用"""
        timestamp = datetime.now()
        self.metrics_history['api_calls'].append({
            'timestamp': timestamp,
            'success': success,
            'service': service
        })
        
        # 计算API成功率
        recent_calls = [m['success'] for m in self.metrics_history['api_calls']]
        if recent_calls:
            self.current_metrics['api_success_rate'] = sum(recent_calls) / len(recent_calls)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        return {
            **self.current_metrics,
            'timestamp': datetime.now().isoformat(),
            'active_alerts': len(self.alerts),
            'alerts': self.alerts
        }
    
    def get_agent_performance(self) -> Dict[str, Any]:
        """获取智能体性能"""
        return {
            agent: {
                **metrics,
                'error_rate': metrics['errors'] / metrics['calls'] if metrics['calls'] > 0 else 0
            }
            for agent, metrics in self.agent_metrics.items()
        }
    
    def get_historical_metrics(
        self,
        metric: str,
        duration: timedelta = timedelta(minutes=5)
    ) -> List[Dict]:
        """获取历史指标"""
        if metric not in self.metrics_history:
            return []
        
        cutoff_time = datetime.now() - duration
        return [
            m for m in self.metrics_history[metric]
            if m['timestamp'] > cutoff_time
        ]
    
    def generate_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_requests': self.current_metrics['total_requests'],
                'success_rate': 1 - (self.current_metrics['total_errors'] / 
                                    max(1, self.current_metrics['total_requests'])),
                'avg_response_time': self.current_metrics['avg_response_time'],
                'cache_hit_rate': self.current_metrics['cache_hit_rate'],
                'api_success_rate': self.current_metrics['api_success_rate']
            },
            'system': {
                'cpu_percent': self.current_metrics['cpu_percent'],
                'memory_percent': self.current_metrics['memory_percent'],
                'memory_mb': self.current_metrics['memory_mb']
            },
            'agents': self.get_agent_performance(),
            'alerts': {
                'active': self.alerts,
                'history': list(self.alert_history)[-10:]  # 最近10条警报
            }
        }
        
        # 添加建议
        report['recommendations'] = self._generate_recommendations()
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # CPU建议
        if self.current_metrics['cpu_percent'] > 70:
            recommendations.append("Consider scaling up CPU resources or optimizing computation")
        
        # 内存建议
        if self.current_metrics['memory_percent'] > 75:
            recommendations.append("Memory usage is high, consider increasing memory or optimizing memory usage")
        
        # 响应时间建议
        if self.current_metrics['avg_response_time'] > 3:
            recommendations.append("Response times are slow, consider enabling caching or optimizing queries")
        
        # 缓存建议
        if self.current_metrics['cache_hit_rate'] < 0.3:
            recommendations.append("Cache hit rate is low, consider warming up cache with common queries")
        
        # API建议
        if self.current_metrics['api_success_rate'] < 0.9:
            recommendations.append("API success rate is low, check API keys and network connectivity")
        
        # 错误率建议
        if self.current_metrics['total_errors'] / max(1, self.current_metrics['total_requests']) > 0.05:
            recommendations.append("Error rate is high, review error logs and implement better error handling")
        
        return recommendations
    
    async def export_metrics(self, filepath: str):
        """导出指标到文件"""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'current_metrics': self.current_metrics,
                'agent_metrics': dict(self.agent_metrics),
                'alert_history': list(self.alert_history),
                'recent_history': {
                    key: list(values)[-100:]  # 最近100条记录
                    for key, values in self.metrics_history.items()
                }
            }
            
            with open(path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            logger.info(f"Metrics exported to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
    
    def reset_metrics(self):
        """重置指标"""
        self.current_metrics = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_mb': 0,
            'active_requests': 0,
            'total_requests': 0,
            'total_errors': 0,
            'avg_response_time': 0,
            'cache_hit_rate': 0,
            'api_success_rate': 0
        }
        
        self.agent_metrics.clear()
        
        for history in self.metrics_history.values():
            history.clear()
        
        logger.info("Metrics reset")


# 全局监控实例
performance_monitor = PerformanceMonitor()