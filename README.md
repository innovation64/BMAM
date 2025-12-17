# BMAM - Brain-inspired Multi-Agent Memory System

**生物启发式多智能体记忆系统 V2.0**

一个模拟人脑记忆机制的AI记忆管理系统，实现了从感知编码、短期记忆、长期巩固到主动遗忘的完整记忆闭环。

---

## 🎯 最新状态 (2025-12-17)

### V2.0 发布: Theory of Mind + StoryArc

| 版本 | LoCoMo 准确率 | 说明 |
|------|--------------|------|
| MemOS 基准 | 73.31% | 对比基准 |
| BMAM V1 | 71.86% | 初始版本 |
| **BMAM V2** | **75.38%** | +3.52% 提升 |

**V2.0 新增模块**:
- ✅ **StoryArc** - 时间线索引与时间推理增强
- ✅ **Theory of Mind** - 意图推断与对抗性问题检测
- ✅ **持续学习** - 在线学习与适应性巩固

---

## 🧠 核心架构

### 五大脑区智能体 (Five Brain Region Agents)

```
┌──────────────────────────────────────────────────────────────────┐
│                     BrainInspiredCoordinator                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │
│  │  Hippocampus   │  │ Temporal Lobe  │  │    Amygdala    │      │
│  │    (海马体)    │  │     (颞叶)     │  │    (杏仁核)    │      │
│  │   情节记忆     │  │  语义记忆+KG   │  │   情绪标记     │      │
│  └────────────────┘  └────────────────┘  └────────────────┘      │
│                                                                   │
│  ┌────────────────────────────────┐  ┌────────────────┐          │
│  │     Prefrontal Cortex (PFC)    │  │ Basal Ganglia  │          │
│  │          (前额叶皮层)          │  │    (基底节)    │          │
│  │  ┌─────────────┬─────────────┐ │  │   程序记忆     │          │
│  │  │ 工作记忆    │ ToM (mPFC)  │ │  │   技能模式     │          │
│  │  │ Working Mem │ 意图推断    │ │  └────────────────┘          │
│  │  │             │ 欺骗检测    │ │                              │
│  │  └─────────────┴─────────────┘ │                              │
│  └────────────────────────────────┘                              │
│                                                                   │
├──────────────────────────────────────────────────────────────────┤
│   StoryArc (时间线)  │  ReasoningValidator  │  LearningManager   │
└──────────────────────────────────────────────────────────────────┘
```

> **神经科学对应**: 内侧前额叶皮层 (mPFC) 是前额叶的一部分，负责心智理论 (Theory of Mind)。
> 在本系统中，ToM 功能作为 Prefrontal Agent 的子模块实现。

### 完整的记忆闭环

1. **感知编码** (Encoding) - 自动提取实体、关系和时间信息
2. **记忆存储** (Storage) - 分布式存储到对应脑区
3. **记忆巩固** (Consolidation) - Hippocampus → Temporal Lobe
4. **记忆检索** (Retrieval) - 混合检索 (BM25 + 向量 + KG)
5. **时间推理** (Temporal Reasoning) - StoryArc 时间线索引
6. **对抗检测** (Adversarial Detection) - Theory of Mind 欺骗识别
7. **自动持久化** (Persistence) - SQLite + JSON 双重保存

---

## 📂 项目结构

```
BMAM/
├── src/                           # 源代码
│   ├── agents/                    # 智能体模块
│   │   ├── brain_regions/         # 脑区智能体
│   │   │   ├── hippocampus_agent/      # 海马体 (情节记忆)
│   │   │   ├── temporal_lobe_agent/    # 颞叶 (语义记忆+KG)
│   │   │   ├── prefrontal_agent/       # 前额叶 (工作记忆)
│   │   │   ├── amygdala_agent.py       # 杏仁核 (情绪标记)
│   │   │   └── basal_ganglia_agent.py  # 基底节 (程序记忆)
│   │   │   # ToM 作为 prefrontal_agent 的子模块 (mPFC) [V2.0]
│   │   ├── core/                  # 核心智能体
│   │   │   ├── reasoning_validator/    # 推理验证器
│   │   │   ├── memory_retrieval/       # 记忆检索
│   │   │   └── consolidation/          # 巩固管理
│   │   └── base.py                # 基类
│   │
│   ├── memory/                    # 记忆系统
│   │   ├── story_arc.py           # 时间线管理 [V2.0]
│   │   ├── memory_consolidation_pipeline.py
│   │   ├── adaptive_memory_shaping.py
│   │   └── memory_version_manager.py
│   │
│   ├── coordination/              # 协调层
│   │   ├── brain_coordinator_refactored.py  # 主协调器
│   │   └── learning_manager.py    # 学习管理器
│   │
│   ├── reasoning/                 # 推理模块
│   │   └── input_analyzer.py      # 问题分析器
│   │
│   └── utils/                     # 工具模块
│
├── data/                          # 数据目录
│   ├── hippocampus_state.json     # 海马体状态
│   ├── temporal_lobe.db           # 颞叶数据库
│   ├── story_arc_state.json       # 时间线索引 [V2.0]
│   ├── tom_state.json             # ToM状态 [V2.0]
│   └── ...
│
├── docs/                          # 文档
│   ├── analysis/                  # 分析报告
│   │   └── V2_deficiency_analysis.md
│   ├── changelog/                 # 变更日志
│   │   └── 2025-12-17_StoryArc_V2.md
│   ├── architecture/              # 架构文档
│   ├── guides/                    # 使用指南
│   └── development/               # 开发文档
│
├── experiments/                   # 实验
│   └── benchmarks/
│       └── locomo/                # LoCoMo 基准测试
│           └── test_sequential.py
│
├── scripts/                       # 脚本
│   ├── migrate_to_story_arc.py    # 迁移工具
│   └── evaluation/                # 评测脚本
│
├── tests/                         # 测试
│   └── ...
│
└── config/                        # 配置
    └── ...
```

