#!/bin/bash
# Memory System 测试运行脚本
# 用于本地快速验证所有测试

set -e  # 遇到错误时退出

echo "=========================================="
echo "BMAM Memory System Test Suite"
echo "=========================================="
echo ""

# 检查环境变量
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  警告: OPENAI_API_KEY 未设置"
    echo "请运行: export OPENAI_API_KEY='your-key-here'"
    exit 1
fi

# 创建测试结果目录
mkdir -p test_results
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="test_results/memory_test_report_${TIMESTAMP}.txt"

echo "测试报告将保存到: $REPORT_FILE"
echo ""

# 函数：运行测试并记录结果
run_test() {
    local test_name=$1
    local test_command=$2
    local required=$3  # "required" 或 "optional"

    echo "=========================================="
    echo "运行: $test_name"
    echo "=========================================="

    if $test_command >> "$REPORT_FILE" 2>&1; then
        echo "✅ $test_name: PASSED" | tee -a "$REPORT_FILE"
        return 0
    else
        echo "❌ $test_name: FAILED" | tee -a "$REPORT_FILE"
        if [ "$required" == "required" ]; then
            echo "  (必需测试失败，继续运行其他测试...)"
        fi
        return 1
    fi
    echo ""
}

# 初始化计数器
total_tests=0
passed_tests=0

# 测试 1: Pytest 套件 (快速测试)
total_tests=$((total_tests + 1))
if run_test "Pytest Suite (Fast)" "pytest tests/test_memory_system_suite.py -v -m 'not slow' --tb=short" "required"; then
    passed_tests=$((passed_tests + 1))
fi

# 测试 2: KG 可观测性
total_tests=$((total_tests + 1))
if run_test "KG Observability" "python3 test_kg_observability.py" "required"; then
    passed_tests=$((passed_tests + 1))
fi

# 测试 3: 存储生命周期
total_tests=$((total_tests + 1))
if run_test "Storage Lifecycle" "python3 test_storage_lifecycle.py" "required"; then
    passed_tests=$((passed_tests + 1))
fi

# 测试 4: 推理链断言
total_tests=$((total_tests + 1))
if run_test "Reasoning Chain Assertions" "python3 test_reasoning_chain_assertions.py" "optional"; then
    passed_tests=$((passed_tests + 1))
fi

# 测试 5: 多脑区可观测性
total_tests=$((total_tests + 1))
if run_test "Multi-Brain Region Observability" "python3 test_multi_brain_region_observability.py" "optional"; then
    passed_tests=$((passed_tests + 1))
fi

# 测试 6: LoCoMo 5Q 基准 (慢速，可选)
if [ "$1" == "--full" ]; then
    echo ""
    echo "运行完整测试套件 (包括 LoCoMo 基准)..."
    total_tests=$((total_tests + 1))
    if run_test "LoCoMo 5Q Benchmark" "python3 test_locomo_hrm_5q.py" "optional"; then
        passed_tests=$((passed_tests + 1))
    fi

    # 测试 7: 巩固周期 (慢速)
    total_tests=$((total_tests + 1))
    if run_test "Consolidation Full Cycle" "python3 test_consolidation_full_cycle.py" "optional"; then
        passed_tests=$((passed_tests + 1))
    fi
else
    echo ""
    echo "提示: 使用 ./run_memory_tests.sh --full 运行完整测试（包括慢速测试）"
fi

# 总结
echo ""
echo "=========================================="
echo "测试总结"
echo "=========================================="
echo "通过: $passed_tests / $total_tests"
accuracy=$((passed_tests * 100 / total_tests))
echo "通过率: ${accuracy}%"
echo ""

if [ $accuracy -ge 80 ]; then
    echo "✅ 测试通过 (>= 80%)"
    echo ""
    echo "详细报告: $REPORT_FILE"
    exit 0
elif [ $accuracy -ge 60 ]; then
    echo "⚠️  部分测试失败 (60-79%)"
    echo "建议查看失败的测试："
    echo "  tail -100 $REPORT_FILE"
    exit 0
else
    echo "❌ 测试失败 (< 60%)"
    echo "请查看详细报告: $REPORT_FILE"
    exit 1
fi
