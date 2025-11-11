# Claude #2 拆分指导：reflection.py（重做）

## 📊 文件概况

**文件路径：** `src/agents/core/reflection.py`
**当前行数：** 1177行
**方法总数：** 64个
**复杂度：** ⭐⭐⭐⭐⭐ (最高，方法数最多)
**状态：** 之前只拆分了pattern_analysis.py，需要完整重做

---

## 🎯 拆分目标

将1177行的单一文件拆分为 **10个清晰模块**，每个模块负责一个独立的反思功能。

---

## 📦 建议的模块划分

### 模块结构
```
reflection/
├── __init__.py                    # 导出主类
├── data_models.py                 # 数据模型 (~80行)
├── reflection_triggers.py         # 反思触发器 (~120行)
├── self_monitoring.py             # 自我监控 (~150行)
├── pattern_analysis.py            # 模式分析 (~200行) ✅ 已存在，需更新
├── insight_generation.py          # 洞察生成 (~150行)
├── meta_learning.py               # 元学习 (~140行)
├── performance_evaluation.py      # 性能评估 (~130行)
├── bias_detection.py              # 偏差检测 (~120行)
└── reflection.py                  # 主类 (~140行)
```

---

## 📋 详细拆分步骤

### Step 1: 备份已有文件
```bash
# 备份已存在的pattern_analysis.py
cp src/agents/core/reflection/pattern_analysis.py \
   src/agents/core/reflection/pattern_analysis.py.old

# 备份原文件
cp src/agents/core/reflection.py \
   src/agents/core/reflection.py.bak
```

### Step 2: 分析方法分组

**反思触发器相关 (~8方法)：**
- `_should_trigger_reflection()`
- `_evaluate_trigger_conditions()`
- `_schedule_reflection()`
- 触发条件检查相关方法

**自我监控相关 (~10方法)：**
- `_monitor_performance()`
- `_track_decision_quality()`
- `_monitor_cognitive_load()`
- `_detect_performance_drift()`
- 监控指标收集方法

**模式分析相关 (~12方法)：**
- `_analyze_behavioral_patterns()`
- `_detect_recurring_errors()`
- `_identify_success_patterns()`
- `_analyze_temporal_patterns()`
- 模式识别算法

**洞察生成相关 (~10方法)：**
- `_generate_insights()`
- `_synthesize_learnings()`
- `_formulate_recommendations()`
- `_prioritize_insights()`

**元学习相关 (~9方法)：**
- `_meta_learn_from_reflection()`
- `_update_learning_strategies()`
- `_adapt_reflection_frequency()`
- `_learn_from_mistakes()`

**性能评估相关 (~8方法)：**
- `_evaluate_overall_performance()`
- `_calculate_performance_metrics()`
- `_assess_improvement_trends()`

**偏差检测相关 (~7方法)：**
- `_detect_cognitive_biases()`
- `_identify_blind_spots()`
- `_check_confirmation_bias()`

---

### Step 3: 创建 data_models.py

```python
"""
Reflection Data Models
反思数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional

@dataclass
class ReflectionTrigger:
    """反思触发器"""
    trigger_type: str  # 'error', 'milestone', 'scheduled', 'threshold'
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    priority: float = 0.5

@dataclass
class PerformanceMetrics:
    """性能指标"""
    accuracy: float = 0.0
    response_time: float = 0.0
    error_rate: float = 0.0
    user_satisfaction: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Insight:
    """洞察"""
    insight_id: str
    insight_type: str  # 'pattern', 'bias', 'opportunity', 'risk'
    content: str
    confidence: float
    actionable: bool
    recommendations: List[str] = field(default_factory=list)
    evidence: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ReflectionCycle:
    """反思周期"""
    cycle_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    triggers: List[ReflectionTrigger] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    actions_taken: List[str] = field(default_factory=list)

# 反思配置
REFLECTION_CONFIG = {
    'frequency': {
        'error_threshold': 3,      # 错误达到3次触发反思
        'time_interval': 3600,     # 每小时定期反思
        'milestone_tasks': 10      # 每完成10个任务反思
    },
    'depth': {
        'shallow': 0.3,  # 快速反思
        'medium': 0.6,   # 中等深度
        'deep': 1.0      # 深度反思
    }
}
```

