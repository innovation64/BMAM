# 多维度答案融合设计方案

## 当前问题分析

### 现状: 单一优先级机制的缺陷

**当前实现** (capability_orchestrator.py:680-690):
```python
capability_priority = {
    'identity_inference': 1,  # 最高优先级
    'multi_hop_inference': 2,
    'fact_extraction': 5,     # 最低优先级
}
# 简单按数字排序,选择最小值
```

**问题案例 - Q4失败**:
- 问题: "What fields would Caroline be likely to pursue in her education?"
- 期望: "social work / psychology"
- 实际执行的capabilities: `['interest_inference', 'pattern_recognition', 'identity_inference']`
- identity_inference返回: "transgender woman" (优先级1)
- interest_inference返回: "social work, community advocacy" (优先级2)
- **错误**: 因为identity_inference优先级最高,系统选择了"transgender woman" ❌
- **应该**: 根据问题语义,选择interest_inference的答案 ✅

**根本问题**:
- 固定优先级**忽略了问题的语义**
- 没有考虑capability与问题的**相关性**
- 没有考虑答案的**置信度**和**质量**

## 多维度融合判断设计

### 维度1: Question-Capability相关性 (Semantic Relevance)

**核心思想**: 不同问题类型应该选择不同的最佳capability

```python
question_type_best_capability = {
    # 问题模式 → 最佳capability
    r"what.*identity|who is": "identity_inference",
    r"what.*fields?|what.*study|education": "interest_inference",  # Q4应该用这个!
    r"what.*research": "fact_extraction",
    r"what.*community": "fact_extraction",
    r"when|what.*date": "temporal_calculation",
    r"why|what.*reason": "causal_reasoning",
    r"how long|duration": "duration_inference",
}
```

**实现**: 使用LLM或正则匹配,判断问题类型,给对应capability加分

### 维度2: 答案质量评估 (Answer Quality)

**评估指标**:
1. **Confidence分数** - capability自己返回的confidence
2. **答案长度合理性** - 太短(如"Caroline")或太长都扣分
3. **答案类型匹配** - 问题问fields,答案应该是academic fields而不是identity
4. **Evidence支持度** - 有明确memory支持的答案加分

```python
def evaluate_answer_quality(answer, question, evidence):
    score = 0.0

    # 1. Confidence加分
    score += confidence * 0.4

    # 2. 答案长度合理性
    if 3 <= len(answer.split()) <= 15:  # 合理长度
        score += 0.2

    # 3. 答案类型匹配
    if "fields" in question and is_academic_field(answer):
        score += 0.3
    elif "identity" in question and is_identity(answer):
        score += 0.3

    # 4. Evidence支持度
    if len(evidence) > 0:
        score += 0.1

    return score
```

### 维度3: Capability执行成功度

**评估指标**:
1. **是否有错误** - 有error的结果扣分
2. **是否有answer** - 没有answer的结果排除
3. **执行时间** - 太快可能是fallback,扣分

### 维度4: 上下文一致性 (Context Consistency)

**检查**:
- 如果问"What is X's identity?",答案不应该是活动、职业、研究内容
- 如果问"What fields?",答案应该是学科领域,不应该是身份特征

## 融合算法设计

### 方法1: 加权评分法 (推荐)

```python
async def _synthesize_answer_multidimensional(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    多维度答案融合

    维度权重:
    - Question-Capability相关性: 40%
    - 答案质量: 30%
    - Confidence: 20%
    - 上下文一致性: 10%
    """
    query = context['query']
    intermediate = context['intermediate_results']

    # 1. 分析问题类型
    question_type = await self._analyze_question_type(query)

    # 2. 评估每个capability的答案
    scored_results = []
    for cap_name, result in intermediate.items():
        if not result.get('answer'):
            continue

        score = 0.0

        # 维度1: Question-Capability相关性 (40%)
        semantic_score = self._calculate_semantic_relevance(
            question_type, cap_name, query
        )
        score += semantic_score * 0.4

        # 维度2: 答案质量 (30%)
        quality_score = self._evaluate_answer_quality(
            result.get('answer'),
            query,
            result.get('evidence', []),
            result.get('reasoning', '')
        )
        score += quality_score * 0.3

        # 维度3: Confidence (20%)
        confidence = result.get('confidence', 0.5)
        score += confidence * 0.2

        # 维度4: 上下文一致性 (10%)
        consistency_score = self._check_context_consistency(
            query, result.get('answer'), question_type
        )
        score += consistency_score * 0.1

        scored_results.append((score, cap_name, result))

    # 3. 选择最高分
    if scored_results:
        scored_results.sort(key=lambda x: x[0], reverse=True)
        best_score, best_cap, best_result = scored_results[0]

        logger.info(f"🎯 Multi-dimensional selection:")
        for score, cap, _ in scored_results[:3]:
            logger.info(f"   {cap}: {score:.2f}")
        logger.info(f"   → Selected: {best_cap} (score={best_score:.2f})")

        return {
            'answer': best_result['answer'],
            'confidence': best_result.get('confidence', 0.7),
            'primary_capability': best_cap,
            'selection_score': best_score
        }

    return {'answer': 'No valid answer', 'confidence': 0.1}
```

