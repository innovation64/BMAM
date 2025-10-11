# 脑启发式推理机制设计

**核心问题**: 人脑会像现在的代码一样硬编码"身份推断规则"吗?

**答案**: ❌ 不会。人脑使用**模式识别 + 联想网络 + 概率推理**,而非硬编码规则。

---

## 🧠 人脑实际如何推理身份?

### 人脑的认知过程

当听到"Caroline去了LGBTQ支持小组"时:

```
1. 激活相关概念网络 (自动,无意识)
   LGBTQ → [性少数群体, 多元性别, 跨性别, 同性恋, ...]
   支持小组 → [寻求帮助, 身份认同, 社群归属, ...]

2. 联想激活扩散 (海马体 + 新皮层)
   "第一次参加" → 暗示: 最近觉醒/探索身份
   "transgender stories inspiring" → 暗示: 产生共鸣
   共鸣 + 寻求支持 → 高概率: 自己也是transgender

3. 概率加权 (前额叶)
   P(transgender | LGBTQ_support_group) = 0.4  # 支持小组成员多样
   P(transgender | transgender_stories_inspiring) = 0.7  # 产生共鸣暗示认同
   P(transgender | first_time) = 0.5  # 探索阶段

   贝叶斯更新: P(transgender | all_evidence) = 0.85  # 高概率

4. 阈值决策 (默认模式网络)
   如果 P > 0.7: 推断为"可能是transgender"
   如果 P > 0.9: 推断为"几乎确定是transgender"
```

### 关键差异

| 维度 | 当前代码 (硬编码) | 人脑 (涌现) |
|------|-----------------|-----------|
| **规则来源** | 手写if-else | 经验中学习的统计模式 |
| **灵活性** | 固定规则 | 上下文动态调整 |
| **泛化** | 只对LGBTQ有效 | 可泛化到任何身份推断 |
| **置信度** | 二元(是/否) | 概率分布 |
| **学习能力** | 需要修改代码 | 自动从新案例学习 |

---

## 🎯 脑启发式改进方案

### 方案1: 联想网络 + 概率推理 (推荐)

用**动态联想网络**替代硬编码规则。

#### 架构设计

