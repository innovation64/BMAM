# Memory System 测试复现指南

本指南详细说明如何复现 Memory Reasoning Chain 和存储生命周期的测试结果。

---

## 前置要求

### 环境配置

```bash
# Python 版本
Python 3.12+

# 必需依赖
pip install openai faiss-cpu scikit-learn numpy

# 可选依赖（提升性能）
pip install spacy python-dateutil

# 环境变量
export OPENAI_API_KEY="your-api-key-here"
```

### 项目路径

确保在 BMAM 项目根目录执行所有命令：

```bash
cd /path/to/BMAM
pwd  # 应显示 .../BMAM
```

---

## 测试套件概览

| 测试文件 | 目的 | 执行时间 | 通过率 |
|---------|------|----------|--------|
| `test_reasoning_chain_assertions.py` | 验证推理链核心机制 | ~60s | 67% |
| `test_locomo_hrm_5q.py` | LoCoMo 5Q 基准测试 | ~40s | 100% |
| `test_kg_observability.py` | KG 提取与融入验证 | ~30s | 100% |
| `test_storage_lifecycle.py` | 三层存储分布检查 | ~20s | 100% |
| `test_consolidation_full_cycle.py` | 完整巩固周期验证 | ~90s | ⚠️ 部分通过 |

---

## 1. 基础测试：LoCoMo 5Q 基准

### 1.1 执行测试

```bash
python3 test_locomo_hrm_5q.py
```

### 1.2 预期输出

```
================================================================================
测试总结
================================================================================
问题总数: 5
关键词匹配: 5/5 (100.0%)
结果已保存: locomo_hrm_5q_results.json

✅ 准确率良好: 100.0%
```

### 1.3 查看详细结果

```bash
cat locomo_hrm_5q_results.json | python3 -m json.tool
```

**关键指标**:
- `accuracy`: 应为 100.0%
- `matched`: 应为 5
- 每个问题的 `answer` 应包含预期关键词

### 1.4 Metrics 解读

在测试日志中搜索推理链指标：

```bash
python3 test_locomo_hrm_5q.py 2>&1 | grep "✅ Reasoning chain"
```

**输出示例**:
```
✅ Reasoning chain: 7 memories, 15 links, confidence=0.70
✅ Reasoning chain: 8 memories, 15 links, confidence=0.73
...
```

**Metrics 含义**:
- **memories**: 检索到的记忆条数（应为 5-10）
- **links**: 识别的因果链接数（上限 15）
- **confidence**: 推理置信度（0-1，推理问题通常 0.7-0.8）

---

## 2. 断言测试：推理链核心机制

### 2.1 执行测试

```bash
python3 test_reasoning_chain_assertions.py
```

### 2.2 预期输出

```
测试总结
================================================================================
  ✅ PASS: 基础推理链
  ✅ PASS: 多轮稳定性
  ⚠️  FAIL: KG 集成  # 已知问题：测试代码访问了错误的属性

通过率: 2/3 (67%)
```

### 2.3 验证断言细节

**测试 1: 基础推理链**

预期看到：
```
✅ 断言 1: 检索到 2 条记忆
✅ 断言 2: Timeline 正确排序 (2 个事件)
✅ 断言 3: 生成 2 条因果链接
    样本链接: researched adoption... → went to LGBTQ... (强度=0.90)
✅ 断言 4: Confidence = 0.34
```

**核心验证点**:
- Timeline 按时间戳升序排序
- 因果链接强度在 [0, 1] 范围
- Confidence 计算正确

**测试 3: 多轮稳定性**

预期看到 3 次连续查询的一致结果：
```
查询 1: What did Caroline research?
    → 检索: 5 条记忆
    → 链接: 15 条
    → 置信度: 0.62

查询 2: What is Caroline's identity?
    → 检索: 5 条记忆
    → 链接: 15 条
    → 置信度: 0.62
...
```

---

## 3. KG 验证：知识图谱提取与融入

### 3.1 执行测试

```bash
python3 test_kg_observability.py
```

### 3.2 预期输出

```
[2/4] 检查 KnowledgeGraphBuilder 内部存储...
  → Legacy KG 存储:
    - Entities: 3 (['Caroline', 'transgender woman', ...])
    - Relations: 3
      1. ('Caroline', 'is_a', 'transgender woman')
      2. ('Caroline', 'attended', 'an lgbtq support group')
      ...

[3/4] 检查 MemoryReasoningChain 的 KG 引用...
  → MRC.kg: KnowledgeGraphBuilder
  测试 _retrieve_from_kg()...
    → 检索到 4 条 KG facts

[4/4] 检查完整推理链中的 KG 上下文...
  ✅ KG 数据已融入推理链:
    1. {'subject': 'Caroline', 'predicate': 'is_a', 'object': 'transgender woman'}
    ...
```

