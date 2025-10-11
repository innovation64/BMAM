# BMAM真实架构 - 类脑分布式协作系统

## 核心设计理念

**你说的完全正确**: "类脑不应该是pipeline,应该是图拓扑的形式,每个智能体分布式协作"

---

## 真实架构: BrainNetwork图拓扑激活扩散

### 核心机制

```python
class BrainNetwork:
    """
    大脑激活扩散网络

    模拟真实大脑:
    - 刺激到达 → 多个脑区同时激活 (并行)
    - 激活扩散 → 通过连接权重传播 (图拓扑)
    - 循环反馈 → 前额叶↔海马体往复 (分布式协作)
    - 动态收敛 → 达成一致后输出 (收敛机制)
    """
```

### 工作流程

```
t=0ms: 刺激到达
  ↓
┌─────────────────────────────────────────────┐
│ 阶段1: 初始激活 (t=0ms)                      │
│ - perception_encoding: 1.0                  │
│ - short_term_memory: 0.8                    │
│ - memory_retrieval: 0.9 (如果有记忆)        │
│ - executive_control: 0.5                    │
└───────────────┬─────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ 阶段2: 激活扩散迭代 (t=0-250ms)             │
│                                             │
│ for iteration in range(5):  # 5次迭代      │
│   ┌───────────────────────────────────────┐│
│   │ Step 1: 并行计算新激活                ││
│   │ - 每个脑区收集来自其他脑区的输入       ││
│   │ - 新激活 = Σ(源激活 × 连接权重)       ││
│   │ - asyncio.gather()并行执行            ││
│   └───────────────────────────────────────┘│
│   ┌───────────────────────────────────────┐│
│   │ Step 2: 更新激活并执行agent          ││
│   │ - 如果激活 > 0.3, 执行该agent功能     ││
│   │ - 结果写入workspace (全局工作区)     ││
│   └───────────────────────────────────────┘│
│   ┌───────────────────────────────────────┐│
│   │ Step 3: 检查收敛                      ││
│   │ - 关键脑区激活 > 0.8?                ││
│   │ - 是 → 收敛,跳出循环                 ││
│   │ - 否 → 继续下一次迭代                ││
│   └───────────────────────────────────────┘│
│                                             │
└───────────────┬─────────────────────────────┘
                ↓
┌─────────────────────────────────────────────┐
│ 阶段3: 提取共识答案                          │
│ - 从workspace提取各脑区输出                 │
│ - 综合为最终答案                            │
│ - 返回 {response, confidence, ...}         │
└─────────────────────────────────────────────┘
```

### 图拓扑连接 (脑科学启发)

```python
# 连接权重: {(source, target): weight}
connections = {
    # 感知 → 记忆检索
    ('perception_encoding', 'memory_retrieval'): 0.8,

    # 海马体 ↔ 前额叶 (双向强连接)
    ('memory_retrieval', 'reasoning_validator'): 0.9,
    ('reasoning_validator', 'memory_retrieval'): 0.7,

    # 工作记忆 → 长期记忆
    ('short_term_memory', 'long_term_memory'): 0.6,

    # 反思 ← 多个源
    ('conversation', 'reflection'): 0.5,
    ('reasoning_validator', 'reflection'): 0.6,

    # ... 26个默认连接
}
```

**关键**: 这是**图结构**,不是树或线性pipeline!

---

## 分布式记忆系统

### 设计理念

**记忆与推理深度融合** - 你说的对!

```python
# 分布式记忆 - 每个脑区存储不同类型
distributed_memory = {
    'hippocampus': [情节记忆],      # 海马体: 事件、时间
    'temporal_lobe': [语义记忆],    # 颞叶: 概念、知识
    'prefrontal': [工作记忆],        # 前额叶: 推理中间结果
    'amygdala': [情绪记忆],          # 杏仁核: 情绪标签
    'parietal': [空间记忆]           # 顶叶: 位置、关系
}
```

### 记忆检索流程

```python
# 1. 语义相似度检索 (FAISS)
memories = await memory_retrieval.semantic_search(query, k=20)

# 2. 分布式分配到脑区
for mem in memories:
    if '事件' in mem.content:
        hippocampus.add(mem)  # 海马体存储
    if '概念' in mem.content:
        temporal_lobe.add(mem)  # 颞叶存储
    # ...

# 3. 推理时从分布式记忆提取
context = distributed_memory.retrieve_from_regions(
    query=query,
    regions=['hippocampus', 'temporal_lobe'],
    time_range={'start': '2023-05-08', 'end': '2023-05-25'}
)

# 4. 推理agent使用记忆上下文
answer = await reasoning_validator.reason(
    query=query,
    memories=context  # 记忆融入推理!
)
```

