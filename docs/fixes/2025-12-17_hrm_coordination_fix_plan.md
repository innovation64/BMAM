# HRM协调机制修复 ✅ 已完成

**日期**: 2025-12-17
**问题**: HRM协调在推理之后执行，各脑区未参与推理
**状态**: ✅ 已修复

## 问题分析

### 当前流程（有问题）

```
process_user_input:
1. Query Analysis
2. Hippocampus 检索 (k=15-20)  ← 只有海马体！
3. ToM 判断
4. 生成 Response
───────── Response 已生成 ─────────
5. Thalamus.coordinate_step    ← ❌ 太晚了！
6. AnteriorCingulate.record    ← ❌ 只是记录
7. BasalGanglia.monitor        ← ❌ 只是监控
8. Amygdala.fast_tagging       ← ❌ 只是标记
```

### 各脑区在推理中应发挥的作用

| 脑区 | HRM角色 | 应有作用 | 当前状态 |
|------|---------|----------|----------|
| **颞叶** | H module (慢) | 提供语义知识（概念性偏好） | ❌ 只在brain_retrieval中补充 |
| **杏仁核** | L module (快) | 情绪影响检索权重 | ❌ 只在后处理标记 |
| **基底节** | M module (中) | 识别行为模式 | ❌ 只在后处理监控 |
| **前额叶** | H module (慢) | 工作记忆、策略 | ⚠️ 部分使用(质量评估) |
| **海马体** | L module (快) | 情节记忆检索 | ✅ 正常使用 |
| **丘脑** | Coordinator | 协调各脑区 | ❌ 在后处理调用 |
| **扣带回** | ACT | 质量监测、停止判断 | ❌ 只记录反馈 |

### 对 PersonaMem/PrefEval 的影响

这两个数据集测试用户偏好推理：
- 需要**颞叶**的语义知识（"喜欢音乐"是概念）
- 需要**杏仁核**的情感标签（对音乐的热情）
- 需要**基底节**的行为模式（经常参加音乐活动）

但当前只有海马体参与！

## 修复方案

### 方案A：将HRM协调移到推理前（推荐）

```python
async def process_user_input(self, user_input, context):
    # 1. Query Analysis
    query_features = await self._analyze_query_features(user_input, context)

    # 🔥 2. HRM Pre-coordination: 决定激活哪些脑区
    activation_plan = None
    if self.thalamus:
        activation_plan = await self.thalamus.get_activation_plan(
            user_input,
            {'query_features': query_features}
        )

    # 🔥 3. 多脑区协同检索
    memories = []

    # 3.1 海马体检索（情节记忆）
    hippocampus_memories = await self.hippocampus.search(user_input, k=15)
    memories.extend(hippocampus_memories)

    # 3.2 颞叶补充（语义知识）- 只有在激活计划中时
    if activation_plan and activation_plan.get('temporal_lobe', {}).get('active'):
        semantic_knowledge = await self.temporal_lobe.search_memories(user_input, k=5)
        memories.extend(semantic_knowledge)

    # 3.3 杏仁核情绪增强（调整检索权重）- 只有在激活计划中时
    if activation_plan and activation_plan.get('amygdala', {}).get('active'):
        emotional_boost = await self.amygdala.get_emotional_context(user_input)
        memories = self._apply_emotional_boost(memories, emotional_boost)

    # 3.4 基底节行为模式（如果有相关技能）- 只有在激活计划中时
    if activation_plan and activation_plan.get('basal_ganglia', {}).get('active'):
        skill_patterns = await self.basal_ganglia.find_relevant_patterns(user_input)
        if skill_patterns:
            memories.extend(skill_patterns)

    # 4. 扣带回质量检查
    if self.anterior_cingulate:
        quality = await self.anterior_cingulate.evaluate_retrieval_quality(
            user_input, memories
        )
        if quality.get('should_iterate'):
            # 迭代检索
            memories = await self._iterative_retrieval(user_input, memories, quality)

    # 5. ToM 判断
    # 6. 生成 Response
    # ...
```

### 方案B：增量修复（最小改动）

在现有流程中添加关键脑区的前置调用：

1. **在检索前调用颞叶**获取相关语义知识
2. **在检索后调用杏仁核**调整记忆权重
3. **在ToM前调用扣带回**评估检索质量

### 实施优先级

1. **第一优先**：将颞叶语义检索集成到主检索流程
2. **第二优先**：将杏仁核情绪权重应用到检索结果
3. **第三优先**：将扣带回质量评估用于迭代决策
4. **第四优先**：将基底节行为模式用于偏好推理

## 修改文件

1. `src/coordination/brain_coordinator_refactored.py`
   - 在 `process_user_input` 中添加多脑区协同检索
   - 将 Thalamus 协调移到推理前

2. `src/coordination/brain_retrieval_integration.py`
   - 添加 `_amygdala_emotional_boost` 方法
   - 添加 `_basal_ganglia_pattern_search` 方法

3. `src/agents/brain_regions/amygdala_agent.py`
   - 添加 `get_emotional_context` 方法

4. `src/agents/brain_regions/basal_ganglia_agent.py`
   - 添加 `find_relevant_patterns` 方法

## 实际修复内容

### 1. `amygdala_agent.py` - 新增 `get_emotional_context()` (~100行)

```python
async def get_emotional_context(self, query: str, k: int = 5) -> Dict[str, Any]:
    """
    获取与查询相关的情绪上下文，用于在推理时提供情绪信息。
    返回: emotional_memories, dominant_emotion, emotion_distribution,
          emotional_boost_factors, query_sentiment
    """
```

### 2. `basal_ganglia_agent.py` - 新增 `find_relevant_patterns()` (~100行)

```python
async def find_relevant_patterns(self, query: str, k: int = 5) -> Dict[str, Any]:
    """
    查找与查询相关的行为模式，用于识别用户习惯偏好。
    返回: patterns, preference_indicators, habit_strength, suggested_actions
    """
```

### 3. `brain_coordinator_refactored.py` - 新增 HRM Pre-coordination (~110行)

在 `process_user_input` 的检索之后、ToM判断之前添加：

```python
# 3.1.1 Thalamus: 获取激活计划
# 3.1.2 颞叶: 语义知识补充（概念性偏好）
# 3.1.3 杏仁核: 情绪上下文（影响检索权重）
# 3.1.4 基底节: 行为模式（习惯偏好）
# 3.1.5 扣带回: 检索质量评估
```

### 修复后流程

```
process_user_input:
1. Query Analysis
2. Hippocampus 检索 (k=15-20)
3. 🔥 HRM Pre-coordination:
   - Thalamus: 激活计划
   - TemporalLobe: 语义知识补充
   - Amygdala: 情绪上下文 → 调整检索权重
   - BasalGanglia: 行为模式 → 添加偏好信息
   - AnteriorCingulate: 质量评估
4. ToM 判断
5. 生成 Response
```

## 验证

语法验证通过：
```bash
✅ amygdala_agent.py
✅ basal_ganglia_agent.py
✅ brain_coordinator_refactored.py
```

运行 PersonaMem 和 PrefEval 测试：
```bash
cd .
python3 experiments/benchmarks/personamem/test_personamem.py
python3 experiments/benchmarks/prefeval/test_prefeval.py
```
