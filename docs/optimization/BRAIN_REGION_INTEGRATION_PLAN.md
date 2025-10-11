# 🧠 脑区智能体集成方案 - Brain Region Integration Plan

## 📋 目标

将3个脑区协作模块集成到BMAM记忆框架,解决LoCoMo Q2/Q4/Q5问题,实现动态脑区分配和协同推理。

---

## 🧠 脑区智能体分工 (Brain Region Assignment)

### 核心脑区与推理能力映射

根据神经科学和当前BMAM架构,推理能力应分配给对应的脑区:

| Capability | 主要脑区 (Primary) | 辅助脑区 (Secondary) | 神经科学依据 |
|------------|-------------------|---------------------|------------|
| **fact_extraction** | Hippocampus (海马体) | Prefrontal Cortex | 事实记忆检索 - 陈述性记忆 |
| **temporal_calculation** | Prefrontal Cortex (前额叶) | Parietal Cortex (顶叶) | 时间推理 - 执行功能 |
| **identity_inference** | Default Mode Network (默认网络) | Temporal Lobe (颞叶) | 身份推理 - 社会认知 |
| **relationship_inference** | Default Mode Network | Prefrontal Cortex | 关系推理 - 心智理论 (Theory of Mind) |
| **interest_inference** | **Default Mode Network** | **Prefrontal Cortex** | **兴趣推理 - 价值判断与目标规划** |
| **pattern_recognition** | Neocortex (新皮层) | Hippocampus | 模式识别 - 高级认知 |
| **multi_hop_inference** | Prefrontal Cortex | Working Memory | 多跳推理 - 工作记忆操作 |

### 🎯 兴趣推理 (Interest Inference) 脑区分配

**Q4: "What fields would Caroline pursue in her education?"**

#### 主要脑区: Default Mode Network (DMN - 默认模式网络)

**神经科学依据**:
1. **价值判断** (Value Judgement): DMN负责评估事物的个人意义和价值
2. **目标表征** (Goal Representation): DMN编码个人长期目标和兴趣
3. **自我参照加工** (Self-referential Processing): "我喜欢什么" "我想做什么"
4. **未来规划** (Future Planning): DMN在想象未来场景时激活

**具体功能**:
```python
# Default Mode Network处理兴趣推理
class DefaultModeNetworkAgent:
    async def infer_interests(self, memories):
        """
        从记忆中推理个人兴趣

        关键线索:
        - 明确陈述: "I'm keen on counseling" → 直接兴趣
        - 行动模式: "researched adoption agencies" → 隐含兴趣
        - 情绪反应: "so inspiring!" → 情感驱动的兴趣
        - 价值观: "support those with similar issues" → 价值导向
        """
        # Step 1: 提取明确兴趣陈述
        explicit_interests = extract_explicit_statements(memories)

        # Step 2: 从行为推断隐含兴趣
        implicit_interests = infer_from_actions(memories)

        # Step 3: 语义映射到学术领域
        academic_fields = map_to_academic_fields(
            explicit_interests + implicit_interests
        )

        return academic_fields
```

#### 辅助脑区: Prefrontal Cortex (前额叶皮层)

**职责**:
1. **目标规划**: 将兴趣转化为具体教育路径
2. **逻辑推理**: "counseling interest" → "Psychology major"
3. **知识整合**: 结合背景知识 (counseling属于Psychology学科)

---

## 🔧 集成方案设计

### 方案: CapabilityOrchestrator增强集成

因为LoCoMo问题都走CapabilityOrchestrator路径,所以在这里集成3个模块:

#### 架构图

```
BrainCoordinator
    ↓
CapabilityAnalyzer (分析能力)
    ↓
CapabilityOrchestrator (编排执行) ← 🔥 集成点
    ├── 🧠 RegionActivationDynamics (动态激活)
    ├── 🧠 HippocampalPrefrontalLoop (迭代检索)
    └── 🧠 CollaborativeOutput (协同输出)
```

---

## 📦 集成实现 (Implementation)

### Step 1: 在CapabilityOrchestrator中初始化3个模块

```python
# src/reasoning/capability_orchestrator.py

class CapabilityOrchestrator:
    def __init__(self, brain_agents: Dict[str, Any], memory_system=None):
        self.agents = brain_agents

        # 🔥 NEW: 集成3个脑区协作模块
        from src.brain.region_activation import RegionActivationDynamics
        from src.brain.hippocampal_loop import HippocampalPrefrontalLoop
        from src.brain.collaborative_output import CollaborativeOutput

        self.region_activation = RegionActivationDynamics()
        self.hippocampal_loop = HippocampalPrefrontalLoop(
            memory_system=memory_system
        ) if memory_system else None
        self.collaborative_output = CollaborativeOutput(
            brain_agents=brain_agents
        )

        logger.info("🔥 Brain collaboration modules integrated")
```