---

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 环境配置
```bash
cp .env.example .env
# 编辑 .env 设置 OPENAI_API_KEY
```

### 基础使用
```python
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

# 初始化系统 (自动加载历史记忆)
coordinator = BrainInspiredCoordinator()
await coordinator.initialize()

# 处理用户输入
result = await coordinator.process_user_input("你好，记住我的名字是李阳")

# 系统会自动:
# 1. 存储到 Hippocampus (情节记忆)
# 2. 提取实体、关系和时间信息
# 3. 更新 StoryArc 时间线索引
# 4. 触发情绪标记 (如果有情绪内容)
# 5. 累积达到阈值后巩固到 TemporalLobe
# 6. 自动持久化到数据库
```

### 运行 LoCoMo 评测
```bash
# 设置数据集路径
export LOCOMO_DATASET_PATH=/path/to/locomo10.json

# 运行评测
python experiments/benchmarks/locomo/test_sequential.py --groups 1
```

---

## 🔬 V2.0 新功能详解

### 1. StoryArc 时间线模块

```python
from src.memory.story_arc import get_story_arc_manager

story_arc = get_story_arc_manager()

# 查询事件时间
result = await story_arc.query_event_time(
    entity="Caroline",
    event_keywords=["museum", "visit"]
)
# {'formatted_date': '5 July 2023', 'confidence': 0.95}

# 计算时间跨度
duration = await story_arc.calculate_duration(
    entity="Caroline",
    reference="friends"
)
# {'duration': '4 years', 'start_date': date(2019, 5, 8)}
```

### 2. Theory of Mind 模块

```python
from src.agents.brain_regions import get_theory_of_mind_agent

tom = get_theory_of_mind_agent()

# 意图推断
intent = await tom.infer_intent(
    query="Did Caroline attend the parade with her sister?",
    context=["Caroline is a community activist", "..."]
)
# is_adversarial=True, adversarial_type='false_premise'

# 欺骗检测
deception = await tom.detect_deception(query, known_facts)
# is_deceptive=True, suggested_response="The question assumes..."
```

---

## 📊 性能指标

### LoCoMo 长上下文记忆基准 (Conv-26, 199题)

| 版本 | 准确率 | 正确题数 | 变化 |
|------|--------|----------|------|
| MemOS 基准 | 73.31% | - | - |
| BMAM V1 | 71.86% | 143/199 | -1.45% |
| BMAM V2 (StoryArc) | 74.87% | 149/199 | +3.01% |
| **BMAM V2 (+ ToM)** | **75.38%** | **150/199** | **+3.52%** |

### 按问题类别准确率 (预估)

| 类别 | 题数 | V1 准确率 | V2 准确率 |
|------|------|-----------|-----------|
| open-domain | 70 | ~75% | ~80% |
| adversarial | 47 | ~60% | ~65% |
| temporal | 37 | ~35% | ~60% |
| single-hop | 32 | ~85% | ~90% |
| multi-hop | 13 | ~50% | ~55% |

---

## 🛠 开发路线图

### ✅ 已完成
- Phase 1-3: 基础架构与记忆闭环
- Phase 4: LoCoMo 评测与优化
- **V2.0: StoryArc + Theory of Mind** ← 最新

### 🔄 进行中
- 跨脑区协作增强
- 多跳推理优化

### 📋 计划中
- 分布式存储优化
- 多模态记忆扩展
- 生产部署优化

---

## 🔬 技术栈

- **Python 3.12+**
- **OpenAI API** (GPT-4, text-embedding-3-small)
- **FAISS** (向量检索)
- **SQLite** (持久化存储)
- **BM25** (关键词检索)

---

## 📄 许可证

MIT License

---

## 📌 重要提醒

1. **首次运行**: 系统会自动创建 `data/` 目录并初始化数据库
2. **记忆持久化**: 所有记忆自动保存，程序重启后自动加载
3. **环境变量**: 需要设置 `OPENAI_API_KEY`

---

**最后更新**: 2025-12-17
**版本**: V2.0 (StoryArc + Theory of Mind)
**状态**: ✅ Production Ready

**变更日志**: 详见 [docs/changelog/](docs/changelog/)
**缺陷分析**: 详见 [docs/analysis/V2_deficiency_analysis.md](docs/analysis/V2_deficiency_analysis.md)
