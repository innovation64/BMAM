# BMAM 评估框架

用于评估 BMAM 系统在多个记忆 benchmark 上的性能，并与 MemOS 进行对比。

## 支持的 Benchmark

| Benchmark | 描述 | 数据位置 |
|-----------|------|----------|
| **LoCoMo** | 长上下文记忆评测 | `data/locomo/locomo10.json` |
| **LongMemEval** | 长记忆评测 | `data/longmemeval/` |
| **PersonaMem** | 个性化记忆评测 | `data/personamem/` |
| **PrefEval** | 偏好记忆评测 | `data/prefeval/` |

## 目录结构

```
evaluation/
├── scripts/
│   ├── locomo/              # LoCoMo 评估 (复用现有)
│   ├── longmemeval/         # LongMemEval 评估
│   │   └── eval_longmemeval.py
│   ├── personamem/          # PersonaMem 评估
│   │   └── eval_personamem.py
│   ├── prefeval/            # PrefEval 评估
│   │   └── eval_prefeval.py
│   ├── ablation/            # 消融实验
│   │   ├── run_ablation.py         # 组件消融
│   │   └── eval_chunk_topk.py      # Chunk/Top-K 消融
│   ├── baselines/           # 基线对比
│   │   └── eval_baselines.py       # GPT-4+RAG, BM25 等
│   ├── needle_haystack/     # 大规模检索测试
│   │   └── eval_needle_haystack.py
│   ├── efficiency/          # 效率分析
│   │   ├── eval_efficiency.py      # 延迟、吞吐量、成本
│   │   └── eval_robustness.py      # QPS 压力测试
│   ├── interpretability/    # 可解释性分析
│   │   └── eval_interpretability.py # 脑区激活、检索路径
│   ├── category_analysis/   # 按类别分析
│   │   └── eval_category_analysis.py # 分类准确率、置信度校准
│   └── utils/               # 工具脚本
│       ├── bmam_adapter.py
│       └── generate_report.py
├── results/                 # 评估结果
│   ├── locomo/
│   ├── longmemeval/
│   ├── personamem/
│   ├── prefeval/
│   ├── ablation/
│   ├── baselines/
│   ├── needle_haystack/
│   ├── efficiency/
│   ├── robustness/
│   ├── interpretability/
│   └── category_analysis/
├── run_all_benchmarks.sh    # 一键运行所有评估
└── README.md
```

## 快速开始

### 1. 确保数据集已下载

```bash
ls data/locomo/          # locomo10.json
ls data/longmemeval/     # longmemeval_oracle.json
ls data/personamem/      # questions_32k.csv, shared_contexts_32k.jsonl
ls data/prefeval/        # filtered_inter_turns.json
```

### 2. 运行 Benchmark 评估

```bash
# LoCoMo (使用现有脚本)
python experiments/benchmarks/locomo/test_sequential.py --groups 1

# LongMemEval
python evaluation/scripts/longmemeval/eval_longmemeval.py --dataset oracle --samples 50

# PersonaMem
python evaluation/scripts/personamem/eval_personamem.py --personas 5 --samples 10

# PrefEval
python evaluation/scripts/prefeval/eval_prefeval.py --samples 20
```

### 3. 运行消融实验

```bash
# 组件消融 (StoryArc, ToM, KG 等)
python evaluation/scripts/ablation/run_ablation.py --dataset locomo --samples 1

# 只测试特定消融
python evaluation/scripts/ablation/run_ablation.py --ablations full no_story_arc no_tom

# Chunk Size & Top-K 消融
python evaluation/scripts/ablation/eval_chunk_topk.py --chunk-sizes 256 512 1024 --top-k 5 10 20
```

### 4. 运行基线对比

```bash
# 对比 GPT-4+RAG, BM25, FullContext, NoMemory
python evaluation/scripts/baselines/eval_baselines.py --samples 30
```

### 5. 运行效率分析

```bash
# 延迟、扩展性、吞吐量测试
python evaluation/scripts/efficiency/eval_efficiency.py --test all

# 只测试延迟
python evaluation/scripts/efficiency/eval_efficiency.py --test latency

# QPS 压力测试
python evaluation/scripts/efficiency/eval_robustness.py --qps 1 5 10 20
```

