# Claude #4 拆分指导：forgetting.py + environment_agent.py

## 📊 任务概况

**任务A：** forgetting.py (1601行) - 遗忘机制
**任务B：** environment_agent.py (908行) - 环境智能体
**总行数：** 2509行
**状态：** forgetting部分拆分未完成，需补充；environment未拆分

---

## 🎯 拆分目标

### 任务A: forgetting.py → 8个模块
### 任务B: environment_agent.py → 6个模块

---

## 📦 任务A：forgetting.py 拆分方案

### 模块结构
```
forgetting/
├── __init__.py                    # 导出主类
├── data_models.py                 # 数据模型 (~100行)
├── decay_models.py                # 衰减模型 (~250行) ✅ 已存在
├── interference_detection.py      # 干扰检测 (~180行)
├── retrieval_based_forgetting.py  # 检索诱导遗忘 (~150行)
├── context_dependent.py           # 上下文依赖 (~140行)
├── motivated_forgetting.py        # 动机性遗忘 (~120行)
└── forgetting.py                  # 主类 (~180行)
```

### Step 1: 检查已有文件
```bash
ls -la src/agents/core/forgetting/

# 可能已存在：
# - decay.py (859行)
# - 其他部分文件

# 需要：
# 1. 检查已有文件内容
# 2. 补充缺失模块
# 3. 创建统一的主类
```

### Step 2: 创建/补充缺失模块

**interference_detection.py:**
```python
"""
Interference Detection Mixin
干扰检测模块
"""

class InterferenceDetectionMixin:
    """干扰检测Mixin"""

    async def _detect_interference(self, memory_id: str) -> Dict[str, Any]:
        """
        检测记忆干扰

        干扰类型：
        - 前摄干扰：旧记忆干扰新记忆学习
        - 倒摄干扰：新记忆导致旧记忆遗忘
        - 输出干扰：检索错误记忆导致正确记忆遗忘
        """
        memory = self.db_manager.load_memory(memory_id)

        # 检测前摄干扰
        proactive = self._detect_proactive_interference(memory)

        # 检测倒摄干扰
        retroactive = self._detect_retroactive_interference(memory)

        # 检测输出干扰
        output = self._detect_output_interference(memory)

        return {
            'proactive_interference': proactive,
            'retroactive_interference': retroactive,
            'output_interference': output,
            'total_interference_score': self._calculate_total_interference(
                proactive, retroactive, output
            )
        }
```

**retrieval_based_forgetting.py:**
```python
"""
Retrieval-Based Forgetting Mixin
检索诱导遗忘模块
"""

class RetrievalBasedForgettingMixin:
    """检索诱导遗忘Mixin"""

    async def _apply_retrieval_induced_forgetting(
        self,
        retrieved_memory_id: str
    ) -> Dict[str, Any]:
        """
        应用检索诱导遗忘 (RIF)

        现象：检索某记忆会导致相关但未检索的记忆更难回忆
        """
        retrieved_memory = self.db_manager.load_memory(retrieved_memory_id)

        # 查找相关但未检索的记忆
        related_memories = self._find_related_unretreived_memories(
            retrieved_memory
        )

        # 对相关记忆应用抑制
        suppressed_memories = []
        for related_id in related_memories:
            suppression_result = self._suppress_related_memory(
                related_id,
                strength=0.1  # 轻度抑制
            )
            suppressed_memories.append(suppression_result)

        return {
            'retrieved_memory': retrieved_memory_id,
            'suppressed_count': len(suppressed_memories),
            'suppressed_memories': suppressed_memories
        }
```

---

## 📦 任务B：environment_agent.py 拆分方案

### 模块结构
```
environment_agent/
├── __init__.py                    # 导出主类
├── data_models.py                 # 数据模型 (~80行)
├── exploration_manager.py         # 探索管理 (~180行)
├── data_source_connector.py       # 数据源连接 (~150行)
├── query_processor.py             # 查询处理 (~140行)
├── result_synthesizer.py          # 结果综合 (~130行)
└── environment_agent.py           # 主类 (~150行)
```

### Step 1: 分析文件结构
```bash
# 检查environment_agent.py方法分布
grep -n "def " src/agents/environment/environment_agent.py | head -20
```

### Step 2: 创建模块

