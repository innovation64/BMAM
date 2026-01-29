<p align="center">
  <img src="docs/bamalogo.png" alt="BMAM Logo" width="600">
</p>

# BMAM：类脑多智能体记忆系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![arXiv](https://img.shields.io/badge/arXiv-2601.20465-b31b1b.svg)](https://arxiv.org/abs/2601.20465)

**[English](README.md) | 中文**

> **首个面向长期对话 AI 的类脑多智能体记忆框架**

> [!NOTE]
> 本项目是将类脑机制应用于 LLM 记忆系统的**初步探索**。我们正在持续改进框架，欢迎贡献代码、反馈意见和参与讨论！如有建议或发现问题，请提交 Issue。

BMAM 实现了一个受人脑记忆机制启发的多智能体记忆系统。它旨在解决 **灵魂侵蚀（Soul Erosion）** 问题——即 AI 智能体因记忆失效而导致身份和行为一致性逐渐退化的现象——通过协调多个脑区智能体来实现记忆保护。

## 核心特性

- **脑区专业化**：5 个专用智能体（海马体、颞叶、杏仁核、前额叶皮层、基底神经节）
- **StoryArc 时间线**：显式时间索引，支持"何时/多久/先后"类查询
- **混合检索**：BM25 + 稠密向量 + 知识图谱 + 时间线融合
- **灵魂可移植性**：支持记忆档案（.bma 格式）的导出/导入，实现身份迁移
- **HRM 集成**：层次化循环记忆，支持多时间尺度组织

## 性能表现

| 基准测试 | 规模 | 准确率 | 说明 |
|----------|------|--------|------|
| **LoCoMo** | 10 组, 1986 QA | **78.45%** | 长上下文时序推理 |
| **LongMemEval** | 500 样本 | **67.60%** | 6 种问题类型 |
| **PrefEval** | 1000 样本 | **72.9%** | 用户偏好理解 |
| **PersonaMem** | 20 用户, 589 QA | 48.9% | 用户画像记忆 |

### LoCoMo 分类详情

| 类别 | 准确率 | 说明 |
|------|--------|------|
| 单跳推理 | **82.00%** | SOTA |
| 多跳推理 | **70.42%** | SOTA |
| 时序推理 | 62.31% | |
| 开放域 | **79.55%** | SOTA |

## 灵魂侵蚀：为什么记忆很重要

我们提出 **灵魂侵蚀（Soul Erosion）** 作为理解 AI 记忆失效的框架：

| 侵蚀类型 | 问题 | BMAM 解决方案 |
|----------|------|--------------|
| **时序侵蚀** | 丢失事件*发生时间*的追踪 | StoryArc 时间线索引 |
| **语义侵蚀** | 事实变得不一致 | 海马体→颞叶记忆巩固 |
| **身份侵蚀** | 用户偏好被遗忘 | 杏仁核显著性标记 |

**核心洞察**：没有任何单一记忆机制能防止所有类型的侵蚀。BMAM 的多智能体设计提供了互补性保护。

## 系统架构

```
                    BrainInspiredCoordinator（类脑协调器）
    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
    │  │   海马体     │ │    颞叶     │ │   杏仁核    │   │
    │  │ (情景记忆)   │ │(语义+知识图谱)│ │ (显著性)   │   │
    │  └─────────────┘ └─────────────┘ └─────────────┘   │
    │                                                     │
    │  ┌─────────────────────────┐ ┌─────────────────┐   │
    │  │      前额叶皮层          │ │   基底神经节     │   │
    │  │  (工作记忆 + 路由控制)    │ │ (程序性 + 模式)  │   │
    │  └─────────────────────────┘ └─────────────────┘   │
    │                                                     │
    │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
    │  │  StoryArc   │ │   时序推理   │ │   混合检索   │   │
    │  │  (时间线)    │ │             │ │             │   │
    │  └─────────────┘ └─────────────┘ └─────────────┘   │
    └─────────────────────────────────────────────────────┘
```

| 脑区 | 功能 | 抗侵蚀作用 |
|------|------|-----------|
| **海马体** | 情景记忆编码 | 基于 StoryArc 的时间锚定 |
| **颞叶** | 语义记忆 + 知识图谱 | 通过巩固实现事实稳定性 |
| **杏仁核** | 显著性标记 | 身份保护 |
| **前额叶** | 工作记忆 + 路由 | 上下文连贯性 |
| **基底神经节** | 程序性模式 | 行为一致性 |

## 安装

### 前置要求

- Python 3.10+
- OpenAI API 密钥（用于嵌入和 LLM 评估）

### 安装步骤

```bash
# 克隆仓库
git clone https://github.com/innovation64/BMAM.git
cd BMAM

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env：
# OPENAI_API_KEY=sk-xxx
# OPENAI_BASE_URL=https://api.openai.com/v1
```

### 数据集准备

将数据集下载到 `data/datasets/` 目录：

```
data/datasets/
├── locomo/
│   └── locomo10.json           # LoCoMo (10 组)
├── longmemeval/
│   └── longmemeval_oracle.json # LongMemEval (500 样本)
├── prefeval/
│   └── prefeval.json           # PrefEval (1000 样本)
└── personamem/
    └── personamem.json         # PersonaMem (20 用户, 589 QA)
```

## 快速开始

```python
import asyncio
from datetime import datetime
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

async def main():
    # 初始化
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    # 存储记忆
    await coord.store_memory_with_timestamp(
        "用户提到喜欢在山里徒步",
        datetime.now(),
        "user",
        importance=0.8
    )

    # 查询
    result = await coord.process_user_input("我的爱好是什么？")
    print(result.response)

asyncio.run(main())
```

## 评估

### 清理记忆（每次基准测试前必须执行）

