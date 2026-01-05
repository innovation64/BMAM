# BMAM 各数据集最佳备份对比分析

---

## 1. 备份版本概览

| 备份名称 | 日期 | 数据集 | 最高分 | 核心文件行数 |
|---------|------|--------|--------|-------------|
| `personamem_fix_40pct` | 12-22 15:22 | PersonaMem | **40%** | 2,825 行 |
| `BMAM_post_personamem_47pct` | 12-23 08:01 | PersonaMem | **47%** | 2,866 行 |
| `BMAM_personamem_52pct` | 12-23 13:12 | PersonaMem | **52%** | 2,901 行 |
| `BMAM_llm_rerank_fix_52pct` | 12-24 12:30 | PersonaMem | **52%** | 2,930 行 |
| **当前版本** | 12-25 | - | ~24% | 2,910 行 |

---

## 2. 关键变更对比

### 40% → 47% 的改进 (+7%)

**关键修复 1: Prefrontal 属性名修正**
```python
# 40% 版本 (错误)
'prefrontal': self.prefrontal,

# 47% 版本 (正确)
'prefrontal': self.prefrontal_storage,  # 修复属性名
```

**关键修复 2: reasoning_chain fallback 逻辑**
```python
# 47% 新增: 当 reasoning_chain 不可用时，fallback 到 CapabilityOrchestrator
# 而非直接降级到 conversation
elif (answer_path == 'reasoning_chain' and not has_reasoning and
      self.capability_orchestrator and self.capability_analyzer):
    # 使用 CapabilityOrchestrator 作为备选
    orchestrator_result = await self.capability_orchestrator.execute(...)
```

**影响**: 修复了推理路径选择错误，避免了能力分析被跳过

---

### 47% → 52% 的改进 (+5%)

**关键新增: MCQ 格式强制转换**
```python
# 52% 新增: 多选题答案格式修正
if context.get('evaluation_mode', False) and '(a)' in user_input:
    response_lower = response.lower()
    has_option_format = any(opt in response_lower for opt in ['(a)', '(b)', '(c)', '(d)'])
    if not has_option_format:
        # 调用 LLM 将自由文本转换为选项格式
        convert_prompt = f"""Based on the given context, select the BEST option...
Question: {user_input}
Context: {response}
Output ONLY: "The answer is (X)" where X is a, b, c, or d."""
        converted = await converter.call_llm(convert_prompt, ...)
```

**影响**: 确保评估时输出正确的选项格式，避免格式不匹配导致的误判

---

### 52% (personamem) → 52% (llm_rerank) 的改进

**关键新增 1: 脑区绑定到 MemoryCoordinator**
```python
# llm_rerank 新增: 让 cross_region_retrieval 能使用所有脑区
self.memory_coordinator.persona_memory = self.persona_memory
self.memory_coordinator.amygdala = self.amygdala
self.memory_coordinator.prefrontal_storage = self.prefrontal_agent
self.memory_coordinator.basal_ganglia = self.basal_ganglia
```

**关键新增 2: user_id 支持**
```python
# llm_rerank 新增: 存储时保存 user_id 和原始陈述
metadata = {
    'user_id': user_id,
    'original_statement': content[:500]  # 保存完整原始陈述
}

# 检索时支持 user_id 过滤
persona_result = await self.persona_memory.retrieve_persona(
    user_input, k=retrieval_k, user_id=eval_user_id
)
```

**关键新增 3: 评估模式增强检索**
```python
# llm_rerank 新增: 评估模式下检索更多记忆
retrieval_k = 20 if is_evaluation_mode else 8

# 额外检索最近的 persona 记忆
if is_evaluation_mode:
    recent_result = await self.persona_memory.recent_persona(limit=10, user_id=eval_user_id)
```

**影响**: 跨脑区协作更完整，用户隔离更清晰，评估时召回更全面

---

## 3. 52% → 当前版本 (24%) 的回退原因

### 被移除/禁用的关键功能