---

### Step 4: 创建 reflection_triggers.py

```python
"""
Reflection Triggers Mixin
反思触发器模块
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ReflectionTriggersMixin:
    """反思触发器Mixin"""

    def _should_trigger_reflection(self, context: Dict[str, Any]) -> bool:
        """
        判断是否应该触发反思

        触发条件：
        1. 错误次数达到阈值
        2. 到达时间间隔
        3. 达到任务里程碑
        4. 性能下降超过阈值
        5. 检测到重要模式
        """
        # 检查错误阈值
        if self._check_error_threshold():
            return True

        # 检查时间间隔
        if self._check_time_interval():
            return True

        # 检查任务里程碑
        if self._check_milestone():
            return True

        # 检查性能阈值
        if self._check_performance_threshold():
            return True

        return False

    def _check_error_threshold(self) -> bool:
        """检查错误阈值"""
        recent_errors = [e for e in self.error_history
                        if e['timestamp'] > datetime.now() - timedelta(hours=1)]
        return len(recent_errors) >= self.config['error_threshold']

    # ... 其他7个方法
```

---

### Step 5: 创建 self_monitoring.py

**功能：** 实时监控系统性能和状态

```python
"""
Self Monitoring Mixin
自我监控模块
"""

class SelfMonitoringMixin:
    """自我监控Mixin"""

    async def _monitor_performance(self) -> Dict[str, Any]:
        """
        监控整体性能

        监控维度：
        - 响应时间
        - 准确率
        - 错误率
        - 资源使用
        - 用户满意度
        """
        metrics = {
            'response_time': self._calculate_avg_response_time(),
            'accuracy': self._calculate_accuracy(),
            'error_rate': self._calculate_error_rate(),
            'resource_usage': self._get_resource_usage(),
            'user_satisfaction': self._estimate_user_satisfaction()
        }

        # 检测性能下降
        if self._detect_performance_drift(metrics):
            logger.warning("Performance drift detected")

        return metrics

    # ... 其他9个方法
```

---

### Step 6: 更新 pattern_analysis.py

**注意：** 这个文件已存在（163行），需要扩展到完整版本

```python
"""
Pattern Analysis Mixin
模式分析模块（扩展版）
"""

class PatternAnalysisMixin:
    """模式分析Mixin"""

    async def _analyze_behavioral_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """
        分析行为模式

        分析内容：
        1. 决策模式
        2. 错误模式
        3. 成功模式
        4. 时间模式
        5. 上下文模式
        """
        patterns = {
            'recurring_errors': self._detect_recurring_errors(history),
            'success_patterns': self._identify_success_patterns(history),
            'temporal_patterns': self._analyze_temporal_patterns(history),
            'context_patterns': self._analyze_context_patterns(history)
        }

        return patterns

    # ... 其他11个方法
```

---

### Step 7: 创建 insight_generation.py

```python
"""
Insight Generation Mixin
洞察生成模块
"""

class InsightGenerationMixin:
    """洞察生成Mixin"""

    async def _generate_insights(self, analysis_results: Dict) -> List[Dict]:
        """
        从分析结果生成洞察

        洞察类型：
        - 模式洞察：识别到的行为模式
        - 偏差洞察：检测到的认知偏差
        - 机会洞察：改进机会
        - 风险洞察：潜在风险
        """
        insights = []

        # 从模式生成洞察
        pattern_insights = self._synthesize_pattern_insights(
            analysis_results.get('patterns', {})
        )
        insights.extend(pattern_insights)

        # 从性能指标生成洞察
        performance_insights = self._synthesize_performance_insights(
            analysis_results.get('metrics', {})
        )
        insights.extend(performance_insights)

        # 优先级排序
        insights = self._prioritize_insights(insights)

        return insights

    # ... 其他9个方法
```