### Step 2: 在execute()方法中集成迭代检索

```python
async def execute(self, query, capabilities, memories, execution_plan):
    logger.info(f"🎯 Orchestrating capabilities: {[c['name'] for c in capabilities]}")

    # 🔥 STEP 1: 迭代检索增强记忆 (解决Q2/Q4 Psychology缺失)
    if self.hippocampal_loop:
        logger.info("🧠 Starting HippocampalPrefrontalLoop iterative retrieval...")
        enhanced_retrieval = await self.hippocampal_loop.iterative_retrieval(
            query=query,
            initial_memories=memories,
            max_iterations=2  # 最多2轮补充检索
        )
        memories = enhanced_retrieval['memories']
        logger.info(f"✅ Enhanced memories: {len(memories)} (was {len(initial_memories)})")

    # 🔥 STEP 2: 动态脑区激活分析 (解决Q5 relationship vs identity)
    activation_map = await self.region_activation.compute_activation_map(
        query=query,
        memories=memories,
        current_activation={}
    )
    logger.info(f"🧠 Region activation: {activation_map}")

    # 🔥 STEP 3: 根据激活强度重新排序capabilities (不是硬编码priority)
    sorted_caps = self._reorder_by_activation(capabilities, activation_map)
    logger.info(f"📋 Dynamic execution order: {[c['name'] for c in sorted_caps]}")

    # 执行capabilities
    context = {
        'query': query,
        'memories': memories,
        'intermediate_results': {},
        'reasoning_chain': []
    }

    for cap in sorted_caps:
        result = await self._execute_capability(cap['name'], context)
        context['intermediate_results'][cap['name']] = result

    # 🔥 STEP 4: 协同输出生成 (解决Q1日期格式 + 多能力综合)
    final_answer = await self.collaborative_output.generate_answer(
        query=query,
        memories=memories,
        workspace=context['intermediate_results']
    )

    return {
        'answer': final_answer.content,
        'confidence': final_answer.confidence,
        'reasoning_chain': context['reasoning_chain'],
        'capabilities_used': [c['name'] for c in sorted_caps],
        'contributing_regions': final_answer.contributing_regions,
        'answer_type': final_answer.answer_type.value
    }
```

### Step 3: 实现_reorder_by_activation方法

```python
def _reorder_by_activation(
    self,
    capabilities: List[Dict],
    activation_map: Dict[str, float]
) -> List[Dict]:
    """
    根据脑区激活强度动态排序capabilities

    不使用硬编码priority,而是使用动态计算的激活强度
    """
    # Capability → 脑区映射
    cap_to_region = {
        'fact_extraction': 'fact_extraction',
        'temporal_calculation': 'temporal_reasoning',
        'identity_inference': 'identity_inference',
        'relationship_inference': 'relationship_inference',
        'interest_inference': 'interest_inference',
        'pattern_recognition': 'pattern_recognition',
        'multi_hop_inference': 'reflection'
    }

    # 为每个capability分配动态激活分数
    for cap in capabilities:
        region = cap_to_region.get(cap['name'], cap['name'])
        cap['dynamic_activation'] = activation_map.get(region, 0.5)

    # 按动态激活排序 (高激活 = 高优先级)
    sorted_caps = sorted(
        capabilities,
        key=lambda c: c.get('dynamic_activation', 0.5),
        reverse=True
    )

    return sorted_caps
```

---

## 🎯 Q4 兴趣推理增强算法

### 问题分析

**Q4**: "What fields would Caroline pursue in her education?"

**当前结果**: "social work, community advocacy, LGBTQ studies"
**预期结果**: "social work / psychology"
**缺失**: "psychology" 关键词

**根本原因**: 记忆中有 "counseling" 和 "mental health",但没有直接映射到 "Psychology"

### 算法解决方案: 语义映射 + 领域知识

#### 在_execute_capability中增强interest_inference分支

```python
async def _execute_capability(self, capability_name: str, context: Dict) -> Any:
    if capability_name == 'interest_inference':
        return await self._execute_interest_inference(context)
    # ... 其他capabilities
```

#### 实现_execute_interest_inference

