# BMAM 四数据集最佳备份详细对比分析

---

## 1. 数据集最高分汇总

| 数据集 | 最高分 | 备份时间 | 备份文件 |
|--------|--------|----------|----------|
| **LoCoMo** | **75.88%** (199题) | 12-21 01:51 | `BMAM_storyarc_integration_20251221_015100.tar.gz` |
| **LongMemEval** | **86.67%** (30题) | 12-21 01:51 | `BMAM_storyarc_integration_20251221_015100.tar.gz` |
| **PrefEval** | **60%** | 12-22 17:42 | `BMAM_pre_ideation_fix_20251222_174202.tar.gz` |
| **PersonaMem** | **52%** | 12-24 12:30 | `BMAM_llm_rerank_fix_52pct_20251224_123000.tar.gz` |

**关键发现**: LoCoMo 和 LongMemEval 最佳成绩来自同一个备份！

---

## 2. 三个最佳备份版本概览

由于 LoCoMo 和 LongMemEval 共用同一备份，实际上只有 **3 个不同的最佳备份版本**：

| 版本 | 备份文件 | 代码行数 | 目标数据集 |
|------|----------|----------|------------|
| **V1 (12-21)** | `BMAM_storyarc_integration_20251221_015100.tar.gz` | brain_coordinator: 2,599 行<br>persona_memory: 360 行 | LoCoMo 75%<br>LongMemEval 86.67% |
| **V2 (12-22)** | `BMAM_pre_ideation_fix_20251222_174202.tar.gz` | brain_coordinator: 2,825 行 (+226)<br>persona_memory: 439 行 (+79) | PrefEval 60% |
| **V3 (12-24)** | `BMAM_llm_rerank_fix_52pct_20251224_123000.tar.gz` | brain_coordinator: 2,930 行 (+105)<br>persona_memory: 711 行 (+272) | PersonaMem 52% |

---

## 3. V1 → V2 代码差异详解 (LoCoMo/LongMemEval → PrefEval)

### 3.1 新增功能: PreferenceAwareRetrieval

```python
# V2 新增 (brain_coordinator_refactored.py)
# 🔥 2025-12-21: Initialize PreferenceAwareRetrieval (PersonaMem/PrefEval优化)
logger.info("🔧 [16/16] Initializing PreferenceAwareRetrieval...")
try:
    from ..memory.preference_aware_retrieval import get_preference_aware_retrieval
    self.preference_aware_retrieval = get_preference_aware_retrieval(
        memory_system=self.memory_system,
        preference_boost_weight=0.3,
        enable_contrastive_learning=True,
        enable_metamemory=True,
        enable_silent_engram=True
    )
    self._feature_status['preference_aware_retrieval'] = True
except Exception as e:
    self.preference_aware_retrieval = None
```

**作用**: 偏好感知检索，根据用户偏好动态调整检索权重

---

### 3.2 新增功能: UserPreferenceExtractor 增强版

```python
# V2 新增 (brain_coordinator_refactored.py)
# 🎯 2025-12-22: 使用增强版 UserPreferenceExtractor 提取偏好
if self.persona_memory and content and speaker:
    speaker_lower = speaker.lower()
    if speaker_lower == 'user' or 'user:' in content.lower()[:20]:
        try:
            # 🔥 使用增强版提取器而不是简单关键词匹配
            if self._feature_status.get('preference_extraction') and self.preference_extractor:
                extracted = self.preference_extractor.extract_from_text(content)
                total_prefs = sum(len(v) for v in extracted.values())

                if total_prefs > 0:
                    # 结构化存储到 PersonaMemoryAgent
                    for pref_type, prefs in extracted.items():
                        for pref in prefs:
                            await self.persona_memory.store_persona({
                                'content': f"User {pref_type}: {pref}",
                                'category': pref_type,
                                'importance': self._get_preference_importance(pref_type),
                                'metadata': {
                                    'source': 'conversation_shaping',
                                    'preference_type': pref_type,
                                    'preference_value': pref,
                                    'structured_category': self._get_structured_category(pref_type),
                                    'timestamp': str(timestamp),
                                    'speaker': speaker
                                }
                            })
```

**作用**: 自动提取用户偏好并结构化存储，支持 PrefEval 的偏好感知需求

---

### 3.3 V1 vs V2 功能矩阵

| 功能 | V1 (LoCoMo/LongMemEval) | V2 (PrefEval) |
|------|-------------------------|---------------|
| StoryArc V2.0 时间线 | ✅ | ✅ |
| 混合检索 (BM25+Vector+KG) | ✅ | ✅ |
| HRM 五脑区协调 | ✅ | ✅ |
| PreferenceAwareRetrieval | ❌ | ✅ |
| UserPreferenceExtractor | ❌ | ✅ |
| PersonaMemory 结构化存储 | ❌ | ✅ |
| 偏好分类 (likes/interests/facts) | ❌ | ✅ |

---

## 4. V2 → V3 代码差异详解 (PrefEval → PersonaMem)

### 4.1 新增功能: 脑区绑定到 MemoryCoordinator