---

### Step 8: 创建 meta_learning.py

```python
"""
Meta Learning Mixin
元学习模块
"""

class MetaLearningMixin:
    """元学习Mixin - 学习如何学习"""

    async def _meta_learn_from_reflection(self, reflection_cycle: Dict) -> Dict:
        """
        从反思周期中元学习

        元学习内容：
        - 哪些反思触发器最有效
        - 哪些洞察导致了实际改进
        - 反思频率是否合适
        - 学习策略是否有效
        """
        learnings = {
            'effective_triggers': self._identify_effective_triggers(),
            'actionable_insights': self._track_actionable_insights(),
            'optimal_frequency': self._calculate_optimal_frequency(),
            'strategy_effectiveness': self._evaluate_strategies()
        }

        # 更新学习策略
        self._update_learning_strategies(learnings)

        return learnings

    # ... 其他8个方法
```

---

### Step 9: 创建 performance_evaluation.py

```python
"""
Performance Evaluation Mixin
性能评估模块
"""

class PerformanceEvaluationMixin:
    """性能评估Mixin"""

    async def _evaluate_overall_performance(self, time_window: int = 3600) -> Dict:
        """
        评估整体性能

        评估维度：
        - 任务完成质量
        - 响应速度
        - 错误率趋势
        - 改进速度
        - 学习效率
        """
        evaluation = {
            'quality_score': self._calculate_quality_score(time_window),
            'efficiency_score': self._calculate_efficiency_score(time_window),
            'reliability_score': self._calculate_reliability_score(time_window),
            'improvement_trend': self._assess_improvement_trends(time_window),
            'learning_rate': self._calculate_learning_rate()
        }

        return evaluation

    # ... 其他7个方法
```

---

### Step 10: 创建 bias_detection.py

```python
"""
Bias Detection Mixin
偏差检测模块
"""

class BiasDetectionMixin:
    """偏差检测Mixin"""

    async def _detect_cognitive_biases(self, decisions: List[Dict]) -> List[Dict]:
        """
        检测认知偏差

        检测类型：
        - 确认偏差：只关注支持性证据
        - 可得性偏差：过度依赖易获得的信息
        - 锚定效应：过度依赖初始信息
        - 过度自信：高估自己的判断
        """
        biases = []

        # 检查确认偏差
        confirmation_bias = self._check_confirmation_bias(decisions)
        if confirmation_bias['detected']:
            biases.append(confirmation_bias)

        # 检查可得性偏差
        availability_bias = self._check_availability_bias(decisions)
        if availability_bias['detected']:
            biases.append(availability_bias)

        # ... 检查其他偏差

        return biases

    # ... 其他6个方法
```

---

### Step 11: 创建主类 reflection.py

