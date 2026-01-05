# BMAM 系统架构文档

> Brain-Mimetic Agent Memory - 类脑多智能体记忆框架
>
> 更新时间: 2025-12-23

## 一、系统概述

**BMAM** (Brain-Mimetic Agent Memory) 是一个类脑多智能体记忆框架，模拟人类大脑的记忆存储、检索、巩固和遗忘机制。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     BrainInspiredCoordinator (主协调器)                   │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        委托模块层 (Delegation Layer)                 │ │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐            │ │
│  │  │MessageBus │ │ Routing   │ │  Memory   │ │ Learning  │ ...        │ │
│  │  │ Manager   │ │ Manager   │ │Coordinator│ │ Manager   │            │ │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                       脑区智能体层 (Brain Regions)                   │ │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐            │ │
│  │  │Hippocampus│ │Temporal   │ │Prefrontal │ │ Amygdala  │ ...        │ │
│  │  │ (情节记忆) │ │Lobe(语义) │ │ (工作记忆) │ │ (情绪标记) │            │ │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                      功能智能体层 (Functional Agents)                │ │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐            │ │
│  │  │Consolidate│ │ Forgetting│ │ Reflection│ │ Reasoning │ ...        │ │
│  │  │ (巩固)    │ │  (遗忘)   │ │  (反思)   │ │ Validator │            │ │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AdvancedMemorySystem (持久化存储层)                   │
│  ┌───────────┐ ┌───────────────┐ ┌─────────────┐ ┌────────────────┐    │
│  │ SQLAlchemy│ │ FAISS Vector  │ │  Embedding  │ │ Search Mixins  │    │
│  │  Database │ │   Database    │ │   Service   │ │(Semantic/Hybrid)│    │
│  └───────────┘ └───────────────┘ └─────────────┘ └────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 二、核心组件详解

### 2.1 主协调器 (BrainInspiredCoordinator)

**文件**: `src/coordination/brain_coordinator_refactored.py`

重构后的主协调器采用**委托模式**，将职责分散到7个专门模块：

| 委托模块 | 职责 |
|---------|------|
| `MessageBusManager` | 消息队列、后台任务调度 |
| `AgentLifecycleManager` | 智能体激活、生命周期管理 |
| `RoutingManager` | 智能路由、查询分析 |
| `LearningManager` | 持续学习、可塑性 |
| `KGMergeHandler` | 知识图谱操作 |
| `MemoryCoordinator` | 记忆存储/检索/巩固/遗忘 |
| `MetricsCollector` | 统计、性能监控 |

> **重构收益**: 原7908行的God Class被拆分为~500行委托调用 + 7个专注模块，每个模块职责单一，便于测试和维护。

---

### 2.2 脑区智能体 (Brain Region Agents)

**目录**: `src/agents/brain_regions/`

| 脑区 | 文件 | 功能 | 容量 |
|------|------|------|------|
| **Hippocampus** | `hippocampus_agent/` | 情节记忆存储、事件分割、时序推理 | 20,000条 |
| **TemporalLobe** | `temporal_lobe_agent/` | 语义记忆、知识图谱、概念管理 | 70,000条 |
| **Prefrontal** | `prefrontal_agent/` | 工作记忆、执行控制、推理追踪 | 10条 |
| **Amygdala** | `amygdala_agent.py` | 情绪记忆标记、情感权重 | 1,000条 |
| **BasalGanglia** | `basal_ganglia_agent.py` | 程序记忆、习惯形成 | 500条 |
| **Thalamus** | `thalamus_agent.py` | 多时间尺度协调 (HRM) | - |
| **AnteriorCingulate** | `anterior_cingulate_agent.py` | 自适应计算时间 (ACT) | - |
| **TheoryOfMind** | `theory_of_mind_agent.py` | 意图推断、欺骗检测 | - |

**Hippocampus Agent 内部架构** (Mixin组合模式):

```python
class HippocampusAgent(
    StorageMixin,        # 存储和索引
    RetrievalMixin,      # 基本检索
    ConsolidationMixin,  # 记忆巩固
    ForgettingMixin,     # 遗忘机制
    AdvancedSearchMixin, # 高级搜索(事件分割、时间推理)
    HippocampusAgentCore # 核心基础
):
    pass
```

---

### 2.3 功能智能体 (Functional Agents)

**目录**: `src/agents/core/`

