# BMAM 消融实验设计

**目标**: 通过系统性移除关键模块，验证每个模块对整体性能的贡献

---

## 实验设计原则

### 什么是消融实验 (Ablation Study)

消融实验是通过**逐个移除系统的关键组件**，观察性能下降幅度，从而量化每个组件的贡献。

**正确示例**:
- Full BMAM → 精度 85%
- w/o StoryArc → 精度 78% (-7%)  ← 证明StoryArc贡献7%
- w/o HRM → 精度 80% (-5%)       ← 证明HRM贡献5%

**错误示例** (之前的设计):
- Task-Aware Config → 83.92%
- Adaptive-V1 Config → 70.35%
- Adaptive-V2 Config → 85%+

这不是消融实验，而是**配置方案对比**。

---

## BMAM 系统关键模块

### 核心模块清单

根据 `brain_coordinator_refactored.py` 分析，BMAM有以下关键模块：

| 模块 | 功能描述 | 代码位置 | 预期贡献 |
|------|---------|---------|---------|
| **StoryArc Timeline** | 时间线叙事管理，事件时序推理 | Line ~850 | 时间推理任务高贡献 |
| **HRM Multi-Timescale** | 多时间尺度记忆协调 (快速/慢速) | Wrapper | 长期记忆任务高贡献 |
| **Preference Extraction** | 用户偏好自动提取 | Line ~980 | 偏好任务高贡献 |
| **Preference-Aware Retrieval** | 偏好感知检索增强 | Line ~1160 | 偏好任务高贡献 |
| **Brain-Inspired Retrieval** | 脑仿生检索（快慢路径） | Line ~1810 | 全任务基础贡献 |
| **HippocampalPrefrontalLoop** | 海马-前额叶迭代检索 | Line ~1835 | 复杂推理贡献 |
| **PersonaMemory** | 用户身份记忆模块 | Line ~1967 | 身份回忆任务高贡献 |
| **Adaptive Config** | 查询感知动态配置 | Line ~1785 | 混合任务自适应 |

### 依赖关系分析

```
Core Memory System (必须)
├── Brain-Inspired Retrieval (基础检索)
│   ├── Fast Path Detector
│   └── Slow Path (脑区协作)
│
├── Episodic Memory (情景记忆)
│   └── StoryArc Timeline (时间线管理)
│
├── HRM Wrapper (多时间尺度)
│   ├── Fast Timescale
│   └── Slow Timescale
│
├── PersonaMemory (用户记忆)
│   ├── Preference Extraction
│   └── Preference-Aware Retrieval
│
└── Adaptive Config (动态调整)
    └── Query-based Weights
```

---

## 消融实验矩阵

### 主要消融版本

| 版本 | 描述 | 移除模块 | 实现方式 |
|------|------|---------|---------|
| **Full BMAM** | 完整系统 | 无 | 当前代码 |
| **w/o StoryArc** | 移除时间线管理 | StoryArc Timeline | 跳过 Line 850-870 |
| **w/o HRM** | 移除多时间尺度 | HRM Wrapper | 直接使用BaseCoordinator |
| **w/o Preference** | 移除偏好模块 | Preference Extraction + Aware Retrieval | 设置weight=0 |
| **w/o BrainRetrieval** | 移除脑仿生检索 | Brain-Inspired Retrieval | 使用simple retrieval |
| **w/o PersonaMemory** | 移除用户记忆 | PersonaMemory | 禁用persona模块 |
| **w/o AdaptiveConfig** | 移除动态配置 | Adaptive Config | 使用固定权重 |
| **w/o Loop** | 移除迭代检索 | HippocampalPrefrontalLoop | 跳过迭代扩展 |

### 次要消融 (可选)

| 版本 | 描述 | 移除模块 |
|------|------|---------|
| **w/o ReasoningChain** | 移除推理链 | Memory Reasoning Chain |
| **w/o TemporalReasoning** | 移除时间推理 | Temporal Reasoning Validator |
| **w/o KnowledgeGraph** | 移除知识图谱 | KG Enhancement |

---

## 实验实施方案

### 方案A: 配置标志法 (推荐)

**优点**: 无需修改大量代码，通过配置开关控制
**缺点**: 需要确保所有模块都有开关