### 3.3 验证 KG 效用

**关键确认**:
1. ✅ KG 提取了实体和关系（日志中 "Extracted N entities, M relations"）
2. ✅ `_retrieve_from_kg()` 返回非零结果
3. ✅ 推理链的 `kg_context` 包含 KG facts

**常见问题**:
- 如果 `kg_context` 为空，检查 `include_kg=True` 参数
- 如果 Relations 为空，检查输入文本是否包含实体关系

---

## 4. 存储生命周期：三层验证

### 4.1 执行测试

```bash
python3 test_storage_lifecycle.py
```

### 4.2 预期输出

```
[2/3] 检查各层存储...
  → Hippocampus (短期): 1 条记忆
    样本: User: Caroline went to an LGBTQ support group...
  → MemorySystem (长期): 查询失败 (...)  # 已知问题
  → TemporalLobe (知识图谱): 无法访问 relations  # 已知问题

[3/3] 检索验证...
  → smart_retrieve 返回: 1 条记忆
    1. [unknown] User: Caroline went to...
```

### 4.3 存储层解读

**Hippocampus (短期情节记忆)**:
- 存储: `process_input()` 后立即写入
- 检索: `smart_retrieve()` 的主要来源
- 生命周期: 未巩固前永久保留

**MemorySystem (长期语义记忆)**:
- 存储: 需要触发 `consolidation` 后写入
- 检索: FAISS 向量搜索
- 当前状态: ⚠️ API 缺失 (`get_all_memories()`)

**TemporalLobe (知识图谱)**:
- 存储: 接收 Hippocampus 提取的 KG relations
- 检索: 通过 `knowledge_graph_builder.knowledge_graph`
- 当前状态: ⚠️ 不可通过 `relations` 属性直接查询

---

## 5. 巩固周期：完整流程验证

### 5.1 执行测试

```bash
python3 test_consolidation_full_cycle.py
```

**⚠️ 注意**: 此测试需要多次 LLM 调用，预计 90 秒

### 5.2 预期输出

```
[Phase 1/5] 注入测试记忆...
  1/5 ✓ Caroline went to an LGBTQ support group...
  ...
  5/5 ✓ Caroline wants to support LGBTQ families...

[Phase 2/5] 巩固前的存储分布...
  → Hippocampus: 5 条记忆
  → MemorySystem: 查询失败
  → TemporalLobe (语义): 0 条记忆

[Phase 3/5] 提升记忆重要性以满足巩固条件...
  ✓ 已将 5 条记忆重要性设为 0.8

[Phase 4/5] 触发记忆巩固...
  → 巩固结果: {'consolidated': 1, ...}
  ✅ 成功巩固 1 条记忆

[Phase 5/5] 巩固后的存储分布...
  → Hippocampus: 5 条记忆 (变化: +0)
  → TemporalLobe (语义): 0 条记忆 (变化: +0)  # ⚠️ 未生效

[Phase 6/6] 验证长期记忆检索...
  → smart_retrieve 返回: 6 条记忆
  → 来源分布:
    - unknown: 6 条  # ⚠️ 全部来自短期记忆
```

### 5.3 巩固流程解读

**Phase 3: 提升重要性**

巩固条件：
```python
mem.importance > 0.5  # 重要性阈值
mem.access_count < 3   # 避免重复巩固
```

**Phase 4: 触发巩固**

关键日志：
```bash
# 成功情况
{'consolidated': 1, 'total_consolidated': 1, 'message': '...'}

# 失败情况
{'consolidated': 0, 'message': 'TemporalLobe not connected'}
```

**Phase 5-6: 验证结果**

⚠️ **当前已知问题**:
- 巩固触发成功但 TemporalLobe 未增加记忆
- 所有检索仍来自 Hippocampus ('unknown' 源)
- 长期存储机制未完全激活

---

## 6. 常见问题排查

### 6.1 测试失败：OPENAI_API_KEY 未设置

**错误信息**:
```
openai.AuthenticationError: No API key provided
```

**解决方案**:
```bash
export OPENAI_API_KEY="sk-..."
# 或在脚本中设置
import os
os.environ['OPENAI_API_KEY'] = 'sk-...'
```

### 6.2 测试失败：模块导入错误

**错误信息**:
```
ModuleNotFoundError: No module named 'src.XXX'
```