**exploration_manager.py:**
```python
"""
Exploration Manager Mixin
探索管理模块
"""

class ExplorationManagerMixin:
    """探索管理Mixin"""

    async def _plan_exploration(self, query: Dict) -> Dict[str, Any]:
        """
        规划探索策略

        探索类型：
        - 深度优先：深入单一主题
        - 广度优先：广泛探索相关主题
        - 启发式：基于重要性优先
        """
        exploration_plan = {
            'strategy': self._select_exploration_strategy(query),
            'data_sources': self._select_data_sources(query),
            'depth': self._determine_exploration_depth(query),
            'breadth': self._determine_exploration_breadth(query)
        }

        return exploration_plan

    def _select_exploration_strategy(self, query: Dict) -> str:
        """选择探索策略"""
        # 基于查询类型选择策略
        query_type = query.get('type', 'general')

        if query_type == 'specific':
            return 'depth_first'
        elif query_type == 'overview':
            return 'breadth_first'
        else:
            return 'heuristic'
```

**data_source_connector.py:**
```python
"""
Data Source Connector Mixin
数据源连接模块
"""

class DataSourceConnectorMixin:
    """数据源连接Mixin"""

    async def _connect_to_data_source(self, source_name: str) -> Dict:
        """
        连接到数据源

        支持的数据源：
        - Wikipedia
        - ArXiv
        - Google Scholar
        - Custom APIs
        """
        if source_name == 'wikipedia':
            return await self._connect_wikipedia()
        elif source_name == 'arxiv':
            return await self._connect_arxiv()
        # ... 其他数据源

    async def _connect_wikipedia(self) -> Dict:
        """连接Wikipedia API"""
        # Wikipedia API连接逻辑
        return {
            'source': 'wikipedia',
            'connected': True,
            'api_endpoint': 'https://en.wikipedia.org/w/api.php'
        }
```

---

## 📋 详细执行步骤

### 阶段1：处理 forgetting.py (60分钟)

1. **检查已有文件** (10分钟)
```bash
cd src/agents/core/forgetting
ls -la
cat __init__.py  # 检查现有导出
```

2. **补充缺失模块** (30分钟)
   - 创建 interference_detection.py
   - 创建 retrieval_based_forgetting.py
   - 创建 context_dependent.py
   - 创建 motivated_forgetting.py

3. **创建/更新主类** (15分钟)
   - 整合所有Mixin
   - 确保向后兼容

4. **测试验证** (5分钟)

---

### 阶段2：处理 environment_agent.py (45分钟)

1. **创建package目录** (5分钟)
```bash
mkdir -p src/agents/environment/environment_agent
```

2. **创建各模块** (30分钟)
   - data_models.py
   - exploration_manager.py
   - data_source_connector.py
   - query_processor.py
   - result_synthesizer.py
   - 主类 environment_agent.py

3. **创建__init__.py** (5分钟)

4. **测试验证** (5分钟)

---

## ✅ 验证步骤

### forgetting.py验证
```bash
# 编译测试
python3 -m py_compile src/agents/core/forgetting/*.py

# 导入测试
python3 -c "
from src.agents.core.forgetting import ForgettingAgent
agent = ForgettingAgent()
print('✅ forgetting导入成功')
"
```

### environment_agent.py验证
```bash
# 编译测试
python3 -m py_compile src/agents/environment/environment_agent/*.py

# 导入测试
python3 -c "
from src.agents.environment.environment_agent import EnvironmentAgent
agent = EnvironmentAgent()
print('✅ environment导入成功')
"

# 归档原文件
mv src/agents/environment/environment_agent.py \
   archived/split_originals_20251110/
```

---

## 📝 重要提示

### forgetting.py注意事项：
1. **检查已有结构：** `forgetting/decay.py` 已存在，不要重复创建
2. **补充完整：** 确保所有衰减相关方法都在合适的模块中
3. **主类整合：** 确保主类能访问所有Mixin的方法

### environment_agent.py注意事项：
1. **API依赖：** 可能依赖外部API，确保依赖正确导入
2. **异步方法：** 大部分方法可能是async，注意async/await
3. **数据源配置：** 保留所有数据源配置项

---

## 🎯 完成标准

**forgetting:**
- [ ] 8个模块完整（包括已有的decay.py）
- [ ] 所有文件编译通过
- [ ] 导入测试通过
- [ ] 主类整合所有功能

**environment_agent:**
- [ ] 6个模块完整
- [ ] 所有文件编译通过
- [ ] 导入测试通过
- [ ] 原文件归档

---

## 📊 时间分配

- **forgetting.py:** 60分钟
- **environment_agent.py:** 45分钟
- **测试验证:** 15分钟
- **总计:** 120分钟

---

**难度：** ⭐⭐⭐⭐ (两个文件，需要协调)