```python
"""
Reflection Agent
反思智能体 - 主类
"""

import logging
from typing import Dict, Any, List
from collections import deque
from datetime import datetime

from ..base import BrainAgent, AgentMessage, BrainRegion

# 导入所有Mixin
from .reflection_triggers import ReflectionTriggersMixin
from .self_monitoring import SelfMonitoringMixin
from .pattern_analysis import PatternAnalysisMixin
from .insight_generation import InsightGenerationMixin
from .meta_learning import MetaLearningMixin
from .performance_evaluation import PerformanceEvaluationMixin
from .bias_detection import BiasDetectionMixin
from .data_models import (
    ReflectionTrigger, PerformanceMetrics, Insight,
    ReflectionCycle, REFLECTION_CONFIG
)

logger = logging.getLogger(__name__)


class ReflectionAgent(
    BrainAgent,
    ReflectionTriggersMixin,
    SelfMonitoringMixin,
    PatternAnalysisMixin,
    InsightGenerationMixin,
    MetaLearningMixin,
    PerformanceEvaluationMixin,
    BiasDetectionMixin
):
    """
    Reflection Agent

    核心概念：元认知、自我监控
    主要功能：
    - 自我监控和性能评估
    - 模式识别和洞察生成
    - 认知偏差检测
    - 元学习和策略优化
    """

    def __init__(self):
        super().__init__(
            agent_id="reflection",
            brain_region=BrainRegion.PREFRONTAL,
            system_prompt="""You monitor system performance, detect patterns,
            generate insights, and facilitate meta-learning."""
        )

        # 配置
        self.config = REFLECTION_CONFIG

        # 反思历史
        self.reflection_cycles = deque(maxlen=50)
        self.insights = deque(maxlen=100)

        # 性能监控
        self.performance_history = deque(maxlen=200)
        self.error_history = deque(maxlen=50)

        # 统计
        self.total_reflections = 0
        self.insights_generated = 0
        self.biases_detected = 0

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process reflection requests"""
        action = message.content.get('action')

        if action == 'trigger_reflection':
            return await self._trigger_reflection_cycle(message.content)
        elif action == 'monitor_performance':
            return await self._monitor_performance()
        elif action == 'analyze_patterns':
            return await self._analyze_behavioral_patterns(message.content['history'])
        elif action == 'generate_insights':
            return await self._generate_insights(message.content['analysis'])
        elif action == 'detect_biases':
            return await self._detect_cognitive_biases(message.content['decisions'])

        return {'error': f'Unknown action: {action}'}

    async def _trigger_reflection_cycle(self, context: Dict) -> Dict:
        """触发完整的反思周期"""
        cycle_id = f"reflection_{datetime.now().isoformat()}"

        # 1. 监控性能
        metrics = await self._monitor_performance()

        # 2. 分析模式
        patterns = await self._analyze_behavioral_patterns(
            list(self.performance_history)
        )

        # 3. 生成洞察
        insights = await self._generate_insights({
            'metrics': metrics,
            'patterns': patterns
        })

        # 4. 元学习
        learnings = await self._meta_learn_from_reflection({
            'cycle_id': cycle_id,
            'insights': insights
        })

        return {
            'cycle_id': cycle_id,
            'metrics': metrics,
            'patterns': patterns,
            'insights': insights,
            'learnings': learnings
        }
```

---

### Step 12: 创建 __init__.py

```python
"""
Reflection Package
反思智能体模块
"""

from .reflection import ReflectionAgent
from .data_models import (
    ReflectionTrigger,
    PerformanceMetrics,
    Insight,
    ReflectionCycle,
    REFLECTION_CONFIG
)

__all__ = [
    'ReflectionAgent',
    'ReflectionTrigger',
    'PerformanceMetrics',
    'Insight',
    'ReflectionCycle',
    'REFLECTION_CONFIG'
]
```

---

## ✅ 验证步骤

### 1. 编译测试
```bash
python3 -m py_compile src/agents/core/reflection/*.py
```

### 2. 导入测试
```python
from src.agents.core.reflection import ReflectionAgent

agent = ReflectionAgent()
print("✅ 导入成功")
```

### 3. 清理旧文件
```bash
# 归档原文件
mv src/agents/core/reflection.py \
   archived/split_originals_20251110/reflection.py

# 删除旧的pattern_analysis备份
rm src/agents/core/reflection/pattern_analysis.py.old
```

---

## ⚠️ 重要注意事项

1. **已存在的文件：** `pattern_analysis.py` 已存在，需要扩展而不是覆盖
2. **方法数量最多：** 64个方法，需要仔细分类
3. **Mixin依赖：** 注意各Mixin间可能的方法调用关系
4. **性能监控：** 确保监控逻辑不影响系统性能
5. **向后兼容：** 保持所有公开接口不变

---

## 🎯 完成标准

- [ ] 10个模块文件全部创建/更新
- [ ] 所有文件通过编译测试
- [ ] 导入测试通过
- [ ] 原文件归档
- [ ] pattern_analysis.py 已扩展完整
- [ ] 代码行数：每个模块 100-200行

---

**预计耗时：** 90-120分钟
**难度：** ⭐⭐⭐⭐⭐ (方法数最多，需要仔细分类)