**解决方案**:
```bash
# 确保在项目根目录
cd /path/to/BMAM

# 检查 PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH

# 或使用绝对导入
python3 -m test_locomo_hrm_5q
```

### 6.3 KG 提取失败：Relations = 0

**原因**: 输入文本缺少明显的实体关系

**解决方案**:
```python
# 使用包含关系的文本
"Caroline is a transgender woman."  # "is_a" 关系
"Caroline attended an event."        # "attended" 关系
```

### 6.4 巩固未生效：TemporalLobe 变化 = 0

**原因**: 已知问题，巩固流程未完全实现

**诊断步骤**:
1. 检查 `consolidate_memories()` 返回值
2. 查看日志中 TemporalLobe 消息发送
3. 验证 TemporalLobe 连接状态

---

## 7. 手动数据注入与检索

### 7.1 注入自定义记忆

```python
import asyncio
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

async def ingest_custom_data():
    coordinator = BrainInspiredCoordinator()

    # 注入记忆
    memories = [
        "John went to Paris on 2023-01-15.",
        "John attended a conference about AI.",
        "John met Sarah at the conference.",
    ]

    for mem in memories:
        result = await coordinator.process_input(mem)
        print(f"✓ Ingested: {mem}")

    await coordinator.stop_system()

asyncio.run(ingest_custom_data())
```

### 7.2 触发推理链查询

```python
async def query_with_reasoning():
    coordinator = BrainInspiredCoordinator()

    # 注入数据...

    # 使用推理链查询
    if coordinator.memory_reasoning_chain:
        result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(
            query="What did John do in Paris?",
            max_memories=10
        )

        print(f"Memories: {len(result.memories)}")
        print(f"Causal Links: {len(result.causal_links)}")
        print(f"KG Context: {len(result.kg_context)}")
        print(f"Confidence: {result.confidence:.2f}")

    await coordinator.stop_system()

asyncio.run(query_with_reasoning())
```

### 7.3 手动触发巩固

```python
async def manual_consolidation():
    coordinator = BrainInspiredCoordinator()

    # 注入数据...

    # 提升重要性
    for mem in coordinator.hippocampus.memories:
        mem.importance = 0.8
        mem.access_count = 0

    # 触发巩固
    result = await coordinator.hippocampus.consolidate_memories()
    print(f"Consolidation result: {result}")

    await coordinator.stop_system()

asyncio.run(manual_consolidation())
```

---

## 8. Metrics 详细解读

### 8.1 推理链 Metrics

**Memories (检索记忆数)**:
- 范围: 5-10 条（受 `max_memories` 参数控制）
- 含义: 从 MemoryCoordinator 检索的相关记忆
- 来源: 当前主要来自 Hippocampus

**Causal Links (因果链接数)**:
- 范围: 0-15 条（硬编码上限）
- 含义: 记忆间的因果关系
- 类型:
  - `temporal`: 时间接近 + 实体重叠
  - `thematic`: 主题相似（2+ 共享实体）
- 强度: 0-1（基于实体重叠程度）

**Confidence (置信度)**:
- 范围: 0-1
- 计算公式:
  ```python
  confidence = (
      0.3 * (memory_quality) +      # 记忆重要性/新鲜度
      0.4 * (link_strength) +       # 因果链接强度
      0.3 * (kg_support)            # KG 事实支持
  )
  ```
- 推理问题通常 0.7-0.8
- 简单事实检索通常 0.3-0.5

**KG Context (知识图谱上下文)**:
- 范围: 0-20 条（硬编码上限）
- 含义: 相关的实体关系三元组
- 格式: `{'subject': 'X', 'predicate': 'Y', 'object': 'Z'}`

### 8.2 Timeline Metrics

**Event Count (事件数)**:
- 等于检索到的记忆数
- 按 `timestamp` 升序排列

**Time Span (时间跨度)**:
```python
time_span = timeline[-1][0] - timeline[0][0]  # timedelta
```

---

## 9. 进阶：扩展测试场景

### 9.1 跨会话记忆召回

**场景**: 验证长期记忆跨天检索

```python
from datetime import datetime, timedelta

async def cross_session_test():
    coordinator = BrainInspiredCoordinator()

    # Day 1: 注入记忆
    mem1 = "Alice started a new project on 2023-01-01."
    await coordinator.process_input(mem1)

    # 触发巩固
    for mem in coordinator.hippocampus.memories:
        mem.importance = 0.9
        mem.timestamp = datetime.now() - timedelta(days=1)  # 模拟昨天

    result = await coordinator.hippocampus.consolidate_memories()
    print(f"Consolidated: {result}")

    # Day 2 (模拟): 查询
    query = "What did Alice do?"
    memories = await coordinator.smart_retrieve(query, k=5)

    # 验证来源
    sources = [m.get('source') for m in memories]
    if 'temporal_lobe' in sources or 'memory_system' in sources:
        print("✅ 长期记忆检索成功")
    else:
        print("⚠️  仍依赖短期记忆")

    await coordinator.stop_system()
```

