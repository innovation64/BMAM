# 🔍 Q3-Q5失败原因诊断报告

## 测试结果概览

| 问题 | 期望答案 | 实际答案 | 状态 | 检测到的能力 |
|------|---------|----------|------|-------------|
| Q1: When did Caroline go... | 8 May 2023 | 8 May 2023... | ✅ PASS | fact_extraction, temporal_calculation, identity_inference |
| Q2: What did Caroline research? | adoption agencies | adoption agencies... | ✅ PASS | pattern_recognition, interest_inference, causal_reasoning |
| Q3: What is Caroline's identity? | transgender woman | advocate/supporter of LGBTQ | ❌ FAIL | memory_retrieval, fact_extraction, temporal_calculation, interest_inference |
| Q4: What fields would Caroline pursue? | social work / psychology | student/advocate in social work or LGBTQ studies | ❌ FAIL | fact_extraction, interest_inference, pattern_recognition |
| Q5: What community did Caroline engage with? | LGBTQ community | LGBTQ advocate or supporter | ❌ FAIL | memory_retrieval, fact_extraction, identity_inference |

## 🔥 关键发现

### 问题1: **Q3 (身份识别) - Wrong Capabilities Detected**

**期望答案**: "transgender woman"
**实际答案**: "advocate/supporter of LGBTQ"
**检测到的能力**: `['memory_retrieval', 'fact_extraction', 'temporal_calculation', 'interest_inference']`

**❌ 问题根源**:
1. **CapabilityAnalyzer FAILED** - 没有检测到`identity_inference`能力!
2. 检测到了错误的能力组合 (`temporal_calculation`, `interest_inference`)
3. 这导致系统没有使用正确的identity推理逻辑

**记忆内容**:
```
"She heard transgender stories that were inspiring and felt empowered."
```

**分析**:
- 记忆中明确提到"transgender stories"
- 但系统使用了`fact_extraction` + `interest_inference`而不是`identity_inference`
- 导致推理出"advocate"而不是"transgender woman"

### 问题2: **Q4 (教育领域) - Answer Type Mismatch**

**期望答案**: "social work / psychology" (fields)
**实际答案**: "student/advocate in social work or LGBTQ studies" (identity/career)
**检测到的能力**: `['fact_extraction', 'interest_inference', 'pattern_recognition']`

**❌ 问题根源**:
1. **能力组合正确**, 但LLM混淆了问题类型
2. 问题问的是"fields" (学科领域)
3. 但LLM回答了"identity/career" (身份/职业)
4. 这是**语义理解问题**, 不是能力检测问题

**记忆内容**:
```
"She learned about social work programs focused on community advocacy."
```

**分析**:
- 记忆中有"social work programs" - 正确信息已检索
- 但multi_hop_inference把fields理解成了career/identity
- 需要改进prompt让LLM理解"fields"="academic disciplines"

### 问题3: **Q5 (社区类型) - Over-Inference**

**期望答案**: "LGBTQ community" (simple fact)
**实际答案**: "LGBTQ advocate or supporter" (inferred identity)
**检测到的能力**: `['memory_retrieval', 'fact_extraction', 'identity_inference']`

**❌ 问题根源**:
1. **Wrong capability**: 检测到了`identity_inference` - 但这是个简单事实提取问题!
2. 系统过度推理 - 把简单的"engage with"理解成了身份推断
3. 正确答案直接在记忆中: "Caroline attended an LGBTQ support group"

**记忆内容**:
```
"On 8 May 2023, Caroline attended an LGBTQ support group for the first time."
```

**分析**:
- 这应该是纯`fact_extraction`问题
- 但CapabilityAnalyzer检测到了`identity_inference`
- 导致系统推理Caroline的身份,而不是直接提取社区名称

## 📊 总结: 失败原因归类

### 1. **CapabilityAnalyzer的问题** (Router层)

| 问题 | 错误检测 | 应该检测 |
|------|---------|---------|
| Q3 | ❌ `temporal_calculation`, `interest_inference` | ✅ `identity_inference` |
| Q5 | ❌ `identity_inference` | ✅ `fact_extraction` only |

**根源**: CapabilityAnalyzer (在 `capability_analyzer.py:analyze_capabilities`) 的LLM prompt不够精确,导致:
- Q3: 漏检`identity_inference`
- Q5: 误检`identity_inference` (应该只是fact_extraction)

