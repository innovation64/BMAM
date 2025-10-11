# BMAM vs MemOS Benchmark Comparison Guide

## 🎯 科研诚信声明

**本评估系统不使用任何模拟(mock)数据。所有对比必须基于真实的MemOS评估结果。**

这确保了：
- ✅ 科研诚信和可重复性
- ✅ 公平的性能对比
- ✅ 可验证的实验结果

---

## 📋 评估流程

### 步骤 1: 检查 MemOS 基线是否可用

```bash
python run_benchmark_comparison.py --mode check
```

这将检查：
- MemOS 评估结果是否存在
- 结果文件路径是否正确
- 提供缺失数据的生成指南

### 步骤 2: 生成 MemOS 基线数据（如果缺失）

如果 `--mode check` 显示缺失数据，需要先运行 MemOS 评估：

#### 对于 LongMemEval:
```bash
cd /Users/liyang/Desktop/testversion/MemOS
python evaluation/scripts/run_longmemeval.py
```

#### 对于 LoCoMo:
```bash
cd /Users/liyang/Desktop/testversion/MemOS
python evaluation/scripts/run_locomo.py
```

**重要**:
- 确保 MemOS 环境配置正确
- 检查 API keys (如需要)
- 评估可能需要数小时完成
- 结果将自动保存到 `evaluation/scripts/results/` 目录

### 步骤 3: 查看可用的 Benchmark 数据集

```bash
python run_benchmark_comparison.py --mode list
```

显示：
- 可用的 benchmark 数据集
- 数据集缓存状态
- 数据集描述

### 步骤 4: 设置 Benchmark 数据集（首次运行）

```bash
python run_benchmark_comparison.py --mode setup
```

这将下载并缓存：
- LongMemEval 数据集
- LoCoMo 数据集
- Needle in Haystack 数据集
- MemoryBank 数据集

### 步骤 5: 运行快速对比（核心 benchmarks）

```bash
python run_benchmark_comparison.py --mode quick
```

运行对比：
- LongMemEval
- LoCoMo

预计时间：30-60分钟

### 步骤 6: 运行完整对比（所有 benchmarks）

```bash
python run_benchmark_comparison.py --mode full
```

运行对比：
- LongMemEval
- LoCoMo
- Needle in Haystack
- MemoryBank

预计时间：2-3小时

---

## 🔧 高级选项

### 指定特定 benchmark

```bash
python run_benchmark_comparison.py --benchmarks longmemeval
python run_benchmark_comparison.py --benchmarks locomo longmemeval
```

### 指定 MemOS 路径

```bash
python run_benchmark_comparison.py --memos-path /path/to/MemOS --mode check
```

### 指定输出目录

```bash
python run_benchmark_comparison.py --output-dir ./my_results --mode quick
```

### 强制刷新数据集缓存

```bash
python run_benchmark_comparison.py --mode setup --force-refresh
```

### 启用详细日志

```bash
python run_benchmark_comparison.py --mode quick --verbose
```

---

## 📊 结果输出

评估完成后，结果保存在 `results/benchmark_comparison/`:

```
results/benchmark_comparison/
├── comprehensive_benchmark_comparison_YYYYMMDD_HHMMSS.json  # 详细 JSON 结果
├── benchmark_summary_YYYYMMDD_HHMMSS.txt                    # 文本摘要
├── latest_comprehensive_comparison.json                      # 最新结果快速访问
└── individual_benchmark_results/
    ├── longmemeval_comparison_YYYYMMDD_HHMMSS.json
    └── locomo_comparison_YYYYMMDD_HHMMSS.json
```

### 结果内容：

1. **整体对比**
   - BMAM vs MemOS 获胜指标数
   - 平均性能提升百分比
   - 各 benchmark 表现汇总

2. **详细指标**
   - LLM Judge 评分
   - 词法指标 (F1, ROUGE, BLEU, METEOR)
   - 语义指标 (BERT F1, Similarity)
   - 性能指标 (响应时间, 检索时间, token使用)