### 6. 运行 Needle-in-Haystack 测试

```bash
# 1K 记忆，测试不同深度
python evaluation/scripts/needle_haystack/eval_needle_haystack.py --size 1000 --depths 0 25 50 75 100

# 10K 记忆
python evaluation/scripts/needle_haystack/eval_needle_haystack.py --size 10000 --depths 50
```

### 7. 运行可解释性分析

```bash
# 脑区激活分析
python evaluation/scripts/interpretability/eval_interpretability.py --test activation

# 检索路径分析
python evaluation/scripts/interpretability/eval_interpretability.py --test retrieval

# 失败案例分析
python evaluation/scripts/interpretability/eval_interpretability.py --test failure

# 全部分析
python evaluation/scripts/interpretability/eval_interpretability.py --test all
```

### 8. 运行按类别分析

```bash
# 分类准确率分析
python evaluation/scripts/category_analysis/eval_category_analysis.py --dataset locomo --samples 50

# 置信度校准测试
python evaluation/scripts/category_analysis/eval_category_analysis.py --calibration
```

### 9. 运行全部评估

```bash
# 快速测试 (少量样本)
bash evaluation/run_all_benchmarks.sh 10 no

# 完整评估 (需要较长时间)
bash evaluation/run_all_benchmarks.sh all yes
```

### 10. 生成对比报告

```bash
python evaluation/scripts/utils/generate_report.py
```

## 评估指标

### 主要指标

- **Accuracy**: 正确答案比例
- **LLM-as-Judge**: 使用 GPT-4o-mini 评判答案正确性
- **F1 Score**: Token 级别的准确率
- **ROUGE-L**: 最长公共子序列相似度
- **Cosine Similarity**: 语义向量相似度
- **Latency**: 响应延迟 (p50, p95, p99)

### 按类别指标

- **LoCoMo**: single-hop, multi-hop, temporal, open-domain
- **LongMemEval**: temporal-reasoning, fact-recall, etc.
- **PersonaMem**: 按问题类型和 topic
- **Category Analysis**: hop_type, temporal_spatial, adversarial, difficulty

### 效率指标

- **QPS**: 每秒查询数
- **Memory Usage**: 内存使用量 (MB)
- **Disk Usage**: 磁盘使用量 (MB)
- **API Cost**: API 调用成本估算

## 消融实验配置

### 组件消融

| 配置 | 描述 |
|------|------|
| `full` | 完整 BMAM 系统 |
| `no_story_arc` | 移除 StoryArc 时间线模块 |
| `no_tom` | 移除 Theory of Mind 模块 |
| `no_kg` | 移除知识图谱 |
| `no_emotion` | 移除情绪模块 |
| `no_hrm` | 移除层次记忆管理 |
| `hippocampus_only` | 仅使用 Hippocampus |

### 参数消融

| 参数 | 测试范围 |
|------|----------|
| `chunk_size` | 256, 512, 1024, 2048 tokens |
| `top_k` | 3, 5, 10, 20, 50 |

## 基线系统

| 基线 | 描述 |
|------|------|
| `GPT-4 + RAG` | OpenAI Embedding + 向量检索 |
| `BM25 + GPT-4` | BM25 稀疏检索 |
| `FullContext` | 完整上下文输入 (无记忆系统) |
| `NoMemory` | 无记忆基线 |

## 与 MemOS 对比

MemOS 官方结果 (来源: MemOS Paper):

| Benchmark | MemOS |
|-----------|-------|
| LoCoMo | 73.31% |

BMAM 当前结果:

| Benchmark | BMAM | 差异 |
|-----------|------|------|
| LoCoMo | 75.38% | +2.07% |

## BMAM 特有实验 (核心创新验证)

BMAM 的核心创新需要专门的实验来验证，这些是区别于 MemOS 等系统的关键差异化实验。

### 1. 脑区协同分析 (`bmam_specific/eval_brain_regions.py`)

验证 BMAM 五大脑区架构的有效性：

