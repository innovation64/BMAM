# 动态记忆推理框架 v2 - Memory-Aware Dynamic Reasoning

## 🎯 核心设计理念

**问题**: 当前框架依赖硬编码规则和例子来指导推理,缺乏真正的泛化能力

**解决方案**: 让推理能力直接检查记忆内容,自适应地决定推理策略

## 📐 架构设计

### 1. Memory-Aware Reasoning (记忆感知推理)

每个推理能力在执行时:
1. **检查记忆内容** - 分析记忆中包含的信息类型
2. **自适应选择策略** - 根据记忆内容动态决定推理方法
3. **无需外部规则** - 完全基于记忆本身的语义理解

```python
class MemoryAwareReasoning:
    async def reason(self, query: str, memories: List[Dict]) -> Dict:
        # 步骤1: 分析记忆内容特征
        memory_features = await self._analyze_memory_content(memories)

        # 步骤2: 基于特征自适应推理
        if memory_features['has_relative_time']:
            return await self._temporal_inference(query, memories, memory_features)
        elif memory_features['has_behavioral_clues']:
            return await self._identity_inference(query, memories, memory_features)
        elif memory_features['has_career_mentions']:
            return await self._professional_inference(query, memories, memory_features)
        else:
            return await self._general_extraction(query, memories, memory_features)
```

### 2. Self-Adaptive Capability Selection (自适应能力选择)

不用预定义的Analyzer,而是:
1. **问题结构分析** - 只分析问句类型(When/What/Who),不给例子
2. **记忆内容触发** - 检索到的记忆自动触发相应推理能力
3. **动态能力组合** - 根据记忆内容动态决定需要哪些能力

```python
class SelfAdaptiveSelector:
    async def select_capabilities(self, query: str, memories: List[Dict]) -> List[str]:
        # 只分析问句结构,不依赖例子
        question_type = self._parse_question_structure(query)

        # 基于记忆内容触发能力
        capabilities = []

        # 检查记忆是否包含相对时间表达
        if self._contains_relative_time(memories):
            capabilities.append('temporal_reasoning')

        # 检查记忆是否包含身份线索
        if self._contains_identity_clues(memories):
            capabilities.append('identity_inference')

        # 检查记忆是否包含职业/教育相关内容
        if self._contains_professional_context(memories):
            capabilities.append('professional_inference')

        return capabilities
```

### 3. Content-Driven Reasoning (内容驱动推理)

每个推理能力的prompt完全基于记忆内容,不使用任何固定例子:

```python
async def _temporal_inference(self, query: str, memories: List[Dict], features: Dict) -> Dict:
    # 提取记忆中的时间线索
    time_clues = features['time_expressions']

    prompt = f"""Based ONLY on the memory content below, answer the temporal question.

Question: {query}

Memory Content:
{self._format_memories(memories)}

Detected Time Expressions: {time_clues}

Task:
1. If memories contain relative time (yesterday/last week), calculate the absolute date
2. Use the conversation date context if available
3. Return the specific date

Output JSON: {{"answer": "absolute date", "confidence": 0.0-1.0}}
"""
    # 完全基于记忆内容推理,无需任何例子
    return await self._llm_inference(prompt)
```

### 4. 推理能力实现原则

#### 4.1 时序推理 (Temporal Reasoning)
- 自动检测记忆中的时间表达(yesterday, last week, etc.)
- 提取对话日期上下文
- 动态计算相对时间→绝对时间

#### 4.2 身份推理 (Identity Inference)
- 检测记忆中的身份线索强度(transgender stories → strong clue)
- 要求推理出最具体的身份,不接受模糊分类
- 基于行为模式聚类推理

#### 4.3 职业/教育领域推理 (Professional Inference)
- 识别记忆中明确提到的职业意向("interested in counseling")
- 区分职业领域 vs 话题关键词
- 输出学术/专业领域名称

## 🔑 关键差异对比

| 维度 | 旧框架 (v1) | 新框架 (v2) |
|------|------------|------------|
| 能力选择 | 基于硬编码规则和例子 | 基于记忆内容特征自动触发 |
| 推理策略 | 固定prompt模板 | 完全基于记忆内容动态生成 |
| 泛化能力 | 依赖见过的例子 | 理解记忆语义,适用任何问题 |
| 规则依赖 | 大量if-else规则 | 零规则,纯语义理解 |

## 🚀 实现步骤

1. **MemoryContentAnalyzer** - 分析记忆内容特征
2. **AdaptiveReasoningEngine** - 自适应推理引擎
3. **MemoryAwareCapabilities** - 记忆感知的推理能力实现
4. **DynamicOrchestrator** - 动态编排器

## 📊 预期效果

- ✅ 无需任何硬编码规则
- ✅ 无需任何具体例子
- ✅ 完全基于记忆内容推理
- ✅ 真正的泛化能力
- ✅ 适用任何领域的问答
