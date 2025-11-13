# Adaptive Routing Analysis: Where is "Adaptive" Actually?
# 自适应路由分析：自适应到底体现在哪里？

**Date:** 2025-11-11
**Issue:** 当前HRM实现对**所有查询**都使用完整推理流程
**Problem:** "不是所有的信息都需要推理"

---

## Current Problem | 当前问题

### 用户的关键洞察

> "自适应是体现在哪里？不是所有的信息都需要推理吧"

**完全正确！** 当前实现有严重的**过度推理**问题：

```python
# 当前流程：所有查询都走HRM全流程
async def process(self, user_input: str) -> str:
    # 无论查询简单还是复杂，都调用Thalamus
    result = await self.thalamus.process(user_input)

    # Thalamus会启动：
    # - Prefrontal (慢速战略规划)
    # - Hippocampus (快速检索)
    # - ACC (自适应停止)
    # - Basal Ganglia (固定点检测)
    # ... 所有机制都运行！
```

### 问题示例

**简单查询：**
```python
"你好"  # 仅需问候响应
→ 却运行完整HRM流程
→ Prefrontal战略规划（不需要）
→ Hippocampus记忆检索（不需要）
→ 多轮迭代（浪费）
→ 最终返回"你好"
```

**事实查询：**
```python
"今天几号？"  # 直接返回日期
→ 运行完整HRM流程（不需要）
→ Thalamus协调10步慢速更新（浪费）
→ ACC迭代判断（不需要）
```

**复杂推理：**
```python
"分析AI对社会的长远影响"  # 确实需要深度推理
→ 运行完整HRM流程 ✅ 正确
```

---

## Missing: Query Classification & Fast Path
## 缺失：查询分类与快速路径

### 应该有的"自适应"层级

```
用户查询
    ↓
┌─────────────────────────────────────┐
│  1. Query Classifier (查询分类器)    │  ← 缺失！
│  - 简单问候                           │
│  - 事实查询                           │
│  - 记忆检索                           │
│  - 复杂推理                           │
└─────────────────────────────────────┘
    ↓
    ├─→ Fast Path (快速路径) ← 80%的查询应该走这里
    │   - 直接返回
    │   - 无需推理
    │   - 0-1步
    │
    └─→ HRM Path (推理路径) ← 20%的查询才需要
        - 完整HRM机制
        - 多轮迭代
        - 3-20步
```

### 当前实现：100%走HRM路径

```
用户查询
    ↓
┌─────────────────────────────────────┐
│  ❌ 没有分类器                        │
└─────────────────────────────────────┘
    ↓
    └─→ HRM Path (所有查询) ← 100%
        - Thalamus协调
        - 多时间尺度
        - ACT判断
        - 固定点检测
        浪费！
```

---

## Where "Adaptive" Should Be | 自适应应该在哪里

### Level 1: Query-Level Adaptation (查询级自适应) - **缺失**

**根据查询类型选择路径：**

```python
class QueryRouter:
    """查询路由器 - Level 1 自适应"""

    async def route_query(self, query: str) -> str:
        # 分类
        query_type = self.classify_query(query)

        if query_type == QueryType.GREETING:
            # Fast Path: 直接返回
            return await self.greeting_handler.handle(query)

        elif query_type == QueryType.FACT:
            # Fast Path: 单步检索
            return await self.fact_retriever.retrieve(query)

        elif query_type == QueryType.MEMORY:
            # Medium Path: 记忆检索（无推理）
            return await self.memory_retriever.retrieve(query)

        elif query_type == QueryType.REASONING:
            # Full HRM Path: 完整推理
            return await self.hrm_coordinator.process(query)

        else:
            # Uncertain: 使用HRM（保守）
            return await self.hrm_coordinator.process(query)
```

### Level 2: Iteration-Level Adaptation (迭代级自适应) - **部分实现**

**ACT机制（已实现）：**

```python
# ✅ 已有：ACC判断何时停止
should_continue, confidence = await acc.should_continue_thinking(
    current_state=state,
    iteration=i
)

if not should_continue:
    break  # 自适应停止
```

**问题：** 只对进入HRM的查询有效，无法避免简单查询进入HRM

### Level 3: Region-Level Adaptation (脑区级自适应) - **已实现**

**多时间尺度（已实现）：**

```python
# ✅ 已有：不同脑区不同更新频率
Prefrontal: 每10步更新（慢）
Hippocampus: 每1步更新（快）
```

**问题：** 对简单查询来说，即使是"快速"更新也是浪费

---

## Proposed Solution: Three-Tier Adaptive Routing
## 解决方案：三层自适应路由

### Architecture | 架构