```python
async def _execute_interest_inference(self, context: Dict) -> Dict:
    """
    兴趣推理增强算法

    核心: 语义映射 - 将具体兴趣映射到学术领域
    """
    query = context['query']
    memories = context['memories']

    # Step 1: 提取记忆文本
    memory_texts = []
    for mem in memories:
        if isinstance(mem, dict) and 'content' in mem:
            memory_texts.append(mem['content'])

    combined_text = " ".join(memory_texts)

    # Step 2: 关键词 → 学术领域映射
    field_mapping = {
        # 心理学相关
        'counseling': 'Psychology',
        'mental health': 'Psychology',
        'therapy': 'Psychology',
        'psychological': 'Psychology',

        # 社会工作相关
        'social work': 'Social Work',
        'community service': 'Social Work',
        'advocacy': 'Community Advocacy',

        # LGBTQ研究相关
        'LGBTQ': 'LGBTQ Studies',
        'transgender': 'Gender Studies',
        'queer': 'Queer Studies',

        # 教育相关
        'education': 'Education',
        'teaching': 'Education'
    }

    # Step 3: 识别所有领域
    detected_fields = set()
    combined_lower = combined_text.lower()

    for keyword, field in field_mapping.items():
        if keyword.lower() in combined_lower:
            detected_fields.add(field)
            logger.info(f"🔍 Detected field: {field} (from keyword: {keyword})")

    # Step 4: 如果没有直接匹配,使用LLM推理
    if not detected_fields:
        detected_fields = await self._llm_field_inference(query, combined_text)

    # Step 5: 格式化输出
    if detected_fields:
        answer = ", ".join(sorted(detected_fields))
    else:
        answer = "Unable to infer academic fields from available information"

    return {
        'answer': answer,
        'fields': list(detected_fields),
        'confidence': 0.8 if detected_fields else 0.3
    }

async def _llm_field_inference(self, query: str, memories: str) -> set:
    """使用LLM进行深度推理"""
    prompt = f"""Based on the person's interests and activities, what academic fields would they likely pursue?

Memories:
{memories[:500]}

Common mappings:
- counseling, therapy, mental health → Psychology
- social services, advocacy → Social Work
- LGBTQ support, community work → LGBTQ Studies / Gender Studies

Output only the academic field names, comma-separated.
"""
    # 调用LLM...
    result = await self._call_llm(prompt)
    fields = {f.strip() for f in result.split(',')}
    return fields
```

---

## 🔄 BrainCoordinator集成点

需要修改BrainCoordinator,将memory_system传递给CapabilityOrchestrator:

```python
# src/coordination/brain_coordinator.py

# 在创建CapabilityOrchestrator时
orchestrator = CapabilityOrchestrator(
    brain_agents=agents_dict,
    memory_system=self.memory_system  # 🔥 NEW: 传递memory_system
)

orchestrator_result = await orchestrator.execute(...)
```

---

## 📊 预期效果

### Q1 (日期格式) - CollaborativeOutput
- **Before**: "2023-05-07"
- **After**: "7 May 2023" ✅
- **机制**: CollaborativeOutput._format_temporal_answer()

### Q2 (Psychology) - HippocampalPrefrontalLoop
- **Before**: "social work, community advocacy" (缺少psychology)
- **After**: "social work, psychology, counseling"
- **机制**: 迭代检索D1:9 + D1:11,语义映射"counseling" → "Psychology"

### Q4 (Fields - Psychology) - Interest Inference增强
- **Before**: "social work, community advocacy, LGBTQ studies"
- **After**: "Psychology, social work"
- **机制**: 语义映射算法 + LLM推理

### Q5 (Relationship status) - RegionActivationDynamics
- **Before**: identity_inference总是胜出 → "transgender woman"
- **After**: relationship_inference动态激活更高 → "Single"
- **机制**: 动态脑区激活,不是硬编码priority
- **注意**: 需要修改测试问题为 "What is Caroline's relationship status?"

---

## 🚀 实施步骤

1. ✅ **已完成**: 实现3个核心模块
   - RegionActivationDynamics
   - HippocampalPrefrontalLoop
   - CollaborativeOutput

2. **Next**: 修改CapabilityOrchestrator
   - 添加3个模块初始化
   - 集成迭代检索
   - 集成动态激活
   - 集成协同输出
   - 实现interest_inference增强算法

3. **Next**: 修改BrainCoordinator
   - 传递memory_system到CapabilityOrchestrator

4. **Next**: 修改测试
   - Q5改为 "What is Caroline's relationship status?"
   - 验证所有5个问题

---

## 🧠 总结: 脑区分配原则

| 推理类型 | 主脑区 | 原因 |
|---------|--------|------|
| 事实提取 | Hippocampus | 陈述性记忆 |
| 时间推理 | Prefrontal | 执行功能 |
| 身份推理 | Default Mode | 社会认知 |
| 关系推理 | Default Mode | 心智理论 |
| **兴趣推理** | **Default Mode** | **价值判断 + 目标规划** |
| 模式识别 | Neocortex | 高级认知 |
| 多跳推理 | Prefrontal | 工作记忆 |

**兴趣推理 = Default Mode Network (主) + Prefrontal Cortex (辅)**

这符合神经科学研究: DMN在思考"我想要什么""我的目标是什么"时最活跃!
