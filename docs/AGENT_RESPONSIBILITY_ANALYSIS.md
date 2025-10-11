# 类脑多智能体架构 - 职责分析与性能优化映射

## 当前15个Agent架构

### 核心记忆层 (Memory Core)

#### 1. **Short-term Memory** (短期记忆 - 前额叶)
- **脑区**: Prefrontal Cortex
- **职责**:
  - Working memory (7±2项, 20-30秒)
  - 快速查询缓存 (query_cache)
  - Phonological loop & Visuospatial sketchpad
- **性能问题映射**:
  - ✅ **已优化**: 多层快速路径 (Ultra-fast/Fast/Hybrid)
  - ✅ **已优化**: Query cache持久化 (SQLite)
  - 🎯 **Cycle 1/2成果**: WM命中率 50% → 80%

#### 2. **Long-term Memory** (长期记忆 - 新皮层)
- **脑区**: Neocortex
- **职责**:
  - 永久存储 (FAISS + SQLite)
  - 语义网络维护
  - 记忆巩固和关联构建
- **性能问题映射**:
  - ✅ **已优化**: 多层降级检索 (threshold 0.25→0.15→0.05)
  - ✅ **已优化**: 去重优化 (Ultra-fast跳过存储)
  - ❌ **待优化**: KG集成未启用 (multi-hop弱)

#### 3. **Memory Retrieval** (记忆检索 - 海马体)
- **脑区**: Hippocampus
- **职责**:
  - 执行各类检索策略 (semantic/episodic/keyword)
  - 向量搜索调度
  - 结果排序和过滤
- **性能问题映射**:
  - ✅ **已优化**: 语义检索成功率 0% → 100%
  - ⚠️ **需配合**: Retrieval Router策略选择

---

### 检索控制层 (Retrieval Control)

#### 4. **Retrieval Router** (检索路由器 - 前额叶DLPFC)
- **脑区**: Dorsolateral Prefrontal Cortex
- **职责**:
  - 动态策略选择 (semantic/episodic/associative/keyword/multi_strategy)
  - 查询特征提取 (时序/实体/关系)
  - 策略成功率学习
- **性能问题映射**:
  - ✅ **工作正常**: 策略选择准确
  - 🔧 **Multi-hop问题**: `multi_strategy`选择后**未启用KG**
  - 🎯 **关键发现**:
    ```python
    # Line 473: KG默认禁用!
    kg_enabled_env = get_env("KG_ENHANCED_SEARCH", "false").lower() == "true"
    kg_enhanced = base_context.get('kg_enhanced_search', False) and kg_enabled_env
    ```

---

### 记忆管理层 (Memory Management)

#### 5. **Consolidation** (记忆巩固 - 海马体)
- **脑区**: Hippocampus
- **职责**:
  - 短期→长期记忆转移
  - 重要性评估
  - 巩固时间调度 (睡眠模拟)
- **性能问题映射**:
  - ⏸️ **使用率**: 30% (条件触发)
  - 💡 **优化方向**: 可与long_term_memory合并

#### 6. **Forgetting** (遗忘 - 抑制机制)
- **脑区**: Inhibition System
- **职责**:
  - 低重要性记忆衰减
  - 过期记忆清理
  - 记忆容量管理
- **性能问题映射**:
  - ⏸️ **使用率**: 5% (很少触发)
  - 🔧 **建议**: 可考虑移除或合并到long_term_memory

#### 7. **Memory Distortion** (记忆失真 - 丘脑)
- **脑区**: Thalamus
- **职责**:
  - 记忆噪声模拟
  - 虚假记忆检测
  - 真实性评估
- **性能问题映射**:
  - ⏸️ **使用率**: 5% (研究功能)
  - 🔧 **建议**: 生产环境可禁用

---

### 高级认知层 (Higher Cognition)

#### 8. **Reflection** (反思 - 默认模式网络)
- **脑区**: Default Mode Network
- **职责**:
  - 元认知分析
  - 模式发现
  - Insight生成
- **性能问题映射**:
  - ⏸️ **使用率**: 10%
  - 💡 **潜力**: Multi-hop推理可利用

