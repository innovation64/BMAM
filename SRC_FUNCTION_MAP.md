# BMAM src/ 功能地图

> 313 个文件 | 88,619 行代码
> 分析时间: 2025-12-15

---

## 🎯 核心流程 (必须理解)

```
用户输入 "你好"
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/coordination/brain_coordinator_refactored.py (入口)         │
│ - process_input() 处理所有输入                                  │
│ - 初始化所有脑区智能体                                          │
│ - 调用 memory_coordinator 进行记忆检索                          │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/coordination/memory_coordinator.py (记忆协调)               │
│ - cross_region_retrieval() 5脑区协作检索                        │
│ - store_with_brain_processing() 存储记忆                        │
└─────────────────────────────────────────────────────────────────┘
     │
     ├──────────────────────┬──────────────────┬─────────────────┐
     ▼                      ▼                  ▼                 ▼
┌──────────┐         ┌──────────┐       ┌──────────┐      ┌──────────┐
│海马体    │         │颞叶      │       │前额叶    │      │杏仁核    │
│情节记忆  │         │语义记忆  │       │推理      │      │情绪      │
└──────────┘         └──────────┘       └──────────┘      └──────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/reasoning/capability_orchestrator/ (推理编排)               │
│ - 多跳推理、时间推理、因果推理                                  │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
返回结果
```

---

## 📁 目录详解

### 1️⃣ src/agents/ (154文件, 35,832行) - 最大模块

```
agents/
├── brain_regions/          # 🧠 5个脑区智能体 (核心!)
│   ├── hippocampus_agent/  # 海马体 - 情节记忆 ⭐核心
│   │   ├── core.py         # 主逻辑
│   │   ├── storage.py      # 存储
│   │   ├── retrieval.py    # 检索
│   │   └── consolidation.py# 巩固
│   │
│   ├── temporal_lobe_agent/# 颞叶 - 语义记忆、知识图谱 ⭐核心
│   ├── prefrontal_agent/   # 前额叶 - 推理、决策 ⭐核心
│   ├── amygdala_agent.py   # 杏仁核 - 情绪标注 ⭐核心
│   ├── basal_ganglia_agent.py # 基底节 - 习惯记忆 ⭐核心
│   │
│   ├── thalamus_agent.py   # 丘脑 - HRM多时间尺度 (可选)
│   ├── anterior_cingulate_agent.py # 前扣带回 - HRM自适应 (可选)
│   └── *_hrm_extension.py  # HRM扩展 (可选)
│
├── core/                   # 🔧 核心代理
│   ├── memory_retrieval/   # 记忆检索策略 ⭐核心
│   ├── consolidation/      # 记忆巩固 ⭐活跃
│   ├── forgetting/         # 遗忘机制 ⭐活跃
│   ├── reflection/         # 反思/元认知 ⭐活跃
│   ├── stress_response/    # 压力响应
│   └── memory_distortion/  # 记忆失真检测
│
├── environment/            # 🌍 环境智能体
│   ├── environment_agent/  # 环境感知
│   └── data_sources.py     # 数据源
│
├── base.py                 # 基类 BrainAgent ⭐核心
└── llm_service.py          # LLM调用服务 ⭐核心
```

**状态:**
- ⭐ 5脑区 + core代理 = 核心功能
- ⚠️ HRM相关 = 可选高级功能
- ❓ environment = 需确认是否使用

---

### 2️⃣ src/memory/ (41文件, 15,336行)

```
memory/
├── memory_system/          # 📦 统一记忆接口 ⭐核心
│   ├── memory_system.py    # 主接口
│   ├── embedding_service.py# 嵌入服务
│   └── vector_database.py  # 向量数据库
│
├── brain_regions/          # 🧠 脑区特化存储
│   ├── hippocampal_event_graph.py  # 海马体事件图
│   ├── temporal_concept_graph.py   # 颞叶概念图
│   └── prefrontal_inference_rules.py # 前额叶推理规则
│
├── knowledge_graph.py      # 知识图谱 ⭐核心
├── key_value_stores.py     # KV存储 ⭐核心
├── memory_archive.py       # 记忆归档
├── metamemory.py           # 元记忆
├── storage_coordinator.py  # 存储协调 ⭐核心
│
├── contrastive_key_optimizer.py # ❓ 对比学习优化器 (未使用?)
├── memory_migration.py     # ❓ 迁移工具 (未使用?)
└── memory_transfer.py      # ❓ 传输工具 (未使用?)
```

**状态:**
- ⭐ memory_system/, knowledge_graph, storage_coordinator = 核心
- ❓ contrastive_key_optimizer, migration, transfer = 可能未使用

---

### 3️⃣ src/coordination/ (25文件, 13,456行)

```
coordination/
├── brain_coordinator_refactored.py  # 🎯 主入口 ⭐⭐⭐
├── memory_coordinator.py            # 记忆协调 ⭐⭐
├── brain_retrieval_integration.py   # 脑仿生检索 ⭐
│
├── routing_manager.py      # 路由决策 ⭐
├── learning_manager.py     # 学习管理 ⭐
├── agent_lifecycle.py      # 生命周期 ⭐
├── message_bus.py          # 消息总线 ⭐
├── metrics_collector.py    # 指标收集 ⭐
│
├── hrm_coordinator_wrapper.py  # HRM包装器 (可选)
├── adaptive_consolidation.py   # 自适应巩固 (可选)
├── collaboration_triggers.py   # 协作触发 (可选)
│
├── clean_agent_system.py   # ❓ 旧版智能体系统?
├── query_expansion.py      # 查询扩展
└── kg_merge_*.py           # 知识图谱合并
```