```python
# src/agents/core/associative_reasoning.py

class AssociativeReasoningAgent(BrainAgent):
    """
    基于联想网络的推理智能体
    模拟海马体的模式完成和新皮层的概念关联
    """

    def __init__(self):
        super().__init__()
        self.concept_network = ConceptNetwork()  # 概念网络
        self.pattern_memory = PatternMemory()    # 模式记忆

    async def infer_from_context(
        self,
        query: str,
        evidence: List[Dict],
        target_attribute: str  # e.g., "identity", "preference", "occupation"
    ) -> Dict[str, Any]:
        """
        从上下文证据中推断目标属性

        人脑过程模拟:
        1. 激活相关概念 (Spreading Activation)
        2. 模式匹配 (Pattern Completion)
        3. 概率整合 (Probabilistic Integration)
        """

        # Step 1: 概念激活 (模拟海马体)
        activated_concepts = await self._spreading_activation(evidence)

        # Step 2: 模式识别 (模拟新皮层)
        patterns = await self._pattern_matching(
            query, evidence, activated_concepts
        )

        # Step 3: 概率推理 (模拟前额叶)
        inference = await self._probabilistic_inference(
            target_attribute, patterns
        )

        return inference


    async def _spreading_activation(
        self,
        evidence: List[Dict]
    ) -> Dict[str, float]:
        """
        扩散激活: 从证据向相关概念扩散

        Example:
        Input: ["LGBTQ support group", "transgender stories"]
        Output: {
            "transgender": 0.85,
            "gender_identity": 0.75,
            "lgbtq_community": 0.90,
            "self_discovery": 0.60,
            ...
        }
        """
        activation = defaultdict(float)

        for item in evidence:
            # 提取关键短语
            keywords = self._extract_keywords(item['content'])

            for keyword in keywords:
                # 从概念网络中获取相关概念
                related = self.concept_network.get_related(
                    keyword,
                    max_distance=2  # 2跳范围内的概念
                )

                # 激活值随距离衰减
                for concept, distance in related:
                    decay = 0.9 ** distance
                    activation[concept] += decay

        # 归一化
        total = sum(activation.values())
        if total > 0:
            activation = {k: v/total for k, v in activation.items()}

        return dict(activation)


    async def _pattern_matching(
        self,
        query: str,
        evidence: List[Dict],
        activated_concepts: Dict[str, float]
    ) -> List[Dict]:
        """
        模式匹配: 在记忆中寻找相似情境

        人脑机制: 海马体的模式完成 (Pattern Completion)
        - 不完整的输入 → 自动补全为完整模式

        Example:
        Input: ["LGBTQ support group", "transgender inspiring"]
        Pattern Memory:
        - Pattern A: "LGBTQ group + resonance → likely member"
        - Pattern B: "transgender stories + inspiring → identifies with"

        Output: [Pattern A (conf=0.8), Pattern B (conf=0.85)]
        """

        # 从Pattern Memory中检索相似模式
        patterns = []

        # 构建当前情境向量
        situation_vector = self._vectorize_situation(evidence, activated_concepts)

        # 在模式记忆中搜索
        similar_patterns = self.pattern_memory.search(
            situation_vector,
            top_k=5
        )

        for pattern in similar_patterns:
            # 计算匹配度
            match_score = self._compute_match(situation_vector, pattern['vector'])

            patterns.append({
                'pattern': pattern['template'],  # e.g., "X + Y → Z"
                'confidence': match_score,
                'inference': pattern['conclusion'],  # e.g., "likely transgender"
                'evidence_match': pattern['matched_features']
            })

        return patterns


    async def _probabilistic_inference(
        self,
        target_attribute: str,
        patterns: List[Dict]
    ) -> Dict[str, Any]:
        """
        概率推理: 整合多个模式的证据

        人脑机制: 前额叶的贝叶斯推理
        - 整合多条证据
        - 加权不确定性
        - 输出概率分布

        Example:
        Input: target_attribute = "identity"
        Patterns:
        - Pattern 1: "transgender" (conf=0.85)
        - Pattern 2: "lgbtq_member" (conf=0.90)

        Output: {
            "inferred_value": "transgender woman",
            "confidence": 0.85,
            "alternatives": [("lgbtq_member", 0.10), ("questioning", 0.05)],
            "reasoning": "Strong evidence from LGBTQ support + transgender stories resonance"
        }
        """

        # 收集所有候选答案及其证据
        candidates = defaultdict(list)

        for pattern in patterns:
            inference = pattern['inference']
            confidence = pattern['confidence']
            candidates[inference].append(confidence)

        # 贝叶斯更新: 整合多条证据
        final_probs = {}
        for candidate, confidences in candidates.items():
            # 组合概率 (假设独立)
            combined = 1.0
            for conf in confidences:
                combined *= conf
            # 归一化
            final_probs[candidate] = combined

        # 归一化为概率分布
        total = sum(final_probs.values())
        if total > 0:
            final_probs = {k: v/total for k, v in final_probs.items()}

        # 选择最高概率的答案
        sorted_candidates = sorted(
            final_probs.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_answer, top_confidence = sorted_candidates[0]

        return {
            'inferred_value': top_answer,
            'confidence': top_confidence,
            'alternatives': sorted_candidates[1:3],  # Top 2备选
            'reasoning': self._generate_reasoning_explanation(patterns),
            'distribution': final_probs
        }


    def _generate_reasoning_explanation(self, patterns: List[Dict]) -> str:
        """
        生成人类可读的推理解释

        模拟: 前额叶的元认知 (知道自己如何推理)
        """
        explanations = []

        for i, pattern in enumerate(patterns[:3], 1):  # Top 3模式
            exp = f"Evidence {i}: {pattern['pattern']} → {pattern['inference']} (confidence: {pattern['confidence']:.2f})"
            explanations.append(exp)

        return "\n".join(explanations)
```

---

#### 概念网络 (Concept Network)