**融合点**: 记忆不是独立模块,而是融入每个推理步骤!

---

## brain_coordinator的真实角色

### 两种模式

```python
class BrainInspiredCoordinator:
    def __init__(self):
        # 初始化BrainNetwork (图拓扑)
        self.brain_network = BrainNetwork(agents=self.agents)

        # 环境变量控制模式
        self.use_brain_network = os.getenv('USE_BRAIN_NETWORK', 'true').lower() == 'true'

    async def process_user_input(self, user_input: str) -> ProcessingResult:
        if self.use_brain_network:
            # 模式1: BrainNetwork图拓扑 (类脑)
            return await self._process_with_brain_network(...)
        else:
            # 模式2: Pipeline串行 (传统,fallback)
            return await self._process_with_pipeline(...)
```

### _process_with_brain_network

**这才是真正的类脑流程!**

```python
async def _process_with_brain_network(self, user_input, context, start_time):
    # 步骤1: 语言检测
    language = await perception_encoding.detect_language(user_input)

    # 步骤2: 能力分析 (CapabilityAnalyzer)
    capability_analysis = await CapabilityAnalyzer().analyze(user_input)
    capabilities = capability_analysis['capabilities']

    # 步骤3: 复杂度检测
    complexity_level = ...  # 0-3

    # 步骤4: 记忆检索
    memories = await memory_retrieval.semantic_search(
        query=user_input,
        k=20,
        time_range=time_range  # 🔥 时间过滤!
    )

    # 步骤5: 分布式记忆分配
    distributed_memory.distribute_to_regions(memories)

    # 🔥 核心: 如果有特殊推理能力需求
    if len(capabilities) > 0:
        # 使用CapabilityOrchestrator编排推理
        orchestrator = CapabilityOrchestrator(brain_agents)
        result = await orchestrator.execute(
            query=user_input,
            capabilities=capabilities,
            memories=memories  # 记忆融入!
        )
        return ProcessingResult(mode='capability_orchestrator', ...)

    # 🧠 否则: 使用BrainNetwork图拓扑激活扩散
    network_result = await self.brain_network.process(
        stimulus=user_input,
        context={
            'memories': memories,  # 记忆融入!
            'complexity': complexity_level
        },
        max_iterations=5
    )
    return ProcessingResult(mode='brain_network', ...)
```

---

## CapabilityOrchestrator的正确位置

### 设计意图 (我现在理解了!)

**CapabilityOrchestrator是推理编排层,位于BrainNetwork之上!**

```
用户输入
  ↓
brain_coordinator.process_user_input()
  ↓
┌─────────────────────────────────────────┐
│ CapabilityAnalyzer                      │
│ 分析需要哪些推理能力                     │
│ → ['memory_retrieval', 'identity_inference'] │
└──────────────┬──────────────────────────┘
               ↓
         有特殊能力需求?
         /              \
       是                否
       ↓                 ↓
┌──────────────────┐  ┌──────────────────┐
│CapabilityOrche   │  │ BrainNetwork     │
│ strator          │  │ (图拓扑激活扩散)  │
│ - 编排推理步骤    │  │ - 通用处理       │
│ - 调用brain       │  │ - 迭代收敛       │
│   agents执行      │  │                  │
│ - 应用约束规则    │  │                  │
└──────────────────┘  └──────────────────┘
```

### 两者关系

**CapabilityOrchestrator** (高层):
- 针对复杂推理任务 (identity inference, multi-hop reasoning)
- 动态编排推理步骤
- 调用brain agents执行
- 使用ConditionalConstraintEngine优化

**BrainNetwork** (底层):
- 通用信息处理
- 图拓扑激活扩散
- 所有agents分布式协作
- 迭代收敛机制

**关键**: CapabilityOrchestrator**调用**BrainNetwork中的agents,不是替换!

---

## 记忆与推理融合的3个层次

### 层次1: 记忆作为推理输入

```python
# 检索记忆
memories = await memory_retrieval.search(query)

# 推理时使用
answer = await reasoning_validator.reason(
    query=query,
    memories=memories  # 记忆提供上下文
)
```

### 层次2: 分布式记忆支持推理

```python
# 记忆分布在不同脑区
hippocampus_memories = [事件记忆]
temporal_lobe_memories = [语义知识]

# 推理时从多个脑区提取
context = {
    'episodic': hippocampus.retrieve(),
    'semantic': temporal_lobe.retrieve()
}

# 多模态推理
answer = combine_reasoning(episodic_reasoning, semantic_reasoning)
```

### 层次3: 推理结果形成新记忆

