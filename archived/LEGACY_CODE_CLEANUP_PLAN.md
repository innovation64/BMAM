# Legacy Code Cleanup Plan

## 问题诊断

你说得对!系统中存在大量旧代码,导致:
1. **调用路径混乱** - 多个处理入口,不确定哪个被使用
2. **功能冲突** - 新的CapabilityOrchestrator vs 旧的BrainNetwork迭代
3. **测试失败** - 旧测试调用旧代码,无法验证新功能

---

## 当前架构混乱点

### 1. 多个处理入口 (brain_coordinator.py)

```
process_user_input(line 256)  ← 新入口,返回ProcessingResult
  ↓
  if use_brain_network:
    → _process_with_brain_network(line 302)  ← 这里集成了CapabilityOrchestrator
  else:
    → _process_with_pipeline(line ???)  ← 旧pipeline

process_input(line 1615)  ← Legacy wrapper,返回str
  ↓
  calls process_user_input()
```

**问题**: `_process_with_brain_network`名字暗示用的是BrainNetwork,但实际上现在应该主要用CapabilityOrchestrator。

### 2. CapabilityOrchestrator集成点 (brain_coordinator.py:513-586)

```python
# 🔥🔥🔥 核心改造: 使用CapabilityOrchestrator替代硬编码路由 🔥🔥🔥
orchestrator = CapabilityOrchestrator(brain_agents=agents_dict)

# 如果有能力需要执行,直接用CapabilityOrchestrator处理
if len(capabilities) > 0:
    orchestrator_result = await orchestrator.execute(...)
    return ProcessingResult(mode='capability_orchestrator', ...)

# 🔥 Fallback: 如果没有特定能力或orchestrator失败,使用BrainNetwork
network_result = await self.brain_network.process(...)  ← 旧代码Fallback
```

**问题**:
- CapabilityOrchestrator只在`len(capabilities) > 0`时触发
- 如果CapabilityAnalyzer没检测到能力,fallback到旧BrainNetwork
- BrainNetwork使用5次迭代(iteration 1/5...),这是旧架构

### 3. BrainNetwork迭代架构 (src/brain/brain_network.py)

这是旧的"并行激活"架构:
```python
# 🔄 Iteration 1/5
# 🔄 Iteration 2/5
# ...
# ⚠️ Did not converge after 5 iterations
```

**这个应该被CapabilityOrchestrator完全取代!**

---

## 需要清理的旧代码

### Priority 1: 核心路由逻辑

#### File: src/coordination/brain_coordinator.py

1. **Rename `_process_with_brain_network`** (line 302)
   ```python
   # OLD NAME (misleading):
   async def _process_with_brain_network(...)

   # NEW NAME (accurate):
   async def _process_with_capability_orchestrator(...)
   ```

2. **Remove BrainNetwork fallback** (line 587-594)
   ```python
   # 🔥 DELETE THIS:
   logger.info(f"🧠 Fallback to BrainNetwork: {max_iterations} iterations...")
   network_result = await self.brain_network.process(
       stimulus=user_input,
       context=context,
       max_iterations=max_iterations,
       convergence_threshold=0.8
   )
   ```

   **Replace with**:
   ```python
   # 如果没有检测到能力,使用conversation agent直接回答
   logger.info("💬 No specific capabilities detected, using conversation agent")
   conv_result = await self._activate_agent('conversation', ...)
   return ProcessingResult(mode='simple_conversation', ...)
   ```

3. **Simplify capability detection** (line 365-375)
   ```python
   # REMOVE THIS complexity check:
   if len(capabilities) == 0:
       complexity_level = 0
   elif len(capabilities) <= 2:
       complexity_level = 1
   # ...
   ```

   **Replace with**:
   ```python
   # CapabilityOrchestrator决定执行计划,不需要手动complexity_level
   ```

### Priority 2: BrainNetwork迭代架构

#### Option A: 完全移除 (RECOMMENDED)
- Delete `src/brain/brain_network.py` 或标记为deprecated
- CapabilityOrchestrator完全取代其功能

#### Option B: 保留作为fallback (NOT RECOMMENDED)
- 保留但明确标记为legacy
- 只在特殊情况下使用

**推荐**: Option A - 完全移除。CapabilityOrchestrator更清晰、更可维护。

### Priority 3: 清理旧测试

#### 问题测试文件

