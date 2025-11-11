# Claude #3 拆分指导：consolidation.py（重做）

## 📊 文件概况

**文件路径：** `src/agents/core/consolidation.py`
**当前行数：** 1052行
**状态：** 之前拆分失败，需要完整重做
**复杂度：** ⭐⭐⭐⭐ (高)

---

## 🎯 拆分目标

将1052行的单一文件拆分为 **7个清晰模块**。

---

## 📦 建议的模块划分

```
consolidation/
├── __init__.py                    # 导出主类
├── data_models.py                 # 数据模型 (~80行)
├── rehearsal.py                   # 复述巩固 (~180行)
├── schema_integration.py          # 模式整合 (~160行)
├── interference_resolution.py     # 干扰解决 (~150行)
├── memory_strengthening.py        # 记忆强化 (~140行)
├── sleep_consolidation.py         # 睡眠巩固 (~150行)
└── consolidation.py               # 主类 (~150行)
```

---

## 📋 详细拆分步骤

### Step 1: 清理旧文件（如果存在）
```bash
# 检查是否有旧的package
if [ -d "src/agents/core/consolidation" ]; then
    mv src/agents/core/consolidation \
       src/agents/core/consolidation.old_failed
fi

# 创建新package
mkdir -p src/agents/core/consolidation
```

### Step 2: 创建 data_models.py

```python
"""
Consolidation Data Models
记忆巩固数据模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any
from enum import Enum

class ConsolidationStage(Enum):
    """巩固阶段"""
    INITIAL = "initial"           # 初始编码
    EARLY = "early"               # 早期巩固 (0-6小时)
    LATE = "late"                 # 晚期巩固 (6-24小时)
    SYSTEMS = "systems"           # 系统巩固 (>24小时)

@dataclass
class ConsolidationJob:
    """巩固任务"""
    memory_id: str
    memory_type: str
    priority: float
    stage: ConsolidationStage
    rehearsal_count: int = 0
    interference_score: float = 0.0
    last_consolidated: datetime = field(default_factory=datetime.now)

@dataclass
class ConsolidationResult:
    """巩固结果"""
    memory_id: str
    success: bool
    strength_before: float
    strength_after: float
    operations_performed: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

# 巩固配置
CONSOLIDATION_CONFIG = {
    'rehearsal': {
        'min_interval': 300,      # 最小复述间隔（秒）
        'max_rehearsals': 5,      # 最大复述次数
        'spacing_factor': 2.0     # 间隔递增因子
    },
    'strength': {
        'initial': 0.3,           # 初始强度
        'rehearsal_boost': 0.15,  # 每次复述增加
        'decay_rate': 0.05        # 衰减率
    }
}
```

---

### Step 3: 创建 rehearsal.py

```python
"""
Rehearsal Consolidation Mixin
复述巩固模块
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RehearsalMixin:
    """复述巩固Mixin"""

    async def _rehearse_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        复述巩固记忆

        使用间隔重复算法：
        - 第1次: 立即
        - 第2次: 5分钟后
        - 第3次: 25分钟后
        - 第4次: 2小时后
        - 第5次: 1天后
        """
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}

        # 检查复述间隔
        if not self._should_rehearse_now(memory):
            return {'skipped': True, 'reason': 'Too soon for next rehearsal'}

        # 执行复述
        rehearsal_result = await self._perform_rehearsal(memory)

        # 更新记忆强度
        self._update_memory_strength(memory, rehearsal_result)

        # 记录复述
        memory.metadata['rehearsal_count'] = memory.metadata.get('rehearsal_count', 0) + 1
        memory.metadata['last_rehearsal'] = datetime.now().isoformat()

        self.db_manager.save_memory(memory)

        return rehearsal_result

    def _should_rehearse_now(self, memory) -> bool:
        """判断是否应该复述"""
        rehearsal_count = memory.metadata.get('rehearsal_count', 0)
        last_rehearsal = memory.metadata.get('last_rehearsal')

        if not last_rehearsal:
            return True

        # 计算下次复述时间
        intervals = [0, 300, 1500, 7200, 86400]  # 秒
        if rehearsal_count >= len(intervals):
            return False

        next_interval = intervals[rehearsal_count]
        last_time = datetime.fromisoformat(last_rehearsal)
        time_since = (datetime.now() - last_time).total_seconds()

        return time_since >= next_interval

    async def _perform_rehearsal(self, memory) -> Dict:
        """执行复述操作"""
        # 重新编码记忆
        rehearsed_content = await self._reactivate_and_reconsolidate(memory)

        return {
            'memory_id': memory.id,
            'rehearsal_count': memory.metadata.get('rehearsal_count', 0) + 1,
            'strength_increase': 0.15,
            'rehearsed_at': datetime.now().isoformat()
        }

    # ... 其他复述相关方法
```

---

### Step 4: 创建 schema_integration.py