```python
# src/memory/concept_network.py

class ConceptNetwork:
    """
    概念网络: 存储概念间的关联强度

    模拟: 语义记忆网络 (Semantic Memory Network)
    - 概念以节点形式存在
    - 边表示关联强度
    - 激活扩散遍历网络
    """

    def __init__(self):
        self.graph = nx.Graph()  # 使用NetworkX图
        self._initialize_base_concepts()

    def _initialize_base_concepts(self):
        """
        初始化基础概念及关联

        这些可以从:
        1. 预训练知识库 (WordNet, ConceptNet)
        2. 对话历史中学习
        3. 外部知识图谱
        """
        # 示例: LGBTQ相关概念网络
        concepts = [
            ("lgbtq", "transgender", 0.8),
            ("lgbtq", "gay", 0.7),
            ("lgbtq", "lesbian", 0.7),
            ("lgbtq", "bisexual", 0.7),
            ("lgbtq", "queer", 0.8),
            ("transgender", "gender_identity", 0.9),
            ("transgender", "transition", 0.85),
            ("transgender", "coming_out", 0.7),
            ("support_group", "community", 0.8),
            ("support_group", "identity_exploration", 0.75),
            ("inspiring_stories", "resonance", 0.8),
            ("resonance", "identification", 0.85),
            ("identification", "self_recognition", 0.9),
        ]

        for concept1, concept2, weight in concepts:
            self.graph.add_edge(concept1, concept2, weight=weight)

    def get_related(
        self,
        concept: str,
        max_distance: int = 2
    ) -> List[Tuple[str, int]]:
        """
        获取与给定概念相关的所有概念 (在max_distance跳内)

        Args:
            concept: 源概念
            max_distance: 最大跳数

        Returns:
            [(相关概念, 距离), ...]
        """
        if concept not in self.graph:
            return []

        related = []
        visited = {concept}
        queue = [(concept, 0)]

        while queue:
            current, dist = queue.pop(0)

            if dist < max_distance:
                for neighbor in self.graph.neighbors(current):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        related.append((neighbor, dist + 1))
                        queue.append((neighbor, dist + 1))

        return related

    def learn_from_conversation(
        self,
        conversation: str,
        entity: str,
        attribute: str,
        value: str
    ):
        """
        从对话中学习新的概念关联

        Example:
        conversation: "Caroline went to LGBTQ support group and found transgender stories inspiring"
        entity: "Caroline"
        attribute: "identity"
        value: "transgender woman"

        Learning:
        - "lgbtq_support_group" <-> "transgender" (weight += 0.1)
        - "inspiring_stories" <-> "identity_resonance" (weight += 0.1)
        """
        # 提取关键短语
        keywords = self._extract_keywords_from_text(conversation)

        # 将value与上下文关键词关联
        for keyword in keywords:
            if self.graph.has_edge(keyword, value):
                # 增强已有关联
                self.graph[keyword][value]['weight'] += 0.1
            else:
                # 创建新关联
                self.graph.add_edge(keyword, value, weight=0.3)
```

---

#### 模式记忆 (Pattern Memory)

```python
# src/memory/pattern_memory.py

class PatternMemory:
    """
    模式记忆: 存储成功的推理模式

    模拟: 程序性记忆 (Procedural Memory)
    - "如何"推理的记忆
    - 可迁移的推理模板
    """

    def __init__(self):
        self.patterns = []

    def add_pattern(
        self,
        situation: Dict,
        inference: str,
        confidence: float
    ):
        """
        添加新模式到记忆

        人脑机制: 每次成功推理后,大脑会强化该模式
        """
        pattern = {
            'situation_vector': self._vectorize(situation),
            'template': self._extract_template(situation),
            'conclusion': inference,
            'confidence': confidence,
            'usage_count': 1
        }
        self.patterns.append(pattern)

    def search(self, query_vector, top_k=5):
        """
        检索相似模式
        """
        similarities = []
        for pattern in self.patterns:
            sim = cosine_similarity(query_vector, pattern['situation_vector'])
            similarities.append((pattern, sim))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        return [p for p, s in similarities[:top_k]]

    def _extract_template(self, situation: Dict) -> str:
        """
        提取抽象模板

        Example:
        Situation: {
            "event": "LGBTQ support group",
            "emotion": "inspiring",
            "context": "first time"
        }

        Template: "X attends [community_group] + finds [identity_stories] inspiring → X identifies with [identity]"
        """
        # 使用LLM提取抽象模式
        # 或使用规则提取
        pass
```

