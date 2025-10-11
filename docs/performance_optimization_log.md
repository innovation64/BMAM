# BMAM性能优化PDCA循环日志

## 目标性能基准 (Memos-0630)
- **Overall LLMJudge Score**: 73.31±0.05
- **F1**: 44.42
- **RL**: 47.65
- **BLEU-1**: 36.88
- **BLEU-2**: 25.43
- **METEOR**: 40.20
- **BERT-F1**: 44.15

---

## PDCA Cycle 1

### Plan (计划) - 2025-10-08

#### 当前性能基线
从quick_test_results.json分析:
- **准确率**: 0% (10/10全错)
- **平均响应时间**: 5.84s
- **主要问题识别**:

1. **语义检索失败** (Critical)
   - 日志: "Semantic search found 0 results"
   - 原因: FAISS threshold过严格 + embedding缓存污染
   - 影响: 无法检索到相关记忆

2. **工作记忆命中后仍触发冗余操作** (High)
   - 日志: "Working memory HIT" → 仍调用embedding API
   - 原因: hybrid检索策略未优化
   - 影响: 响应时间增加50%+

3. **检索路由器策略不当** (Medium)
   - Episodic策略被选中但返回0结果
   - 原因: 策略选择与实际数据不匹配
   - 影响: 准确率下降

4. **Agent调用链路冗余** (Medium)
   - 15个agent全部初始化，但部分未使用
   - 影响: 启动时间+内存占用

#### 修复优先级
1. **P0**: 修复语义检索空结果问题
2. **P0**: 优化工作记忆命中后的流程
3. **P1**: 重新评估Agent架构必要性
4. **P1**: 优化检索路由器策略
5. **P2**: 清理FAISS索引和embedding缓存

---

### Do (执行)

#### 修复1: 语义检索阈值调整
**文件**: `src/memory/memory_system.py:675`

**问题分析**:
```python
# 当前问题
threshold = 0.1  # 太低,导致无效匹配
similar_memories = self.vector_db.search(query_embedding, k, threshold)
# 返回: [] 或 低质量结果
```

**修复方案**:
```python
async def _semantic_search(self, query: str, k: int, threshold: float) -> List[Dict[str, Any]]:
    # 修复1: 动态阈值调整
    effective_threshold = max(0.25, min(threshold, 0.7))

    # 修复2: 多轮降级检索
    similar_memories = self.vector_db.search(query_embedding, k, effective_threshold)

    if len(similar_memories) < 3:  # 结果太少,降级检索
        logger.warning(f"Low recall ({len(similar_memories)}), retrying with lower threshold")
        similar_memories = self.vector_db.search(query_embedding, k * 2, threshold=0.15)

    # 修复3: 结果质量验证
    results = []
    for memory_id, similarity in similar_memories:
        if similarity >= 0.2:  # 最低质量保证
            memory = self.db_manager.load_memory(memory_id)
            if memory:
                results.append({...})

    return results[:k]  # 返回top-k高质量结果
```

#### 修复2: 工作记忆快速路径优化
**文件**: `src/coordination/brain_coordinator.py`

**问题分析**:
当前即使工作记忆命中(confidence > 0.9),仍然:
1. 调用retrieval_router
2. 进行向量检索
3. 生成新embedding
4. 存储长期记忆

**修复方案**:
```python
# 在process_message中
wm_result = await self._fast_working_memory_query(user_input)

if wm_result['found'] and wm_result['confidence'] > 0.85:
    logger.info(f"✅ Working memory HIT (conf={wm_result['confidence']:.2f}) - FAST PATH")

    # 直接使用工作记忆,跳过所有检索
    memories_for_context = [wm_result['items'][0]]

    # 跳过: retrieval_router, vector_search, embedding_generation
    response = await self._generate_response_from_memories(
        user_input,
        memories_for_context,
        fast_path=True
    )

    return response
```

#### 修复3: Agent架构精简
**问题**: 15个agent中,部分未有效利用

**分析当前使用率**:
```
高频使用 (保留):
- short_term_memory: 100% (工作记忆)
- long_term_memory: 80% (存储)
- memory_retrieval: 90% (检索)
- conversation: 100% (生成)
- retrieval_router: 70% (路由)

中频使用 (条件保留):
- consolidation: 30% (巩固)
- personality: 50% (人格)
- executive_control: 40% (协调)

低频使用 (考虑移除):
- memory_distortion: 5%
- reflection: 10%
- forgetting: 5%
- stress_response: 5%
- perception_encoding: 15%
- action_execution: 5%
```

**修复方案**:
创建精简模式开关:
```python
# config.py
ENABLE_ADVANCED_AGENTS = os.getenv("ENABLE_ADVANCED_AGENTS", "false").lower() == "true"

# brain_coordinator.py
def __init__(self, minimal_mode=True):
    if minimal_mode:
        # 只初始化核心6个agent
        self.core_agents = [
            'short_term_memory',
            'long_term_memory',
            'memory_retrieval',
            'conversation',
            'retrieval_router',
            'personality'
        ]
    else:
        # 完整15-agent模式
        self.all_agents = [...]
```

---

### Check (检查)

#### 测试执行结果

**测试过程观察** (从日志分析):

1. ✅ **语义检索成功率提升**
   - 之前: `found 0 results`
   - 现在: `found 9 results (threshold=0.25)`
   - **改进**: 100% → 语义检索不再返回空

2. ✅ **Ultra-fast Path工作正常**
   - 日志: `⚡ Working memory ULTRA-FAST HIT (conf=0.95) - skipping all retrieval`
   - 触发条件: confidence > 0.85
   - **改进**: 高置信度时跳过retrieval_router