```
┌─────────────────────────────────────────────────────────┐
│  User Query                                              │
└─────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────┐
│  Tier 1: Query Classifier (查询分类器)                   │
│  - Rule-based patterns (规则匹配)                        │
│  - Lightweight LLM classification (轻量分类)             │
│  - Complexity estimation (复杂度估计)                    │
│  Cost: ~10ms                                             │
└─────────────────────────────────────────────────────────┘
    ↓
    ├─→ Fast Path (Level 0 - 直接响应) - 40%
    │   - Greetings: "你好", "谢谢"
    │   - Simple facts: "今天几号"
    │   - Commands: "/help"
    │   Cost: ~50ms
    │
    ├─→ Memory Path (Level 1 - 单步检索) - 30%
    │   - "我昨天说了什么"
    │   - "Caroline是谁"
    │   - Retrieval without reasoning
    │   Cost: ~200ms
    │
    ├─→ Analysis Path (Level 2 - 浅层推理) - 20%
    │   - "总结一下..."
    │   - "比较X和Y"
    │   - Use HRM but with lower max_iterations (5-10)
    │   Cost: ~1-2s
    │
    └─→ Deep Reasoning Path (Level 3 - 深度推理) - 10%
        - "分析...的影响"
        - "设计一个..."
        - Full HRM with max_iterations (20+)
        - Cost: ~3-10s
```

### Implementation | 实现

#### 1. Query Classifier (New)

```python
# src/coordination/query_classifier.py

from enum import IntEnum
from typing import Tuple, Dict, Any

class QueryComplexity(IntEnum):
    """查询复杂度等级"""
    TRIVIAL = 0      # 问候、简单命令
    SIMPLE = 1       # 事实查询、单步检索
    MODERATE = 2     # 分析、总结
    COMPLEX = 3      # 深度推理、创作

class QueryClassifier:
    """
    Query Classifier for Adaptive Routing
    查询分类器用于自适应路由

    Determines query complexity and routes to appropriate processing path.
    """

    def __init__(self):
        # Rule-based patterns
        self.greeting_patterns = [
            r'^(你好|hi|hello|hey)[\s\!！]*$',
            r'^(谢谢|thanks|thank you)[\s\!！]*$',
            r'^(再见|bye|goodbye)[\s\!！]*$'
        ]

        self.fact_patterns = [
            r'^(今天|现在)(几号|什么时间|星期几)',
            r'^天气(怎么样|如何)',
            r'^\d+[\+\-\*\/]\d+',  # 数学计算
        ]

        self.memory_patterns = [
            r'(我|你)(昨天|之前|刚才)(说|提到|讲)',
            r'(记得|还记得|回忆).*吗[\?？]',
            r'^(谁|什么|哪里|when|who|what|where)是',
        ]

        self.reasoning_keywords = [
            '分析', '评估', '设计', '规划', '解释为什么',
            'analyze', 'evaluate', 'design', 'explain why',
            '影响', '原因', '未来', 'future', 'impact'
        ]

    def classify(self, query: str) -> Tuple[QueryComplexity, Dict[str, Any]]:
        """
        Classify query complexity
        分类查询复杂度

        Returns:
            (complexity_level, reasoning)
        """
        query_lower = query.lower().strip()

        # Check trivial (Level 0)
        if self._matches_patterns(query_lower, self.greeting_patterns):
            return QueryComplexity.TRIVIAL, {
                'type': 'greeting',
                'reason': 'Matches greeting pattern',
                'estimated_cost_ms': 50
            }

        if len(query_lower) < 5:
            return QueryComplexity.TRIVIAL, {
                'type': 'short_command',
                'reason': 'Very short query',
                'estimated_cost_ms': 50
            }

        # Check simple (Level 1)
        if self._matches_patterns(query_lower, self.fact_patterns):
            return QueryComplexity.SIMPLE, {
                'type': 'fact_query',
                'reason': 'Matches fact pattern',
                'estimated_cost_ms': 200
            }

        if self._matches_patterns(query_lower, self.memory_patterns):
            return QueryComplexity.SIMPLE, {
                'type': 'memory_retrieval',
                'reason': 'Matches memory pattern',
                'estimated_cost_ms': 200
            }

        # Check complex (Level 3)
        if any(kw in query_lower for kw in self.reasoning_keywords):
            return QueryComplexity.COMPLEX, {
                'type': 'deep_reasoning',
                'reason': 'Contains reasoning keywords',
                'estimated_cost_ms': 5000
            }

        if len(query) > 100:
            return QueryComplexity.COMPLEX, {
                'type': 'long_query',
                'reason': 'Long query requires deep processing',
                'estimated_cost_ms': 3000
            }

        # Default to moderate (Level 2)
        return QueryComplexity.MODERATE, {
            'type': 'general_query',
            'reason': 'Default moderate complexity',
            'estimated_cost_ms': 1000
        }

    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern"""
        import re
        return any(re.search(pattern, text) for pattern in patterns)
```