| 智能体 | 功能 | 内部集成 |
|--------|------|---------|
| `ShortTermMemoryAgent` | 短期记忆缓冲 | - |
| `LongTermMemoryAgent` | 长期存储接口 | - |
| `MemoryRetrievalAgent` | 多策略检索 | multi_round_retrieval |
| `ConsolidationAgent` | 记忆巩固 | consolidation/ package |
| `ForgettingAgent` | 遗忘调度 | forgetting/ package |
| `ReflectionAgent` | 元认知反思 | reflection/ package |
| `MemoryDistortionAgent` | 记忆扭曲模拟 | memory_distortion/ |
| `StressResponseAgent` | 压力响应 | stress_response/ |
| `PersonalityAgent` | 人格特质 | personality/ package |
| `PersonaMemoryAgent` | 用户画像记忆 | - |
| `ReasoningValidatorAgent` | 推理验证、时间推理 | reasoning_validator/ |
| `LearnableAgentRouter` | 可学习路由 | - |

---

### 2.4 记忆系统 (Memory System)

**目录**: `src/memory/`

#### 核心存储层 (`memory_system/`):

```
AdvancedMemorySystem
├── DatabaseManager (SQLAlchemy持久化)
├── FAISSVectorDatabase (向量索引)
├── EmbeddingService (OpenAI Embedding)
└── Search Mixins
    ├── SemanticSearchMixin (向量语义搜索)
    ├── HybridSearchMixin (BM25+向量混合)
    └── KeywordSearchMixin (关键词搜索)
```

#### 高级记忆模块:

| 模块 | 功能 | 集成状态 |
|------|------|---------|
| `story_arc.py` | 时间线索引、事件编年 | ✅ MemoryCoordinator |
| `key_value_stores.py` | 键值记忆存储 | ✅ BrainNetwork |
| `background_memory_processes.py` | 后台巩固/遗忘/重巩固 | ✅ 主协调器 |
| `adaptive_memory_shaping.py` | 自适应记忆塑造 | ✅ 主协调器 |
| `preference_aware_retrieval.py` | 偏好感知检索 | ✅ 主协调器 |
| `knowledge_graph.py` | 轻量级知识图谱 | ✅ 主协调器 |
| `memory_transfer.py` | 记忆转移 | ✅ brain_service |
| `memory_consolidation_pipeline.py` | 巩固流水线 | ✅ background_processes |
| `silent_engram.py` | 沉默印记 | ✅ preference_aware |
| `pattern_separator.py` | 模式分离 | ✅ preference_aware |
| `contrastive_key_optimizer.py` | 对比学习键优化 | ✅ preference_aware |
| `metamemory.py` | 元记忆监控 | ✅ preference_aware |

---

### 2.5 推理系统 (Reasoning)

**目录**: `src/reasoning/`

| 模块 | 功能 | 集成状态 |
|------|------|---------|
| `capability_orchestrator/` | 能力编排器 (9种推理能力) | ✅ 主协调器 |
| `capability_analyzer.py` | 能力分析器 | ✅ 主协调器 |
| `memory_reasoning_chain.py` | 跨存储推理链 | ✅ 主协调器 |
| `conditional_constraint_engine.py` | 条件约束引擎 | ✅ capability_orchestrator |
| `input_analyzer.py` | 输入分析 | ❌ 未集成 |

**CapabilityOrchestrator 支持的9种推理能力**:

1. `memory_retrieval` - 记忆检索
2. `fact_extraction` - 事实提取
3. `temporal_reasoning` - 时间推理
4. `identity_reasoning` - 身份推理
5. `pattern_reasoning` - 模式推理
6. `spatial_reasoning` - 空间推理
7. `causal_reasoning` - 因果推理
8. `preference_reasoning` - 偏好推理
9. `emotional_reasoning` - 情绪推理

---

### 2.6 大脑网络 (Brain Network)

**目录**: `src/brain/`