#### 9. **Stress Response** (应激反应 - 杏仁核)
- **脑区**: Amygdala
- **职责**:
  - 情绪标记
  - 威胁评估
  - 情绪记忆增强
- **性能问题映射**:
  - ⏸️ **使用率**: 5%
  - 🔧 **建议**: 简化为情绪标注器

---

### 人格层 (Personality)

#### 10. **Personality** (人格 - 默认模式网络)
- **脑区**: Default Mode Network
- **职责**:
  - MBTI人格模拟 (摇光明明)
  - 回复风格控制
  - 一致性维护
- **性能问题映射**:
  - ⚠️ **性能影响**: Benchmark模式下被跳过
  - 🔧 **问题**: 可能拖慢响应时间

#### 11. **Persona Memory** (人格记忆)
- **脑区**: Default Mode Network
- **职责**:
  - 用户偏好记录
  - 价值观追踪
  - 交互历史
- **性能问题映射**:
  - ⏸️ **使用率**: 中等
  - 💡 **可合并**: 与long_term_memory user_preferences字段重复

---

### 交互层 (Interaction)

#### 12. **Conversation** (对话 - Broca/Wernicke区)
- **脑区**: Language Areas
- **职责**:
  - 响应生成 (LLM调用)
  - 上下文管理
  - 对话流控制
- **性能问题映射**:
  - ❌ **关键瓶颈**: 5秒LLM调用时间
  - 🔧 **原因分析**:
    1. Prompt过长 (包含完整记忆context)
    2. 未优化的system prompt
    3. Temperature设置可能偏高
  - 🎯 **Cycle 3优先修复**

#### 13. **Executive Control** (执行控制 - ACC)
- **脑区**: Anterior Cingulate Cortex
- **职责**:
  - 任务分解
  - Agent协调
  - 冲突解决
- **性能问题映射**:
  - ⏸️ **使用率**: 40%
  - 💡 **当前**: 由Coordinator直接承担

#### 14. **Perception Encoding** (感知编码 - 丘脑)
- **脑区**: Sensory Cortex
- **职责**:
  - 输入预处理
  - 语言检测
  - 特征提取
- **性能问题映射**:
  - ✅ **工作正常**: 语言检测准确
  - ⏸️ **使用率**: 15%

#### 15. **Action Execution** (行动执行 - 运动皮层)
- **脑区**: Motor Cortex
- **职责**:
  - 外部动作触发
  - API调用
  - 工具使用
- **性能问题映射**:
  - ⏸️ **使用率**: 5%
  - 🔧 **建议**: 当前场景下可禁用

---

## Multi-hop推理问题诊断

### 问题: 为什么Multi-hop性能差?

#### 根因分析

1. **KG系统被禁用** ⭐ 关键问题
   ```python
   # brain_coordinator.py:470-474
   # KG功能目前未完全实现（缺少自动构建机制），默认禁用以避免性能开销
   kg_enabled_env = get_env("KG_ENHANCED_SEARCH", "false").lower() == "true"
   ```

2. **Multi-strategy策略未利用KG**
   - Retrieval Router选择`multi_strategy`
   - 但实际执行时走的是普通semantic search
   - KG的graph_enhanced_retrieval从未被调用

3. **缺少推理链构建**
   - 没有chain-of-thought prompting
   - 没有intermediate reasoning steps
   - Reflection agent未参与multi-hop推理

#### 应该由哪些Agent负责Multi-hop?

**正确的Multi-hop推理流程** (基于类脑架构):

```
用户查询: "Caroline研究了什么?" (需要跨记忆推理)
    ↓
[Retrieval Router] 识别为multi-hop查询
    ↓ (选择multi_strategy)
    ↓
[Memory Retrieval + KG] 图增强检索
    ├─ Step 1: 检索 "Caroline" 相关记忆
    ├─ Step 2: 通过KG关系找到 "research" 节点
    └─ Step 3: 沿着关系链找到 "adoption agencies"
    ↓
[Reflection] 推理链验证和整合
    ↓
[Conversation] 生成连贯答案
```

**当前实际流程** (KG禁用):

