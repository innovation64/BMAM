# Adaptive Config 修复方案 - 真正使用软权重

## 问题根源

**当前实现的致命缺陷**：定义了8个软权重，但只用了2个，并且还是用硬阈值判断（if > 0.3），完全违背软权重的初衷。

```python
# ❌ 错误示范 - 软权重退化成硬阈值
if adaptive_weights.preference_extraction_weight > 0.3:
    # True/False 二元判断，完全没用到0.2-0.8的连续值
```

## 修复方案：端到端软权重集成

### 1. Preference Extraction (偏好提取)

**当前**: `preference_extraction_weight` 只用于 if 判断
**修复**: 将权重传递到实际提取逻辑

```python
# src/coordination/brain_coordinator_refactored.py:981

# ❌ 当前代码
if self.preference_extractor and adaptive_weights.preference_extraction_weight > 0.3:
    extracted = self.preference_extractor.extract_from_text(content)

# ✅ 修复后 - 真正使用权重值
if self.preference_extractor:
    # 权重越高，召回阈值越低（更激进），召回数量越多
    extraction_threshold = 0.85 - 0.2 * adaptive_weights.preference_extraction_weight  # 0.65-0.85
    max_candidates = max(1, int(5 * adaptive_weights.preference_extraction_weight))    # 1-4个

    extracted = self.preference_extractor.extract_from_text(
        content,
        confidence_threshold=extraction_threshold,
        max_items=max_candidates
    )
```

**影响**:
- `preference_extraction_weight=0.2` → threshold=0.81, max=1 (保守提取)
- `preference_extraction_weight=0.8` → threshold=0.69, max=4 (激进提取)

---

### 2. Temporal Reasoning (时间推理)

**当前**: `temporal_reasoning_weight` 完全未使用
**修复**: 用于调整时间线检索和StoryArc权重

```python
# src/coordination/brain_coordinator_refactored.py ~1100行 (StoryArc检索)

# ✅ 新增 - 使用 temporal_reasoning_weight
if self.storyarc_manager:
    # 权重越高，时间线检索的K值越大
    timeline_k = max(3, int(8 * adaptive_weights.temporal_reasoning_weight))  # 3-8条时间线

    timeline_memories = self.storyarc_manager.retrieve_relevant_arcs(
        query=user_input,
        top_k=timeline_k,
        temporal_weight=adaptive_weights.temporal_reasoning_weight  # 传递权重
    )

    # 时间推理权重影响时间线记忆的融合比例
    all_memories.extend([
        (mem, score * adaptive_weights.temporal_reasoning_weight)
        for mem, score in timeline_memories
    ])
```

**影响**:
- `temporal_reasoning_weight=0.3` → 最低权重，时间线检索K=3
- `temporal_reasoning_weight=1.0` → 最高权重，时间线检索K=8

---

### 3. Persona Retrieval (身份检索)

**当前**: `persona_weight` 和 `persona_retrieval_k` 未使用
**修复**: 动态调整Persona检索的K值和融合权重

```python
# src/coordination/brain_coordinator_refactored.py:1946

# ❌ 当前代码
if self.persona_memory and adaptive_weights.preference_extraction_weight > 0.3:
    persona_memories = self.persona_memory.retrieve(
        query=user_input,
        user_id=user_id,
        top_k=20  # 硬编码K值
    )

# ✅ 修复后 - 使用 persona_weight 和 persona_retrieval_k
if self.persona_memory:
    # 使用动态K值 (基于查询特征计算的K)
    persona_k = adaptive_weights.persona_retrieval_k  # 5-15 动态范围

    persona_memories = self.persona_memory.retrieve(
        query=user_input,
        user_id=user_id,
        top_k=persona_k
    )

    # 使用 persona_weight 调整融合权重
    weighted_persona = [
        (mem, score * adaptive_weights.persona_weight)
        for mem, score in persona_memories
    ]
```

**影响**:
- `identity_score=0.0` → persona_k=5, persona_weight=0.4 (低权重)
- `identity_score=1.0` → persona_k=15, persona_weight=1.0 (高权重)

---

### 4. Memory Fusion (记忆融合)

**当前**: `semantic_weight` 和 `episodic_weight` 完全未使用
**修复**: 在记忆融合阶段使用权重调整不同类型记忆的比例

```python
# src/coordination/brain_coordinator_refactored.py ~1200行 (记忆融合)

# ✅ 新增 - 使用 semantic_weight 和 episodic_weight
def fuse_memories(self, episodic_mems, semantic_mems, persona_mems, adaptive_weights):
    """融合不同类型的记忆，使用软权重调整比例"""

    fused = []

    # 情景记忆 - 使用 episodic_weight
    for mem, score in episodic_mems:
        fused.append((mem, score * adaptive_weights.episodic_weight))

    # 语义记忆 - 使用 semantic_weight
    for mem, score in semantic_mems:
        fused.append((mem, score * adaptive_weights.semantic_weight))

    # Persona记忆 - 使用 persona_weight
    for mem, score in persona_mems:
        fused.append((mem, score * adaptive_weights.persona_weight))

    # 重排序
    fused.sort(key=lambda x: x[1], reverse=True)
    return fused[:20]  # 返回Top20
```

