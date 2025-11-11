"""
Reflection Package
反思智能体模块

这个package包含了重构后的ReflectionAgent，使用Mixin架构将
原始的1177行单一文件拆分为10个清晰的模块。

模块组成：
- data_models.py: 数据模型和配置
- reflection_triggers.py: 反思触发器逻辑
- self_monitoring.py: 自我监控
- pattern_analysis.py: 模式分析
- insight_generation.py: 洞察生成
- meta_learning.py: 元学习
- performance_evaluation.py: 性能评估
- bias_detection.py: 偏差检测
- reflection.py: 主类（组合所有Mixin）
"""

from .reflection import ReflectionAgent
from .data_models import (
    ReflectionTrigger,
    PerformanceMetrics,
    Insight,
    ReflectionCycle,
    REFLECTION_CONFIG
)

# 导出所有Mixin（如果需要单独使用）
from .reflection_triggers import ReflectionTriggersMixin
from .self_monitoring import SelfMonitoringMixin
from .pattern_analysis import PatternAnalysisMixin
from .insight_generation import InsightGenerationMixin
from .meta_learning import MetaLearningMixin
from .performance_evaluation import PerformanceEvaluationMixin
from .bias_detection import BiasDetectionMixin

__all__ = [
    # 主类
    'ReflectionAgent',

    # 数据模型
    'ReflectionTrigger',
    'PerformanceMetrics',
    'Insight',
    'ReflectionCycle',
    'REFLECTION_CONFIG',

    # Mixins（可选导出）
    'ReflectionTriggersMixin',
    'SelfMonitoringMixin',
    'PatternAnalysisMixin',
    'InsightGenerationMixin',
    'MetaLearningMixin',
    'PerformanceEvaluationMixin',
    'BiasDetectionMixin',
]

# 版本信息
__version__ = '2.0.0'
__author__ = 'BMAM Team'
__description__ = 'Reflection Agent with Mixin Architecture'
