# KG 配置对比实验指南

本目录包含用于分析学习日志和运行 KG 配置对比实验的脚本。

## 📁 文件结构

```
scripts/
├── analysis/
│   └── analyze_learning_log.py      # 学习日志分析脚本
├── evaluation/
│   ├── run_bmam_memos_eval.py       # MeMOS 评估脚本（支持实验配置）
│   ├── run_kg_comparison.py         # 批量对比实验运行器
│   └── README_KG_COMPARISON.md      # 本文档

configs/experiment_configs/
├── no_kg_config.json                # 无 KG 配置
├── low_kg_config.json               # 低 KG 配置
└── baseline_config.json             # 基准配置

data/
└── learning_log.jsonl               # 学习日志（自动生成）

results/
├── learning_log_analysis.json       # 日志分析结果
├── memos_eval/                      # 单次评估结果
└── kg_comparison/                   # 对比实验结果
```

## 🔧 功能模块

### 1. 学习日志分析 (`analyze_learning_log.py`)

分析 `data/learning_log.jsonl` 文件，提供以下洞察：

- **策略分布**: 不同检索策略的使用频率
- **可塑性趋势**: 记忆可塑性值的统计和趋势
- **KG 触发**: 知识图谱触发的频率和模式
- **反思触发**: 反思机制触发的频率和模式
- **覆盖率**: 查询覆盖率的统计
- **记忆数量**: 总记忆数和返回记忆数的统计

#### 使用方法

```bash
# 基本用法
python scripts/analysis/analyze_learning_log.py

# 指定日志文件
python scripts/analysis/analyze_learning_log.py --log data/learning_log.jsonl

# 指定输出路径
python scripts/analysis/analyze_learning_log.py --output results/my_analysis.json

# 仅打印报告，不保存 JSON
python scripts/analysis/analyze_learning_log.py --report-only
```

#### 输出示例

```
================================================================================
LEARNING LOG ANALYSIS REPORT
================================================================================
Log file: data/learning_log.jsonl
Total events: 50

RETRIEVAL STRATEGY DISTRIBUTION
----------------------------------------
Total retrievals: 50
Overall strategy distribution:
  temporal_hybrid_fallback: 20 (40.0%)
  hybrid: 30 (60.0%)

PLASTICITY TRENDS
----------------------------------------
Mean plasticity: 0.7234
Median plasticity: 0.6721
Range: 0.4005 - 1.2268
Std deviation: 0.1891
Total samples: 250

KNOWLEDGE GRAPH TRIGGERING
----------------------------------------
KG trigger rate: 20.00%
  Triggered: 10
  Not triggered: 40
```

### 2. MeMOS 评估脚本 (`run_bmam_memos_eval.py`)

运行单次 MeMOS 评估，支持自定义实验配置。

#### 使用方法

```bash
# 使用基准配置
python scripts/evaluation/run_bmam_memos_eval.py

# 使用无 KG 配置
python scripts/evaluation/run_bmam_memos_eval.py \
  --config configs/experiment_configs/no_kg_config.json

# 使用低 KG 配置
python scripts/evaluation/run_bmam_memos_eval.py \
  --config configs/experiment_configs/low_kg_config.json

# 自定义输出目录
python scripts/evaluation/run_bmam_memos_eval.py \
  --config configs/experiment_configs/baseline_config.json \
  --output results/my_eval

# 启用详细日志
python scripts/evaluation/run_bmam_memos_eval.py \
  --config configs/experiment_configs/no_kg_config.json \
  --verbose
```

#### 输出结果

评估完成后会生成：

- `memos_eval_{experiment_name}_{timestamp}.json`: 详细评估结果
- `summary_{experiment_name}_{timestamp}.json`: 汇总结果

### 3. 批量对比实验 (`run_kg_comparison.py`)

自动运行无 KG、低 KG、基准三种配置的对比实验。

#### 使用方法

```bash
# 运行所有对比实验
python scripts/evaluation/run_kg_comparison.py

# 指定输出目录
python scripts/evaluation/run_kg_comparison.py \
  --output results/my_comparison
```

#### 输出结果

```
================================================================================
KG CONFIGURATION COMPARISON REPORT
================================================================================
Timestamp: 2025-10-29T10:30:00.000000
Experiments: 3

ACCURACY COMPARISON
----------------------------------------
1. Baseline
   Accuracy: 87.50%
   Correct: 35/40

2. Low KG
   Accuracy: 82.50%
   Correct: 33/40

3. No KG
   Accuracy: 75.00%
   Correct: 30/40

DETAILED COMPARISON
----------------------------------------
No KG vs Baseline:
  Absolute difference: -12.50%
  Relative difference: -14.3%

Low KG vs Baseline:
  Absolute difference: -5.00%
  Relative difference: -5.7%

INSIGHTS
----------------------------------------
• Best configuration: Baseline (87.50%)
• KG provides 16.7% improvement over no KG
• Current KG weighting appears optimal
```

生成文件：
- `comparison_results_{timestamp}.json`: JSON 格式结果
- `comparison_report_{timestamp}.txt`: 文本报告

## 🎯 实验配置说明