#### 2. Adaptive Coordinator (Enhanced)

```python
# src/coordination/coordinator_v3_hrm.py (Enhanced)

class BrainInspiredCoordinatorV3_HRM:
    """
    Enhanced with adaptive routing
    """

    def __init__(self, ...):
        # ... existing init ...

        # NEW: Query classifier for adaptive routing
        self.query_classifier = QueryClassifier()

        # NEW: Fast path handlers
        self.greeting_handler = GreetingHandler()
        self.fact_handler = FactHandler()
        self.memory_handler = MemoryHandler(self.memory_system)

    async def process(self, user_input: str, context: Optional[Dict] = None) -> str:
        """
        Process with Adaptive Routing
        自适应路由处理
        """
        # 1. Classify query
        complexity, reasoning = self.query_classifier.classify(user_input)

        logger.info(f"Query complexity: {complexity.name} ({reasoning['reason']})")
        logger.info(f"Estimated cost: {reasoning['estimated_cost_ms']}ms")

        # 2. Route to appropriate path
        if complexity == QueryComplexity.TRIVIAL:
            # Fast Path: Direct response
            return await self._fast_path_trivial(user_input, reasoning)

        elif complexity == QueryComplexity.SIMPLE:
            # Memory Path: Single retrieval
            return await self._fast_path_simple(user_input, reasoning)

        elif complexity == QueryComplexity.MODERATE:
            # Analysis Path: Light HRM (max 10 iterations)
            return await self._hrm_path_moderate(user_input, context, max_iter=10)

        else:  # COMPLEX
            # Deep Reasoning Path: Full HRM (max 20 iterations)
            return await self._hrm_path_complex(user_input, context, max_iter=20)

    async def _fast_path_trivial(self, query: str, reasoning: Dict) -> str:
        """
        Fast Path for Trivial Queries (Level 0)
        琐碎查询的快速路径

        Cost: ~50ms
        Examples: "你好", "谢谢", "/help"
        """
        query_type = reasoning['type']

        if query_type == 'greeting':
            return await self.greeting_handler.handle(query)

        elif query_type == 'short_command':
            return await self._handle_command(query)

        return "I don't understand. Could you elaborate?"

    async def _fast_path_simple(self, query: str, reasoning: Dict) -> str:
        """
        Fast Path for Simple Queries (Level 1)
        简单查询的快速路径

        Cost: ~200ms
        Examples: "今天几号", "我昨天说了什么"
        """
        query_type = reasoning['type']

        if query_type == 'fact_query':
            return await self.fact_handler.handle(query)

        elif query_type == 'memory_retrieval':
            # Single-step memory retrieval (no reasoning)
            memories = await self.memory_handler.retrieve(query, k=5)
            return self._format_memory_response(memories)

        return await self._hrm_path_moderate(query, {}, max_iter=5)

    async def _hrm_path_moderate(
        self,
        query: str,
        context: Dict,
        max_iter: int = 10
    ) -> str:
        """
        Moderate HRM Path (Level 2)
        中等推理路径

        Cost: ~1-2s
        Max iterations: 10 (vs 20 for complex)
        """
        # Configure HRM for lighter processing
        original_max = self.anterior_cingulate.max_iterations
        self.anterior_cingulate.max_iterations = max_iter

        try:
            result = await self.thalamus.process(query)
            return result
        finally:
            self.anterior_cingulate.max_iterations = original_max

    async def _hrm_path_complex(
        self,
        query: str,
        context: Dict,
        max_iter: int = 20
    ) -> str:
        """
        Deep Reasoning HRM Path (Level 3)
        深度推理路径

        Cost: ~3-10s
        Max iterations: 20
        Full HRM capabilities
        """
        # Full HRM processing (existing implementation)
        return await self.thalamus.process(query)
```

#### 3. Fast Path Handlers (New)