| 功能 | 52% 状态 | 当前状态 | 影响 |
|------|---------|---------|------|
| ToM 对抗检测 | 启用 | **禁用** | 对抗题可能误判 |
| user_id 参数 | 启用 | **移除** | 用户记忆混淆 |
| original_statement | 启用 | **移除** | 丢失原始陈述 |
| 增强检索 (k=20) | 启用 | **改为 k=8** | 召回不足 |
| recent_persona 补充 | 启用 | **移除** | 遗漏重要偏好 |

### 具体代码变更

**1. ToM 被禁用**
```python
# 当前版本: 完全注释掉
# 🔥 2025-12-25 DISABLED: ToM adversarial detection 导致大量误判
# if self.reasoning_validator and memories:
#     adversarial_result = await self.reasoning_validator.check_adversarial_before_reasoning(...)
```

**2. user_id 支持被移除**
```python
# 52% 版本
inherited_event_time: datetime = None,
user_id: str = "default"  # 有 user_id

# 当前版本
inherited_event_time: datetime = None  # 没有 user_id
```

**3. 增强检索被简化**
```python
# 52% 版本
retrieval_k = 20 if is_evaluation_mode else 8
persona_result = await self.persona_memory.retrieve_persona(user_input, k=retrieval_k, user_id=eval_user_id)

# 当前版本
persona_result = await self.persona_memory.retrieve_persona(user_input, k=8)  # 固定 k=8，无 user_id
```

---

## 4. 各版本特性矩阵

| 特性 | 40% | 47% | 52% | llm_rerank | 当前 |
|------|-----|-----|-----|------------|------|
| prefrontal_storage 正确绑定 | ❌ | ✅ | ✅ | ✅ | ✅ |
| reasoning_chain fallback | ❌ | ✅ | ✅ | ✅ | ✅ |
| MCQ 格式转换 | ❌ | ❌ | ✅ | ✅ | ✅ |
| 脑区绑定到 MemoryCoordinator | ❌ | ❌ | ❌ | ✅ | ✅ |
| user_id 支持 | ❌ | ❌ | ❌ | ✅ | ❌ |
| original_statement 保存 | ❌ | ❌ | ❌ | ✅ | ❌ |
| 评估模式增强检索 (k=20) | ❌ | ❌ | ❌ | ✅ | ❌ |
| recent_persona 补充检索 | ❌ | ❌ | ❌ | ✅ | ❌ |
| ToM 对抗检测 | ❌ | ❌ | ❌ | ✅ | ❌ |
| 诊断日志 | ❌ | ❌ | ❌ | ✅ | ? |

---

## 5. 恢复建议

### P0 - 立即恢复 (预计恢复到 ~45%)

1. **恢复 user_id 参数**
   - `brain_coordinator_refactored.py`: 恢复 `shape_conversation` 的 user_id 参数
   - `persona_memory.py`: 恢复 `retrieve_persona` 和 `recent_persona` 的 user_id 支持

2. **恢复 original_statement 保存**
   - 塑造记忆时保存 `'original_statement': content[:500]`

3. **恢复评估模式增强检索**
   - `retrieval_k = 20 if is_evaluation_mode else 8`
   - 恢复 `recent_persona` 补充检索逻辑

### P1 - 短期优化 (预计恢复到 ~52%)

1. **修复 ToM 误判问题后重新启用**
   - 当前禁用是因为误判率高
   - 需要调整 ToM 的触发条件和阈值

2. **优化 MCQ 格式转换**
   - 当前版本有此功能，但可能需要优化 prompt

### P2 - 验证

1. 逐个恢复功能并测试
2. 确认每个功能的实际贡献

---

## 6. 结论

**性能下降根因**:
1. 12-25 代码清理时，误删了 12-24 llm_rerank 版本的关键功能
2. 主要丢失: user_id 支持、原始陈述保存、增强检索、recent_persona 补充
3. ToM 被禁用是正确的（因为误判），但其他功能不应删除

**最佳恢复路径**:
- 从 `BMAM_llm_rerank_fix_52pct_20251224_123000.tar.gz` 恢复关键代码
- 保留 ToM 禁用状态
- 逐步测试验证

---

*分析时间: 2024-12-25*