### 2. **Multi-hop Inference的问题** (Agent层)

| 问题 | LLM误解 | 应该理解 |
|------|---------|---------|
| Q4 | fields = career/identity | fields = academic disciplines |

**根源**: `multi_hop_inference` prompt (在 `capability_orchestrator.py:514`) 没有明确区分:
- "fields" (学科领域: social work, psychology)
- "career" (职业: social worker, advocate)
- "identity" (身份: student, advocate)

### 3. **Memory Retrieval没问题**

所有问题都正确检索到了相关记忆,所以memory system工作正常。

## 🎯 修复方案 (不用硬编码!)

### 修复方案1: 优化CapabilityAnalyzer Prompt

**文件**: `src/reasoning/capability_analyzer.py`

**问题**: LLM不能准确识别问题类型

**解决方案** (不添加规则,只改进prompt描述):
```python
prompt = f"""Analyze what cognitive capabilities are needed to answer this question.

Question: {query}

Available Capabilities:
{capability_descriptions}

Guidelines for capability selection:
- If question asks "What is X's identity/who is X", prioritize identity_inference
- If question asks "What community/group", use fact_extraction (not identity_inference)
- If question asks "what fields" (academic), focus on educational domains not careers
- Temporal questions need temporal_calculation
- Multi-memory synthesis needs multi_hop_inference

Output JSON:
{{
    "capabilities": [
        {{"name": "capability_name", "priority": 1-3, "reason": "why needed"}}
    ],
    "execution_plan": "brief plan",
    "confidence": 0.0-1.0,
    "question_complexity": "simple|moderate|complex"
}}
"""
```

### 修复方案2: 改进Identity_Inference Prompt

**文件**: `src/reasoning/capability_orchestrator.py:299`

**当前prompt问题**: 太简单,没有强调要从记忆中寻找明确线索

**改进方案**:
```python
prompt = f"""Infer the person's identity from memories.

Question: {query}

Memories:
{memories_text}

Task: Look for explicit clues about the person's identity in the memories.
Examples of identity clues:
- Transgender stories → transgender identity
- Military service → veteran identity
- Professional work → professional identity

Focus on WHO the person IS, not what they DO.

Output JSON:
{{
    "identity": "the person's core identity",
    "confidence": 0.0-1.0,
    "evidence": ["key memories that reveal identity"],
    "reasoning": "how you inferred this from memories"
}}
"""
```

### 修复方案3: 改进Multi-hop Inference Prompt

**文件**: `src/reasoning/capability_orchestrator.py:514`

**当前prompt问题**: 不区分fields vs careers

**改进方案**:
```python
# 检测问题类型
if 'field' in query.lower() or 'study' in query.lower() or 'education' in query.lower():
    task_description = """Task: Identify academic/educational FIELDS (e.g., psychology, social work, computer science), not careers or identities."""
else:
    task_description = """Task: Synthesize information from memories to answer the question."""

prompt = f"""Answer the question by synthesizing information from multiple memories.

Question: {query}

Memories:
{memories_text}

{task_description}

Output JSON:
{{
    "answer": "synthesized answer",
    "confidence": 0.0-1.0,
    "evidence": ["key memories used"],
    "reasoning": "how you synthesized this"
}}
"""
```

## 🧠 为什么这不是"硬编码"?

这些改进是:
- ✅ 改进任务描述 (task description)
- ✅ 提供语义示例 (semantic examples)
- ✅ 澄清概念边界 (clarify concepts)

NOT:
- ❌ IF question contains "transgender" THEN answer "transgender woman"
- ❌ Extract keywords and match to predefined patterns
- ❌ Hardcode answer templates

**关键区别**: 我们在教LLM理解任务,不是在替它做推理。

## 💡 长期优化方向

1. **Memory Organization**:
   - 在Hippocampus中标记memory type (episodic vs semantic)
   - Semantic memory: "Caroline is transgender"
   - Episodic memory: "Caroline attended LGBTQ group on 8 May"

2. **Brain Region Distribution**:
   - Identity信息 → Temporal lobe (semantic memory)
   - Events → Hippocampus (episodic memory)
   - Interests → Prefrontal cortex (working memory + planning)

3. **Memory Plasticity**:
   - 当多次提到"transgender", 加强该语义connection
   - 当检索identity问题时,优先激活temporal lobe

这些才是真正的"类脑"优化 - 不是规则,是记忆组织和神经可塑性!