**状态:**
- ⭐⭐⭐ brain_coordinator_refactored = 最核心
- ⭐⭐ memory_coordinator = 核心
- ⭐ 其他协调模块 = 活跃
- ❓ clean_agent_system = 需确认

---

### 4️⃣ src/brain/ (15文件, 4,463行)

```
brain/
├── brain_network.py        # 脑网络 ⭐活跃
├── collaborative_output.py # 协作输出 ⭐活跃
├── region_activation.py    # 脑区激活 ⭐活跃
├── hippocampal_loop.py     # 海马回路 ⭐活跃
│
├── active_learning.py      # 主动学习 ⭐新增 (2025-12-14)
│
├── synaptic_plasticity.py  # ❌ 突触可塑性 (已禁用!)
├── connection_matrix.py    # ❌ 连接矩阵 (已禁用!)
├── neural_plasticity.py    # ❌ 可塑性引擎 (已禁用!)
│
├── distributed_memory.py   # 分布式记忆
├── habit_learner.py        # 习惯学习
└── semantic_memory_tagger.py # 语义标注
```

**状态:**
- ⭐ brain_network, collaborative_output, region_activation = 活跃
- ⭐ active_learning = 新增功能
- ❌ *plasticity* = 代码存在但被禁用!

---

### 5️⃣ src/reasoning/ (11文件, 2,847行)

```
reasoning/
├── capability_orchestrator/    # 能力编排器 ⭐核心
│   ├── __init__.py
│   ├── core_execution.py       # 核心执行
│   ├── basic_capabilities.py   # 基础能力
│   ├── reasoning_capabilities.py # 推理能力
│   └── answer_synthesis.py     # 答案合成
│
├── memory_reasoning_chain.py   # 推理链 ⭐核心
├── input_analyzer.py           # 输入分析 ⭐活跃
├── capability_analyzer.py      # 能力分析
└── conditional_constraint_engine.py # 约束引擎
```

**状态:** 全部活跃

---

### 6️⃣ src/optimization/ (6文件, 2,040行)

```
optimization/
├── metacognition.py       # ⚠️ 元认知 (optimize只是模拟!)
├── query_cache.py         # 查询缓存 ⭐活跃
├── fast_path.py           # 快速路径 ⭐活跃
├── capacity_manager.py    # 容量管理 ⭐活跃
└── context_limiter.py     # 上下文限制 ⭐活跃
```

**状态:**
- ⭐ cache, fast_path, capacity = 活跃
- ⚠️ metacognition = optimize()只是模拟

---

### 7️⃣ src/core/ (18文件, 3,539行)

```
core/
├── config.py              # 配置 ⭐
├── container.py           # 依赖注入容器 ⭐
│
├── interfaces/            # 接口定义
│   ├── memory_interface.py
│   └── agent_interface.py
│
├── adapters/              # 适配器
│   └── *.py
│
└── testing/               # ❓ 测试工具 (可能未使用)
    ├── mock_factories.py
    └── fixtures.py
```

**状态:**
- ⭐ config, container = 核心
- ❓ testing/ = 可能是开发时用的

---

### 8️⃣ 其他目录

| 目录 | 文件 | 行数 | 状态 |
|------|------|------|------|
| src/utils/ | 17 | 5,777 | ⭐ 核心工具 |
| src/ui/ | 11 | 1,970 | 🖥️ Web/语音界面 |
| src/monitoring/ | 6 | 1,345 | 📈 监控 |
| src/systems/ | 3 | 833 | 📦 外部系统 |
| src/services/ | 3 | 657 | 🌐 OpenAI服务 |
| src/learning/ | 2 | 492 | 📚 反馈学习 |

---

## 📊 代码分布总结

```
┌─────────────────────────────────────────────────────────────┐
│  agents/        ████████████████████████████████████  40%   │
│  memory/        ████████████████                      17%   │
│  coordination/  ███████████████                       15%   │
│  utils/         ██████                                 7%   │
│  brain/         █████                                  5%   │
│  core/          ████                                   4%   │
│  reasoning/     ███                                    3%   │
│  其他           █████                                  9%   │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ 需要关注的问题

### 1. 禁用的功能 (代码存在但不工作)
```
src/brain/synaptic_plasticity.py     388行
src/brain/connection_matrix.py       314行
src/brain/neural_plasticity.py       376行
─────────────────────────────────────────
                                   1,078行 禁用代码
```

### 2. 可能未使用的文件
```
src/memory/contrastive_key_optimizer.py   625行
src/memory/memory_migration.py            585行
src/memory/memory_transfer.py             570行
src/core/testing/                       1,099行
src/coordination/clean_agent_system.py    741行
─────────────────────────────────────────
                                       3,620行 待确认
```

### 3. 模拟/未完成的功能
```
src/optimization/metacognition.py - optimize() 只是 'simulated'
```

---

## 🗺️ 快速导航

| 想了解... | 看这里 |
|----------|--------|
| 系统如何启动 | coordination/brain_coordinator_refactored.py |
| 记忆如何存储 | agents/brain_regions/hippocampus_agent/ |
| 记忆如何检索 | coordination/memory_coordinator.py |
| 推理如何工作 | reasoning/capability_orchestrator/ |
| 知识图谱 | memory/knowledge_graph.py |
| 配置选项 | utils/config.py |
