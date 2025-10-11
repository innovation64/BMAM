# 基于脑区协同的LoCoMo优化方案

## 🔍 当前问题诊断

### Session-Based测试结果
```
准确率: 40% (2/5)
✅ Q3: Adoption agencies
✅ Q4: transgender woman
❌ Q1: 日期格式 ("2023-05-07" vs "7 May 2023")
❌ Q2: 有counseling但缺"Psychology"
❌ Q5: 答了identity而非relationship status
```

### 根本原因分析

#### 问题1: 脑区激活不充分
**现象**: Q5答错identity而非relationship status
**原因**:
- `identity_inference` 脑区激活过强 (priority=1)
- `relationship_inference` 脑区未被激活
- 脑区间缺乏竞争和抑制机制

#### 问题2: 记忆检索不完整
**现象**: Q2有counseling但缺Psychology
**原因**:
- 只检索到D1:11 "counseling, mental health"
- 未检索到相关的education context (D1:9)
- 海马体↔前额叶循环反馈不足

#### 问题3: 多脑区协同不足
**现象**: 日期格式不统一
**原因**:
- Temporal reasoning单独工作
- 缺少与language production的协同
- 输出格式化由单一脑区决定

## 🧠 设计方案：脑区协同优化

### 方案1: 动态脑区激活与抑制机制

**灵感**: 真实大脑的Winner-Takes-All + Lateral Inhibition

```python
# 当前问题: 所有脑区平等竞争
capability_priority = {
    'identity_inference': 1,  # 总是获胜
    'relationship_inference': 1,  # 从不被激活
}

# 解决方案: 动态激活扩散
class RegionActivationDynamics:
    """
    脑区激活动力学

    核心机制:
    1. Spreading Activation: 激活从高相关区域扩散
    2. Lateral Inhibition: 强激活区域抑制弱激活区域
    3. Competitive Dynamics: 多个候选区域竞争
    """

    async def compute_activation_map(
        self,
        query: str,
        memories: List,
        current_activation: Dict[str, float]
    ) -> Dict[str, float]:
        """
        基于query和记忆内容,动态计算各脑区激活水平

        不是硬编码priority,而是:
        - 分析query语义 → 哪些脑区相关
        - 检查记忆内容 → 哪些脑区有输入
        - 计算竞争强度 → 最相关的区域胜出
        """

        # Step 1: Query语义分析 → 初始激活
        semantic_activation = await self._analyze_query_semantics(query)
        # "What is relationship status?"
        #   → relationship_inference: 0.9
        #   → identity_inference: 0.3

        # Step 2: 记忆内容分析 → 调制激活
        memory_activation = await self._analyze_memory_relevance(memories)
        # memories含 "transgender"
        #   → identity_inference +0.2
        # memories含 "single"
        #   → relationship_inference +0.5

        # Step 3: 竞争动力学 → 最终激活
        final_activation = {}
        for region in all_regions:
            # 整合多源输入
            base = semantic_activation.get(region, 0.0)
            modulation = memory_activation.get(region, 0.0)
            lateral_input = self._compute_lateral_input(region, current_activation)

            # Winner-takes-all dynamics
            total = base + modulation + lateral_input
            final_activation[region] = self._apply_sigmoid(total)

        # Step 4: Lateral inhibition
        winner = max(final_activation, key=final_activation.get)
        for region in final_activation:
            if region != winner:
                # 赢家抑制其他区域
                inhibition = final_activation[winner] * 0.3
                final_activation[region] = max(0, final_activation[region] - inhibition)

        return final_activation
```

### 方案2: 海马体-前额叶循环强化记忆检索

**灵感**: 真实大脑的记忆巩固需要海马体↔前额叶多次交互