### 无 KG 配置 (`no_kg_config.json`)

**目标**: 完全禁用知识图谱，作为对比基线

**关键参数**:
- `kg_fact_plasticity_score`: 0.0（KG 不参与排序）
- `min_object_word_count`: 999（过滤所有 KG facts）
- `enable_kg`: false（禁用 KG）

### 低 KG 配置 (`low_kg_config.json`)

**目标**: 降低知识图谱权重，测试弱化 KG 的影响

**关键参数**:
- `kg_fact_plasticity_score`: 0.8（低于基准的 2.5）
- `plasticity_score_threshold`: 0.3（较高的过滤阈值）
- `temporal_timeline_bonus`: 0.2（降低时间加成）

### 基准配置 (`baseline_config.json`)

**目标**: 当前生产配置，作为性能标准

**关键参数**:
- `kg_fact_plasticity_score`: 2.5（高优先级）
- `plasticity_score_threshold`: 0.2（适中过滤）
- `temporal_timeline_bonus`: 0.5（标准时间加成）

## 📊 分析工作流

### 典型分析流程

1. **运行对比实验**
   ```bash
   python scripts/evaluation/run_kg_comparison.py
   ```

2. **分析学习日志**
   ```bash
   python scripts/analysis/analyze_learning_log.py \
     --log data/learning_log.jsonl \
     --output results/learning_analysis.json
   ```

3. **查看结果**
   ```bash
   # 查看对比报告
   cat results/kg_comparison/comparison_report_*.txt

   # 查看学习日志分析
   python -m json.tool results/learning_analysis.json
   ```

### 单独测试某个配置

```bash
# 测试无 KG 配置
python scripts/evaluation/run_bmam_memos_eval.py \
  --config configs/experiment_configs/no_kg_config.json \
  --output results/test_no_kg \
  --verbose

# 分析该次运行的学习日志
python scripts/analysis/analyze_learning_log.py \
  --log data/learning_log.jsonl \
  --output results/test_no_kg/log_analysis.json
```

## 🔍 自定义实验配置

### 创建新配置

复制现有配置并修改关键参数：

```bash
cp configs/experiment_configs/baseline_config.json \
   configs/experiment_configs/my_config.json
```

编辑 `my_config.json`:

```json
{
  "experiment_name": "My Custom Config",
  "description": "自定义实验配置",
  "kg_merge_config": {
    "kg_fact_plasticity_score": 1.5,
    "overlap_threshold": 0.6,
    ...
  }
}
```

运行自定义配置：

```bash
python scripts/evaluation/run_bmam_memos_eval.py \
  --config configs/experiment_configs/my_config.json
```

### 关键可调参数

1. **KG 权重相关**
   - `kg_fact_plasticity_score`: KG facts 的可塑性得分（越高越优先）
   - `kg_facts_at_front`: KG facts 是否放在前面

2. **质量过滤**
   - `low_quality_predicates`: 低质量谓词集合
   - `min_object_word_count`: 对象最小词数

3. **去重策略**
   - `overlap_threshold`: 内容重叠阈值（越高越保守）
   - `preserve_vector_memories`: 是否保留向量记忆

4. **时间增强**
   - `temporal_timeline_bonus`: 时间线匹配加成
   - `temporal_relative_time_event_bonus`: 相对时间+事件加成

## 📈 结果解读

### 准确率差异解读

- **> 10%**: 显著差异，配置影响明显
- **5-10%**: 中等差异，值得进一步调查
- **< 5%**: 微小差异，可能在误差范围内

### KG 效果判断

如果 `Baseline accuracy > No KG accuracy + 5%`，则 KG 有明显效果。

如果 `Low KG accuracy ≈ Baseline accuracy`，则当前 KG 权重可能过高。

## 🐛 故障排查

### 常见问题

1. **日志文件不存在**
   ```
   Error: Log file not found at data/learning_log.jsonl
   ```

   **解决**: 先运行一次评估以生成日志：
   ```bash
   python scripts/evaluation/run_bmam_memos_eval.py
   ```

2. **配置验证失败**
   ```
   ValueError: Invalid KG merge config
   ```

   **解决**: 检查配置文件中的参数范围是否合法

3. **评估超时**
   ```
   Evaluation timed out after 10 minutes
   ```

   **解决**: 检查系统负载，或增加超时时间

## 📝 最佳实践

1. **先运行单次评估**，确保系统正常工作
2. **定期分析学习日志**，了解系统行为
3. **对比实验前清空旧日志**，避免混淆
4. **保存实验结果**，用于后续分析和对比
5. **记录配置变更**，维护实验可重复性

## 🔗 相关文档

- `TEAM_F_KG_MERGE_PARAMETRIZATION_GUIDE.md`: KG 融合参数化指南
- `BMAM/src/coordination/kg_merge_config.py`: 配置系统源码
- `PHASE_4_P1_TRACK2_FINAL_DIAGNOSIS.md`: Phase 4 P1 诊断报告

## 📧 问题反馈

如遇到问题或有改进建议，请：
1. 检查日志文件中的错误信息
2. 查看 `results/` 目录中的详细输出
3. 提供完整的错误堆栈信息