### 方法2: LLM驱动的答案选择 (更智能)

```python
async def _synthesize_answer_llm_driven(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用LLM判断哪个capability的答案最好
    """
    query = context['query']
    intermediate = context['intermediate_results']

    # 准备候选答案
    candidates = []
    for cap_name, result in intermediate.items():
        if result.get('answer'):
            candidates.append({
                'capability': cap_name,
                'answer': result.get('answer'),
                'confidence': result.get('confidence'),
                'reasoning': result.get('reasoning', '')
            })

    if not candidates:
        return {'answer': 'No answer available', 'confidence': 0.1}

    # LLM评估
    candidates_text = '\n\n'.join([
        f"Candidate {i+1} (from {c['capability']}):\n"
        f"  Answer: {c['answer']}\n"
        f"  Confidence: {c['confidence']}\n"
        f"  Reasoning: {c['reasoning']}"
        for i, c in enumerate(candidates)
    ])

    prompt = f"""You have multiple candidate answers from different reasoning capabilities.
Select the BEST answer that directly addresses the question.

Question: {query}

Candidates:
{candidates_text}

Selection Criteria:
1. Semantic relevance: Does the answer match what the question asks for?
   - If asking "what fields", answer should be academic fields (NOT identity)
   - If asking "what identity", answer should be identity (NOT activities)
2. Directness: Does it directly answer the question?
3. Conciseness: Is it appropriately concise?
4. Evidence quality: Is it well-supported?

Output JSON:
{{
    "selected_candidate": 1-{len(candidates)} (which candidate number),
    "reason": "why this answer is best",
    "final_answer": "the selected answer (or refined version)"
}}
"""

    # 调用LLM
    from src.agents.base import BrainAgent
    class TempSelector(BrainAgent):
        async def process_message(self, msg): return {}

    selector = TempSelector('answer_selector', 'prefrontal', 'Answer Selector')
    response = await selector.call_llm(prompt, temperature=0.1, max_tokens=300)

    # 解析选择结果
    import json
    result = json.loads(response)
    selected_idx = result['selected_candidate'] - 1

    logger.info(f"🎯 LLM-driven selection: {candidates[selected_idx]['capability']}")
    logger.info(f"   Reason: {result['reason']}")

    return {
        'answer': result.get('final_answer', candidates[selected_idx]['answer']),
        'confidence': candidates[selected_idx]['confidence'],
        'primary_capability': candidates[selected_idx]['capability'],
        'selection_reasoning': result['reason']
    }
```

### 方法3: 混合策略 (平衡性能与准确性)

