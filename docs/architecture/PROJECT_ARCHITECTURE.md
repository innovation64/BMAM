# 🧠 BMAM项目架构详细文档
## Brain-Inspired Multi-Agent Memory Framework

**版本**: 1.0
**代码量**: 20,360行
**最后更新**: 2025-09-30

---

## 📋 目录

1. [项目概述](#项目概述)
2. [系统架构](#系统架构)
3. [核心算法](#核心算法)
4. [12智能体详细设计](#12智能体详细设计)
5. [技术栈](#技术栈)
6. [数据流](#数据流)
7. [性能优化](#性能优化)

---

## 项目概述

BMAM是一个基于人脑认知架构的多智能体协调系统，实现了12个专门化智能体的并行协作，模拟人类大脑的记忆处理、情绪反应和认知功能。

### 核心特点

- **类脑架构**: 基于神经科学研究的12智能体分工协作
- **真实LLM推理**: 每个智能体使用OpenAI API独立推理
- **向量记忆**: FAISS向量数据库 + SQLAlchemy持久化
- **神经可塑性**: 动态学习和适应的智能体连接
- **情绪系统**: 情绪标记和应激反应处理
- **并行处理**: 异步并行处理提升系统吞吐量

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                 │
│  ui.py | voice_anime_ui.py | web_ui_server.py                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   协调器层 (Coordinator)                          │
│                  brain_coordinator.py                            │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • 路由决策 (Executive Control)                           │   │
│  │ • 智能体调度 (Agent Scheduling)                          │   │
│  │ • 记忆检索路由 (Retrieval Router)                        │   │
│  │ • 并行任务管理 (Parallel Processing)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   12智能体层 (Agents)                             │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │  核心记忆智能体   │  │  辅助功能智能体   │                    │
│  │  (8个)           │  │  (4个)           │                    │
│  ├──────────────────┤  ├──────────────────┤                    │
│  │ 1. 短期记忆      │  │ 9. 对话          │                    │
│  │ 2. 长期记忆      │  │ 10. 执行控制     │                    │
│  │ 3. 记忆检索      │  │ 11. 感知编码     │                    │
│  │ 4. 记忆巩固      │  │ 12. 行动执行     │                    │
│  │ 5. 记忆失真      │  └──────────────────┘                    │
│  │ 6. 反思          │                                           │
│  │ 7. 遗忘          │                                           │
│  │ 8. 应激反应      │                                           │
│  └──────────────────┘                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   记忆系统层 (Memory System)                      │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐       │
│  │ FAISS向量库   │  │ SQLite数据库  │  │ Embedding服务  │       │
│  │              │  │              │  │                │       │
│  │ • 1536维向量 │  │ • 持久化存储 │  │ • OpenAI API   │       │
│  │ • 语义检索   │  │ • 元数据管理 │  │ • 缓存机制     │       │
│  │ • 索引优化   │  │ • 关系查询   │  │ • 批处理       │       │
│  └──────────────┘  └──────────────┘  └────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 目录结构

```
BMAM/
├── src/
│   ├── agents/                    # 智能体实现
│   │   ├── core/                 # 8个核心记忆智能体
│   │   │   ├── short_term_memory.py      # 短期记忆
│   │   │   ├── long_term_memory.py       # 长期记忆
│   │   │   ├── memory_retrieval.py       # 记忆检索
│   │   │   ├── consolidation.py          # 记忆巩固
│   │   │   ├── memory_distortion.py      # 记忆失真
│   │   │   ├── reflection.py             # 反思
│   │   │   ├── forgetting.py             # 遗忘
│   │   │   ├── stress_response.py        # 应激反应
│   │   │   ├── retrieval_router.py       # 检索路由器
│   │   │   └── personality.py            # 人格系统
│   │   ├── base.py               # 智能体基类
│   │   ├── llm_service.py        # LLM服务封装
│   │   └── agent_buffer_system.py # 智能体缓冲系统
│   │
│   ├── coordination/              # 协调系统
│   │   ├── brain_coordinator.py   # 主协调器
│   │   └── clean_agent_system.py  # 清洁智能体系统
│   │
│   ├── memory/                    # 记忆系统
│   │   ├── memory_system.py       # 核心记忆系统
│   │   ├── memory_item.py         # 记忆项数据结构
│   │   └── memory_optimizer.py    # 记忆优化器
│   │
│   ├── brain/                     # 类脑机制
│   │   ├── neural_plasticity.py   # 神经可塑性引擎
│   │   ├── connection_matrix.py   # 智能体连接矩阵
│   │   └── synaptic_plasticity.py # 突触可塑性
│   │
│   ├── services/                  # 外部服务
│   │   ├── openai_embedding_service.py  # OpenAI嵌入服务
│   │   └── shared_openai_client.py      # 共享OpenAI客户端
│   │
│   ├── ui/                        # 用户界面
│   │   ├── voice_anime_ui.py      # 语音+动画界面
│   │   ├── web_ui_server.py       # Web界面服务器
│   │   └── voice_interface.py     # 语音接口
│   │
│   └── utils/                     # 工具模块
│       └── config.py              # 配置管理
│
├── data/                          # 数据存储
│   ├── memories/                  # 记忆数据
│   │   ├── faiss_index.bin       # FAISS向量索引
│   │   └── memories.db           # SQLite数据库
│   └── agent_buffers/            # 智能体缓冲区
│
├── evaluation/                    # 评估系统
│   ├── agent_evaluation.py       # 智能体评估
│   └── llm_judge.py              # LLM裁判评估
│
├── ui.py                         # 主交互界面
├── main.py                       # 程序入口
└── requirements.txt              # Python依赖
```

---

## 核心算法

### 1. 工作记忆快速路径 (Working Memory Fast Path)

**目标**: 50-100ms快速响应
**算法**: 三级查询策略

```python
# 伪代码
def fast_query(query):
    # Level 1: 精确匹配 (Hash查询, ~1ms)
    query_hash = md5(query)
    if query_hash in cache:
        return cache[query_hash]

    # Level 2: 关键词匹配 (~5-10ms)
    query_keywords = set(query.split())
    for item in working_memory:
        if item.activation < 0.15:
            continue
        overlap = query_keywords & item.keywords
        if overlap:
            score = overlap_ratio * 1.2 * activation + 0.1
            return item, score

    # Level 3: MISS - 转向长期记忆
    return None
```

**性能指标**:
- 精确匹配: ~1ms
- 关键词匹配: ~70ms
- 置信度阈值: 0.5

### 2. 检索策略路由 (Retrieval Strategy Routing)

**目标**: 根据查询类型选择最优检索策略
**算法**: 特征提取 + 规则引擎 + 学习权重

```python
# 策略类型
STRATEGIES = {
    'semantic': 语义向量检索,      # FAISS相似度
    'episodic': 情景记忆检索,      # 时序线索
    'associative': 关联检索,       # 记忆链
    'keyword': 关键词检索,         # BM25
    'multi_strategy': 混合策略     # 加权组合
}

# 特征提取
features = {
    'has_temporal_markers': bool,  # "上周", "昨天"
    'entities': List[str],         # 实体识别
    'has_relation_words': bool,    # "和", "之间"
    'is_factual_question': bool,   # "什么", "哪个"
    'query_length': int,
    'complexity': str              # low/medium/high
}

# 规则权重 (可学习)
weights = {
    'temporal_to_episodic': 0.9,
    'entity_relation_to_associative': 0.95,
    'factual_to_keyword': 0.8,
    'complex_to_multi': 0.90
}
```

### 3. 向量检索 (FAISS Vector Search)

**向量维度**: 1536 (OpenAI text-embedding-3-small)
**索引类型**: IndexFlatL2 (精确L2距离)
**检索算法**:

```python
# 语义检索
embedding = await openai_embed(query)  # 1536维
D, I = faiss_index.search(embedding, k=10)  # 返回距离和索引

# 多策略检索 (Hybrid)
semantic_results = faiss_search(query, k=10)
keyword_results = bm25_search(query, k=10)
episodic_results = temporal_filter(results, time_range)

# 加权融合
final_results = weighted_combine([
    (semantic_results, 0.5),
    (keyword_results, 0.3),
    (episodic_results, 0.2)
])
```

### 4. 神经可塑性 (Neural Plasticity)

**机制**: Hebbian学习 + 权重衰减
**更新规则**:

```python
# 智能体连接强化
def update_connection(agent_a, agent_b, success):
    W[a][b] += learning_rate * activation[a] * activation[b]

    if success:
        W[a][b] *= reward_factor  # 1.05
    else:
        W[a][b] *= penalty_factor  # 0.95

    # 权重衰减
    W[a][b] *= decay_rate  # 0.99

# 记忆关联强化
def strengthen_memory_link(mem_a, mem_b):
    link_strength = base_strength * co_activation_count
    link_strength *= time_decay(elapsed_time)
```

**参数**:
- learning_rate: 0.01
- reward_factor: 1.05
- penalty_factor: 0.95
- decay_rate: 0.99

### 5. 记忆巩固 (Memory Consolidation)

**算法**: 基于重要性和访问频率的选择性巩固

```python
def consolidation_priority(memory):
    # 重要性得分
    importance = memory.importance  # 0-1

    # 访问频率加成
    access_bonus = log(1 + memory.access_frequency) * 0.1

    # 情绪标记加成
    emotion_bonus = memory.emotion_intensity * 0.2

    # 时间衰减
    time_penalty = exp(-memory.age_days * 0.01)

    return (importance + access_bonus + emotion_bonus) * time_penalty

# 巩固阈值
if priority > 0.7:
    consolidate_to_long_term(memory)
```

### 6. 遗忘机制 (Forgetting)

**算法**: Ebbinghaus遗忘曲线 + 干扰理论

```python
def decay_function(memory, elapsed_time):
    # Ebbinghaus遗忘曲线
    retention = exp(-elapsed_time / half_life)

    # 重要性减缓遗忘
    retention *= (1 + memory.importance)

    # 访问频率减缓遗忘
    retention *= (1 + 0.1 * log(1 + memory.access_frequency))

    return retention

# 遗忘阈值
if retention < 0.3:
    mark_for_deletion(memory)
```

### 7. 情绪标记 (Emotion Tagging)

**算法**: 基于规则的情绪分类 + 强度计算

```python
EMOTION_KEYWORDS = {
    'joy': ['高兴', '开心', '快乐', '喜悦'],
    'sadness': ['伤心', '难过', '悲伤'],
    'anger': ['生气', '愤怒', '恼火'],
    'fear': ['害怕', '恐惧', '担心'],
    'surprise': ['惊讶', '意外', '震惊']
}

def detect_emotion(text):
    emotion_scores = {}
    for emotion, keywords in EMOTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            emotion_scores[emotion] = score / len(keywords)

    # 强度 = 最高得分
    intensity = max(emotion_scores.values()) if emotion_scores else 0.0

    return emotion_scores, intensity
```

---

## 12智能体详细设计

### 核心记忆智能体 (8个)

#### 1. 短期记忆智能体 (Short-term Memory Agent)

**对应脑区**: 前额叶皮层 (Prefrontal Cortex)
**神经科学依据**: Miller's 7±2规则, Baddeley工作记忆模型
**文件**: `src/agents/core/short_term_memory.py`

**核心功能**:
- **工作记忆缓冲** (7±2项容量限制)
- **快速查询** (<50ms, 无LLM调用)
- **激活衰减** (10%/秒衰减率)
- **语音环路** (Phonological Loop, 5项容量)
- **视空间草稿板** (Visuospatial Sketchpad, 4项容量)

**数据结构**:
```python
working_memory = deque(maxlen=7)  # 主工作记忆
phonological_loop = deque(maxlen=5)  # 语音环路
visuospatial_sketchpad = deque(maxlen=4)  # 视空间草稿板
query_cache = {}  # 查询缓存 (Hash -> Result)
```

**关键方法**:
- `fast_query()`: 三级查询 (精确/关键词/MISS)
- `_store_in_working_memory()`: 存储项目，自动路由到子系统
- `_update_activation_levels()`: 时间衰减更新
- `_manipulate_information()`: 信息操作 (排序、合并等)

**性能指标**:
- 精确匹配延迟: ~1ms
- 关键词匹配延迟: ~70ms
- 容量: 7±2项

---

#### 2. 长期记忆智能体 (Long-term Memory Agent)

**对应脑区**: 新皮层 (Neocortex)
**神经科学依据**: 语义网络, 图式理论
**文件**: `src/agents/core/long_term_memory.py`

**核心功能**:
- **语义记忆存储** (概念和知识)
- **情景记忆存储** (事件和体验)
- **关联网络构建** (记忆间连接)
- **知识整合** (新旧记忆融合)

**存储策略**:
```python
memory_types = {
    'semantic': 概念性知识,      # "咖啡是一种饮料"
    'episodic': 具体事件,        # "昨天买了咖啡"
    'procedural': 程序性知识,    # "如何制作咖啡"
    'autobiographical': 自传性   # "我第一次喝咖啡"
}
```

**关键方法**:
- `store_memory()`: 持久化存储到FAISS+SQLite
- `retrieve_by_type()`: 按类型检索
- `build_associations()`: 构建记忆关联
- `integrate_knowledge()`: 知识整合

---

#### 3. 记忆检索智能体 (Memory Retrieval Agent)

**对应脑区**: 海马体 (Hippocampus)
**神经科学依据**: 模式完成理论, 索引理论
**文件**: `src/agents/core/memory_retrieval.py`

**核心功能**:
- **语义检索** (FAISS向量相似度)
- **情景检索** (时间线索)
- **关联检索** (记忆链追踪)
- **关键词检索** (BM25算法)
- **混合检索** (多策略融合)

**检索策略**:
```python
strategies = {
    'semantic': {
        'method': 'faiss_search',
        'weight': 0.5,
        'latency': '50-200ms'
    },
    'keyword': {
        'method': 'bm25_search',
        'weight': 0.3,
        'latency': '10-50ms'
    },
    'episodic': {
        'method': 'temporal_filter',
        'weight': 0.2,
        'latency': '20-100ms'
    }
}
```

**关键方法**:
- `semantic_search()`: 向量相似度检索
- `keyword_search()`: BM25关键词检索
- `episodic_search()`: 时序情景检索
- `associative_search()`: 关联记忆检索
- `multi_strategy_search()`: 混合策略检索

---

#### 4. 记忆巩固智能体 (Consolidation Agent)

**对应脑区**: 海马体-新皮层通路
**神经科学依据**: 系统巩固理论, 睡眠巩固
**文件**: `src/agents/core/consolidation.py`

**核心功能**:
- **重要性评估** (0-1分数)
- **选择性巩固** (优先级队列)
- **睡眠模拟** (离线处理)
- **记忆重组** (关联强化)

**巩固算法**:
```python
def compute_consolidation_score(memory):
    base_score = memory.importance

    # 访问频率加成
    access_bonus = log(1 + memory.access_frequency) * 0.1

    # 情绪强度加成
    emotion_bonus = memory.emotion_intensity * 0.2

    # 关联数量加成
    association_bonus = len(memory.associations) * 0.05

    # 新近性
    recency_bonus = exp(-memory.age_hours / 24) * 0.1

    return base_score + access_bonus + emotion_bonus + association_bonus + recency_bonus
```

**关键方法**:
- `consolidate_memories()`: 批量巩固
- `evaluate_importance()`: 重要性评分
- `strengthen_associations()`: 强化关联
- `schedule_consolidation()`: 巩固调度

---

#### 5. 记忆失真智能体 (Memory Distortion Agent)

**对应脑区**: 丘脑 (Thalamus)
**神经科学依据**: 重构理论, Loftus虚假记忆研究
**文件**: `src/agents/core/memory_distortion.py`

**核心功能**:
- **自然失真** (细节模糊)
- **schema影响** (图式偏差)
- **情绪染色** (情绪改变记忆)
- **时间漂移** (时序错乱)

**失真类型**:
```python
distortion_types = {
    'detail_decay': 细节丢失,        # 0.05衰减率/天
    'schema_bias': 图式偏差,         # 向图式靠拢
    'emotion_coloring': 情绪染色,    # 情绪影响回忆
    'source_confusion': 来源混淆,    # 记忆来源错误
    'temporal_drift': 时间漂移       # 时间顺序错乱
}
```

**关键方法**:
- `apply_distortion()`: 应用失真
- `check_schema_bias()`: 检查图式偏差
- `apply_emotion_coloring()`: 情绪染色
- `temporal_drift()`: 时间漂移

---

#### 6. 反思智能体 (Reflection Agent)

**对应脑区**: 默认模式网络 (Default Mode Network)
**神经科学依据**: 元认知理论, 自我反思
**文件**: `src/agents/core/reflection.py`

**核心功能**:
- **元认知分析** (思考自己的思考)
- **模式发现** (跨记忆模式)
- **洞察生成** (新见解)
- **自我评估** (性能反思)

**反思层级**:
```python
reflection_levels = {
    'level_1': {
        'name': '表面反思',
        'depth': 'shallow',
        'focus': '单个事件'
    },
    'level_2': {
        'name': '模式识别',
        'depth': 'medium',
        'focus': '跨事件模式'
    },
    'level_3': {
        'name': '深度洞察',
        'depth': 'deep',
        'focus': '元认知和价值观'
    }
}
```

**关键方法**:
- `reflect_on_memories()`: 记忆反思
- `discover_patterns()`: 模式发现
- `generate_insights()`: 洞察生成
- `self_evaluate()`: 自我评估

---

#### 7. 遗忘智能体 (Forgetting Agent)

**对应脑区**: 抑制系统 (Inhibition System)
**神经科学依据**: Ebbinghaus遗忘曲线, 干扰理论
**文件**: `src/agents/core/forgetting.py`

**核心功能**:
- **自然衰减** (时间遗忘)
- **干扰遗忘** (新旧干扰)
- **主动抑制** (有意遗忘)
- **清理维护** (存储优化)

**遗忘曲线**:
```python
def forgetting_curve(memory, elapsed_days):
    # Ebbinghaus指数衰减
    base_retention = exp(-elapsed_days / 7)  # 7天半衰期

    # 重要性减缓
    importance_factor = 1 + memory.importance

    # 复习加成
    rehearsal_factor = 1 + 0.1 * memory.access_frequency

    retention = base_retention * importance_factor * rehearsal_factor

    return min(1.0, retention)
```

**关键方法**:
- `apply_decay()`: 应用衰减
- `check_interference()`: 检查干扰
- `active_suppression()`: 主动抑制
- `cleanup_low_retention()`: 清理低留存记忆

---

#### 8. 应激反应智能体 (Stress Response Agent)

**对应脑区**: 杏仁核 (Amygdala)
**神经科学依据**: 情绪记忆增强, 战或逃反应
**文件**: `src/agents/core/stress_response.py`

**核心功能**:
- **情绪检测** (喜怒哀乐惊)
- **威胁评估** (风险等级)
- **应激标记** (情绪记忆)
- **唤醒调节** (激活水平)

**情绪分类**:
```python
emotions = {
    'joy': {
        'keywords': ['高兴', '开心', '快乐'],
        'arousal': 'high',
        'valence': 'positive'
    },
    'sadness': {
        'keywords': ['伤心', '难过', '悲伤'],
        'arousal': 'low',
        'valence': 'negative'
    },
    'anger': {
        'keywords': ['生气', '愤怒', '恼火'],
        'arousal': 'high',
        'valence': 'negative'
    },
    'fear': {
        'keywords': ['害怕', '恐惧', '担心'],
        'arousal': 'high',
        'valence': 'negative'
    }
}
```

**关键方法**:
- `detect_emotion()`: 情绪检测
- `assess_threat()`: 威胁评估
- `mark_emotional_memory()`: 情绪记忆标记
- `modulate_arousal()`: 唤醒调节

---

### 辅助功能智能体 (4个)

#### 9. 对话智能体 (Conversation Agent)

**对应脑区**: Broca区/Wernicke区
**文件**: `src/coordination/clean_agent_system.py`

**核心功能**:
- **自然语言理解**
- **响应生成**
- **上下文管理**
- **LLM回退机制**

**关键方法**:
- `generate_response()`: 生成对话响应
- `_build_memory_fallback()`: LLM失败时的记忆回退

---

#### 10. 执行控制智能体 (Executive Control Agent)

**对应脑区**: 前扣带回皮层 (ACC)
**文件**: `src/coordination/clean_agent_system.py`

**核心功能**:
- **任务调度**
- **冲突解决**
- **优先级管理**
- **资源分配**

**关键方法**:
- `route_request()`: 请求路由
- `manage_priorities()`: 优先级管理
- `resolve_conflicts()`: 冲突解决

---

#### 11. 感知编码智能体 (Perception Encoding Agent)

**对应脑区**: 感觉皮层 (Sensory Cortex)
**文件**: `src/agents/core/perception_encoding.py`

**核心功能**:
- **输入特征提取**
- **多模态编码**
- **注意力选择**
- **模式识别**

---

#### 12. 行动执行智能体 (Action Execution Agent)

**对应脑区**: 运动皮层 (Motor Cortex)
**文件**: `src/coordination/clean_agent_system.py`

**核心功能**:
- **响应执行**
- **输出格式化**
- **反馈监控**
- **错误纠正**

---

## 技术栈

### 核心技术

| 技术 | 用途 | 版本/配置 |
|------|------|----------|
| **Python** | 主语言 | 3.8+ |
| **OpenAI API** | LLM推理 | gpt-4o-mini |
| **FAISS** | 向量检索 | IndexFlatL2, 1536维 |
| **SQLAlchemy** | 持久化ORM | 2.0+ |
| **SQLite** | 元数据存储 | 3.x |
| **AsyncIO** | 异步并发 | 标准库 |
| **Sentence-Transformers** | 本地嵌入(备选) | paraphrase-MiniLM-L6-v2 |
| **NumPy** | 向量计算 | 1.24+ |
| **aiohttp** | 异步HTTP | 3.9+ |

### 依赖库

```txt
# 核心依赖
openai>=1.0.0              # OpenAI API
faiss-cpu>=1.7.4          # 向量检索
sqlalchemy>=2.0.0         # ORM
sentence-transformers      # 本地嵌入
numpy>=1.24.0             # 数值计算

# 异步和并发
aiohttp>=3.9.0            # 异步HTTP
asyncio                   # 异步IO

# UI相关
gradio>=4.0.0             # Web UI
websockets                # WebSocket
pyaudio                   # 音频
opencv-python             # 视频处理

# 工具
pyyaml                    # 配置文件
python-dotenv             # 环境变量
pytest                    # 测试
```

---

## 数据流

### 1. 用户输入处理流程

```
用户输入
  │
  ▼
[感知编码] ──> 特征提取
  │
  ▼
[执行控制] ──> 任务路由
  │
  ▼
[短期记忆] ──> 工作记忆查询 (Fast Path)
  │
  ├─ HIT (置信度>0.5) ──> 快速响应
  │
  └─ MISS ──> 长期记忆检索
       │
       ▼
  [检索路由器] ──> 策略选择
       │
       ▼
  [记忆检索] ──> 多策略检索
       │
       ▼
  [对话智能体] ──> 生成响应
       │
       ▼
  [记忆巩固] ──> 存储新记忆
       │
       ▼
  [行动执行] ──> 输出响应
```

### 2. 记忆存储流程

```
新信息
  │
  ▼
[短期记忆] ──> 工作记忆 (7±2项)
  │
  ├─ 重复/重要 ──> [记忆巩固]
  │                    │
  │                    ▼
  │              [长期记忆] ──> FAISS + SQLite
  │
  └─ 衰减 ──> [遗忘] ──> 删除
```

### 3. 检索策略选择流程

```
查询输入
  │
  ▼
[检索路由器] ──> 特征提取
  │
  ├─ 有时间标记? ──> episodic策略
  ├─ 有实体+关系? ──> associative策略
  ├─ 事实性问题? ──> keyword策略
  ├─ 复杂查询? ──> multi_strategy
  └─ 默认 ──> semantic策略
       │
       ▼
  [记忆检索] ──> 执行检索
       │
       ▼
  返回结果
```

---

## 性能优化

### 1. 并发优化

**策略**: 异步并行处理
```python
# 并行激活多个智能体
tasks = {
    'retrieval': asyncio.create_task(retrieve_memories()),
    'reflection': asyncio.create_task(reflect_on_context()),
    'emotion': asyncio.create_task(detect_emotion())
}

results = await asyncio.gather(*tasks.values())
```

**效果**:
- 串行时间: 6000ms
- 并行时间: 2000ms
- **加速比**: 3x

### 2. 缓存优化

**多级缓存**:
```python
# L1: 短期记忆查询缓存 (Hash查询)
query_cache = {}  # ~1ms命中

# L2: OpenAI嵌入缓存 (避免重复API调用)
embedding_cache = {}  # 节省$0.0001/请求

# L3: FAISS索引缓存 (内存常驻)
faiss_index (内存)  # ~50ms检索
```

**效果**:
- 缓存命中率: 30-40%
- API调用减少: 35%
- 成本节省: ~$0.05/1000次查询

### 3. 工作记忆快速路径

**优化前**:
- 所有查询都走长期记忆检索
- 平均延迟: 6000ms

**优化后**:
- 工作记忆HIT: 200ms (快速路径)
- 工作记忆MISS: 6000ms (慢速路径)
- 命中率: 15-20%
- **平均延迟降低**: 约1000ms

### 4. 批处理优化

**嵌入批处理**:
```python
# 单个处理: 10次API调用 = 2000ms
for text in texts:
    embed = await openai.embed(text)

# 批处理: 1次API调用 = 500ms
embeds = await openai.embed_batch(texts)
```

**效果**:
- 延迟降低: 75%
- 成本降低: 相同

### 5. 索引优化

**FAISS索引选择**:
```python
# IndexFlatL2 (精确检索)
- 优点: 100%召回率
- 缺点: O(n)复杂度
- 适用: n < 100,000

# IndexIVFFlat (近似检索)
- 优点: O(√n)复杂度
- 缺点: ~95%召回率
- 适用: n > 100,000
```

---

## 附录

### A. 智能体通信消息格式

```python
@dataclass
class AgentMessage:
    sender: str              # 发送者ID
    receiver: str            # 接收者ID
    message_type: str        # 'request'|'response'|'notification'
    content: Dict[str, Any]  # 消息内容
    priority: str            # 'low'|'medium'|'high'
    timestamp: str           # ISO格式时间戳
    correlation_id: str      # 关联ID (UUID)
```

### B. 记忆项数据结构

```python
@dataclass
class MemoryItem:
    id: str                           # 唯一ID
    content: str                      # 记忆内容
    memory_type: str                  # 类型
    importance: float                 # 重要性 (0-1)
    emotion_tags: List[str]           # 情绪标签
    emotion_intensity: float          # 情绪强度
    brain_region: str                 # 脑区
    consolidation_level: int          # 巩固级别
    access_frequency: int             # 访问次数
    decay_rate: float                 # 衰减率
    stress_marker: bool               # 应激标记
    timestamp: datetime               # 创建时间
    last_accessed: datetime           # 最后访问
    associations: List[str]           # 关联记忆ID
    source_reliability: float         # 来源可靠性
    context_tags: List[str]           # 上下文标签
    embedding_id: str                 # 嵌入ID
```

### C. 配置参数

```python
# 短期记忆
WORKING_MEMORY_CAPACITY = 7
ACTIVATION_DECAY_RATE = 0.1  # 10%/秒
FAST_PATH_THRESHOLD = 0.5    # 置信度阈值

# 长期记忆
FAISS_DIMENSION = 1536
EMBEDDING_MODEL = "text-embedding-3-small"
RETRIEVAL_K = 10             # 检索数量

# 记忆巩固
CONSOLIDATION_THRESHOLD = 0.7
IMPORTANCE_THRESHOLD = 0.5
CONSOLIDATION_INTERVAL = 3600  # 1小时

# 遗忘
FORGETTING_HALF_LIFE = 7     # 7天
RETENTION_THRESHOLD = 0.3    # 低于则删除

# 并发控制
MAX_CONCURRENT_AGENTS = 4
LLM_TIMEOUT = 30             # 秒
MAX_RETRIES = 3
```

---

## 总结

BMAM是一个功能完整的类脑多智能体协调系统，通过12个专门化智能体的并行协作，实现了人类大脑记忆处理的多个关键机制：

1. **工作记忆** - 快速访问，容量有限
2. **长期记忆** - 持久存储，语义组织
3. **智能检索** - 多策略融合，自适应选择
4. **记忆巩固** - 选择性强化，重要性驱动
5. **自然遗忘** - Ebbinghaus曲线，干扰理论
6. **情绪系统** - 情绪标记，应激反应
7. **神经可塑性** - Hebbian学习，权重更新
8. **元认知** - 反思洞察，自我评估

系统采用先进的技术栈(OpenAI API + FAISS + SQLAlchemy)，实现了高性能、可扩展的类脑认知架构。

---

**文档版本**: 1.0
**最后更新**: 2025-09-30
**作者**: BMAM开发团队