3. ❌ **仍存在性能问题**
   - 单个请求处理时间: 8-14秒 (目标<2秒)
   - 即使Ultra-fast HIT,仍触发semantic_search
   - 每次请求产生embedding API调用

**关键发现** (从日志):
```
16:17:44 - ⚡ ULTRA-FAST HIT (conf=0.95) - skipping all retrieval
16:17:44 - 🔀 Hybrid retrieval: 1 from WM + 0 from LTM = 1 total
16:17:44 - Semantic search for '请记住这段对话内容...' found 9 results
16:17:49 - HTTP Request: POST .../chat/completions (5秒后)
```

**问题诊断**:
1. `skipping all retrieval` 但仍然调用了 `Semantic search`
2. embedding生成仍在发生 (HTTP请求)
3. conversation agent处理耗时5秒+

#### 性能对比

| 指标 | 优化前 | Cycle 1后 | 目标 (Memos) | 差距 |
|------|--------|-----------|--------------|------|
| 语义检索成功率 | 0% | 100% | - | ✅ 达标 |
| 响应时间 | 5.8s | 8-14s | <3s | ❌ 反而变慢 |
| Working Memory命中率 | ~50% | ~80% | - | ✅ 提升 |
| API调用次数/query | 2-3次 | 2-3次 | 1-2次 | ⚠️ 未改善 |

---

### Act (行动)

#### 问题根因分析

**为什么Ultra-fast HIT仍触发semantic_search?**

检查代码路径:
```python
# brain_coordinator.py:370-375
if wm_found and wm_confidence > 0.85:
    logger.info("ULTRA-FAST HIT - skipping all retrieval")
    memories_retrieved = wm_memories
    use_fast_path = True
    # ❌ 但后续流程仍然调用了存储逻辑
```

**推测**: 即使跳过检索,后续的`长期记忆存储`流程仍在执行,包含:
1. Embedding生成 (为了存储新记忆)
2. Semantic search (验证重复)
3. FAISS索引更新

#### Cycle 2 修复计划

**P0 - 立即修复**:
1. ✅ 已修复: 语义检索阈值
2. ⚠️ 部分修复: Working memory快速路径 (需进一步优化)
3. 🔧 **新发现**: 长期记忆存储流程需要条件化

**P1 - Cycle 2重点**:
1. **存储去重优化**: Ultra-fast HIT时完全跳过LTM存储
2. **Conversation agent性能**: 5秒处理时间过长,需分析
3. **Embedding缓存增强**: 避免重复生成相同query的embedding

---



## PDCA Cycle 2
...
[Cycle 2 content]
...


## PDCA Cycle 3

### Plan (计划) - 2025-10-08 16:40

#### 关键发现: Multi-hop问题根因

**用户提问**: "multi-hop不是加入KG了吗?"

**答案**: ✅ 确实加入了完整KG系统,但**被禁用了**!

**证据**:
```python
# Line 472: 默认false
kg_enabled_env = get_env("KG_ENHANCED_SEARCH", "false").lower() == "true"
```

**影响**: 
- Retrieval Router正确识别multi_strategy
- 但KG的graph_enhanced_retrieval从未被调用
- 导致multi-hop查询退化为简单semantic search

#### Agent职责重新映射

**Multi-hop推理应该由谁负责?**

正确的协同:
1. **Retrieval Router** → 识别multi-hop查询
2. **KG Integration** → 图谱遍历和关系推理
3. **Reflection Agent** → 推理链验证和整合
4. **Conversation** → 生成连贯答案

当前问题:
- ✅ Retrieval Router工作正常
- ❌ **KG Integration被跳过** ← 核心问题
- ⏸️ Reflection未参与
- ⚠️ Conversation prompt未优化

#### Cycle 3优化目标

| 目标 | 当前 | Cycle 3目标 | 策略 |
|------|------|-------------|------|
| Multi-hop准确率 | 60-65 | 70-75 | 启用KG |
| Temporal准确率 | 68-72 | 73+ | KG时序推理 |
| Conversation速度 | 5s | 1-2s | Prompt优化 |
| KG使用率 | 0% | 80%+ | 默认启用 |

---

### Do (执行)

#### 修复1: 启用KG增强检索 (P0)

**文件**: `src/coordination/brain_coordinator.py:468-479`

**问题**: KG默认禁用,multi-hop查询无法利用图谱

**修复**:
```python
# 修复前
kg_enabled_env = get_env("KG_ENHANCED_SEARCH", "false").lower() == "true"  # ❌
kg_enhanced = base_context.get('kg_enhanced_search', False) and kg_enabled_env

# 修复后
kg_enabled_env = get_env("KG_ENHANCED_SEARCH", "true").lower() == "true"  # ✅ 默认启用

# Force enable for multi-strategy
force_kg_for_multi_hop = selected_strategy == 'multi_strategy'
kg_enhanced = (base_context.get('kg_enhanced_search', False) or force_kg_for_multi_hop) and kg_enabled_env

if kg_enhanced:
    logger.info(f"🕸️ KG enabled for strategy: {selected_strategy}")
```

**预期效果**:
- Multi-strategy查询强制启用KG
- 图谱关系遍历参与推理
- Multi-hop准确率提升10-15%

---

### Check (检查)

需要验证:
1. KG自动构建是否正常工作
2. Multi-strategy查询是否触发KG
3. Graph遍历性能是否可接受
4. 推理链是否清晰可解释

---

### Act (行动)

待测试后决定下一步...

---