---

## 💡 与当前代码的对比

### 当前方案 (硬编码)
```python
if is_identity_question and has_lgbtq_context:
    requirement = """
    - If memories mention "LGBTQ support group" + "first time" → Person is part of LGBTQ community
    - If memories mention "transgender stories" as "inspiring" → Person identifies with transgender experience
    """
```

**问题:**
- ❌ 只对LGBTQ有效,不泛化
- ❌ 无法学习新模式
- ❌ 无法处理不确定性
- ❌ 缺少置信度

### 新方案 (联想推理)
```python
# 自动激活概念网络
activated = spreading_activation(["LGBTQ support group", "transgender inspiring"])
# → {"transgender": 0.85, "gender_identity": 0.75, ...}

# 模式匹配
patterns = pattern_matching(activated)
# → [Pattern("resonance + community → identification", conf=0.85)]

# 概率推理
inference = probabilistic_inference(patterns)
# → {"value": "transgender woman", "confidence": 0.85}
```

**优势:**
- ✅ **泛化**: 可处理任何身份/属性推断
- ✅ **学习**: 从成功案例中自动学习模式
- ✅ **不确定性**: 输出概率分布
- ✅ **可解释**: 有推理链

---

## 🔬 实现路径

### Quick Win: 混合方案 (本周)

在现有代码基础上,用**LLM模拟联想推理**:

```python
# src/coordination/clean_agent_system.py

if is_identity_question:
    # 用LLM做联想推理,而非硬编码规则
    inference_prompt = f"""
You are simulating human associative reasoning for identity inference.

Question: {user_input}

Evidence from memories:
{format_memories(relevant_memories)}

Task: Use spreading activation and pattern matching

Step 1 - Spreading Activation:
From the evidence keywords, what concepts are activated in a semantic network?
Example: "LGBTQ support group" → activates: lgbtq_community, gender_identity, transgender, support, belonging...

Step 2 - Pattern Matching:
Do you recognize patterns from common knowledge?
Pattern: "Attending [identity] support group + finding [identity] stories inspiring → likely identifies with [identity]"

Step 3 - Probabilistic Inference:
What is the most likely identity, and with what confidence?
Confidence scale: 0.9+ = almost certain, 0.7-0.9 = likely, 0.5-0.7 = possible, <0.5 = uncertain

Output JSON:
{{
    "activated_concepts": ["transgender", "lgbtq_community", "gender_identity", "self_discovery"],
    "matched_patterns": ["resonance pattern", "community seeking pattern"],
    "inferred_identity": "Transgender woman",
    "confidence": 0.85,
    "reasoning": "Strong resonance with transgender stories + seeking LGBTQ support indicates high likelihood of transgender identity"
}}
"""

    response = await llm_call(inference_prompt)
    # 解析JSON并使用
```

**优势:**
- ✅ 1小时实现
- ✅ 利用LLM的联想能力
- ✅ 更符合人脑推理
- ✅ 输出置信度

---

### Long-term: 显式网络 (下个月)

完整实现ConceptNetwork + PatternMemory:

1. 从ConceptNet导入基础概念网络
2. 从对话历史中学习新关联
3. 保存成功的推理模式
4. 每次推理都强化成功模式

---

## 总结

**人脑不会硬编码规则,而是:**
1. ✅ 通过联想网络激活相关概念
2. ✅ 通过模式匹配识别相似情境
3. ✅ 通过概率推理整合证据
4. ✅ 从每次成功经验中学习

**建议:**
- **短期** (本周): 用LLM模拟联想推理 (Quick Win)
- **长期** (下月): 显式实现ConceptNetwork和PatternMemory

这样BMAM才真正是"Brain-Inspired"! 🧠
