# Claude #1 拆分指导：stress_response.py

## 📊 文件概况

**文件路径：** `src/agents/core/stress_response.py`
**当前行数：** 1101行
**方法总数：** 47个
**复杂度：** ⭐⭐⭐⭐⭐ (最高)

---

## 🎯 拆分目标

将1101行的单一文件拆分为 **8个清晰模块**，每个模块负责一个独立的功能领域。

---

## 📦 建议的模块划分

### 模块结构
```
stress_response/
├── __init__.py                    # 导出主类
├── data_models.py                 # 数据模型和状态 (~100行)
├── threat_detection.py            # 威胁检测 (~200行, 10方法)
├── emotional_processing.py        # 情绪处理 (~180行, 9方法)
├── stress_modulation.py           # 压力调节 (~200行, 11方法)
├── trauma_handler.py              # 创伤处理 (~120行, 3方法)
├── regulation_strategies.py       # 调节策略 (~120行, 5方法)
└── stress_response.py             # 主类 (~180行)
```

---

## 📋 详细拆分步骤

### Step 1: 创建package目录
```bash
mkdir -p src/agents/core/stress_response
cd src/agents/core/stress_response
```

### Step 2: 创建 data_models.py

**包含内容：**
- 情绪状态数据结构
- 威胁关键词字典
- 情绪分类字典
- HPA轴参数

**代码提取：** 原文件 L38-L82 (初始化部分的数据)

```python
"""
Stress Response Data Models
应激反应数据模型
"""

from typing import Dict, List
from collections import deque

class EmotionalState:
    """情绪状态"""
    def __init__(self):
        self.valence = 0.0      # -1 (negative) to +1 (positive)
        self.arousal = 0.3      # 0 (calm) to 1 (excited)
        self.dominance = 0.5    # 0 (submissive) to 1 (dominant)

# 威胁关键词字典
THREAT_KEYWORDS = {
    'danger': 0.8,
    'risk': 0.6,
    'threat': 0.9,
    # ... (复制完整字典)
}

# 情绪分类
EMOTION_CATEGORIES = {
    'positive': ['joy', 'happiness', 'satisfaction', ...],
    'negative': ['sadness', 'anger', 'fear', ...],
    'neutral': ['calm', 'neutral', 'indifferent', ...]
}

# HPA轴参数
HPA_DEFAULTS = {
    'cortisol_level': 0.3,
    'adrenaline_level': 0.2,
    'recovery_rate': 0.05
}
```

---

### Step 3: 创建 threat_detection.py

**功能：** 威胁检测的所有方法（10个方法）

**包含方法：**
- `_detect_threat()` - 主检测方法
- `_detect_keyword_threats()`
- `_detect_contextual_threats()`
- `_detect_pattern_threats()`
- `_detect_emotional_threats()`
- `_detect_temporal_threats()`
- `_calculate_overall_threat_score()`
- `_classify_threat_level()`
- `_update_emotional_state_from_threat()`
- `_get_threat_response_recommendation()`

**Mixin模式：**
```python
"""
Threat Detection Mixin
威胁检测功能模块
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ThreatDetectionMixin:
    """威胁检测Mixin"""

    async def _detect_threat(self, stimulus: Dict[str, Any]) -> Dict[str, Any]:
        """
        威胁检测主方法

        检测以下类型威胁：
        1. 关键词威胁
        2. 上下文威胁
        3. 模式威胁
        4. 情绪威胁
        5. 时间威胁
        """
        # 提取stimulus中的内容
        content = stimulus.get('content', '')
        context = stimulus.get('context', {})

        # 多层次威胁检测
        keyword_threat = self._detect_keyword_threats(content)
        contextual_threat = self._detect_contextual_threats(content, context)
        # ... (实现完整逻辑)

    # ... 其他9个方法
```

**从原文件提取：** 搜索所有包含 `threat` 的方法

---

### Step 4: 创建 emotional_processing.py

**功能：** 情绪处理和情绪记忆编码（9个方法）

**包含方法：**
- `_emotional_memory_encoding()` - 主编码方法
- `_regulate_emotional_state()`
- `_process_emotional_contagion()`
- `_analyze_emotional_content()`
- `_calculate_emotional_importance()`
- `_apply_emotional_suppression()`
- `_calculate_emotional_stability()`
- 其他情绪相关方法

**Mixin模式：**
```python
"""
Emotional Processing Mixin
情绪处理功能模块
"""

class EmotionalProcessingMixin:
    """情绪处理Mixin"""

    async def _emotional_memory_encoding(self, memory_data: Dict) -> Dict[str, Any]:
        """
        情绪记忆编码

        为记忆添加情绪标签和重要性权重
        """
        content = memory_data.get('content', '')

        # 分析情绪内容
        emotional_analysis = self._analyze_emotional_content(content)

        # 计算情绪重要性
        importance = self._calculate_emotional_importance(emotional_analysis)

        # ... (实现完整逻辑)

    # ... 其他8个方法
```

---

### Step 5: 创建 stress_modulation.py

**功能：** 压力调节和激素管理（11个方法）

**包含方法：**
- `_modulate_stress_response()` - 主调节方法
- `_assess_current_stress_state()`
- `_update_stress_level()`
- `_process_stressor()`
- `_update_stress_hormones()`
- `_apply_stress_recovery()`
- `_calculate_stress_effects_on_cognition()`
- `_calculate_stress_effects_on_memory()`
- `_get_stress_category()`
- `_get_stress_management_recommendations()`
- `_assess_stress_risk_factors()`

---

### Step 6: 创建 trauma_handler.py

