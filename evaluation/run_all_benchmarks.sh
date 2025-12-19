#!/bin/bash
# BMAM 完整评估脚本
# 运行所有 benchmark 评估

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "BMAM 完整 Benchmark 评估"
echo "========================================"
echo "时间: $(date)"
echo ""

# 参数
SAMPLES=${1:-"all"}  # 样本数: all 或 数字
RUN_ABLATION=${2:-"yes"}  # 是否运行消融: yes/no
RUN_EXTRA=${3:-"yes"}  # 是否运行额外测试: yes/no

if [ "$SAMPLES" != "all" ]; then
    SAMPLE_ARG="--samples $SAMPLES"
else
    SAMPLE_ARG=""
fi

# 1. LoCoMo (使用现有脚本)
echo ""
echo "========================================"
echo "1/10: LoCoMo 评估"
echo "========================================"
cd ../experiments/benchmarks/locomo
if [ "$SAMPLES" != "all" ]; then
    python test_sequential.py --groups 1 --questions "$SAMPLES"
else
    python test_sequential.py --groups 10
fi
cd "$SCRIPT_DIR"

# 2. LongMemEval
echo ""
echo "========================================"
echo "2/10: LongMemEval 评估"
echo "========================================"
python scripts/longmemeval/eval_longmemeval.py --dataset oracle $SAMPLE_ARG

# 3. PersonaMem
echo ""
echo "========================================"
echo "3/10: PersonaMem 评估"
echo "========================================"
python scripts/personamem/eval_personamem.py --personas 10 $SAMPLE_ARG

# 4. PrefEval
echo ""
echo "========================================"
echo "4/10: PrefEval 评估"
echo "========================================"
python scripts/prefeval/eval_prefeval.py $SAMPLE_ARG

# 5. 消融实验 (可选)
if [ "$RUN_ABLATION" = "yes" ]; then
    echo ""
    echo "========================================"
    echo "5/10: 组件消融实验"
    echo "========================================"
    python scripts/ablation/run_ablation.py --dataset locomo --samples 1
fi

# 6. 基线对比
if [ "$RUN_EXTRA" = "yes" ]; then
    echo ""
    echo "========================================"
    echo "6/10: 基线对比 (RAG, BM25)"
    echo "========================================"
    if [ "$SAMPLES" != "all" ]; then
        python scripts/baselines/eval_baselines.py --samples "$SAMPLES"
    else
        python scripts/baselines/eval_baselines.py --samples 30
    fi
fi

# 7. 效率分析
if [ "$RUN_EXTRA" = "yes" ]; then
    echo ""
    echo "========================================"
    echo "7/10: 效率分析"
    echo "========================================"
    python scripts/efficiency/eval_efficiency.py --test all
fi

# 8. Needle-in-Haystack
if [ "$RUN_EXTRA" = "yes" ]; then
    echo ""
    echo "========================================"
    echo "8/10: Needle-in-Haystack 测试"
    echo "========================================"
    python scripts/needle_haystack/eval_needle_haystack.py --size 1000 --depths 0 25 50 75 100 --repeats 2
fi

# 9. 可解释性分析
if [ "$RUN_EXTRA" = "yes" ]; then
    echo ""
    echo "========================================"
    echo "9/10: 可解释性分析"
    echo "========================================"
    python scripts/interpretability/eval_interpretability.py --test all
fi

# 10. 按类别分析
if [ "$RUN_EXTRA" = "yes" ]; then
    echo ""
    echo "========================================"
    echo "10/10: 按类别分析"
    echo "========================================"
    if [ "$SAMPLES" != "all" ]; then
        python scripts/category_analysis/eval_category_analysis.py --samples "$SAMPLES"
    else
        python scripts/category_analysis/eval_category_analysis.py --samples 50
    fi
fi

# 生成汇总报告
echo ""
echo "========================================"
echo "生成汇总报告"
echo "========================================"
python scripts/utils/generate_report.py

echo ""
echo "========================================"
echo "评估完成!"
echo "========================================"
echo "结果保存在: evaluation/results/"
echo ""
echo "使用方法:"
echo "  bash run_all_benchmarks.sh 10 no no   # 快速测试 (10 样本, 无消融, 无额外测试)"
echo "  bash run_all_benchmarks.sh all yes no # Benchmark + 消融"
echo "  bash run_all_benchmarks.sh all yes yes # 完整测试 (需要较长时间)"