```bash
python evaluation/scripts/bmam_specific/eval_brain_regions.py --test contribution  # 贡献度
python evaluation/scripts/bmam_specific/eval_brain_regions.py --test synergy       # 协同效应
python evaluation/scripts/bmam_specific/eval_brain_regions.py --test activation    # 激活模式
```

测试维度：
- **脑区贡献度**: 每个脑区对不同任务类型的贡献
- **协同效应**: 多脑区组合 vs 单脑区的性能差异
- **激活模式**: 不同任务触发的脑区激活模式差异

### 2. StoryArc 时间线模块 (`bmam_specific/eval_story_arc.py`)

验证 BMAM V2.0 的时序推理能力：

```bash
python evaluation/scripts/bmam_specific/eval_story_arc.py --test timeline   # 时间线构建
python evaluation/scripts/bmam_specific/eval_story_arc.py --test temporal   # 时序推理
python evaluation/scripts/bmam_specific/eval_story_arc.py --test conflict   # 冲突检测
```

测试维度：
- **时间线构建**: 事件排序正确性
- **时序推理**: before/after/during 关系推理
- **冲突检测**: 矛盾时间信息的识别

### 3. Theory of Mind 模块 (`bmam_specific/eval_theory_of_mind.py`)

验证 BMAM V2.0 的意图推理和欺骗检测能力：

```bash
python evaluation/scripts/bmam_specific/eval_theory_of_mind.py --test intent      # 意图推理
python evaluation/scripts/bmam_specific/eval_theory_of_mind.py --test deception   # 欺骗检测
python evaluation/scripts/bmam_specific/eval_theory_of_mind.py --test emotion     # 情感理解
```

测试维度：
- **意图推理**: 理解用户真实意图 (显式/隐式)
- **欺骗检测**: 识别矛盾或误导性信息
- **情感理解**: 理解用户情绪状态

### 4. 可解释性分析 (`interpretability/eval_interpretability.py`)

- **脑区激活热力图**: 可视化各脑区在不同任务上的激活程度
- **检索路径追踪**: 记录记忆检索的来源和处理路径
- **失败案例分类**: 系统性识别 6 种失败模式

### 5. 置信度校准 (`category_analysis/eval_category_analysis.py`)

测试系统是否"知道自己不知道"，计算 Expected Calibration Error (ECE)。

### 6. Needle-in-Haystack (`needle_haystack/eval_needle_haystack.py`)

在大规模记忆池 (1K/10K/100K) 中检索特定信息，测试系统的扩展性。

## BMAM vs MemOS 实验对比

| 实验类型 | BMAM | MemOS | 说明 |
|----------|------|-------|------|
| Benchmark 评估 | ✓ | ✓ | LoCoMo, LongMemEval 等 |
| 组件消融 | ✓ (脑区级别) | ✓ (模块级别) | BMAM 细分到 5 个脑区 |
| 时序推理专项 | ✓ (StoryArc) | ✗ | BMAM 独有 |
| 意图/欺骗检测 | ✓ (ToM) | ✗ | BMAM 独有 |
| 脑区协同效应 | ✓ | ✗ | BMAM 独有 |
| 参数消融 | ✓ (Chunk/TopK) | ✓ | 类似 |
| 效率/鲁棒性 | ✓ | ✓ | 类似 |

## 注意事项

1. **API Key**: 确保设置 `OPENAI_API_KEY` 环境变量
2. **内存**: 部分评估需要较大内存，建议 16GB+
3. **时间**: 完整评估可能需要数小时
4. **成本**: LLM Judge 会产生 API 调用成本

## 故障排除

### 常见问题

1. **数据集文件不存在**
   - 按照 README 下载对应数据集

2. **内存不足**
   - 使用 `--samples` 参数限制样本数

3. **API 调用失败**
   - 检查 API Key 和网络连接
   - 脚本会自动 fallback 到字符串匹配

## 引用

如果你在论文中使用这些评估结果，请引用:

```
@misc{bmam2025,
  title={BMAM: Brain-inspired Multi-Agent Memory System},
  year={2025}
}
```