3. **分类表现** (LoCoMo)
   - Single-hop 问题
   - Multi-hop 问题
   - Temporal reasoning
   - Open-domain 问题

---

## ⚠️ 常见问题

### Q: 为什么不提供默认的 MemOS 基线数据？

**A**: 为了确保科研诚信。评估对比必须基于您本地运行的真实 MemOS 结果，而不是预设的估计值。这确保：
- 评估环境的一致性（相同的硬件、API 版本等）
- 结果的可重复性
- 公平的对比（相同的评估条件）

### Q: MemOS 评估失败怎么办？

**A**: 检查：
1. MemOS 环境是否正确安装
2. OpenAI API key 是否配置 (`.env` 文件)
3. 网络连接是否正常
4. 查看 MemOS 的评估文档

### Q: 可以跳过 MemOS 基线只评估 BMAM 吗？

**A**: 可以，但这不是"对比评估"。如果只想评估 BMAM 性能，使用：
```bash
# 直接运行 BMAM 评估脚本
python evaluation/run_bmam_only_evaluation.py
```

### Q: 评估需要多长时间？

**A**: 取决于：
- Benchmark 大小
- LLM API 响应速度
- 选择的 benchmark 数量

估计时间：
- Quick mode: 30-60分钟
- Full mode: 2-3小时
- MemOS baseline 生成: 每个 benchmark 30-90分钟

---

## 📚 评估指标说明

### LLM Judge Score
- GPT-4 评估响应质量
- 范围: 0-1
- 越高越好

### F1 Score
- 精确率和召回率的调和平均
- 范围: 0-1
- 越高越好

### ROUGE (Recall-Oriented Understudy for Gisting Evaluation)
- rouge1_f: Unigram overlap
- rouge2_f: Bigram overlap
- rougeL_f: Longest common subsequence
- 范围: 0-1, 越高越好

### BLEU (Bilingual Evaluation Understudy)
- bleu1-4: N-gram precision (1-4 grams)
- 范围: 0-1, 越高越好

### METEOR
- 考虑同义词和词形的机器翻译评估指标
- 范围: 0-1, 越高越好

### BERT F1
- 基于 BERT 嵌入的语义相似度
- 范围: 0-1, 越高越好

### Similarity
- Sentence-BERT 余弦相似度
- 范围: 0-1, 越高越好

### 性能指标
- **response_duration_ms**: 响应生成时间
- **search_duration_ms**: 记忆检索时间
- **total_duration_ms**: 总处理时间
- **context_tokens**: 使用的上下文 token 数

---

## 🚀 快速开始示例

完整的评估流程：

```bash
# 1. 检查状态
python run_benchmark_comparison.py --mode check

# 2. 如果缺失 MemOS 基线，生成它
cd /Users/liyang/Desktop/testversion/MemOS
python evaluation/scripts/run_locomo.py
cd -

# 3. 再次检查确认
python run_benchmark_comparison.py --mode check

# 4. 运行快速对比
python run_benchmark_comparison.py --mode quick

# 5. 查看结果
cat results/benchmark_comparison/latest_comprehensive_comparison.json
```

---

## 📖 引用

如果您在研究中使用此评估框架，请引用：

```bibtex
@software{bmam_benchmark_2024,
  title = {BMAM Benchmark Comparison Framework},
  author = {Your Name},
  year = {2024},
  note = {No mock data - real evaluations only}
}
```

---

## 🔗 相关资源

- [MemOS Repository](https://github.com/mem0ai/mem0)
- [LongMemEval Benchmark](https://github.com/Psycoy/LongMemEval)
- [LoCoMo Benchmark](https://github.com/psycoy/LoCoMo-Benchmark)
- [BMAM Documentation](./README.md)

---

**最后提醒**:
- ❌ 禁止使用模拟数据
- ✅ 所有对比基于真实评估
- 📊 确保结果可重复
- 🔬 保持科研诚信