```python
# src/coordination/fast_path_handlers.py

class GreetingHandler:
    """Handle greeting queries without reasoning"""

    GREETINGS = {
        'zh': {
            '你好': '你好！有什么我可以帮助你的吗？',
            '谢谢': '不客气！很高兴能帮到你。',
            '再见': '再见！祝你有美好的一天！'
        },
        'en': {
            'hi': 'Hello! How can I help you today?',
            'hello': 'Hi there! What can I do for you?',
            'thanks': 'You\'re welcome! Happy to help.',
            'bye': 'Goodbye! Have a great day!'
        }
    }

    async def handle(self, query: str) -> str:
        query_lower = query.lower().strip()

        # Try Chinese
        for pattern, response in self.GREETINGS['zh'].items():
            if pattern in query_lower:
                return response

        # Try English
        for pattern, response in self.GREETINGS['en'].items():
            if pattern in query_lower:
                return response

        return "Hello! How can I assist you?"

class FactHandler:
    """Handle factual queries without reasoning"""

    async def handle(self, query: str) -> str:
        from datetime import datetime

        # Date/time queries
        if '今天' in query or '现在' in query:
            if '几号' in query or '日期' in query:
                return datetime.now().strftime("今天是%Y年%m月%d日")
            elif '星期' in query:
                weekdays = ['一', '二', '三', '四', '五', '六', '日']
                return f"今天是星期{weekdays[datetime.now().weekday()]}"
            elif '时间' in query:
                return datetime.now().strftime("现在是%H:%M:%S")

        # Math queries (simple)
        if '+' in query or '-' in query or '*' in query or '/' in query:
            try:
                result = eval(query.strip())
                return f"结果是: {result}"
            except:
                pass

        return "抱歉，我无法回答这个事实性问题。"

class MemoryHandler:
    """Handle memory retrieval without reasoning"""

    def __init__(self, memory_system):
        self.memory_system = memory_system

    async def retrieve(self, query: str, k: int = 5) -> List[Dict]:
        """Single-step memory retrieval"""
        memories = await self.memory_system.search_memories(query, k=k)
        return memories
```

---

## Performance Impact | 性能影响

### Before (All HRM)

```
Query: "你好"
→ Full HRM processing
→ 3-20 iterations
→ Cost: ~2-5s

Query: "今天几号"
→ Full HRM processing
→ 3-20 iterations
→ Cost: ~2-5s

Query: "分析AI影响"
→ Full HRM processing
→ 3-20 iterations
→ Cost: ~3-10s

Average: ~3-7s per query
```

### After (Adaptive Routing)

```
Query: "你好" (Trivial - 40%)
→ Fast path
→ 0 iterations
→ Cost: ~50ms ✅ 100x faster

Query: "今天几号" (Simple - 30%)
→ Memory path
→ 1 step
→ Cost: ~200ms ✅ 25x faster

Query: "总结一下" (Moderate - 20%)
→ Light HRM
→ 3-10 iterations
→ Cost: ~1-2s ✅ 2x faster

Query: "分析AI影响" (Complex - 10%)
→ Full HRM
→ 3-20 iterations
→ Cost: ~3-10s (same)

Average: ~500ms per query ✅ 6-14x faster overall!
```

---

## Metrics to Track | 跟踪指标

```python
{
    'query_distribution': {
        'trivial': 0.40,      # 40% of queries
        'simple': 0.30,       # 30%
        'moderate': 0.20,     # 20%
        'complex': 0.10       # 10%
    },
    'avg_latency_by_level': {
        'trivial': 50,        # ms
        'simple': 200,
        'moderate': 1500,
        'complex': 5000
    },
    'classification_accuracy': 0.85,  # 85% correctly classified
    'false_positives': {
        'trivial_as_complex': 0.02,   # 2% over-estimated
        'complex_as_trivial': 0.01    # 1% under-estimated
    }
}
```

---

## Implementation Priority | 实施优先级

### Phase 1 (本周)
1. ✅ Create `QueryClassifier` with rule-based patterns
2. ✅ Implement fast path handlers (Greeting, Fact, Memory)
3. ✅ Enhance `CoordinatorV3` with routing logic
4. ✅ Add classification metrics

### Phase 2 (下周)
5. Add LLM-based classification for ambiguous queries
6. Tune classification thresholds based on metrics
7. A/B test adaptive vs non-adaptive

### Phase 3 (2周后)
8. Learn classification from usage patterns
9. Auto-tune complexity thresholds
10. Personalized routing per user

---

## Conclusion | 结论

### 你的问题非常准确

> "自适应是体现在哪里？不是所有的信息都需要推理吧"

**当前状态：**
- ❌ 自适应只在**迭代级别**（ACT何时停止）
- ❌ **没有查询级别自适应**（是否需要推理）
- ❌ 所有查询都走HRM（浪费）

**应该的自适应：**
- ✅ **Level 1: Query Classification** - 根据查询选择路径
- ✅ **Level 2: Iteration Adaptation** - 已有（ACT）
- ✅ **Level 3: Region Adaptation** - 已有（多时间尺度）

### 改进收益

**性能：**
- 40%查询：100x加速（问候）
- 30%查询：25x加速（事实）
- 20%查询：2x加速（分析）
- 10%查询：无变化（推理）
- **总体：6-14x加速**

**用户体验：**
- 简单查询即时响应（<100ms）
- 复杂查询深度推理（3-10s）
- 自适应资源分配

---

**状态：** ⏳ 设计完成，待实施
**预计工作量：** 2-3天
**优先级：** P0 - Critical UX Improvement