```
用户查询: "Caroline研究了什么?"
    ↓
[Retrieval Router] 选择keyword策略
    ↓
[Memory Retrieval] 简单semantic search
    ├─ 直接查找 "Caroline" + "research"
    └─ 如果没有直接匹配 → 返回空/低相关结果
    ↓
[Conversation] 基于不足信息生成答案 → ❌ 准确率低
```

---

## Memos对比 - 架构差异

### Memos架构 (推测)

```
简化的3-5层架构:
1. Memory Storage (向量存储)
2. Retrieval Engine (高效检索)
3. LLM Generation (精简prompt)
```

**优势**:
- ✅ 架构简单,延迟低
- ✅ Prompt高度优化
- ✅ 专注核心检索+生成

**劣势**:
- ❌ 缺少working memory机制
- ❌ 无动态策略选择
- ❌ 不模拟脑区功能

### BMAM架构 (当前)

```
完整的15-agent类脑架构:
1. 记忆层 (3个agent)
2. 检索控制 (1个agent)
3. 管理层 (3个agent)
4. 认知层 (2个agent)
5. 人格层 (2个agent)
6. 交互层 (4个agent)
```

**优势**:
- ✅ 完整的类脑模拟
- ✅ Working memory优势明显
- ✅ 可扩展性强

**劣势**:
- ❌ 架构复杂,调试困难
- ❌ 某些agent使用率<10%
- ❌ KG等高级功能未启用

---

## PDCA Cycle 3修复计划 (基于Multi-hop问题)

### Plan

#### P0: 启用KG增强检索

**目标**: 将multi-hop准确率从60-65提升到70-75

**修复点**:
1. **启用KG自动构建**
   ```python
   # 修改默认值
   kg_enabled_env = get_env("KG_ENHANCED_SEARCH", "true").lower() == "true"
   ```

2. **Multi-strategy强制使用KG**
   ```python
   if selected_strategy == 'multi_strategy':
       kg_enhanced = True  # 强制启用
       kg_memories = await kg_integration.graph_enhanced_retrieval(query, k=10)
   ```

3. **添加Reflection推理链**
   ```python
   if is_multi_hop_query:
       # 调用reflection agent整合推理步骤
       reasoning_chain = await reflection_agent.build_reasoning_chain(memories)
   ```

#### P1: Conversation Agent优化

**目标**: LLM调用时间从5秒降到1-2秒

**修复点**:
1. **精简System Prompt** (减少30%)
2. **动态Context Pruning** (只保留top-3记忆)
3. **Cache响应模板**

#### P2: Agent架构精简

**目标**: 移除低使用率agent,降低初始化开销

**可移除/合并**:
- Forgetting → 合并到Long-term Memory
- Memory Distortion → 生产环境禁用
- Stress Response → 简化为emotion tagger
- Action Execution → 当前场景禁用

---

## 总结: 性能问题的Agent职责映射

| 性能问题 | 责任Agent | 状态 | Cycle |
|---------|----------|------|-------|
| 语义检索失败 | Long-term Memory | ✅ 已修复 | Cycle 1 |
| WM命中率低 | Short-term Memory | ✅ 已优化 | Cycle 1 |
| Ultra-fast仍慢 | Coordinator | ✅ 已修复 | Cycle 2 |
| Multi-hop弱 | **KG + Reflection** | ❌ **未启用** | **Cycle 3** |
| LLM调用慢 | **Conversation** | ❌ **待优化** | **Cycle 3** |
| Agent冗余 | Architecture | ⏸️ 待精简 | Cycle 4 |

**关键发现**:
- Multi-hop问题**不是架构缺陷**,而是**KG功能未启用**!
- 应该由 **Memory Retrieval + KG Integration + Reflection** 三个agent协同完成
- 当前只用了Memory Retrieval,另外两个未参与

---

## 下一步行动

### 立即执行 (Cycle 3)

1. ✅ **启用KG**: 修改默认配置 + 自动构建机制
2. ✅ **Multi-strategy → KG**: 强制路由到graph_enhanced_retrieval
3. ✅ **添加Reflection**: 构建推理链
4. ✅ **优化Conversation**: 精简prompt

### 后续规划 (Cycle 4)

1. 架构精简 (移除4-5个低使用率agent)
2. 完整benchmark验证
3. 针对性修复各类别弱项