```python
class HippocampalPrefrontalLoop:
    """
    海马体-前额叶循环

    解决: Q2缺少Psychology的问题

    工作流程:
    1. 海马体检索 → "counseling, mental health" (D1:11)
    2. 前额叶推理 → "education相关,需要更多context"
    3. 海马体再检索 → "continue education" (D1:9)
    4. 前额叶整合 → "counseling + education → Psychology"
    """

    async def iterative_retrieval(
        self,
        query: str,
        initial_memories: List,
        max_iterations: int = 3
    ) -> List:
        """
        迭代检索: 不是一次性检索,而是多轮refinement
        """
        current_memories = initial_memories
        retrieval_context = {'query': query}

        for iteration in range(max_iterations):
            # 前额叶分析当前记忆
            analysis = await self.prefrontal_cortex.analyze_memory_gaps(
                query, current_memories
            )

            if analysis['is_sufficient']:
                break

            # 识别缺失信息
            missing_info = analysis['missing_aspects']
            # 例如: ["educational background", "career planning context"]

            # 海马体补充检索
            additional_memories = await self.hippocampus.retrieve_by_aspects(
                missing_info, context=retrieval_context
            )

            current_memories.extend(additional_memories)
            retrieval_context['previous_iterations'] = iteration

        return current_memories
```

### 方案3: 多脑区协同输出

**灵感**: 语言输出需要多个区域协同 (Broca + Wernicke + Prefrontal)

```python
class CollaborativeOutput:
    """
    多脑区协同输出

    解决: 日期格式问题

    工作流程:
    1. Temporal reasoning → 计算日期 "2023-05-07"
    2. Language production → 格式化 "7 May 2023"
    3. Prefrontal validation → 检查一致性
    """

    async def generate_answer(
        self,
        workspace: Dict[str, Any]  # 所有脑区的输出
    ) -> str:
        """
        从workspace整合多个脑区的输出

        不是单一脑区输出,而是协同合成
        """
        # 收集所有脑区的候选答案
        candidates = {}
        for region, output in workspace.items():
            if 'answer' in output:
                candidates[region] = output['answer']

        # 识别answer类型
        answer_type = await self._classify_answer_type(candidates)
        # 例如: "temporal" → 需要日期格式化

        # 根据类型选择协同策略
        if answer_type == 'temporal':
            # 时间答案 → temporal + language协同
            raw_answer = candidates.get('temporal_calculation')
            formatted = await self.language_production.format_temporal(raw_answer)
            validated = await self.prefrontal_cortex.validate_answer(formatted)
            return validated

        elif answer_type == 'identity':
            # 身份答案 → identity + context协同
            identity = candidates.get('identity_inference')
            context = workspace.get('context_analysis', {})
            enriched = await self._enrich_with_context(identity, context)
            return enriched

        # ... 其他类型
```

## 🔬 实现策略

### 不是修改单个文件,而是优化脑区协同机制

#### 文件1: [src/brain/region_activation.py](src/brain/region_activation.py) (新建)
**功能**: 动态脑区激活与抑制
**核心算法**:
- Query语义分析 → 初始激活
- 记忆内容调制 → 激活调整
- Lateral inhibition → 竞争抑制

#### 文件2: [src/brain/hippocampal_loop.py](src/brain/hippocampal_loop.py) (新建)
**功能**: 海马体-前额叶循环检索
**核心算法**:
- 迭代记忆检索
- Gap analysis (识别缺失信息)
- Context-aware retrieval

#### 文件3: [src/brain/collaborative_output.py](src/brain/collaborative_output.py) (新建)
**功能**: 多脑区协同输出
**核心算法**:
- Answer type classification
- Region-specific formatting
- Cross-region validation

#### 文件4: [src/brain/brain_network.py](src/brain/brain_network.py) (修改)
**修改点**:
- 集成RegionActivationDynamics
- 添加迭代检索循环
- 使用协同输出机制

## 📊 预期效果

### Q1 (日期格式)
**Before**: temporal_calculation单独输出 "2023-05-07"
**After**: temporal + language协同 → "7 May 2023"

### Q2 (Psychology)
**Before**: 单次检索D1:11 → "counseling, mental health"
**After**: 迭代检索D1:9+D1:11 → "Psychology, counseling certification"

### Q5 (Relationship status)
**Before**: identity_inference总是胜出 → "transgender woman"
**After**: 动态激活 → relationship_inference: 0.9 > identity: 0.3 → "Single"

## 🎯 核心原则

1. **不硬编码** - 所有策略基于动态计算
2. **脑区协同** - 充分利用15个脑区的parallel processing
3. **类脑机制** - 所有算法有神经科学依据:
   - Winner-takes-all (侧抑制)
   - Hippocampal-Prefrontal loop (记忆巩固)
   - Distributed representation (协同输出)

---

**Status**: Design Complete | Ready for Implementation
**Next**: 实现3个核心模块 + 集成到BrainNetwork