```bash
rm -f data/memory/*.db data/memory/*.index data/memory/*.json
rm -f data/memory/checkpoints/*.json data/state/*.json
rm -rf data/cache/embedding data/cache/faiss_index data/cache/knowledge_graph
```

### 基准测试

```bash
# LoCoMo（10 组，约 10 小时）
python evaluation/benchmarks/locomo/test_sequential.py --groups 10

# LongMemEval（500 样本）
python evaluation/benchmarks/longmemeval/test_longmemeval.py --questions 0

# PrefEval（1000 样本）
python evaluation/benchmarks/prefeval/test_prefeval.py --questions 0

# PersonaMem（20 用户）
python evaluation/benchmarks/personamem/test_personamem.py --users 20
```

### 消融实验

BMAM 支持两个层级的消融实验来验证多智能体协作的有效性：

#### 脑区消融（验证 5 脑区协作）

```bash
# 运行所有脑区消融
python evaluation/scripts/ablation/run_ablation.py --brain-regions --groups 3

# 可用消融配置：
# - no_hippocampus: 禁用情景记忆编码
# - no_temporal_lobe: 禁用语义记忆 + 知识图谱
# - no_amygdala: 禁用显著性标记
# - no_prefrontal: 禁用工作记忆控制
# - no_basal_ganglia: 禁用程序性模式
```

#### 组件消融（验证功能模块）

```bash
# 运行组件消融
python evaluation/scripts/ablation/run_ablation.py --components --groups 3

# 可用消融配置：
# - no_story_arc: 禁用时间线索引
# - no_temporal_reasoning: 禁用时序查询
# - no_kg: 禁用知识图谱
# - no_hybrid_retrieval: 仅向量检索
# - no_consolidation: 禁用记忆巩固
```

#### 列出所有消融配置

```bash
python evaluation/scripts/ablation/run_ablation.py --list
```

### 灵魂可移植性测试

验证记忆档案的导出/导入及身份一致性：

```bash
# 运行灵魂可移植性测试
python evaluation/benchmarks/soul_portability/test_soul_portability.py

# 使用更多问题
python evaluation/benchmarks/soul_portability/test_soul_portability.py --questions 50
```

**测试阶段：**
1. **塑造**：存储记忆并回答测试问题
2. **导出**：保存记忆档案（.bma 格式）
3. **恢复**：清除记忆并从档案重新加载
4. **一致性**：比较恢复前后的回答

**灵魂完整性评分**：导出成功率、恢复成功率和回答一致性的加权综合分数。

## 项目结构

```
BMAM/
├── src/
│   ├── agents/
│   │   ├── brain_regions/           # 5 个脑区智能体
│   │   │   ├── hippocampus_agent/   # 海马体 - 情景记忆
│   │   │   ├── temporal_lobe_agent/ # 颞叶 - 语义 + 知识图谱
│   │   │   ├── prefrontal_agent/    # 前额叶 - 工作记忆
│   │   │   ├── amygdala_agent.py    # 杏仁核 - 显著性标记
│   │   │   └── basal_ganglia_agent.py
│   │   └── core/                    # 功能智能体
│   ├── memory/
│   │   ├── story_arc.py             # 时间线管理
│   │   ├── memory_archive.py        # .bma 格式
│   │   └── memory_system/           # 存储后端
│   ├── coordination/
│   │   ├── brain_coordinator_refactored.py
│   │   ├── hrm_coordinator_wrapper.py
│   │   └── memory_archive_manager.py
│   ├── config/
│   │   └── ablation_config.py       # 消融配置
│   └── reasoning/
│       └── memory_reasoning_chain.py
├── evaluation/
│   ├── benchmarks/
│   │   ├── locomo/
│   │   ├── longmemeval/
│   │   ├── prefeval/
│   │   ├── personamem/
│   │   └── soul_portability/        # 灵魂可移植性测试
│   ├── scripts/
│   │   └── ablation/                # 消融实验
│   └── results/
├── data/
│   ├── datasets/                    # 基准测试数据集
│   ├── memory/                      # 运行时存储
│   └── state/                       # 智能体状态
└── archives/                        # 记忆档案 (.bma)
```

## 记忆档案格式（.bma）

BMAM 支持以 `.bma` 格式导出/导入记忆：

```python
from src.coordination.memory_archive_manager import MemoryArchiveManager

# 导出
archive_manager = MemoryArchiveManager(coordinator)
result = archive_manager.export_archive(
    archive_name="my_memory",
    output_dir=Path("archives/"),
    tags=["user_profile", "v1"]
)

# 导入
result = archive_manager.load_archive(Path("archives/my_memory.bma"))
```

**档案内容：**
- SQLite 数据库（情景记忆 + 语义记忆）
- FAISS 向量索引
- 脑区状态文件（JSON）
- 知识图谱
- StoryArc 时间线
- 包含校验和的清单文件

## 常见问题

### 常见故障排除

**1. OpenAI API 错误（502/Cloudflare）**
- 检查 `.env` 中的 API 密钥和 Base URL
- 临时问题请等待后重试

**2. 记忆污染**
- 每次基准测试前清理记忆
- 不要并行运行多个基准测试

**3. 内存不足**
- 确保 8GB+ RAM
- 使用 `--groups 1` 减少批次大小

### 验证安装

```bash
python3 -c "from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator; print('OK')"
```

## 引用

```bibtex
@article{li2026bmam,
  title={BMAM: Brain-inspired Multi-Agent Memory Framework for LLM-Based Agents},
  author={Li, Yang and Liu, Jiaxiang and Wang, Yusong and Wu, Yujie and Xu, Mingkun},
  journal={arXiv preprint arXiv:2601.20465},
  year={2026}
}
```

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)。

---

**版本**：2.1
**最后更新**：2026 年 1 月
