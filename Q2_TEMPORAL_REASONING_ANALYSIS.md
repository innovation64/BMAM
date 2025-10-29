# Q2 Temporal Reasoning Failure Analysis
**Question**: "When did Melanie paint a sunrise?"
**Expected**: 2022
**Actual**: 6 October 2023
**Score**: 0.0

---

## Problem Statement

Q2 要求时间推理能力：根据相对时间表达（"last year"）+ 对话时间戳（2023年5月8日）推断出绝对时间（2022）。

### Ground Truth

**Evidence**: D1:14 (Session 1, Message 14)
```
Speaker: Melanie
dia_id: D1:14
Date: 8 May 2023, 1:56 pm
Text: "Yeah, I painted that lake sunrise last year! It's special to me."
```

**推理链**:
1. 对话发生在 2023年5月8日
2. Melanie 说 "last year"（去年）
3. 因此答案是 2022

---

## Root Cause Analysis

### 1. 检索问题

**Current Behavior**:
- Query: "When did Melanie paint a sunrise?"
- Top retrieved memory: Session 14 (BM25=0.833), NOT Session 1
- Session 1 only ranked #8 with BM25=0.667

**Why Session 1 ranked low**:
```
Query keywords: ["when", "melanie", "paint", "sunrise"]
Session 1 contains: "painted", "lake", "sunrise", "last", "year"
Session 14 contains: "melanie", "painted", (no "sunrise")
```

BM25 favors Session 14 because:
- Multiple "paint" mentions across the session
- More recent date (August 2023 vs May 2023)
- Longer content = more keyword matches

### 2. 时间推理问题

**Current System Cannot**:
- ❌ Parse "last year" as relative temporal expression
- ❌ Link "last year" to dialogue timestamp (8 May 2023)
- ❌ Calculate: 2023 - 1 = 2022
- ❌ Recognize that "6 October 2023" is AFTER the dialogue, impossible for "last year"

**LLM Generated Wrong Answer**:
```
Actual: "6 October 2023"
```

This suggests the LLM:
1. Retrieved memories from Session 17 (October 2023)
2. Found a painting event on 6 October
3. Ignored the "last year" temporal constraint
4. Returned a chronologically impossible answer

---

## Analysis of System Capabilities

### What Works
✅ Semantic retrieval finds painting-related memories
✅ BM25 + embedding hybrid scoring
✅ Temporal routing detects time-related queries

### What's Missing
❌ **Temporal Expression Parsing**: No "last year" → relative time conversion
❌ **Timeline Validation**: No check if answer makes temporal sense
❌ **Relative Time Calculation**: No anchor date → absolute date conversion
❌ **Temporal Consistency Check**: No validation that 2023 October > 2023 May

---

## Proposed Solution: Temporal Reasoning Enhancement

### Option 1: Temporal Reasoning Agent (Heavyweight)
创建新的 brain region 专门处理时间推理

**Pros**:
- Architectural清晰，符合多脑区协作模式
- 可复用于其他时间推理任务
- 可集成到 Phase 3a gap detection

**Cons**:
- 需要新的 agent 实现
- 增加系统复杂度
- 需要更多测试

### Option 2: Enhanced Retrieval with Temporal Parsing (Lightweight)
在现有检索中增强时间表达解析

**Pros**:
- 最小改动，利用现有架构
- 快速实现
- 专注解决 Q2 类问题

**Cons**:
- 功能局限于检索增强
- 不支持复杂时间推理

### Option 3: Hybrid Approach (Recommended)
结合两者优势：
1. **Retrieval Enhancement**: 解析查询中的时间表达，扩展检索关键词
2. **Temporal Validation**: 在记忆中提取时间信息，验证时间一致性
3. **Optional Agent**: 仅在复杂推理时触发专门的时间推理模块

---

## Recommended Implementation Plan

### Phase 1: Retrieval Enhancement (Quick Win)
**Goal**: 让 Q2 从 0.0 → 0.7+

**Changes**:
1. **Temporal Expression Expansion** in `smart_retrieve()`:
   - Detect "last year", "yesterday", "next week" etc.
   - Calculate absolute time based on session timestamp
   - Add absolute time to search keywords

2. **Timeline Validation** in memory ranking:
   - Extract dates from memories
   - Filter out chronologically impossible answers
   - Penalize memories with timeline conflicts

**Implementation**:
```python
# In brain_coordinator.py smart_retrieve()
if query_features.get('has_temporal_expression'):
    # Parse "last year" → 2022 (relative to session date)
    absolute_time = self._parse_temporal_expression(query, reference_date)
    # Add to search keywords
    expanded_query = f"{query} {absolute_time}"
```

### Phase 2: Temporal Consistency Checker (Medium-term)
**Goal**: Validate retrieved memories have temporally consistent information

**Changes**:
1. **Extract timeline from memories**:
   - Parse "last year", "yesterday", dates, etc.
   - Build timeline graph
   - Detect conflicts

2. **Rank memories by temporal consistency**:
   - Boost memories with matching timeframes
   - Penalize timeline violations

### Phase 3: Dedicated Temporal Reasoning Agent (Long-term)
**Goal**: Handle complex multi-hop temporal inference

**Use Cases**:
- "How long ago was Caroline's 18th birthday?" (requires age calculation)
- "When did Caroline move from Sweden?" (requires duration inference)
- "What happened between May and June?" (requires timeline sequencing)

---

## Success Criteria

### Minimum (Phase 1)
- ✅ Q2 score improves from 0.0 to ≥0.7
- ✅ System correctly parses "last year" → 2022
- ✅ Session 1 ranks in top 3 retrieved memories

### Target (Phase 2)
- ✅ Q2 score reaches 1.0
- ✅ Timeline validation prevents chronologically impossible answers
- ✅ No regression on other questions

### Stretch (Phase 3)
- ✅ All temporal reasoning questions (Q1, Q2, Q6, Q8, Q9) score ≥0.9
- ✅ System handles complex multi-hop temporal inference

---

## Estimated Impact

### Current LoCoMo小批 Score Breakdown
| Q | Type | Current | Potential with Fix |
|---|------|---------|-------------------|
| Q1 | Temporal (date) | 1.0 | 1.0 (no change) |
| Q2 | **Temporal (relative)** | **0.0** | **0.7-1.0** |
| Q3 | Inference | 0.8 | 0.8 (no change) |
| Q4 | Factual | 1.0 | 1.0 (no change) |
| Q5 | Identity | 0.9 | 0.9 (no change) |

**Projected Score**:
- Current: 3.7/5 (74%)
- With Q2 Fix (0.7): 4.4/5 (88%) ✅ **+0.7 improvement**
- With Q2 Fix (1.0): 4.7/5 (94%) ✅ **+1.0 improvement**

---

## Next Steps

1. ✅ **Complete this analysis** (DONE)
2. ⏳ **Implement Phase 1**: Temporal expression parsing + retrieval enhancement
3. ⏳ **Test on Q2**: Verify score improves to ≥0.7
4. ⏳ **Validate no regression**: Run full LoCoMo小批 test
5. ⏳ **Document results**: Create Q2_FIX_REPORT.md

---

## References

- **Q2 Test Results**: locomo_small_20251028_160922_final.json
- **Q2 Retrieval Log**: /tmp/locomo_phase3a_final.log (lines 2025-10-28 16:07:53 onwards)
- **LoCoMo Data**: /Users/liyang/Desktop/testversion/MemOS/evaluation/data/locomo/locomo10.json
- **Evidence Location**: D1:14 ("Yeah, I painted that lake sunrise last year!")