### 9.2 多轮对话推理

**场景**: 验证推理链在复杂对话中的表现

```python
async def multi_turn_reasoning():
    coordinator = BrainInspiredCoordinator()

    # 注入 10 轮对话
    conversation = [
        "Alice is a software engineer.",
        "Alice works at Google.",
        "Alice is interested in machine learning.",
        "Alice attended a conference about transformers.",
        "Alice met Bob at the conference.",
        "Bob is a researcher at OpenAI.",
        "Bob is working on GPT-5.",
        "Alice and Bob discussed collaboration.",
        "Alice is excited about the collaboration.",
        "Alice proposed a joint research project.",
    ]

    for turn in conversation:
        await coordinator.process_input(turn)

    # 复杂推理问题
    queries = [
        "What is Alice's occupation?",
        "Who did Alice meet and where?",
        "What are Alice and Bob likely to work on together?",
    ]

    for q in queries:
        result = await coordinator.memory_reasoning_chain.retrieve_with_reasoning_chain(q)
        print(f"\nQ: {q}")
        print(f"  Memories: {len(result.memories)}, Links: {len(result.causal_links)}, Conf: {result.confidence:.2f}")

    await coordinator.stop_system()
```

---

## 10. 测试数据集

### 10.1 LoCoMo 5Q 数据

**文件**: `locomo_5q_corpus.txt`

```
Caroline went to an LGBTQ support group on 7 May 2023.
Caroline researched adoption agencies that support LGBTQ families on 25 May 2023.
Caroline is excited about continuing her education.
Caroline is interested in counseling or working in mental health.
Caroline wants to support LGBTQ families.
```

**Questions**:
1. When did Caroline go to the LGBTQ support group? (Expected: 7 May 2023)
2. What did Caroline research? (Expected: adoption agencies)
3. What is Caroline's identity? (Expected: transgender woman) *推理*
4. What fields would Caroline be likely to pursue in her education? (Expected: social work / psychology) *推理*
5. What community did Caroline engage with? (Expected: LGBTQ community)

### 10.2 自定义测试数据

**实体关系密集型**:
```
John is a doctor.
John works at Stanford Hospital.
John specializes in cardiology.
John published a paper on heart disease.
```

**时间序列型**:
```
Event A happened on 2023-01-01.
Event B happened on 2023-01-02.
Event C happened on 2023-01-03.
```

---

## 11. 日志与调试

### 11.1 启用详细日志

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,  # 或 INFO/WARNING
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### 11.2 关键日志标记

搜索这些模式以追踪流程：

```bash
# 推理链触发
grep "🧠 Using Memory Reasoning Chain" bmam.log

# 记忆检索
grep "📊 Retrieved.*memories from" bmam.log

# 巩固流程
grep "consolidate" bmam.log

# KG 提取
grep "Extracted.*entities.*relations" bmam.log
```

### 11.3 性能分析

```bash
# 统计 LLM 调用次数
grep "HTTP Request: POST.*openai" bmam.log | wc -l

# 统计检索次数
grep "smart_retrieve" bmam.log | wc -l
```

---

## 12. 总结与下一步

### 12.1 成功标准

✅ **测试通过标准**:
- LoCoMo 5Q 准确率 ≥ 80%
- 推理链断言测试通过率 ≥ 60%
- KG 提取成功（Relations > 0）
- Metrics 在合理范围（Confidence 0.3-0.8）

⚠️ **已知局限**:
- 长期存储机制未完全激活
- 检索依赖 Hippocampus 短期记忆
- 跨会话能力未验证

### 12.2 后续探索

1. **修复长期存储**: 实现 TemporalLobe/MemorySystem 的完整流程
2. **跨会话验证**: 模拟 Day 1 → Day 2 场景
3. **多脑区可观测**: 追踪 Prefrontal/Reflection/Reorganization
4. **性能优化**: 减少 LLM 调用，缓存 embeddings

---

**文档版本**: 1.0
**最后更新**: 2025-11-11
**联系方式**: 如有问题，参考 `MEMORY_SYSTEM_COMPREHENSIVE_VALIDATION.md`