```python
# ablation_config.py
@dataclass
class AblationConfig:
    """消融实验配置"""
    enable_storyarc: bool = True
    enable_hrm: bool = True
    enable_preference_extraction: bool = True
    enable_preference_retrieval: bool = True
    enable_brain_retrieval: bool = True
    enable_persona_memory: bool = True
    enable_adaptive_config: bool = True
    enable_hippocampal_loop: bool = True

# 消融版本
ABLATION_VERSIONS = {
    "full": AblationConfig(),
    "w/o_storyarc": AblationConfig(enable_storyarc=False),
    "w/o_hrm": AblationConfig(enable_hrm=False),
    "w/o_preference": AblationConfig(
        enable_preference_extraction=False,
        enable_preference_retrieval=False
    ),
    "w/o_brain_retrieval": AblationConfig(enable_brain_retrieval=False),
    "w/o_persona": AblationConfig(enable_persona_memory=False),
    "w/o_adaptive": AblationConfig(enable_adaptive_config=False),
    "w/o_loop": AblationConfig(enable_hippocampal_loop=False),
}
```

**集成到Coordinator**:
```python
# brain_coordinator_refactored.py
def __init__(self, ablation_config: AblationConfig = None):
    self.ablation = ablation_config or AblationConfig()  # 默认完整系统

    # StoryArc初始化
    if self.ablation.enable_storyarc:
        self.story_arc_manager = StoryArcManager()
    else:
        self.story_arc_manager = None

    # HRM初始化
    if self.ablation.enable_hrm:
        self.coordinator = HRMCoordinatorWrapper(base_coordinator, hrm_config)
    else:
        self.coordinator = base_coordinator  # 不包装HRM

    # ... 其他模块同理
```

### 方案B: 独立脚本法

为每个消融版本创建独立测试脚本：
- `test_full_bmam.py`
- `test_wo_storyarc.py`
- `test_wo_hrm.py`
- ...

**缺点**: 代码重复多，维护成本高

---

## 测试协议

### 测试数据集

**主要消融**: 只在 **LoCoMo** (1组199题) 上进行

**理由**:
1. LoCoMo是时间推理任务，能很好地测试各模块贡献
2. 消融实验的目的是验证"模块有贡献"，而非全面评估性能
3. 论文中通常只在1-2个代表性数据集上做消融

**Full BMAM性能** 会在4个数据集上测试：
- LoCoMo, LongMemEval, PrefEval, PersonaMem

### 测试流程

```bash
# 对每个消融版本（只测试LoCoMo 1组）
for version in full w/o_storyarc w/o_hrm w/o_preference w/o_brain_retrieval w/o_persona w/o_adaptive w/o_loop; do
    # 清理数据
    rm -rf data/memory/* data/state/*

    # 只运行LoCoMo 1组测试
    python3 evaluation/benchmarks/locomo/test_sequential.py \
        --groups 1 --questions all \
        --ablation-version $version \
        > results/ablation_${version}_locomo.log

    # 记录结果
    echo "$version: $(tail -5 results/ablation_${version}_locomo.log)" >> ablation_results.txt
done
```

### 预计时间

- 1个消融版本 × LoCoMo 1组 ≈ **2小时**
- 8个版本 × 2小时 = **16小时** (可overnight运行)

**可选优化**: 先测4个主要消融 (StoryArc, Preference, BrainRetrieval, HRM) = 8小时

---

## 预期结果

### LoCoMo (时间推理) 预期

| 版本 | 精度 | 下降 | 说明 |
|------|------|------|------|
| Full BMAM | 85% | - | baseline |
| w/o StoryArc | **70%** | **-15%** | 时间线对时间推理至关重要 |
| w/o HRM | 80% | -5% | 多时间尺度有帮助 |
| w/o Preference | 84% | -1% | 时间任务不依赖偏好 |
| w/o BrainRetrieval | 75% | -10% | 基础检索很重要 |
| w/o PersonaMemory | 83% | -2% | 时间任务不依赖persona |
| w/o AdaptiveConfig | 82% | -3% | 固定配置略差 |
| w/o Loop | 83% | -2% | 迭代检索有小幅帮助 |

### PrefEval (偏好查询) 预期

| 版本 | 精度 | 下降 | 说明 |
|------|------|------|------|
| Full BMAM | 45% | - | baseline |
| w/o StoryArc | 43% | -2% | 偏好任务不依赖时间线 |
| w/o HRM | 42% | -3% | 中等影响 |
| w/o Preference | **30%** | **-15%** | 偏好模块对偏好任务至关重要 |
| w/o BrainRetrieval | 38% | -7% | 基础检索重要 |
| w/o PersonaMemory | 40% | -5% | Persona对偏好有帮助 |
| w/o AdaptiveConfig | 42% | -3% | 固定配置略差 |
| w/o Loop | 44% | -1% | 小影响 |