```python
"""
Schema Integration Mixin
模式整合模块
"""

class SchemaIntegrationMixin:
    """模式整合Mixin"""

    async def _integrate_into_schema(self, memory_id: str) -> Dict[str, Any]:
        """
        将记忆整合到已有知识结构

        整合步骤：
        1. 识别相关schema
        2. 检查兼容性
        3. 整合新信息
        4. 更新schema连接
        """
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}

        # 识别相关schema
        relevant_schemas = self._find_relevant_schemas(memory)

        # 选择最佳schema
        best_schema = self._select_best_schema(memory, relevant_schemas)

        if best_schema:
            # 整合到已有schema
            integration_result = self._perform_schema_integration(
                memory, best_schema
            )
        else:
            # 创建新schema
            integration_result = self._create_new_schema(memory)

        return integration_result

    def _find_relevant_schemas(self, memory) -> List[Dict]:
        """查找相关的知识结构"""
        # 基于内容相似度查找
        schemas = []

        # 获取记忆的关键概念
        concepts = memory.metadata.get('entities', [])

        # 查找包含相似概念的schema
        for concept in concepts:
            related = self._search_schemas_by_concept(concept)
            schemas.extend(related)

        return schemas

    def _perform_schema_integration(self, memory, schema) -> Dict:
        """执行schema整合"""
        # 更新schema连接
        self._add_memory_to_schema(memory, schema)

        # 增强记忆强度
        memory.consolidation_level += 0.2

        return {
            'integrated': True,
            'schema_id': schema['id'],
            'strength_increase': 0.2
        }

    # ... 其他schema相关方法
```

---

### Step 5: 创建 interference_resolution.py

```python
"""
Interference Resolution Mixin
干扰解决模块
"""

class InterferenceResolutionMixin:
    """干扰解决Mixin"""

    async def _resolve_interference(self, memory_id: str) -> Dict[str, Any]:
        """
        解决记忆干扰

        干扰类型：
        - 前摄干扰：旧记忆干扰新记忆
        - 倒摄干扰：新记忆干扰旧记忆
        - 相似性干扰：相似记忆互相混淆
        """
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}

        # 检测干扰
        interferences = self._detect_interferences(memory)

        if not interferences:
            return {'interference_detected': False}

        # 解决每个干扰
        resolutions = []
        for interference in interferences:
            resolution = self._apply_interference_resolution(
                memory, interference
            )
            resolutions.append(resolution)

        return {
            'interference_detected': True,
            'count': len(interferences),
            'resolutions': resolutions
        }

    def _detect_interferences(self, memory) -> List[Dict]:
        """检测干扰记忆"""
        interferences = []

        # 查找时间接近的相似记忆
        similar_memories = self._find_similar_memories(
            memory,
            time_window=3600  # 1小时内
        )

        for similar in similar_memories:
            similarity = self._calculate_similarity(memory, similar)
            if similarity > 0.7:  # 高相似度
                interferences.append({
                    'type': 'similarity',
                    'interfering_memory': similar,
                    'similarity': similarity
                })

        return interferences

    def _apply_interference_resolution(self, memory, interference) -> Dict:
        """应用干扰解决策略"""
        strategy = self._select_resolution_strategy(interference)

        if strategy == 'differentiation':
            # 增强记忆的区分特征
            result = self._enhance_distinctiveness(memory, interference)
        elif strategy == 'consolidation':
            # 强化目标记忆
            result = self._strengthen_target_memory(memory)
        else:
            result = {'strategy': 'none'}

        return result

    # ... 其他干扰解决方法
```

---

### Step 6: 创建 memory_strengthening.py

```python
"""
Memory Strengthening Mixin
记忆强化模块
"""

class MemoryStrengtheningMixin:
    """记忆强化Mixin"""

    async def _strengthen_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        强化记忆

        强化方法：
        - 增加连接权重
        - 添加检索路径
        - 增强情绪标签
        - 提高重要性评分
        """
        memory = self.db_manager.load_memory(memory_id)
        if not memory:
            return {'error': 'Memory not found'}

        original_strength = memory.consolidation_level

        # 应用多种强化策略
        strengthening_results = []

        # 1. 连接强化
        connection_result = self._strengthen_connections(memory)
        strengthening_results.append(connection_result)

        # 2. 检索路径优化
        pathway_result = self._optimize_retrieval_pathways(memory)
        strengthening_results.append(pathway_result)

        # 3. 情绪增强
        if memory.emotion_tags:
            emotion_result = self._enhance_emotional_markers(memory)
            strengthening_results.append(emotion_result)

        # 更新巩固等级
        memory.consolidation_level = min(3.0, memory.consolidation_level + 0.3)

        self.db_manager.save_memory(memory)

        return {
            'memory_id': memory_id,
            'strength_before': original_strength,
            'strength_after': memory.consolidation_level,
            'operations': strengthening_results
        }

    # ... 其他强化方法
```

---

### Step 7: 创建 sleep_consolidation.py