```python
# V3 新增 (brain_coordinator_refactored.py)
# 🔥 2025-12-23: 绑定脑区到 MemoryCoordinator（跨脑区协作检索需要）
# 必须在 MemoryCoordinator 创建后立即执行，才能让 cross_region_retrieval 使用所有脑区
self.memory_coordinator.persona_memory = self.persona_memory
self.memory_coordinator.amygdala = self.amygdala
self.memory_coordinator.prefrontal_storage = self.prefrontal_agent
self.memory_coordinator.basal_ganglia = self.basal_ganglia
logger.info("   🎯 Brain regions bound: PersonaMemory, Amygdala, Prefrontal, BasalGanglia")
```

**作用**: 启用跨脑区协作检索，让 MemoryCoordinator 可以访问所有脑区

---

### 4.2 新增功能: user_id 参数支持

```python
# V3 新增 (brain_coordinator_refactored.py)
async def store_memory_with_timestamp(
    self,
    content: str,
    # ... 其他参数 ...
    inherited_event_time: datetime = None,  # 🔥 2025-12-16: 继承的事件时间
    user_id: str = "default"  # 🔥 2025-12-24: 用户标识
) -> Dict[str, Any]:
    # ...
    metadata = {
        'user_id': user_id,  # 🔥 2025-12-24: 传入 user_id
        'original_statement': content[:500]  # 🔥 2025-12-24: 保存原始用户陈述
    }
```

**作用**: 支持多用户隔离，避免不同用户的记忆混淆

---

### 4.3 新增功能: 评估模式增强检索

```python
# V3 新增 (brain_coordinator_refactored.py)
# 🔥 2025-12-24: 评估模式下检索更多 persona 记忆
# PersonaMem 问题可能与用户偏好语义距离远（如问事件但需要知道用户喜好）
# 因此需要检索更多记忆以覆盖各种偏好类型
retrieval_k = 20 if is_evaluation_mode else 8

# 🔥 2025-12-24: 获取 user_id 用于过滤特定用户的记忆
eval_user_id = context.get('user_id') or context.get('persona_user_id')

# 从 PersonaMemory 检索偏好和事实
persona_result = await self.persona_memory.retrieve_persona(
    user_input, k=retrieval_k, user_id=eval_user_id
)
```

**作用**: 评估模式下大幅增加检索数量，提高召回率

---

### 4.4 新增功能: recent_persona 补充检索

```python
# V3 新增 (brain_coordinator_refactored.py)
# 🔥 2025-12-24: 评估模式下额外检索最近的 persona 记忆
# 补充语义检索可能遗漏的重要偏好
if is_evaluation_mode:
    recent_result = await self.persona_memory.recent_persona(
        limit=10, user_id=eval_user_id
    )
    recent_mems = recent_result.get('memories', [])
    # 合并，去重
    existing_ids = {pm.get('memory', {}).get('id') for pm in persona_memories if isinstance(pm, dict)}
    for rm in recent_mems:
        rm_id = rm.get('id') if isinstance(rm, dict) else None
        if rm_id not in existing_ids:
            # 包装成与语义检索一致的格式
            persona_memories.append({'memory': rm, 'retrieval_confidence': 0.5})
```

**作用**: 补充语义检索可能遗漏的最近偏好

---

### 4.5 新增功能: reasoning_chain fallback

```python
# V3 新增 (brain_coordinator_refactored.py)
# 🔥 2025-12-22 FIX: reasoning_chain fallback to orchestrator (not conversation)
# 当选择reasoning_chain但没有结果时，应该用orchestrator，而非conversation
elif (answer_path == 'reasoning_chain' and not has_reasoning and
      self.capability_orchestrator and self.capability_analyzer):
    logger.info(f"🔄 Dynamic route → reasoning_chain unavailable, using CapabilityOrchestrator")
    try:
        cap_analysis = await self.capability_analyzer.analyze(user_input, context)
        capabilities = cap_analysis.get('capabilities', [])
        execution_plan = cap_analysis.get('execution_plan', 'Default plan')

        orchestrator_result = await self.capability_orchestrator.execute(
            query=user_input,
            capabilities=capabilities,
            memories=memories,
            execution_plan=execution_plan,
            supplementary_context=None
        )
        response = orchestrator_result.get('answer', 'I understand.')
```

**作用**: 当 reasoning_chain 不可用时，fallback 到 CapabilityOrchestrator 而非直接降级

---

### 4.6 PersonaMemory 模块变更

```python
# V3 新增 (persona_memory.py)
async def retrieve_persona(self, query: str, k: int = 5, user_id: str = None) -> Dict[str, Any]:
    """Public wrapper for retrieving persona memories.
    Args:
        query: 检索查询
        k: 返回结果数量
        user_id: 用户ID (可选，用于过滤特定用户的记忆)
    """
    return await self._retrieve_persona_memories(query, k, user_id)

async def recent_persona(self, limit: int = 5, user_id: str = None) -> Dict[str, Any]:
    """Public wrapper for recent persona memories.
    Args:
        limit: 返回结果数量
        user_id: 用户ID (可选，用于过滤特定用户的记忆)
    """
    return await self._get_recent_persona_memories(limit, user_id)
```

