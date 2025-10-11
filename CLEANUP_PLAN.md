# 🧹 BMAM 项目整理方案

## 📊 当前状态分析

### 根目录文件统计:
- **Python测试文件**: 43个
- **Markdown文档**: 45个
- **问题**: 结构混乱,难以维护

---

## 🎯 整理目标结构

```
BMAM/
├── README.md                 # 主README (保留)
├── main.py                   # 主入口 (保留)
├── ui.py                     # UI入口 (保留)
├── requirements.txt          # 依赖 (保留)
│
├── src/                      # ✅ 源代码 (已整理)
│   ├── agents/
│   ├── brain/
│   ├── coordination/
│   ├── memory/
│   ├── reasoning/
│   └── ...
│
├── tests/                    # 测试文件目录
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   ├── benchmarks/           # 性能测试
│   │   ├── test_locomo_5questions.py      # 保留: 主要5题测试
│   │   ├── test_locomo_20questions.py     # 保留: 主要20题测试
│   │   └── evaluate_20q_with_llm_judge.py # 保留: LLM评估器
│   └── deprecated/           # 废弃测试 (待删除)
│
├── docs/                     # 文档目录
│   ├── architecture/         # 架构文档
│   ├── optimization/         # 优化记录
│   ├── sessions/             # 会话记录
│   └── guides/               # 使用指南
│
├── scripts/                  # 工具脚本
│   ├── clean_faiss_index.py
│   ├── fix_reasoning_signatures.py
│   └── install_voice_dependencies.py
│
├── config/                   # 配置文件
├── data/                     # 数据目录
└── archived/                 # 归档旧文件
```

---

## 📋 文件分类

### ✅ **保留在根目录**:
- `README.md`
- `main.py`
- `ui.py`
- `requirements.txt`

### 🗂️ **移动到 tests/benchmarks/**:
- `test_locomo_5questions.py` ✅ 主要
- `test_locomo_20questions.py` ✅ 主要
- `evaluate_20q_with_llm_judge.py` ✅ 主要
- `test_intelligent_selection.py` ✅ 主要

### 🗑️ **移动到 tests/deprecated/** (废弃测试):
- `test_locomo_correct.py`
- `test_locomo_expanded.py`
- `test_locomo_extended.py`
- `test_locomo_full.py`
- `test_locomo_session_based.py`
- `test_locomo_small.py`
- `test_brain_network_basic.py`
- `test_brain_network_distributed.py`
- `test_brain_vs_pipeline.py`
- `test_capability_generalization.py`
- `test_capability_orchestrator.py`
- `test_capability_quick.py`
- `test_complexity_detection.py`
- `test_constraint_engine.py`
- `test_cycle1_minimal.py`
- `test_distributed_memory.py`
- `test_distributed_reasoning_extended.py`
- `test_distributed_reasoning_simple.py`
- `test_memory_value_detection.py`
- `test_q3_q5_diagnosis.py`
- `test_q4_q7_final.py`
- `test_q4_q7_fix.py`
- `test_quick.py`
- `test_retrieval_debug.py`
- `test_time_range.py`
- `quick_5q_test.py`
- `quick_locomo_test.py`
- `run_locomo_benchmark.py`
- `run_quick_test.py`

### 🗂️ **移动到 scripts/**:
- `clean_faiss_index.py`
- `clean_prompts.py`
- `fix_reasoning_signatures.py`
- `install_voice_dependencies.py`
- `run_voice_ui.py`
- `run_benchmark_comparison.py`
- `run_evaluation.py`
- `brain_network_integration.py`

### 📚 **移动到 docs/architecture/**:
- `PROJECT_ARCHITECTURE.md`
- `CURRENT_ARCHITECTURE_TRUTH.md`
- `REAL_ARCHITECTURE.md`
- `CORRECTED_ARCHITECTURE.md`
- `BRAIN_AGENTS_WORKFLOW_EXPLAINED.md`
- `CORRECTED_BRAIN_REGION_ASSIGNMENT.md`
- `CORRECT_CLEANUP_UNDERSTANDING.md`

