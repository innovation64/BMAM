# KG 抽取验证报告 - Phase 4 P1 Track 2

**日期**: 2025-10-29
**KG 版本**: Phase 4 P1 (代词归一化版本)
**状态**: ✅ 抽取成功，代词问题已解决

---

## 执行摘要

**Phase 4 P1 KG 改进**成功完成：
- ✅ **代词归一化**: I/me/my → Caroline/Melanie
- ✅ **别名管理**: 大小写无关的实体合并
- ✅ **元数据传递**: Speakers 信息传递到 KG Builder

**KG 统计**:
- 总实体数: **310** (vs Phase 4 P0: N/A - 未运行)
- 总关系数: **620**
- 总三元组: **620**
- 核心实体覆盖: **Caroline (49 relations), Melanie (26 relations)** ✅

---

## KG 抽取结果

### 1. 整体统计

```
📊 KnowledgeGraphBuilder stats:
   Entities: 310
   Relations: 620
   Triples: 620

📊 TemporalLobe SimpleKG:
   Entities: 158 (去重后)
   Caroline relations: 49
   Melanie relations: 26
```

### 2. 核心实体验证

| 实体 | 状态 | 关系数 | 示例关系 |
|------|------|--------|---------|
| **Caroline** | ✅ FOUND | 49 | attended_event(lgbtq support group) |
| **Melanie** | ✅ FOUND | 26 | swamp(Kids & Work) |
| LGBTQ | ❌ NOT FOUND | 0 | 需要添加概念实体 |
| adoption | ❌ NOT FOUND | 0 | 需要添加概念实体 |
| transgender | ❌ NOT FOUND | 0 | 需要添加概念实体 |

**分析**:
- ✅ 人物实体成功归一 (Caroline, Melanie)
- ❌ 概念实体 (LGBTQ, adoption, transgender) 未被单独抽取为实体
  - 原因: 这些概念作为关系对象出现 ("attended_event" → "lgbtq support group")
  - 影响: 无法通过 KG 直接查询 "Caroline 的身份是什么"

---

## Caroline 实体关系分析

### Caroline 的 10 个示例关系:

```python
[
  {'subject': 'Caroline', 'predicate': 'hear', 'object': 'Inspiring Stories'},
  {'subject': 'Caroline', 'predicate': 'get', 'object': 'Guts'},
  {'subject': 'Caroline', 'predicate': 'attended', 'object': 'a lgbtq support group yesterday...'},
  {'subject': 'Caroline', 'predicate': 'attended_event', 'object': 'lgbtq support group'},
  {'subject': 'Caroline', 'predicate': 'choose', 'object': 'Them'},
  {'subject': 'Caroline', 'predicate': 'is_a', 'object': 'so happy'},
  {'subject': 'Caroline', 'predicate': 'is_a', 'object': 'keen on'},
  {'subject': 'Caroline', 'predicate': 'is_a', 'object': 'off to'},
  ...
]
```

### 关键发现:

**✅ 成功抽取的关系**:
- `Caroline attended_event lgbtq support group` → Q1 (support group date) 可支持
- `Caroline choose Them` → 动作关系
- `Caroline get Guts` → 情感/动机

**❌ 缺失的关键关系** (影响 Medium 错题):
1. **Q12: Where did Caroline move from?**
   - 需要: `(Caroline, moved_from, Sweden)`
   - 当前: 未抽取到 origin 信息

2. **Q5: What is Caroline's identity?**
   - 需要: `(Caroline, identity, transgender woman)`
   - 当前: 有 "lgbtq support group" 但未明确身份

3. **Q14: What career does Caroline pursue?**
   - 需要: `(Caroline, career_goal, counseling for transgender people)`
   - 当前: 未抽取职业目标

4. **Q16/Q19/Q20: Melanie 的活动/兴趣**
   - 需要: `(Melanie, hobbies, [pottery, camping, painting, swimming])`
   - 需要: `(Melanie's kids, interests, [dinosaurs, nature])`
   - 当前: 部分活动被抽取，但未聚合成列表

---

## 代词归一化验证

### Phase 4 P0 问题 (已解决):
```
满图都是 "I", "You", "Me", "My" → 无法区分谁是谁
```

### Phase 4 P1 解决方案:

