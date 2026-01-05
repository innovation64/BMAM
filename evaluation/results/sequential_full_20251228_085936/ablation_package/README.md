# BMAM 消融实验包 (Ablation Study Package)

## 概述

本包包含 BMAM (Brain-inspired Multi-Agent Memory) 系统的完整消融实验代码、配置和结果。
消融实验用于验证各脑区和功能模块对系统性能的贡献。

---

## 目录结构

```
ablation_package/
├── README.md                    # 本说明文档
├── config/
│   └── ablation_config.py       # 消融配置核心文件
├── scripts/
│   └── run_ablation.py          # 消融实验运行脚本
├── results/
│   ├── ablation_complete.json   # 完整消融结果 (11个配置)
│   ├── ablation_complete.log    # 完整消融日志
│   ├── ablation_core_v3.json    # 核心配置结果 (4个配置)
│   └── ablation_core_v3.log     # 核心配置日志
└── modified_src/
    ├── story_arc.py                    # StoryArc 消融支持
    ├── memory_coordinator.py           # 记忆协调器消融支持
    ├── brain_coordinator_refactored.py # 脑区协调器消融支持
    ├── hrm_coordinator_wrapper.py      # HRM 消融支持
    ├── temporal_reasoning.py           # 时间推理消融支持
    ├── hybrid_search.py                # 混合搜索消融支持
    ├── consolidation.py                # 记忆巩固消融支持
    ├── kg_operations.py                # 知识图谱消融支持
    ├── kg_merge_handler.py             # KG合并消融支持
    └── emotion_modulator.py            # 情绪调节消融支持
```

---

## 代码改动说明

### 1. 核心配置文件 `ablation_config.py`

**位置**: `src/config/ablation_config.py`

**功能**:
- 定义 `AblationConfig` 数据类，包含所有可消融组件的开关
- 提供 14 个预定义消融配置
- 通过环境变量 `BMAM_DISABLE_*` 动态控制组件启用/禁用
- 提供 `is_component_enabled()` 函数供其他模块检查组件状态

**支持的消融维度**:

| 类型 | 组件 | 环境变量 | 说明 |
|------|------|----------|------|
| 脑区 | Hippocampus | BMAM_DISABLE_HIPPOCAMPUS | 情景记忆编码 |
| 脑区 | Temporal Lobe | BMAM_DISABLE_TEMPORAL_LOBE | 语义记忆 + KG |
| 脑区 | Amygdala | BMAM_DISABLE_AMYGDALA | 显著性标记 |
| 脑区 | Prefrontal | BMAM_DISABLE_PREFRONTAL | 工作记忆控制 |
| 脑区 | Basal Ganglia | BMAM_DISABLE_BASAL_GANGLIA | 程序性记忆 |
| 模块 | StoryArc | BMAM_DISABLE_STORY_ARC | 时间线索引 |
| 模块 | Temporal Reasoning | BMAM_DISABLE_TEMPORAL_REASONING | 时间推理 |
| 模块 | KG | BMAM_DISABLE_KG | 知识图谱 |
| 模块 | Hybrid Retrieval | BMAM_DISABLE_HYBRID_RETRIEVAL | 混合检索 |
| 模块 | Consolidation | BMAM_DISABLE_CONSOLIDATION | 记忆巩固 |
| 模块 | HRM | BMAM_DISABLE_HRM | 层次记忆管理 |
| 模块 | Salience | BMAM_DISABLE_SALIENCE | 显著性加权 |

### 2. 各模块消融集成

每个被消融的模块都添加了类似以下的检查代码:

```python
from src.config.ablation_config import is_component_enabled

# 在关键功能入口检查
if not is_component_enabled('story_arc'):
    logger.info("⚠️ 消融实验: StoryArc 已禁用")
    return DisabledStoryArcManager()  # 返回空操作占位符
```

**改动的文件列表**:

| 文件 | 改动内容 |
|------|----------|
| `src/memory/story_arc.py` | 添加 `DisabledStoryArcManager` 占位类 |
| `src/coordination/memory_coordinator.py` | 检查各脑区和模块是否启用 |
| `src/coordination/brain_coordinator_refactored.py` | 脑区激活消融控制 |
| `src/coordination/hrm_coordinator_wrapper.py` | HRM 消融控制 |
| `src/agents/core/reasoning_validator/temporal_reasoning.py` | 时间推理消融 |
| `src/memory/memory_system/hybrid_search.py` | 混合检索消融 |
| `src/agents/core/consolidation/consolidation.py` | 记忆巩固消融 |
| `src/agents/brain_regions/temporal_lobe_agent/kg_operations.py` | KG操作消融 |
| `src/coordination/kg_merge_handler.py` | KG合并消融 |
| `src/brain/emotion_modulator.py` | 情绪调节消融 |