**功能：** 创伤记忆处理（3个方法）

```python
"""
Trauma Handler Mixin
创伤处理功能模块
"""

class TraumaHandlerMixin:
    """创伤处理Mixin"""

    async def _process_traumatic_memory(self, trauma_data: Dict) -> Dict[str, Any]:
        """
        创伤记忆处理

        使用保护性措施处理创伤记忆
        """
        # 应用保护措施
        protection = self._apply_trauma_protective_measures(trauma_data)

        # 获取处理建议
        recommendations = self._get_trauma_processing_recommendations(trauma_data)

        # ... (实现完整逻辑)

    # ... 其他2个方法
```

---

### Step 7: 创建 regulation_strategies.py

**功能：** 情绪和压力调节策略（5个方法）

**包含方法：**
- `_apply_mindfulness_regulation()`
- `_apply_distraction_regulation()`
- `_apply_reappraisal_regulation()`
- `_assess_regulation_capacity()`
- 其他调节策略

---

### Step 8: 创建主类 stress_response.py

**功能：** 组合所有Mixin，提供统一接口

```python
"""
Stress Response Agent
应激反应智能体 - 主类
"""

import logging
from typing import Dict, Any
from collections import deque

from ...base import BrainAgent, AgentMessage, BrainRegion

# 导入所有Mixin
from .threat_detection import ThreatDetectionMixin
from .emotional_processing import EmotionalProcessingMixin
from .stress_modulation import StressModulationMixin
from .trauma_handler import TraumaHandlerMixin
from .regulation_strategies import RegulationStrategiesMixin
from .data_models import EmotionalState, THREAT_KEYWORDS, EMOTION_CATEGORIES

logger = logging.getLogger(__name__)


class StressResponseAgent(
    BrainAgent,
    ThreatDetectionMixin,
    EmotionalProcessingMixin,
    StressModulationMixin,
    TraumaHandlerMixin,
    RegulationStrategiesMixin
):
    """
    Stress Response Agent (Amygdala + HPA Axis)

    核心概念：应激
    对应脑区：杏仁核（Amygdala）+ HPA轴
    主要功能：威胁检测，情绪记忆编码，应激调节
    """

    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="stress_response",
            brain_region=BrainRegion.AMYGDALA,
            system_prompt="""You detect threats and encode emotional memories with appropriate intensity.
            Modulate stress responses and regulate their impact on memory formation."""
        )

        # External services
        self.db_manager = db_manager

        # 初始化状态
        self.emotional_state = EmotionalState()
        self.stress_level = 0.3

        # 初始化buffers
        self.threat_history = deque(maxlen=20)
        self.emotional_buffer = deque(maxlen=15)
        self.stress_events = deque(maxlen=10)

        # HPA axis simulation
        self.cortisol_level = 0.3
        self.adrenaline_level = 0.2
        self.recovery_rate = 0.05

        # Statistics
        self.threats_detected = 0
        self.emotional_memories_encoded = 0
        self.stress_responses_triggered = 0

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process stress response requests"""
        action = message.content.get('action')

        if action == 'threat_detection':
            return await self._detect_threat(message.content['stimulus'])
        elif action == 'emotional_encoding':
            return await self._emotional_memory_encoding(message.content['memory_data'])
        elif action == 'stress_modulation':
            return await self._modulate_stress_response(message.content.get('stressor'))
        elif action == 'trauma_processing':
            return await self._process_traumatic_memory(message.content['trauma_data'])
        elif action == 'emotional_regulation':
            return await self._regulate_emotional_state(message.content['regulation_strategy'])

        return {'error': f'Unknown action: {action}'}
```

---

### Step 9: 创建 __init__.py

```python
"""
Stress Response Package
应激反应智能体模块
"""

from .stress_response import StressResponseAgent
from .data_models import EmotionalState, THREAT_KEYWORDS, EMOTION_CATEGORIES

__all__ = [
    'StressResponseAgent',
    'EmotionalState',
    'THREAT_KEYWORDS',
    'EMOTION_CATEGORIES'
]
```

---

## ✅ 验证步骤

### 1. 编译测试
```bash
python3 -m py_compile src/agents/core/stress_response/*.py
```

### 2. 导入测试
```python
from src.agents.core.stress_response import StressResponseAgent

agent = StressResponseAgent()
print("✅ 导入成功")
```

### 3. 更新引用
搜索项目中所有引用 `stress_response` 的地方：
```bash
grep -r "from.*stress_response import" src --include="*.py"
```

确保所有导入保持向后兼容。

---

## ⚠️ 重要注意事项

1. **保持self引用：** 所有Mixin方法都要能访问 `self.stress_level`, `self.emotional_state` 等属性
2. **Logger导入：** 每个模块都要导入logger
3. **类型提示：** 保持所有类型提示完整
4. **文档字符串：** 保留所有docstring
5. **向后兼容：** 通过`__init__.py`确保原有导入方式不变

---

## 🎯 完成标准

- [ ] 8个模块文件全部创建
- [ ] 所有文件通过编译测试
- [ ] 导入测试通过
- [ ] 原文件备份到archived/
- [ ] 更新所有引用位置
- [ ] 代码行数：每个模块 100-200行

---

## 📝 提交清单

完成后提交以下内容：
1. 新创建的 `stress_response/` 目录
2. 归档的原文件路径
3. 测试验证截图
4. 修改的其他文件列表（如果有引用更新）

---

**预计耗时：** 60-90分钟
**难度：** ⭐⭐⭐⭐⭐ (需要仔细处理Mixin间的依赖)