| 模块 | 功能 | 集成状态 |
|------|------|---------|
| `brain_network.py` | 并行激活、激活扩散、循环反馈 | ✅ 主协调器 (可选) |
| `hippocampal_loop.py` | 海马-前额叶迭代循环 | ✅ 主协调器 |
| `active_learning.py` | 主动学习管理 | ✅ 主协调器 |
| `collaborative_output.py` | 协作输出生成 | ✅ brain_network |
| `region_activation.py` | 脑区激活动力学 | ✅ brain_network |
| `distributed_memory.py` | 分布式记忆 | ✅ brain_network |
| `habit_learner.py` | 习惯学习 | ✅ BasalGangliaAgent |
| `emotion_modulator.py` | 情绪调节 | ✅ AmygdalaAgent |
| `prefrontal_controller.py` | 前额叶控制 | ✅ PrefrontalAgent |
| `semantic_memory_tagger.py` | 语义记忆标签 | ❌ 未集成 |

---

### 2.7 优化模块 (Optimization)

**目录**: `src/optimization/`

| 模块 | 功能 | 集成状态 |
|------|------|---------|
| `capacity_manager.py` | 容量管理 | ✅ get_capacity_manager() |
| `query_cache.py` | 查询缓存 | ✅ get_query_cache() |
| `fast_path.py` | 快速路径检测 | ✅ get_fast_path_detector() |
| `context_limiter.py` | 上下文限制 | ✅ get_context_limiter() |
| `metacognition.py` | 元认知 (持续学习、冲突检测、偏好提取) | ✅ 主协调器 |

---

### 2.8 协调模块 (Coordination)

**目录**: `src/coordination/`

| 模块 | 功能 | 使用方式 |
|------|------|---------|
| `brain_coordinator_refactored.py` | 主协调器 | 入口点 |
| `memory_coordinator.py` | 记忆操作协调 | 委托模块 |
| `routing_manager.py` | 智能路由 | 委托模块 |
| `learning_manager.py` | 学习管理 | 委托模块 |
| `message_bus.py` | 消息总线 | 委托模块 |
| `agent_lifecycle.py` | 生命周期管理 | 委托模块 |
| `kg_merge_handler.py` | KG合并处理 | 委托模块 |
| `metrics_collector.py` | 指标收集 | 委托模块 |
| `brain_retrieval_integration.py` | 脑仿生检索整合 | 高级检索 |
| `result_arbiter.py` | 结果仲裁 | 质量控制 |
| `proactive_inquiry.py` | 主动询问 | 交互增强 |
| `confidence_calibrator.py` | 置信度校准 | 结果评估 |
| `soul_state.py` | 灵魂状态 (内省/价值观) | 人格持久化 |
| `clean_agent_system.py` | 简洁智能体系统 | 智能体定义 |

---

## 三、组件协作流程

### 3.1 查询处理流程

```
用户输入
    │
    ▼
┌─────────────────┐
│ RoutingManager  │ ← 分析查询类型、选择路由策略
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
快速路径    慢速路径
(FastPath)  (SlowPath)
    │         │
    │    ┌────┴────────────────────────┐
    │    ▼                              ▼
    │  MemoryCoordinator          BrainInspiredRetrieval
    │    │                              │
    │    ├─→ Hippocampus (情节)         ├─→ 多轮迭代检索
    │    ├─→ TemporalLobe (语义)        ├─→ 缺口检测
    │    └─→ StoryArc (时间线)          └─→ 前额叶反馈
    │         │                              │
    └────────►├◄─────────────────────────────┘
              ▼
       ┌──────────────┐
       │CapabilityOrch│ ← 能力编排、推理执行
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │ResultArbiter │ ← 结果仲裁、质量评估
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │ Conversation │ ← 响应生成
       │    Agent     │
       └──────────────┘
```

### 3.2 记忆存储流程

```
新信息输入
    │
    ▼
┌─────────────────────┐
│  MemoryCoordinator  │
└─────────┬───────────┘
          │
    ┌─────┼─────┬─────────────┐
    ▼     ▼     ▼             ▼
Hippocampus  Amygdala   TemporalLobe  StoryArc
(情节存储)  (情绪标记)   (语义提取)   (时间线)
    │         │             │           │
    └────┬────┴─────────────┴───────────┘
         ▼
┌─────────────────────┐
│ AdvancedMemorySystem│ ← 持久化到 SQLite + FAISS
└─────────────────────┘
         │
         ▼ (后台)
┌─────────────────────┐
│BackgroundProcesses  │
├─────────────────────┤
│ • 巩固 (30min)      │
│ • 遗忘 (1hour)      │
│ • 重巩固 (15min)    │
└─────────────────────┘
```

### 3.3 HRM 多时间尺度协调