---

## 使用方法

### 方法一: 使用运行脚本 (推荐)

```bash
# 运行完整的5脑区消融实验
python evaluation/scripts/ablation/run_ablation.py \
    --ablations full no_hippocampus no_temporal_lobe no_amygdala no_prefrontal no_basal_ganglia \
    --groups 1 \
    --output evaluation/results/ablation/my_ablation.json

# 运行特定配置
python evaluation/scripts/ablation/run_ablation.py \
    --ablations full no_hippocampus \
    --groups 3 \
    --output results.json
```

**参数说明**:
- `--ablations`: 要运行的消融配置名称列表
- `--groups`: 每个配置运行的对话组数 (1组=199个问题)
- `--output`: 结果输出文件路径

### 方法二: 通过环境变量手动控制

```bash
# 禁用海马体运行测试
export BMAM_DISABLE_HIPPOCAMPUS=true
python your_test_script.py

# 禁用多个组件
export BMAM_DISABLE_HIPPOCAMPUS=true
export BMAM_DISABLE_TEMPORAL_LOBE=true
export BMAM_DISABLE_KG=true
python your_test_script.py

# 重置 (启用所有)
unset BMAM_DISABLE_HIPPOCAMPUS
unset BMAM_DISABLE_TEMPORAL_LOBE
unset BMAM_DISABLE_KG
```

### 方法三: 在代码中动态设置

```python
from src.config.ablation_config import get_ablation_config, set_active_ablation

# 使用预定义配置
config = get_ablation_config('no_hippocampus')
set_active_ablation(config)

# 或创建自定义配置
from src.config.ablation_config import AblationConfig
custom_config = AblationConfig(
    name='my_custom',
    enable_hippocampus=True,
    enable_temporal_lobe=False,
    enable_kg=False
)
set_active_ablation(custom_config)
```

---

## 实验结果

### 5脑区消融结果 (LoCoMo Benchmark, 199 QA pairs)

| 配置 | 准确率 | Δ vs Full | 状态 |
|------|--------|-----------|------|
| Full BMAM | 77.39% | - | 基准 |
| w/o Hippocampus | 52.76% | -24.62% | ✅ 验证有效 |
| w/o Temporal Lobe | 81.41% | +4.02% | ⚠️ 需优化 |
| w/o Amygdala | 75.38% | -2.01% | ✅ 验证有效 |
| w/o Prefrontal | 82.41% | +5.03% | ⚠️ 需优化 |
| w/o Basal Ganglia | 76.88% | -0.50% | ✅ 验证有效 |

### 论文可用结论

**验证有效的脑区 (3/5)**:
1. **Hippocampus (-24.62%)**: 情景记忆编码是系统核心
2. **Amygdala (-2.01%)**: 情感显著性标记有助于检索
3. **Basal Ganglia (-0.50%)**: 程序性记忆有边际贡献

**需要说明的问题**:
- Temporal Lobe 和 Prefrontal 移除后准确率提升
- 建议在论文 Limitations 中提及集成优化方向

---

## 预定义消融配置列表

| 配置名 | 描述 |
|--------|------|
| `full` | 完整 BMAM 系统 |
| `no_hippocampus` | 禁用海马体 |
| `no_temporal_lobe` | 禁用颞叶 + KG |
| `no_amygdala` | 禁用杏仁核 + 显著性 |
| `no_prefrontal` | 禁用前额叶 |
| `no_basal_ganglia` | 禁用基底神经节 |
| `no_story_arc` | 禁用 StoryArc |
| `no_temporal_reasoning` | 禁用时间推理 |
| `no_kg` | 禁用知识图谱 |
| `no_hybrid_retrieval` | 禁用混合检索 |
| `no_consolidation` | 禁用记忆巩固 |
| `no_hrm` | 禁用 HRM |
| `no_salience` | 禁用显著性加权 |
| `hippocampus_only` | 仅保留海马体 |
| `vector_only` | 仅向量检索 (RAG基线) |

---

## 添加新消融配置

在 `ablation_config.py` 中添加:

```python
ABLATION_PRESETS['my_new_config'] = AblationConfig(
    name='my_new_config',
    description='我的自定义消融配置',
    enable_hippocampus=True,
    enable_temporal_lobe=True,
    enable_amygdala=False,  # 禁用杏仁核
    enable_prefrontal=False,  # 禁用前额叶
    # ... 其他配置
)
```

---

## 日期

- 创建日期: 2026-01-01
- 基于 BMAM 版本: ACL 2026 提交版