```python
# 推理过程
reasoning_chain = [
    "检索: Caroline去了gender clinic",
    "推理: 这暗示transgender身份",
    "结论: transgender"
]

# 将推理链存储为新记忆
await consolidation.store_reasoning(
    question=query,
    answer=answer,
    reasoning_chain=reasoning_chain
)

# 下次类似问题可以直接检索这个推理记忆
```

---

## 当前状态总结

### ✅ 已实现 (正常运行)

1. **BrainNetwork图拓扑激活扩散** (src/brain/brain_network.py)
   - 16个brain agents
   - 26个脑区连接
   - 5次迭代收敛
   - 全局workspace

2. **分布式记忆系统** (src/brain/distributed_memory.py)
   - 5个脑区分类存储
   - 时间范围过滤 (time_range)
   - FAISS向量检索

3. **神经可塑性引擎** (src/brain/neural_plasticity.py)
   - 记录激活模式
   - 优化路由策略

### ⚠️ 部分实现 (存在但未完全集成)

4. **CapabilityAnalyzer** (src/reasoning/capability_analyzer.py)
   - ✅ 文件存在,代码完整
   - ❌ brain_coordinator未调用

5. **CapabilityOrchestrator** (src/reasoning/capability_orchestrator.py)
   - ✅ 文件存在,包含3个修复
   - ❌ brain_coordinator未调用

6. **ConditionalConstraintEngine** (src/reasoning/conditional_constraint_engine.py)
   - ✅ 文件存在
   - ❌ 未被使用

### ❌ 缺失

7. **brain_coordinator集成代码**
   - 需要在_process_with_brain_network中:
     - 调用CapabilityAnalyzer
     - 根据capabilities决定路径
     - 传递time_range参数

---

## 下一步: 正确集成方案

### 目标

让CapabilityOrchestrator正确融入BrainNetwork架构!

### 实现方案

```python
async def _process_with_brain_network(self, user_input, context, start_time):
    # ... 语言检测 ...

    # 🔥 步骤1: 使用CapabilityAnalyzer分析
    from src.reasoning.capability_analyzer import CapabilityAnalyzer
    analyzer = CapabilityAnalyzer()
    capability_analysis = await analyzer.analyze(user_input)
    capabilities = capability_analysis['capabilities']

    # 🔥 步骤2: 提取时间范围 (如果需要)
    time_range = None
    cap_names = [c['name'] for c in capabilities]
    if 'temporal_calculation' in cap_names or 'duration_inference' in cap_names:
        from src.utils.date_extractor import DateExtractor
        time_range = DateExtractor.extract_time_range(user_input)

    # 步骤3: 记忆检索 (带时间过滤)
    memories = await memory_retrieval.semantic_search(
        query=user_input,
        k=20,
        time_range=time_range  # 🔥 传递时间范围!
    )

    # 步骤4: 分布式记忆分配
    distributed_memory.distribute_to_regions(memories)

    # 🔥 步骤5: 决策路径
    if len(capabilities) > 0:
        # 路径A: 使用CapabilityOrchestrator (复杂推理)
        from src.reasoning.capability_orchestrator import CapabilityOrchestrator

        agents_dict = {
            'memory_retrieval': self.memory_retrieval,
            'reasoning_validator': self.reasoning_validator,
            'consolidation': self.consolidation,
            'reflection': self.reflection,
            'conversation': self.conversation
        }
        orchestrator = CapabilityOrchestrator(brain_agents=agents_dict)

        result = await orchestrator.execute(
            query=user_input,
            capabilities=capabilities,
            memories=memories,
            execution_plan=capability_analysis['execution_plan']
        )

        return ProcessingResult(
            mode='capability_orchestrator',
            response=result['answer'],
            ...
        )
    else:
        # 路径B: 使用BrainNetwork (通用处理)
        network_result = await self.brain_network.process(
            stimulus=user_input,
            context={
                'memories': memories,
                'detected_language': context.get('detected_language')
            },
            max_iterations=5
        )

        return ProcessingResult(
            mode='brain_network',
            response=network_result['response'],
            ...
        )
```

---

## 总结

### 你的问题核心

"记忆框架必然和推理融合,现在的框架流程与逻辑是什么?"

### 答案

**当前架构**:
1. ✅ BrainNetwork图拓扑 (类脑分布式协作) - 已实现
2. ✅ 分布式记忆系统 (记忆与推理融合) - 已实现
3. ⚠️ CapabilityOrchestrator (推理编排层) - 创建了但未集成

**下一步**:
- 在brain_coordinator中集成CapabilityAnalyzer和CapabilityOrchestrator
- 让它们与BrainNetwork协同工作,不是替换
- 测试验证 test_locomo_correct.py → 100%

**我的理解现在对了吗?**
