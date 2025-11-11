# Claude #5 拆分指导：memory_distortion.py + reasoning_validator.py

## 📊 任务概况

**任务A：** memory_distortion.py (823行) - 记忆扭曲
**任务B：** reasoning_validator.py (850行) - 推理验证
**总行数：** 1673行
**复杂度：** ⭐⭐⭐ (中等，两个中等大小文件)

---

## 🎯 拆分目标

### 任务A: memory_distortion.py → 6个模块
### 任务B: reasoning_validator.py → 5个模块

---

## 📦 任务A：memory_distortion.py 拆分方案

### 模块结构
```
memory_distortion/
├── __init__.py                    # 导出主类
├── data_models.py                 # 数据模型 (~70行)
├── distortion_detection.py        # 扭曲检测 (~160行)
├── reconstruction_errors.py       # 重构错误 (~140行)
├── source_confusion.py            # 来源混淆 (~130行)
├── false_memory.py                # 虚假记忆 (~140行)
└── memory_distortion.py           # 主类 (~140行)
```

### 详细步骤

#### Step 1: 创建 data_models.py
```python
"""
Memory Distortion Data Models
记忆扭曲数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any
from enum import Enum

class DistortionType(Enum):
    """扭曲类型"""
    RECONSTRUCTION = "reconstruction"     # 重构错误
    SOURCE_CONFUSION = "source_confusion" # 来源混淆
    FALSE_MEMORY = "false_memory"         # 虚假记忆
    SCHEMA_DISTORTION = "schema"          # Schema影响
    EMOTIONAL_BIAS = "emotional"          # 情绪偏差
    TEMPORAL_SHIFT = "temporal"           # 时间位移

@dataclass
class DistortionIndicator:
    """扭曲指标"""
    indicator_type: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    severity: float = 0.0  # 0-1

@dataclass
class DistortionReport:
    """扭曲报告"""
    memory_id: str
    distortion_detected: bool
    distortion_types: List[DistortionType] = field(default_factory=list)
    indicators: List[DistortionIndicator] = field(default_factory=list)
    reliability_score: float = 1.0  # 1.0 = 完全可靠
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

# 扭曲检测阈值
DISTORTION_THRESHOLDS = {
    'reconstruction_count': 3,     # 重构次数
    'age_days': 30,                # 记忆年龄
    'source_reliability': 0.5,     # 来源可靠性
    'emotional_intensity': 0.7     # 情绪强度
}
```

#### Step 2: 创建 distortion_detection.py
```python
"""
Distortion Detection Mixin
扭曲检测模块
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class DistortionDetectionMixin:
    """扭曲检测Mixin"""

    async def _detect_distortions(self, memory_id: str) -> Dict[str, Any]:
        """
        检测记忆扭曲

        检测维度：
        1. 重构次数过多
        2. 来源可靠性低
        3. 情绪强度高
        4. 与其他记忆冲突
        5. Schema不一致
        """
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}

        indicators = []

        # 1. 检查重构错误
        reconstruction_indicator = self._check_reconstruction_errors(memory)
        if reconstruction_indicator['detected']:
            indicators.append(reconstruction_indicator)

        # 2. 检查来源混淆
        source_indicator = self._check_source_confusion(memory)
        if source_indicator['detected']:
            indicators.append(source_indicator)

        # 3. 检查虚假记忆特征
        false_memory_indicator = self._check_false_memory_markers(memory)
        if false_memory_indicator['detected']:
            indicators.append(false_memory_indicator)

        # 4. 检查Schema一致性
        schema_indicator = await self._check_schema_consistency(memory)
        if schema_indicator['confidence'] < 0.5:
            indicators.append(schema_indicator)

        # 计算整体可靠性
        reliability = self._calculate_reliability_score(indicators)

        return {
            'memory_id': memory_id,
            'distortion_detected': len(indicators) > 0,
            'indicators': indicators,
            'reliability_score': reliability,
            'recommendations': self._generate_recommendations(indicators)
        }

    def _calculate_reliability_score(self, indicators: List[Dict]) -> float:
        """计算记忆可靠性评分"""
        if not indicators:
            return 1.0

        # 每个指标降低可靠性
        reliability = 1.0
        for indicator in indicators:
            severity = indicator.get('severity', 0.1)
            reliability -= severity * 0.15

        return max(0.0, reliability)

    # ... 其他检测方法
```

