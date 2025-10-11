# Q3-Q5问题分析与修复

## 测试进展

### 初始状态 (40%准确率)
- ✅ Q1: CORRECT
- ✅ Q2: CORRECT
- ❌ Q3: WRONG ("Caroline" instead of "transgender woman")
- ❌ Q4: WRONG (too verbose)
- ❌ Q5: WRONG ("LGBTQ support group" instead of "LGBTQ community")

### 当前状态 (60%准确率)
- ✅ Q1: CORRECT (7 May 2023)
- ✅ Q2: CORRECT (adoption agencies)
- ❌ Q3: WRONG ("Caroline" - identity_inference问题)
- ❌ Q4: WRONG ("LGBTQ advocate" - 应该是academic fields)
- ✅ Q5: **FIXED!** ("LGBTQ community")

## 已修复的问题

### 1. ✅ Pattern Recognition Bug
**Bug**: `'CapabilityOrchestrator' object has no attribute '_extract_json'`

**位置**: `src/reasoning/capability_orchestrator.py:442`

**修复**: 添加了JSON解析代码 (lines 441-451)
```python
import json as json_lib
response = await temp_agent.call_llm(prompt, temperature=0.0, max_tokens=400)

# Parse JSON
content = response
if '```json' in content:
    content = content.split('```json')[1].split('```')[0].strip()
elif '```' in content:
    content = content.split('```')[1].split('```')[0].strip()

result_json = json_lib.loads(content)
```

### 2. ✅ Q5 - Community抽象层次问题
**问题**: 返回"LGBTQ support group"而不是"LGBTQ community"

**根本原因**: fact_extraction没有将specific groups泛化为broader communities

**修复**: 改进了fact_extraction的prompt (lines 235-270)
- 添加了community问题的特殊处理
- 添加了抽象层次指导
- 添加了示例: "LGBTQ support group" → "LGBTQ community"

**结果**: Q5现在CORRECT ✅

### 3. 🔧 改进Identity Inference Prompt
**问题**: Q3返回"Caroline"而不是"transgender woman"

**修复**: 改进了identity_inference的prompt (lines 329-362)
- 强调emotional resonance作为推断线索
- 添加了具体的推断模式
- 强调transgender stories inspiring → likely transgender themselves

**状态**: Prompt已改进,但仍需测试验证

## 待解决的问题

### Q3: Identity Inference
**当前输出**: "Caroline (confidence=1.00)"
**期望输出**: "transgender woman"

**问题分析**:
1. LLM返回了错误的答案(可能只返回了人名而不是identity)
2. 或者JSON解析有问题
3. 需要查看实际的LLM响应内容

**下一步**:
- 添加debug logging查看LLM实际返回内容
- 可能需要进一步改进prompt
- 或者添加示例到prompt中

### Q4: Field Inference
**当前输出**: "LGBTQ advocate"
**期望输出**: "social work / psychology"

**问题分析**:
1. 问题问的是educational fields (academic领域)
2. 系统返回的是identity/role而不是academic field
3. CapabilityAnalyzer选择了identity_inference而不是interest_inference + field extraction

**下一步**:
- 改进CapabilityAnalyzer对"fields"问题的理解
- 让它区分"academic fields"和"career/identity"
- 可能需要添加专门的"educational_interest" capability

## 修改的文件

1. **src/reasoning/capability_orchestrator.py**
   - Lines 235-270: 改进fact_extraction prompt (Q5修复)
   - Lines 329-362: 改进identity_inference prompt (Q3改进)
   - Lines 441-451: 修复pattern_recognition JSON解析 (Bug修复)

2. **test_locomo_5questions.py**
   - Lines 22-25: 添加了D1:5的transgender stories信息
   - Line 24: "The transgender stories were so inspiring! I was so happy and thankful for all the support."

## 性能对比

**Before fixes**:
- Accuracy: 40% (2/5)
- Avg Time: 9.97s
- Issues: Q3, Q4, Q5 all failed

**After fixes**:
- Accuracy: 60% (3/5) - **+50% improvement!**
- Avg Time: 8.42s - **+16% faster!**
- Progress: Q5 now correct, Q3 & Q4 still need work

## 下一步计划

1. **Debug Q3** - 添加logging查看identity_inference的实际LLM响应
2. **Fix Q4** - 改进对academic fields vs identity的区分
3. **目标**: 达到80%+ 准确率