1. **test_locomo_small.py**
   - 问题: 把learning events当问题处理
   - 解决: 已创建test_locomo_correct.py修复
   - **删除旧版test_locomo_small.py**

2. **tests/benchmarks/test_optimized_vs_memos_fixed.py**
   - 问题: 调用process_input导致走BrainNetwork路径
   - 需要修改为调用process_user_input

3. **其他12个后台测试**
   - 检查它们是否调用正确的入口
   - 更新为使用test_locomo_correct.py的模式

---

## 重构步骤

### Step 1: 重命名和简化路由 (30 min)

```python
# brain_coordinator.py

async def process_user_input(...) -> ProcessingResult:
    # 步骤1: CapabilityAnalyzer分析
    capabilities = await analyzer.analyze(user_input)

    # 步骤2: 检索记忆
    memories = await self._retrieve_memories(user_input, capabilities)

    # 步骤3: CapabilityOrchestrator执行
    if len(capabilities) > 0:
        return await self._execute_with_orchestrator(capabilities, memories)
    else:
        return await self._simple_conversation(user_input, memories)

async def _execute_with_orchestrator(...):
    """使用CapabilityOrchestrator执行推理能力"""
    orchestrator = CapabilityOrchestrator(...)
    result = await orchestrator.execute(...)
    return ProcessingResult(mode='capability_orchestrator', ...)

async def _simple_conversation(...):
    """简单对话(无需特殊推理能力)"""
    conv_result = await self.conversation.process(...)
    return ProcessingResult(mode='simple_conversation', ...)
```

### Step 2: 移除BrainNetwork fallback (15 min)

```python
# DELETE these lines from brain_coordinator.py:
- Line 587-594: BrainNetwork fallback code
- Line 365-375: Complexity level calculation (no longer needed)
- Any references to max_iterations, convergence_threshold
```

### Step 3: 标记/移除BrainNetwork (10 min)

```python
# Option A: Delete
rm src/brain/brain_network.py

# Option B: Mark deprecated
# Add to top of brain_network.py:
"""
⚠️ DEPRECATED: This module is no longer used.
Use CapabilityOrchestrator instead.
Kept for reference only.
"""
```

### Step 4: 更新所有测试 (30 min)

1. 删除test_locomo_small.py (已有test_locomo_correct.py)
2. 更新test_optimized_vs_memos_fixed.py使用正确的入口
3. 创建标准测试模板:
```python
# 学习阶段: 直接存储记忆
await coordinator.memory_system.store_memory(content=fact, ...)

# 问答阶段: 调用process_user_input
result = await coordinator.process_user_input(question, {})
assert result.routing_decision['mode'] == 'capability_orchestrator'
```

---

## 预期效果

### Before (现状)
```
process_user_input
  → _process_with_brain_network (misleading name)
    → if capabilities:
        → CapabilityOrchestrator ✅ (good)
      else:
        → BrainNetwork迭代 ❌ (old, slow, confusing)
```

### After (重构后)
```
process_user_input
  → CapabilityAnalyzer.analyze()
  → if capabilities:
      → CapabilityOrchestrator ✅ (主路径)
    else:
      → Simple Conversation ✅ (清晰fallback)
```

---

## 测试验证

重构后运行:
```bash
# 1. 小批量测试
python3 test_locomo_correct.py

# 2. 完整LoCoMo测试
python3 test_locomo_expanded.py

# 3. MEMOS对比测试 (需要先修复)
python3 tests/benchmarks/test_optimized_vs_memos_fixed.py
```

预期结果:
- ✅ 所有测试mode='capability_orchestrator'
- ✅ 没有BrainNetwork迭代日志
- ✅ 准确率提升 (64.3% → 80%+)

---

## 风险评估

### Low Risk
- 重命名方法名
- 删除明显的旧代码(BrainNetwork fallback)

### Medium Risk
- 修改测试脚本
- 更新test_optimized_vs_memos_fixed.py

### High Risk (需要小心)
- 完全删除brain_network.py
- 可能有其他地方依赖

**建议**: 先标记deprecated,运行所有测试,确认没有依赖后再删除

---

## 立即行动

你说得对!现在就应该清理这些旧代码。

**Next Steps**:
1. 先重命名`_process_with_brain_network` → `_execute_with_capability_system`
2. 移除BrainNetwork fallback,替换为简单对话
3. 更新test_optimized_vs_memos_fixed.py
4. 运行测试验证

**要我现在开始执行吗?**