#### Step 3: 创建 reconstruction_errors.py
```python
"""
Reconstruction Errors Mixin
重构错误模块
"""

class ReconstructionErrorsMixin:
    """重构错误Mixin"""

    def _check_reconstruction_errors(self, memory) -> Dict:
        """
        检查重构错误

        重构错误类型：
        - 细节丢失
        - 细节添加
        - 细节替换
        - 顺序错误
        """
        reconstruction_count = memory.metadata.get('reconstruction_count', 0)

        if reconstruction_count == 0:
            return {'detected': False}

        # 高频重构容易引入错误
        if reconstruction_count > self.thresholds['reconstruction_count']:
            return {
                'detected': True,
                'type': 'high_reconstruction',
                'count': reconstruction_count,
                'severity': min(1.0, reconstruction_count / 10),
                'evidence': [
                    f"Memory reconstructed {reconstruction_count} times",
                    "High risk of detail distortion"
                ]
            }

        return {'detected': False}

    async def _estimate_reconstruction_accuracy(self, memory) -> float:
        """估计重构准确度"""
        # 基于重构次数和时间估计
        reconstruction_count = memory.metadata.get('reconstruction_count', 0)
        age_days = self._calculate_memory_age_days(memory)

        # 准确度随重构次数和时间衰减
        accuracy = 1.0
        accuracy -= reconstruction_count * 0.05  # 每次重构降低5%
        accuracy -= age_days * 0.001             # 每天降低0.1%

        return max(0.0, accuracy)
```

#### Step 4: 创建 source_confusion.py
```python
"""
Source Confusion Mixin
来源混淆模块
"""

class SourceConfusionMixin:
    """来源混淆Mixin"""

    def _check_source_confusion(self, memory) -> Dict:
        """
        检查来源混淆

        来源混淆：
        - 内部vs外部来源混淆
        - 时间来源混淆
        - 说话者混淆
        """
        source_reliability = memory.source_reliability

        if source_reliability < self.thresholds['source_reliability']:
            return {
                'detected': True,
                'type': 'low_source_reliability',
                'reliability': source_reliability,
                'severity': 1.0 - source_reliability,
                'evidence': [
                    f"Source reliability: {source_reliability:.2f}",
                    "Risk of source confusion"
                ]
            }

        # 检查多来源冲突
        if self._has_conflicting_sources(memory):
            return {
                'detected': True,
                'type': 'conflicting_sources',
                'severity': 0.6,
                'evidence': ["Multiple conflicting source attributions"]
            }

        return {'detected': False}

    def _has_conflicting_sources(self, memory) -> bool:
        """检查是否有冲突的来源归因"""
        sources = memory.metadata.get('sources', [])
        return len(set(sources)) > 2  # 超过2个不同来源
```

#### Step 5: 创建 false_memory.py
```python
"""
False Memory Mixin
虚假记忆模块
"""

class FalseMemoryMixin:
    """虚假记忆Mixin"""

    def _check_false_memory_markers(self, memory) -> Dict:
        """
        检查虚假记忆标记

        虚假记忆特征：
        - 缺乏感知细节
        - 过度一般化
        - 与已知事实冲突
        - 来源监控失败
        """
        markers = []

        # 1. 检查感知细节
        if self._lacks_perceptual_details(memory):
            markers.append('lacks_perceptual_details')

        # 2. 检查一致性
        if not self._is_internally_consistent(memory):
            markers.append('internally_inconsistent')

        # 3. 检查与事实冲突
        if self._conflicts_with_facts(memory):
            markers.append('conflicts_with_facts')

        if len(markers) >= 2:
            return {
                'detected': True,
                'type': 'false_memory_markers',
                'markers': markers,
                'severity': len(markers) / 3,
                'evidence': [f"Detected {len(markers)} false memory markers"]
            }

        return {'detected': False}

    def _lacks_perceptual_details(self, memory) -> bool:
        """检查是否缺乏感知细节"""
        content = memory.content.lower()

        # 真实记忆通常包含感知细节
        perceptual_words = ['saw', 'heard', 'felt', 'smelled', 'tasted',
                           '看到', '听到', '感觉', '闻到']

        return not any(word in content for word in perceptual_words)
```

#### Step 6: 创建主类 memory_distortion.py
```python
"""
Memory Distortion Agent
记忆扭曲检测智能体 - 主类
"""

import logging
from typing import Dict, Any
from datetime import datetime

from ..base import BrainAgent, AgentMessage, BrainRegion

from .distortion_detection import DistortionDetectionMixin
from .reconstruction_errors import ReconstructionErrorsMixin
from .source_confusion import SourceConfusionMixin
from .false_memory import FalseMemoryMixin
from .data_models import (
    DistortionType, DistortionIndicator, DistortionReport,
    DISTORTION_THRESHOLDS
)

logger = logging.getLogger(__name__)


class MemoryDistortionAgent(
    BrainAgent,
    DistortionDetectionMixin,
    ReconstructionErrorsMixin,
    SourceConfusionMixin,
    FalseMemoryMixin
):
    """
    Memory Distortion Agent

    核心概念：记忆可靠性
    主要功能：
    - 扭曲检测
    - 可靠性评估
    - 虚假记忆识别
    """

    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="memory_distortion",
            brain_region=BrainRegion.PREFRONTAL,
            system_prompt="""You detect memory distortions and assess reliability."""
        )

        self.db_manager = db_manager
        self.thresholds = DISTORTION_THRESHOLDS

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process distortion detection requests"""
        action = message.content.get('action')

        if action == 'detect_distortions':
            return await self._detect_distortions(message.content['memory_id'])
        elif action == 'assess_reliability':
            return await self._assess_memory_reliability(message.content['memory_id'])

        return {'error': f'Unknown action: {action}'}
```