```python
"""
Sleep Consolidation Mixin
睡眠巩固模块
"""

class SleepConsolidationMixin:
    """睡眠巩固Mixin - 模拟睡眠期间的记忆整合"""

    async def _simulate_sleep_consolidation(self, duration_hours: float = 8) -> Dict:
        """
        模拟睡眠期间的记忆巩固

        睡眠阶段：
        - NREM (慢波睡眠): 陈述性记忆巩固
        - REM (快速眼动): 程序性记忆和情绪整合
        """
        consolidation_results = {
            'duration_hours': duration_hours,
            'memories_consolidated': [],
            'nrem_consolidation': [],
            'rem_consolidation': []
        }

        # NREM阶段：巩固陈述性记忆
        nrem_memories = self._select_memories_for_nrem()
        for mem_id in nrem_memories:
            result = await self._nrem_consolidation(mem_id)
            consolidation_results['nrem_consolidation'].append(result)

        # REM阶段：整合情绪记忆
        rem_memories = self._select_memories_for_rem()
        for mem_id in rem_memories:
            result = await self._rem_consolidation(mem_id)
            consolidation_results['rem_consolidation'].append(result)

        return consolidation_results

    def _select_memories_for_nrem(self) -> List[str]:
        """选择需要在NREM期间巩固的记忆"""
        # 优先选择：
        # - 最近学习的重要记忆
        # - 陈述性知识
        # - 需要强化的记忆

        candidates = self.db_manager.search_memories(
            memory_type='semantic',
            limit=20
        )

        # 按重要性和新近度排序
        sorted_candidates = sorted(
            candidates,
            key=lambda m: m.importance * (1.0 / (1 + self._get_age_hours(m))),
            reverse=True
        )

        return [m.id for m in sorted_candidates[:10]]

    # ... 其他睡眠巩固方法
```

---

### Step 8: 创建主类 consolidation.py

```python
"""
Consolidation Agent
记忆巩固智能体 - 主类
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from collections import deque

from ..base import BrainAgent, AgentMessage, BrainRegion

# 导入所有Mixin
from .rehearsal import RehearsalMixin
from .schema_integration import SchemaIntegrationMixin
from .interference_resolution import InterferenceResolutionMixin
from .memory_strengthening import MemoryStrengtheningMixin
from .sleep_consolidation import SleepConsolidationMixin
from .data_models import (
    ConsolidationStage, ConsolidationJob, ConsolidationResult,
    CONSOLIDATION_CONFIG
)

logger = logging.getLogger(__name__)


class ConsolidationAgent(
    BrainAgent,
    RehearsalMixin,
    SchemaIntegrationMixin,
    InterferenceResolutionMixin,
    MemoryStrengtheningMixin,
    SleepConsolidationMixin
):
    """
    Consolidation Agent

    核心概念：记忆巩固
    对应脑区：海马体-新皮层系统
    主要功能：
    - 间隔复述
    - Schema整合
    - 干扰解决
    - 记忆强化
    - 睡眠巩固模拟
    """

    def __init__(self, db_manager=None):
        super().__init__(
            agent_id="consolidation",
            brain_region=BrainRegion.HIPPOCAMPUS,
            system_prompt="""You consolidate memories through rehearsal,
            schema integration, and sleep-like processing."""
        )

        self.db_manager = db_manager
        self.config = CONSOLIDATION_CONFIG

        # 巩固队列
        self.consolidation_queue = deque(maxlen=100)

        # 统计
        self.total_consolidations = 0
        self.successful_consolidations = 0

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process consolidation requests"""
        action = message.content.get('action')

        if action == 'rehearse':
            return await self._rehearse_memory(message.content['memory_id'])
        elif action == 'integrate_schema':
            return await self._integrate_into_schema(message.content['memory_id'])
        elif action == 'resolve_interference':
            return await self._resolve_interference(message.content['memory_id'])
        elif action == 'strengthen':
            return await self._strengthen_memory(message.content['memory_id'])
        elif action == 'sleep_consolidation':
            return await self._simulate_sleep_consolidation(
                message.content.get('duration_hours', 8)
            )

        return {'error': f'Unknown action: {action}'}
```

---

### Step 9: 创建 __init__.py

```python
"""
Consolidation Package
记忆巩固模块
"""

from .consolidation import ConsolidationAgent
from .data_models import (
    ConsolidationStage,
    ConsolidationJob,
    ConsolidationResult,
    CONSOLIDATION_CONFIG
)

__all__ = [
    'ConsolidationAgent',
    'ConsolidationStage',
    'ConsolidationJob',
    'ConsolidationResult',
    'CONSOLIDATION_CONFIG'
]
```

---

## ✅ 验证步骤

```bash
# 1. 编译测试
python3 -m py_compile src/agents/core/consolidation/*.py

# 2. 导入测试
python3 -c "from src.agents.core.consolidation import ConsolidationAgent; print('✅')"

# 3. 归档原文件
mv src/agents/core/consolidation.py \
   archived/split_originals_20251110/consolidation.py
```

---

## ⚠️ 注意事项

1. **之前失败的原因：** indentation错误，使用自动化工具时要仔细检查
2. **建议手动拆分：** 不要用自动化脚本批量生成，容易出错
3. **逐个模块验证：** 每创建一个模块就编译测试一次

---

**预计耗时：** 60-90分钟
**难度：** ⭐⭐⭐⭐ (需要避免上次的错误)