**user_id 过滤逻辑**:
```python
# 🔥 2025-12-24: user_id 过滤 - 但允许 'default' 用户的记忆也被检索
# 因为早期存储的记忆可能没有设置 user_id
if user_id:
    mem_user_id = metadata.get('user_id', 'default')
    # 允许匹配目标用户或 'default' 用户的记忆
    if mem_user_id != user_id and mem_user_id != 'default':
        continue
```

---

### 4.7 V2 vs V3 功能矩阵

| 功能 | V2 (PrefEval) | V3 (PersonaMem) |
|------|---------------|-----------------|
| PreferenceAwareRetrieval | ✅ | ✅ |
| UserPreferenceExtractor | ✅ | ✅ |
| 脑区绑定到 MemoryCoordinator | ❌ | ✅ |
| user_id 参数支持 | ❌ | ✅ |
| original_statement 保存 | ❌ | ✅ |
| 评估模式增强检索 (k=20) | ❌ | ✅ |
| recent_persona 补充检索 | ❌ | ✅ |
| reasoning_chain fallback | ❌ | ✅ |
| persona_memory user_id 过滤 | ❌ | ✅ |

---

## 5. 完整功能矩阵对比

| 功能 | V1 (12-21)<br>LoCoMo/LongMemEval | V2 (12-22)<br>PrefEval | V3 (12-24)<br>PersonaMem |
|------|-----------------------------------|------------------------|---------------------------|
| **基础架构** | | | |
| StoryArc V2.0 时间线 | ✅ | ✅ | ✅ |
| 混合检索 (BM25+Vector+KG) | ✅ | ✅ | ✅ |
| HRM 五脑区协调 | ✅ | ✅ | ✅ |
| 记忆巩固管道 | ✅ | ✅ | ✅ |
| **偏好感知** | | | |
| PreferenceAwareRetrieval | ❌ | ✅ | ✅ |
| UserPreferenceExtractor | ❌ | ✅ | ✅ |
| PersonaMemory 结构化存储 | ❌ | ✅ | ✅ |
| **PersonaMem 增强** | | | |
| 脑区绑定到 MemoryCoordinator | ❌ | ❌ | ✅ |
| user_id 参数支持 | ❌ | ❌ | ✅ |
| original_statement 保存 | ❌ | ❌ | ✅ |
| 评估模式增强检索 (k=20) | ❌ | ❌ | ✅ |
| recent_persona 补充检索 | ❌ | ❌ | ✅ |
| reasoning_chain fallback | ❌ | ❌ | ✅ |
| persona_memory user_id 过滤 | ❌ | ❌ | ✅ |
| **其他** | | | |
| ToM 对抗检测 | ✅ | ✅ | ✅ (后禁用) |

---

## 6. 各数据集最佳版本特征总结

### 6.1 LoCoMo & LongMemEval (V1)

**核心优势**:
- StoryArc V2.0 时间线推理 → LongMemEval temporal-reasoning 86.67%
- 混合检索 (BM25 + Vector + KG) → 全面的记忆召回
- HRM 五脑区协调 → 多时间尺度记忆整合

**为何最佳**: 时间推理能力强，适合 LoCoMo 的时间相关问题和 LongMemEval 的 temporal-reasoning

---

### 6.2 PrefEval (V2)

**核心优势**:
- PreferenceAwareRetrieval → 偏好感知检索
- UserPreferenceExtractor → 自动偏好提取
- PersonaMemory 结构化存储 → 偏好分类存储

**为何最佳**: 偏好提取和感知能力强，适合 PrefEval 的偏好一致性测试

---

### 6.3 PersonaMem (V3)

**核心优势**:
- user_id 隔离 → 多用户记忆不混淆
- original_statement 保存 → 精确回忆原始陈述
- 评估模式增强检索 (k=20) → 高召回率
- recent_persona 补充 → 语义遗漏补救

**为何最佳**: 精确记忆回忆和用户隔离能力强，适合 PersonaMem 的精确偏好测试

---

## 7. 版本选择建议

| 使用场景 | 推荐版本 | 原因 |
|----------|----------|------|
| 时间推理任务 | V1 | StoryArc 时间线最完整 |
| 偏好感知回复 | V2 | 偏好提取 + 感知检索 |
| 精确记忆回忆 | V3 | user_id 隔离 + original_statement |
| 多用户隔离 | V3 | user_id 参数支持 |
| 长对话记忆 | V1 | temporal-reasoning 86.67% |

---

## 8. 备份文件清单

| 备份 | 大小 | 日期 | 数据集 | 最佳成绩 |
|------|------|------|--------|----------|
| `BMAM_storyarc_integration_20251221_015100.tar.gz` | 1.8GB | 12-21 | LoCoMo<br>LongMemEval | 75.88%<br>86.67% |
| `BMAM_pre_ideation_fix_20251222_174202.tar.gz` | 1.0GB | 12-22 | PrefEval | 60% |
| `BMAM_llm_rerank_fix_52pct_20251224_123000.tar.gz` | 184MB | 12-24 | PersonaMem | 52% |

---

*分析时间: 2025-12-25*
*代码对比基于实际备份文件 diff 分析*