```
┌─────────────────────────────────────────────┐
│               Thalamus (丘脑)                │
│           多时间尺度协调器                    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│  │Amygdala │  │Hippocam │  │BasalGan │     │
│  │  τ=1    │  │  τ=1    │  │  τ=3    │     │
│  │(快速)   │  │ (快速)  │  │ (中速)  │     │
│  └─────────┘  └─────────┘  └─────────┘     │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │      Prefrontal   τ=10 (慢速)       │   │
│  │         执行控制 / 工作记忆          │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ← AnteriorCingulate: 决定何时停止思考 →    │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 四、未集成组件清单

经过精确验证，以下组件**确实未被任何其他模块导入**：

| 文件 | 功能描述 | 建议优先级 |
|------|---------|-----------|
| `brain/semantic_memory_tagger.py` | 语义记忆自动标签 | 🟡 中 |
| `memory/forgetting_coordinator.py` | 遗忘统一协调 | 🟢 高 |
| `agents/core/context_compaction.py` | 长对话上下文压缩 | 🟡 中 |
| `agents/core/temporal_content_analyzer.py` | 时序内容分析 | 🟡 中 |
| `agents/core/mbti_integration.py` | MBTI人格完整集成 | 🟡 中 |
| `reasoning/input_analyzer.py` | 用户输入意图分析 | 🟡 中 |
| `learning/feedback_loop.py` | 用户反馈学习循环 | 🟢 高 |
| `evaluation/ai_evaluator.py` | AI自动评估 | 🔴 低 (测试用) |
| `memory/memory_migration.py` | 数据迁移工具 | 🔴 低 (工具类) |

---

## 五、监控与服务

### 5.1 监控模块 (`src/monitoring/`)

| 模块 | 集成状态 | 使用位置 |
|------|---------|---------|
| `memory_metrics.py` | ✅ | MemoryCoordinator, HippocampusAgent |
| `brain_region_metrics.py` | ✅ | monitoring子系统内部 |
| `decorators.py` | ✅ | 装饰器工具 |
| `feedback_stats.py` | ⚠️ | 仅web_ui handler |
| `integration_examples.py` | - | 示例代码 |

### 5.2 服务模块 (`src/services/`)

| 模块 | 功能 | 集成状态 |
|------|------|---------|
| `openai_embedding_service.py` | OpenAI Embedding封装 | ✅ MemorySystem |
| `shared_openai_client.py` | 共享OpenAI客户端 | ✅ 多处 |
| `brain_service.py` | REST/gRPC服务封装 | ✅ remote_brain |
| `remote_brain_service.py` | 远程调用 | ✅ 独立服务 |

---

## 六、目录结构

```
src/
├── __init__.py                 # 包入口，延迟加载
├── coordination/               # 协调层
│   ├── brain_coordinator_refactored.py  # 主协调器
│   ├── memory_coordinator.py   # 记忆协调
│   ├── routing_manager.py      # 路由管理
│   ├── learning_manager.py     # 学习管理
│   ├── message_bus.py          # 消息总线
│   ├── agent_lifecycle.py      # 生命周期
│   ├── kg_merge_handler.py     # KG处理
│   ├── metrics_collector.py    # 指标收集
│   ├── brain_retrieval_integration.py  # 脑仿生检索
│   ├── result_arbiter.py       # 结果仲裁
│   ├── proactive_inquiry.py    # 主动询问
│   ├── confidence_calibrator.py # 置信度校准
│   ├── soul_state.py           # 灵魂状态
│   └── clean_agent_system.py   # 智能体定义
│
├── agents/
│   ├── brain_regions/          # 脑区智能体
│   │   ├── hippocampus_agent/  # 海马体 (情节记忆)
│   │   ├── temporal_lobe_agent/ # 颞叶 (语义记忆)
│   │   ├── prefrontal_agent/   # 前额叶 (工作记忆)
│   │   ├── amygdala_agent.py   # 杏仁核 (情绪)
│   │   ├── basal_ganglia_agent.py # 基底节 (习惯)
│   │   ├── thalamus_agent.py   # 丘脑 (HRM协调)
│   │   ├── anterior_cingulate_agent.py # ACC (ACT)
│   │   └── theory_of_mind_agent.py # ToM (意图推断)
│   │
│   ├── core/                   # 功能智能体
│   │   ├── short_term_memory.py
│   │   ├── long_term_memory.py
│   │   ├── memory_retrieval/
│   │   ├── consolidation/
│   │   ├── forgetting/
│   │   ├── reflection/
│   │   ├── memory_distortion/
│   │   ├── stress_response/
│   │   ├── personality/
│   │   ├── persona_memory.py
│   │   ├── reasoning_validator/
│   │   └── learnable_router.py
│   │
│   └── environment/            # 环境智能体
│       ├── environment_agent/
│       └── stimulus_processor.py
│
├── memory/
│   ├── memory_system/          # 核心存储系统
│   │   ├── advanced_memory_system.py
│   │   ├── database_manager.py
│   │   ├── vector_database.py
│   │   ├── embedding_service.py
│   │   └── *_search.py         # 搜索Mixins
│   │
│   ├── story_arc.py            # 时间线索引
│   ├── key_value_stores.py     # 键值存储
│   ├── knowledge_graph.py      # 知识图谱
│   ├── background_memory_processes.py  # 后台处理
│   ├── adaptive_memory_shaping.py      # 自适应塑造
│   ├── preference_aware_retrieval.py   # 偏好检索
│   └── ...
│
├── brain/
│   ├── brain_network.py        # 大脑网络
│   ├── hippocampal_loop.py     # 海马循环
│   ├── active_learning.py      # 主动学习
│   ├── collaborative_output.py # 协作输出
│   ├── region_activation.py    # 激活动力学
│   ├── habit_learner.py        # 习惯学习
│   ├── emotion_modulator.py    # 情绪调节
│   └── prefrontal_controller.py # 前额叶控制
│
├── reasoning/
│   ├── capability_orchestrator/ # 能力编排器
│   ├── capability_analyzer.py   # 能力分析
│   ├── memory_reasoning_chain.py # 推理链
│   └── conditional_constraint_engine.py
│
├── optimization/
│   ├── capacity_manager.py     # 容量管理
│   ├── query_cache.py          # 查询缓存
│   ├── fast_path.py            # 快速路径
│   ├── context_limiter.py      # 上下文限制
│   └── metacognition.py        # 元认知
│
├── monitoring/                 # 监控
├── services/                   # 服务层
├── learning/                   # 学习模块
├── evaluation/                 # 评估模块
├── systems/                    # 系统模块
├── ui/                         # UI层
└── utils/                      # 工具模块
```

---

## 七、统计摘要

| 类别 | 模块数 | 已集成 | 集成率 |
|------|--------|--------|--------|
| coordination | 17 | 17 | 100% |
| agents/brain_regions | 8 | 8 | 100% |
| agents/core | 16 | 13 | 81% |
| memory | 20 | 18 | 90% |
| brain | 9 | 8 | 89% |
| reasoning | 5 | 4 | 80% |
| optimization | 5 | 5 | 100% |
| monitoring | 5 | 3 | 60% |
| services | 4 | 4 | 100% |
| **总计** | **~89** | **~80** | **~90%** |

---

## 八、设计亮点

1. **委托模式重构** - 主协调器从7908行压缩到~500行，通过7个专门模块实现关注点分离

2. **Mixin组合模式** - HippocampusAgent等脑区使用多重继承组合功能模块，保持单一职责

3. **多层级检索** - 快速路径(BasalGanglia) + 慢速路径(Hippocampus) + 迭代循环(PrefrontalLoop)

4. **HRM时间尺度** - Thalamus协调不同脑区的更新频率 (τ=1快速 → τ=10慢速)

5. **约90%集成率** - 绝大多数模块已接入主流程，仅9个模块未集成

---

## 九、后续集成建议

### 高优先级 (🟢)

1. **`forgetting_coordinator.py`** - 统一遗忘调度，与ForgettingAgent整合
2. **`feedback_loop.py`** - 完善用户反馈学习闭环

### 中优先级 (🟡)

3. **`mbti_integration.py`** - MBTI人格系统完整接入
4. **`context_compaction.py`** - 长对话性能优化
5. **`temporal_content_analyzer.py`** - 增强时间推理
6. **`input_analyzer.py`** - 提升意图理解
7. **`semantic_memory_tagger.py`** - 自动标签增强

### 低优先级 (🔴)

8. **`ai_evaluator.py`** - 测试评估专用
9. **`memory_migration.py`** - 数据迁移工具