```python
async def _synthesize_answer_hybrid(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    混合策略:
    1. 先用规则快速筛选 (低成本)
    2. 如果有冲突,再用LLM精细判断 (高成本)
    """
    query = context['query']
    intermediate = context['intermediate_results']

    # 步骤1: 快速规则筛选
    question_type = self._detect_question_type(query)

    # 根据问题类型优先选择
    priority_map = {
        'identity': ['identity_inference', 'fact_extraction'],
        'fields': ['interest_inference', 'multi_hop_inference'],
        'temporal': ['temporal_calculation', 'duration_inference'],
        'factual': ['fact_extraction', 'memory_retrieval'],
        'reasoning': ['multi_hop_inference', 'causal_reasoning']
    }

    preferred_caps = priority_map.get(question_type, [])

    # 收集答案
    high_priority = []
    low_priority = []

    for cap_name, result in intermediate.items():
        if not result.get('answer'):
            continue
        if cap_name in preferred_caps:
            high_priority.append((cap_name, result))
        else:
            low_priority.append((cap_name, result))

    # 步骤2: 判断是否需要LLM
    if len(high_priority) == 1:
        # 只有一个高优先级答案,直接返回
        cap_name, result = high_priority[0]
        logger.info(f"🎯 Rule-based selection: {cap_name} (clear match)")
        return {
            'answer': result['answer'],
            'confidence': result.get('confidence', 0.7),
            'primary_capability': cap_name
        }

    elif len(high_priority) > 1:
        # 多个高优先级答案冲突,使用LLM
        logger.info(f"⚖️ Multiple candidates, using LLM arbitration")
        return await self._llm_arbitration(query, high_priority)

    elif len(low_priority) > 0:
        # 没有高优先级,从低优先级中选confidence最高的
        low_priority.sort(key=lambda x: x[1].get('confidence', 0), reverse=True)
        cap_name, result = low_priority[0]
        logger.info(f"🎯 Fallback selection: {cap_name} (highest confidence)")
        return {
            'answer': result['answer'],
            'confidence': result.get('confidence', 0.5),
            'primary_capability': cap_name
        }

    return {'answer': 'No valid answer', 'confidence': 0.1}

def _detect_question_type(self, query: str) -> str:
    """快速检测问题类型"""
    q = query.lower()

    if any(kw in q for kw in ['identity', 'who is', 'who are']):
        return 'identity'
    elif any(kw in q for kw in ['field', 'study', 'education', 'pursue', 'major']):
        return 'fields'
    elif any(kw in q for kw in ['when', 'date', 'time', 'how long']):
        return 'temporal'
    elif any(kw in q for kw in ['why', 'reason', 'because', 'cause']):
        return 'reasoning'
    else:
        return 'factual'
```

## 实现推荐

### 阶段1: 快速改进 (方法3 - 混合策略)
**优点**:
- 性能好 (大多数情况用规则)
- 准确性高 (冲突时用LLM)
- 易于理解和调试

**适用场景**: 当前BMAM系统,快速提升准确率

### 阶段2: 完整优化 (方法1 + 方法2)
**优点**:
- 多维度评分更全面
- LLM驱动更智能
- 可解释性强

**适用场景**: 生产环境,追求最高准确率

## Q4案例分析

### 问题: "What fields would Caroline be likely to pursue in her education?"

**当前系统**:
1. CapabilityAnalyzer选择: `['interest_inference', 'pattern_recognition', 'identity_inference']`
2. 并行执行:
   - identity_inference → "transgender woman" (confidence=0.85)
   - interest_inference → "social work, community advocacy" (confidence=0.80)
   - pattern_recognition → 可能失败
3. 简单优先级: identity_inference (priority=1) 胜出
4. **错误答案**: "transgender woman" ❌

**使用混合策略**:
1. 检测问题类型: `'fields'`
2. 优先capability: `['interest_inference', 'multi_hop_inference']`
3. 高优先级答案: interest_inference → "social work, community advocacy"
4. **正确答案**: "social work" ✅ (或需要进一步concise)

## 实现位置

**文件**: `src/reasoning/capability_orchestrator.py`

**修改**:
1. 替换`_synthesize_answer` (line 668-719)
2. 添加辅助函数:
   - `_detect_question_type`
   - `_calculate_semantic_relevance`
   - `_evaluate_answer_quality`
   - `_check_context_consistency`
   - `_llm_arbitration`

**配置**:
```python
# 环境变量控制策略
ANSWER_SYNTHESIS_STRATEGY = os.getenv('ANSWER_SYNTHESIS_STRATEGY', 'hybrid')
# 可选: 'simple_priority', 'multidimensional', 'llm_driven', 'hybrid'
```

## 预期效果

**Q4修复**:
- Before: "transgender woman" ❌
- After: "social work, community advocacy" → 提炼为 "social work" ✅

**整体准确率**:
- Before: 80% (4/5)
- After: 100% (5/5) 🎯

**性能影响**:
- 混合策略: +1-2s (仅冲突时用LLM)
- LLM驱动: +2-3s (每次都用LLM)
- 多维度评分: +0.5s (纯计算)