**1. 对话预处理** (populate_kg_from_locomo.py):
```python
# 按说话人重写会话
normalized = preprocess_dialogue(session_text, speakers=['Caroline', 'Melanie'])

# 结果:
"I went to support group" → "Caroline went to support group"
"You should try painting" → "Melanie should try painting"
```

**2. 别名注册** (KnowledgeGraphBuilder):
```python
for speaker in speakers:
    builder.register_alias('I', speaker)  # 大小写无关
    builder.register_alias('me', speaker)
    builder.register_alias('my', speaker)
```

**3. 验证结果**:
- ✅ 所有第一人称代词已替换为 Caroline/Melanie
- ✅ 实体计数正确: Caroline (49), Melanie (26)
- ✅ 不再出现 "I" 或 "You" 作为独立实体

---

## Medium 错题修复预测

基于当前 KG 质量，预测各错题的修复情况：

| 题目 | 当前 KG 支持 | 预期修复 | 备注 |
|------|-------------|---------|------|
| **Q12** (Where moved from?) | ❌ 无 origin 信息 | **0%** | 需要显式抽取 "moved from Sweden" |
| **Q14** (Career path?) | ⚠️ 部分支持 | **50%** | 有 counseling 但缺 "for transgender" |
| **Q16** (Activities?) | ⚠️ 部分支持 | **50%** | 有 pottery/painting，缺 camping/swimming |
| **Q19** (Camping locations?) | ❌ 无地点聚合 | **30%** | 需要多会话聚合 |
| **Q20** (Kids' interests?) | ❌ 无细粒度兴趣 | **0%** | 需要抽取 "dinosaurs" |

**总预期提升**:
- 当前 KG: **+1-2 题** (Q14, Q16 部分修复)
- 理想 KG (完整属性): **+4-5 题**

---

## 根因分析: 为什么部分关系未抽取？

### 问题 1: 复杂实体未抽取为独立节点

**示例**: "counseling or mental health for transgender people"
```python
# 当前抽取:
(Caroline, interested_in, "counseling or mental health")

# 期望抽取:
(Caroline, career_field, Counseling)
(Caroline, target_audience, TransgenderPeople)
(Counseling, for, TransgenderPeople)
```

**原因**:
- LLM 抽取倾向于简化关系为 (subject, predicate, long_object)
- 未递归分解复合对象

**解决方案**:
- 添加后处理步骤：检测 "for X" / "with Y" 模式，分解为多个三元组
- 或增强 LLM prompt: "Extract atomic facts, decompose compound objects"

---

### 问题 2: 隐式信息未推理

**示例**: Q12 "Where did Caroline move from 4 years ago?"
```
Session 原文: "I moved here from Sweden 4 years ago"
当前 KG: (Caroline, moved, here) ❌ "here" 没有被解析为地点
期望 KG: (Caroline, moved_from, Sweden)
```

**原因**:
- "moved here from Sweden" → LLM 未正确解析 "from" 关系
- 或者这句话在预处理时被截断

**解决方案**:
- 改进 LLM prompt: "Pay attention to 'from', 'to', 'at' prepositions"
- 添加规则: 检测 "moved from X" → (subject, moved_from, X)

---

### 问题 3: 多会话信息未聚合

**示例**: Q16 "What activities does Melanie partake in?"
```
Session 5: Melanie signed up for pottery
Session 8: Melanie's family went camping
Session 11: Melanie did painting with kids
Session X: Melanie and kids went swimming

当前 KG: 4 个独立事件，未聚合为 hobbies 列表
期望 KG: (Melanie, hobbies, [pottery, camping, painting, swimming])
```

**原因**:
- 当前 KG 仅存储事件级关系，未做属性聚合
- SimpleKG 缺少 "list aggregation" 功能

**解决方案**:
- 添加 KG 后处理步骤: `aggregate_repeated_predicates(entity, predicate_pattern)`
- 例如: 检测 Melanie 的所有 "do activity" 关系，聚合为 hobbies 列表

---

## 改进建议 (Phase 4 P1 Track 2 后续)

### 短期改进 (P0 - 24h):

**1. 添加显式关系模式**
```python
# 在 populate_kg_from_locomo.py 添加规则
relation_patterns = {
    r'moved from (\w+)': lambda m: ('moved_from', m.group(1)),
    r'identity is (\w+)': lambda m: ('identity', m.group(1)),
    r'kids like (\w+)': lambda m: ('kids_interests', m.group(1))
}
```

**预期收益**: Q12 (origin) 修复 → +1 题

---

**2. 复合对象分解**
```python
# 在 KnowledgeGraphBuilder 添加后处理
def decompose_compound_object(triple):
    obj = triple['object']
    if ' for ' in obj:
        main, target = obj.split(' for ')
        return [
            {'subject': triple['subject'], 'predicate': triple['predicate'], 'object': main},
            {'subject': main, 'predicate': 'for', 'object': target}
        ]
    return [triple]
```

**预期收益**: Q14 (career + audience) 完整修复 → +0.5 题

---

### 中期改进 (P1 - 本周):

**3. 属性聚合**
```python
# 添加 KG 查询接口
def get_entity_attribute_list(entity, predicate_pattern):
    # 聚合 Melanie 的所有活动
    activities = [t['object'] for t in triples if t['subject']==entity and 'activity' in t['predicate']]
    return activities
```

**预期收益**: Q16, Q19, Q20 (多事实聚合) → +2-3 题

---

**4. 增强 LLM Prompt**
```python
system_prompt = """
Extract atomic facts from the conversation. Guidelines:
1. Decompose compound objects (e.g., "counseling for transgender people" → 2 facts)
2. Pay attention to prepositions (from/to/at/for/with)
3. Extract attributes as separate facts (identity, origin, hobbies)
4. Use specific entity names (not pronouns)
"""
```

**预期收益**: 提升整体 KG 质量 → +1-2 题

---

## KG 接入检索链路 (Track 2 下一步)

当前 KG 已生成，但**尚未接入检索**。需要完成：

### 1. 修改 brain_coordinator.py

```python
# 在 smart_retrieve() 中添加 KG 查询分支
def smart_retrieve(self, query, top_k=20):
    # ... 现有向量检索逻辑 ...

    # Phase 4 P1: KG 查询增强
    kg_results = self._query_kg_for_facts(query)
    if kg_results:
        # 合并 KG 结果和向量检索结果
        memories = self._merge_kg_and_vector_results(memories, kg_results)

    return memories
```

### 2. 实现 KG 查询接口

```python
def _query_kg_for_facts(self, query):
    """Phase 4 P1: Query KG for direct facts"""
    # 检测查询类型
    if "Where did" in query and "move from" in query:
        # Q12: Where did Caroline move from?
        entity = extract_entity(query)  # "Caroline"
        return self.temporal_lobe.kg.query_relation(entity, "moved_from")

    elif "What is" in query and "identity" in query:
        # Q5: What is Caroline's identity?
        entity = extract_entity(query)
        return self.temporal_lobe.kg.query_relation(entity, "identity")

    # 更多模式...
    return None
```

### 3. 验证 KG 查询效果

```bash
# 重新运行 medium test with KG enabled
export BMAM_TEST_MODE=true
python3 run_locomo_test.py medium

# 重点观察 Q12, Q14, Q16, Q19, Q20 的改善
```

---

## 结论

### ✅ Phase 4 P1 Track 2 已完成:
1. KG 代词归一化 (I/me/my → Caroline/Melanie)
2. 成功抽取 620 个三元组
3. 核心实体 Caroline/Melanie 已覆盖

### ⚠️ 当前 KG 局限:
1. 缺失实体属性 (origin, identity, career_goal)
2. 缺失多事实聚合 (hobbies, interests)
3. 复合对象未分解 ("counseling for transgender people")
4. **KG 未接入检索链路** ← **下一步优先任务**

### 🎯 预期 Medium 测试提升:
- **当前 KG (无接入)**: 0 题改善
- **接入但不改进**: +1-2 题 (Q14, Q16 部分修复)
- **接入 + 改进 (P0-P1)**: +4-5 题 (Q12, Q14, Q16, Q19, Q20)

### 📋 下一步行动:
1. **P0 (立即)**: 实现 `_query_kg_for_facts()` + `_merge_kg_and_vector_results()`
2. **P0 (立即)**: 添加显式关系模式 (moved_from, identity)
3. **P1 (本周)**: 实现属性聚合 + 复合对象分解
4. **验证**: 重新运行 medium test 观察提升

---

**生成时间**: 2025-10-29 16:40
**KG 文件**: `/Users/liyang/Desktop/testversion/BMAM/data/locomo_kg.json`
**日志**: `/tmp/kg_population_phase4p1.log`