### 📚 **移动到 docs/optimization/**:
- `OPTIMIZATION_SUCCESS.md`
- `OPTIMIZATION_SUMMARY.md`
- `BRAIN_INSPIRED_VS_HARDCODED.md`
- `BRAIN_REGION_COLLABORATION_DESIGN.md`
- `BRAIN_REGION_INTEGRATION_PLAN.md`
- `CRITICAL_PERFORMANCE_ISSUE.md`
- `PERFORMANCE_BOTTLENECK_ANALYSIS.md`
- `MULTI_DIMENSIONAL_SYNTHESIS_DESIGN.md`
- `MULTI_DIMENSIONAL_SYNTHESIS_RESULTS.md`

### 📚 **移动到 docs/sessions/**:
- `SESSION_SUMMARY.md`
- `SESSION_SUMMARY_FINAL.md`
- `SESSION_BASED_LEARNING_SOLUTION.md`
- `FINAL_IMPLEMENTATION_SUMMARY.md`
- `FINAL_STATUS.md`
- `FINAL_SUMMARY.md`
- `INTEGRATION_COMPLETE_SUMMARY.md`

### 📚 **移动到 docs/fixes/**:
- `FIXES_SUMMARY.md`
- `P1_FIXES_SUMMARY.md`
- `Q3_Q5_FIXES.md`
- `Q4_IMPROVEMENT_SUMMARY.md`
- `SIGNATURE_FIX_SUMMARY.md`
- `TIME_RANGE_FIX_SUMMARY.md`
- `DIAGNOSIS_Q3_Q5_FAILURES.md`
- `FINAL_Q3_Q5_ANALYSIS.md`
- `TEMPORAL_AND_FACTUAL_FAILURE_ANALYSIS.md`

### 📚 **移动到 docs/comparison/**:
- `BMAM_20_CASES_FINAL_REPORT.md`
- `bmam_vs_memos_comparison.md`
- `DETAILED_TEST_COMPARISON.md`

### 📚 **移动到 docs/guides/**:
- `VOICE_UI_README.md`
- `VOICE_UI_USAGE.md`
- `QUICK_START_AB_TEST.md`
- `MICROPHONE_TROUBLESHOOTING.md`

### 🗑️ **可以删除的文档** (已过时/重复):
- `CURRENT_STATUS_AND_SOLUTION.md` (重复)
- `LEGACY_CODE_CLEANUP_PLAN.md` (已完成)
- `MULTI_SCENARIO_SOLUTION.md` (已过时)
- `PROJECT_ISSUES_ANALYSIS.md` (已解决)
- `SEMANTIC_TAGGING_ANALYSIS.md` (已过时)

---

## 🚀 执行步骤

### 1. 创建目录结构
```bash
mkdir -p tests/deprecated
mkdir -p docs/{architecture,optimization,sessions,fixes,comparison,guides}
mkdir -p scripts
mkdir -p archived
```

### 2. 移动测试文件
```bash
# 主要测试保留在tests/benchmarks/
mv test_locomo_{5questions,20questions}.py tests/benchmarks/
mv evaluate_20q_with_llm_judge.py tests/benchmarks/
mv test_intelligent_selection.py tests/benchmarks/

# 废弃测试移动到deprecated/
mv test_*.py tests/deprecated/
mv quick_*.py tests/deprecated/
mv run_locomo_benchmark.py tests/deprecated/
```

### 3. 移动文档
```bash
# 按分类移动所有.md文件
# (详见上面的分类)
```

### 4. 移动脚本
```bash
mv *.py scripts/  # 除了main.py和ui.py
```

### 5. Git提交
```bash
git add -A
git commit -m "Clean up project structure"
```

---

## ✅ 整理后的结构优势

1. **清晰的目录结构** - 文件分类明确
2. **易于维护** - 主要文件在根目录,测试和文档分开
3. **减少混乱** - 废弃文件归档,不影响开发
4. **方便查找** - 文档按类型分类,快速定位

---

## 🎯 最终根目录 (只保留4个文件)

```
BMAM/
├── README.md
├── main.py
├── ui.py
└── requirements.txt
```

所有其他文件都在对应的子目录中!