---

## 📦 任务B：reasoning_validator.py 拆分方案

### 模块结构
```
reasoning_validator/
├── __init__.py                    # 导出主类
├── data_models.py                 # 数据模型 (~70行)
├── logic_validator.py             # 逻辑验证 (~180行)
├── consistency_checker.py         # 一致性检查 (~160行)
├── fact_checker.py                # 事实检查 (~150行)
└── reasoning_validator.py         # 主类 (~150行)
```

### 详细步骤

#### Step 1: 创建 logic_validator.py
```python
"""
Logic Validator Mixin
逻辑验证模块
"""

class LogicValidatorMixin:
    """逻辑验证Mixin"""

    async def _validate_logic(self, reasoning: Dict) -> Dict[str, Any]:
        """
        验证推理逻辑

        检查：
        - 前提是否支持结论
        - 是否有逻辑谬误
        - 推理步骤是否完整
        """
        premises = reasoning.get('premises', [])
        conclusion = reasoning.get('conclusion', '')

        # 检查逻辑连贯性
        coherence = self._check_logical_coherence(premises, conclusion)

        # 检测逻辑谬误
        fallacies = self._detect_logical_fallacies(reasoning)

        # 检查推理链
        chain_validity = self._validate_reasoning_chain(reasoning)

        return {
            'coherence': coherence,
            'fallacies': fallacies,
            'chain_validity': chain_validity,
            'overall_validity': self._calculate_validity_score(
                coherence, fallacies, chain_validity
            )
        }

    def _detect_logical_fallacies(self, reasoning: Dict) -> List[Dict]:
        """检测逻辑谬误"""
        fallacies = []

        # 检测常见谬误
        if self._check_ad_hominem(reasoning):
            fallacies.append({'type': 'ad_hominem', 'severity': 0.8})

        if self._check_hasty_generalization(reasoning):
            fallacies.append({'type': 'hasty_generalization', 'severity': 0.6})

        if self._check_false_dilemma(reasoning):
            fallacies.append({'type': 'false_dilemma', 'severity': 0.7})

        return fallacies
```

#### Step 2: 创建 consistency_checker.py
```python
"""
Consistency Checker Mixin
一致性检查模块
"""

class ConsistencyCheckerMixin:
    """一致性检查Mixin"""

    async def _check_consistency(self, reasoning: Dict) -> Dict[str, Any]:
        """
        检查推理一致性

        检查类型：
        - 内部一致性：推理内部是否自洽
        - 外部一致性：与已知知识是否一致
        - 时间一致性：时间顺序是否合理
        """
        # 内部一致性
        internal = self._check_internal_consistency(reasoning)

        # 外部一致性
        external = await self._check_external_consistency(reasoning)

        # 时间一致性
        temporal = self._check_temporal_consistency(reasoning)

        return {
            'internal_consistency': internal,
            'external_consistency': external,
            'temporal_consistency': temporal,
            'overall_consistency': (internal + external + temporal) / 3
        }
```

---

## ✅ 验证步骤

### 任务A验证
```bash
# 编译
python3 -m py_compile src/agents/core/memory_distortion/*.py

# 导入
python3 -c "from src.agents.core.memory_distortion import MemoryDistortionAgent; print('✅')"

# 归档
mv src/agents/core/memory_distortion.py archived/split_originals_20251110/
```

### 任务B验证
```bash
# 编译
python3 -m py_compile src/agents/core/reasoning_validator/*.py

# 导入
python3 -c "from src.agents.core.reasoning_validator import ReasoningValidator; print('✅')"

# 归档
mv src/agents/core/reasoning_validator.py archived/split_originals_20251110/
```

---

## 📊 时间分配

- **memory_distortion.py:** 45分钟
- **reasoning_validator.py:** 40分钟
- **测试验证:** 15分钟
- **总计:** 100分钟

---

## 🎯 完成标准

**memory_distortion:**
- [ ] 6个模块完整
- [ ] 所有文件编译通过
- [ ] 导入测试通过
- [ ] 原文件归档

**reasoning_validator:**
- [ ] 5个模块完整
- [ ] 所有文件编译通过
- [ ] 导入测试通过
- [ ] 原文件归档

---

**难度：** ⭐⭐⭐ (中等，两个文件但规模较小)