**影响**:
- 事实性查询 (`factual_score=1.0`): semantic_weight=1.0, episodic_weight=0.7 → 偏向语义记忆
- 时间推理查询 (`temporal_score=1.0`): episodic_weight=1.0, semantic_weight=0.5 → 偏向情景记忆

---

### 5. Preference Retrieval Boost (偏好检索增强)

**当前**: `preference_retrieval_boost` 只用于 if 判断
**修复**: 用于调整偏好记忆的重排序权重

```python
# src/coordination/brain_coordinator_refactored.py:1139

# ❌ 当前代码
if self.preference_aware_retrieval and result.memories and adaptive_weights.preference_retrieval_boost > 0.1:
    # 硬阈值判断，只要>0.1就全力增强

# ✅ 修复后 - 使用实际权重值
if self.preference_aware_retrieval and result.memories:
    # 权重越高，偏好记忆的boost越强
    boosted_memories = self.preference_aware_retrieval.rerank_by_preference(
        memories=result.memories,
        user_preferences=preference_context,
        boost_factor=1.0 + adaptive_weights.preference_retrieval_boost  # 1.0-1.3倍boost
    )
```

**影响**:
- `preference_score=0.0` → boost_factor=1.0 (无增强)
- `preference_score=1.0` → boost_factor=1.3 (30%增强)

---

## 修复后的权重使用矩阵

| 权重变量 | 当前使用 | 修复后使用位置 | 影响范围 |
|---------|---------|--------------|---------|
| `preference_extraction_weight` | if > 0.3 | 提取阈值, 召回数量 | 0.65-0.85 threshold, 1-4 items |
| `preference_retrieval_boost` | if > 0.1 | 重排序boost因子 | 1.0-1.3倍权重 |
| `temporal_reasoning_weight` | ❌ 未使用 | 时间线检索K, 融合权重 | K=3-8, weight=0.3-1.0 |
| `persona_weight` | ❌ 未使用 | Persona记忆融合权重 | 0.4-1.0倍权重 |
| `identity_reasoning_weight` | ❌ 未使用 | 身份推理模块权重 | 0.2-1.0倍权重 |
| `persona_retrieval_k` | ❌ 未使用 | Persona检索K值 | 5-15动态K |
| `episodic_retrieval_k` | ❌ 未使用 | 情景记忆检索K值 | 5-15动态K |
| `semantic_weight` | ❌ 未使用 | 语义记忆融合权重 | 0.5-1.0倍权重 |
| `episodic_weight` | ❌ 未使用 | 情景记忆融合权重 | 0.7-1.0倍权重 |

**修复前**: 9个权重中只有2个被使用，且用硬阈值判断 (22%利用率)
**修复后**: 9个权重全部使用，且都参与实际计算 (100%利用率)

---

## 修复优先级

### P0 - 立即修复 (影响最大)
1. ✅ **preference_extraction_weight** → 真正用权重值控制提取强度
2. ✅ **temporal_reasoning_weight** → 集成到StoryArc时间线检索
3. ✅ **persona_retrieval_k** → 使用动态K值替代硬编码

### P1 - 次要修复
4. ✅ **semantic_weight / episodic_weight** → 记忆融合层权重
5. ✅ **preference_retrieval_boost** → 使用实际boost因子

### P2 - 增强功能
6. ✅ **identity_reasoning_weight** → 身份推理模块集成
7. ✅ **episodic_retrieval_k** → 情景记忆动态K

---

## 预期效果

修复后，Adaptive Config的软权重将真正发挥作用：

- **LoCoMo** (时间推理): `temporal_reasoning_weight=0.9` → 强化时间线，抑制偏好提取
- **LongMemEval** (时间推理): `temporal_reasoning_weight=0.95` → 最大化时间推理权重
- **PrefEval** (偏好查询): `preference_extraction_weight=0.8` → 激进偏好提取
- **PersonaMem** (身份回忆): `persona_retrieval_k=15, persona_weight=1.0` → 最大化Persona检索

**消融实验设计**:
1. **Baseline**: Task-Aware Config (硬开关)
2. **Adaptive-V1**: 当前失败的软权重 (2/9权重, 硬阈值)
3. **Adaptive-V2**: 修复后的软权重 (9/9权重, 端到端集成) ← 目标方案

预期 Adaptive-V2 > Task-Aware > Adaptive-V1

---

## 实施计划

1. **Step 1**: 修复 `brain_coordinator_refactored.py` 中的权重使用 (2小时)
2. **Step 2**: 清理数据，重新运行4数据集测试 (5小时)
3. **Step 3**: 对比 Task-Aware vs Adaptive-V2 效果
4. **Step 4**: 撰写消融实验章节，证明软权重优势

**关键论证**:
- Task-Aware的硬开关虽然有效，但缺乏灵活性（二元决策）
- Adaptive-V2的软权重提供连续控制，在边界case上表现更好
- 消融实验证明端到端权重集成的重要性