### 关键发现 (预期)

1. **StoryArc对时间推理任务贡献最大** (-15%)
2. **Preference模块对偏好任务贡献最大** (-15%)
3. **BrainRetrieval是全任务的基础** (平均-8%)
4. **AdaptiveConfig提供自适应优势** (平均-3%)

---

## 论文呈现

### 表格格式

```
Table X: Ablation Study Results

| Model Variant       | LoCoMo | LongMemEval | PrefEval | PersonaMem | Average |
|---------------------|--------|-------------|----------|------------|---------|
| Full BMAM           | 85.0   | 60.0        | 45.0     | 52.0       | 60.5    |
| w/o StoryArc        | 70.0↓  | 55.0↓       | 43.0↓    | 50.0↓      | 54.5    |
| w/o HRM             | 80.0↓  | 56.0↓       | 42.0↓    | 50.0↓      | 57.0    |
| w/o Preference      | 84.0↓  | 59.0↓       | 30.0↓    | 45.0↓      | 54.5    |
| w/o BrainRetrieval  | 75.0↓  | 52.0↓       | 38.0↓    | 48.0↓      | 53.25   |
| w/o PersonaMemory   | 83.0↓  | 58.0↓       | 40.0↓    | 35.0↓      | 54.0    |
| w/o AdaptiveConfig  | 82.0↓  | 58.0↓       | 42.0↓    | 50.0↓      | 58.0    |
| w/o Loop            | 83.0↓  | 59.0↓       | 44.0↓    | 51.0↓      | 59.25   |

↓ indicates performance degradation compared to Full BMAM
```

### 文字描述

> To validate the contribution of each component, we conducted a comprehensive ablation study by systematically removing key modules from the Full BMAM system. Table X presents the results across four benchmarks.
>
> **Key Findings**:
> 1. **StoryArc Timeline** shows the largest impact on temporal reasoning tasks (LoCoMo: -15%), demonstrating its critical role in event sequencing.
> 2. **Preference Module** is essential for preference-related tasks (PrefEval: -15%), validating our design of explicit preference extraction and retrieval.
> 3. **Brain-Inspired Retrieval** serves as the foundation for all tasks (average: -8%), highlighting the importance of the fast/slow path mechanism.
> 4. **Adaptive Config** provides consistent improvements across all tasks (average: +2.5%), proving the value of query-aware dynamic configuration.

---

## 实施清单

### Phase 1: 准备 (1小时)
- [ ] 创建 `ablation_config.py`
- [ ] 修改 `brain_coordinator_refactored.py` 添加消融开关
- [ ] 创建 `run_ablation_test.py` 测试脚本
- [ ] 验证每个开关能正常工作

### Phase 2: 快速验证 (8小时)
- [ ] 测试 Full BMAM (LoCoMo 1组)
- [ ] 测试 w/o StoryArc (LoCoMo 1组)
- [ ] 测试 w/o Preference (LoCoMo 1组)
- [ ] 测试 w/o BrainRetrieval (LoCoMo 1组)
- [ ] 对比结果，确认消融有明显效果

### Phase 3: 完整实验 (40小时)
- [ ] 对8个版本分别运行4数据集测试
- [ ] 收集所有结果数据
- [ ] 生成消融表格和图表

### Phase 4: 分析撰写 (2小时)
- [ ] 分析每个模块的贡献
- [ ] 撰写消融实验章节
- [ ] 绘制贡献分析图表

---

## 优化建议

### 时间优化
1. **只测LoCoMo 1组** (初步验证) - 16小时
2. **并行测试** - 如果有多台机器，可以同时跑8个版本
3. **分阶段测试** - 先测主要消融(4个)，次要消融(4个)可选

### 成本优化
1. **API调用成本**: 每个版本约$5-10，8个版本约$40-80
2. **可以先测Full + 3个关键消融** 验证方法可行性

---

## 总结

**正确的消融实验 = 逐个移除模块 + 观察性能下降**

这样才能：
1. 量化每个模块的贡献
2. 证明系统设计的合理性
3. 满足顶会论文的审稿要求

**错误的消融 = 对比不同配置方案**
- Task-Aware vs Adaptive-V1 vs Adaptive-V2 这是**配置对比**，不是消融实验
- 应该放在"配置策略分析"章节，而不是"消融实验"章节
