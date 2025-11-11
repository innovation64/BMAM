#!/bin/bash
# 性能基准测试脚本
# 用于 nightly job，生成性能报告

set -e

echo "=================================================="
echo "BMAM 性能和稳健性基准测试"
echo "=================================================="
echo ""

# 配置
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="benchmark_reports"
REPORT_FILE="${REPORT_DIR}/benchmark_${TIMESTAMP}.json"
HTML_REPORT="${REPORT_DIR}/benchmark_${TIMESTAMP}.html"
SUMMARY_FILE="${REPORT_DIR}/latest_summary.txt"

# 创建报告目录
mkdir -p "$REPORT_DIR"

echo "报告将保存到: $REPORT_DIR"
echo "时间戳: $TIMESTAMP"
echo ""

# 检查环境变量
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  错误: OPENAI_API_KEY 未设置"
    echo "请运行: export OPENAI_API_KEY='your-key-here'"
    exit 1
fi

# 函数：运行基准测试
run_benchmark() {
    local test_name=$1
    local test_command=$2
    local timeout=$3

    echo "=========================================="
    echo "运行: $test_name"
    echo "超时: ${timeout}秒"
    echo "=========================================="

    start_time=$(date +%s)

    if timeout "${timeout}s" $test_command; then
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))
        echo "✅ $test_name: 完成 (耗时: ${elapsed}秒)"
        return 0
    else
        exit_code=$?
        end_time=$(date +%s)
        elapsed=$((end_time - start_time))

        if [ $exit_code -eq 124 ]; then
            echo "⏱️  $test_name: 超时 (${timeout}秒)"
        else
            echo "❌ $test_name: 失败 (exit code: $exit_code)"
        fi
        return 1
    fi
}

# 初始化计数器
total_benchmarks=0
passed_benchmarks=0
failed_benchmarks=0
timeout_benchmarks=0

# 基准测试套件
echo "=================================================="
echo "第1阶段: 快速功能测试"
echo "=================================================="
echo ""

# 1. 快速功能测试（确保基本功能正常）
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "快速功能验证" "pytest tests/test_memory_system_suite.py -v -m 'not slow' --tb=short --timeout=300" 600; then
    passed_benchmarks=$((passed_benchmarks + 1))
else
    failed_benchmarks=$((failed_benchmarks + 1))
fi

echo ""
echo "=================================================="
echo "第2阶段: 压力测试"
echo "=================================================="
echo ""

# 2. 批量巩固压力测试
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "批量巩固压力测试" "pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress -v -s --timeout=1800" 2400; then
    passed_benchmarks=$((passed_benchmarks + 1))
else
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        timeout_benchmarks=$((timeout_benchmarks + 1))
    else
        failed_benchmarks=$((failed_benchmarks + 1))
    fi
fi

# 3. 长会话压力测试
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "长会话压力测试" "pytest tests/test_batch_consolidation_stress.py::TestLongSessionStress -v -s --timeout=1800" 2400; then
    passed_benchmarks=$((passed_benchmarks + 1))
else
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        timeout_benchmarks=$((timeout_benchmarks + 1))
    else
        failed_benchmarks=$((failed_benchmarks + 1))
    fi
fi

# 4. 容量极限测试
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "容量极限测试" "pytest tests/test_batch_consolidation_stress.py::TestMemoryCapacityLimits -v -s --timeout=2400" 3000; then
    passed_benchmarks=$((passed_benchmarks + 1))
else
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        timeout_benchmarks=$((timeout_benchmarks + 1))
    else
        failed_benchmarks=$((failed_benchmarks + 1))
    fi
fi

echo ""
echo "=================================================="
echo "第3阶段: 故障注入测试"
echo "=================================================="
echo ""

# 5. 数据库故障注入
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "数据库故障注入" "pytest tests/test_fault_injection.py::TestDatabaseFaultInjection -v -s --timeout=600" 900; then
    passed_benchmarks=$((passed_benchmarks + 1))
else
    failed_benchmarks=$((failed_benchmarks + 1))
fi

# 6. API故障注入
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "API故障注入" "pytest tests/test_fault_injection.py::TestAPIFaultInjection -v -s --timeout=600" 900; then
    passed_benchmarks=$((passed_benchmarks + 1))
else
    failed_benchmarks=$((failed_benchmarks + 1))
fi

# 7. 并发故障测试
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "并发故障测试" "pytest tests/test_fault_injection.py::TestConcurrencyFaults -v -s --timeout=600" 900; then
    passed_benchmarks=$((passed_benchmarks + 1))
else
    failed_benchmarks=$((failed_benchmarks + 1))
fi

# 8. 恢复机制测试
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "恢复机制测试" "pytest tests/test_fault_injection.py::TestRecoveryMechanisms -v -s --timeout=600" 900; then
    passed_benchmarks=$((passed_benchmarks + 1))
else
    failed_benchmarks=$((failed_benchmarks + 1))
fi

echo ""
echo "=================================================="
echo "第4阶段: LoCoMo 基准测试 (可选)"
echo "=================================================="
echo ""

# 9. LoCoMo 5Q 基准 (长时间运行)
if [ "$1" == "--full" ]; then
    total_benchmarks=$((total_benchmarks + 1))
    if run_benchmark "LoCoMo 5Q 基准" "pytest tests/test_memory_system_suite.py::TestLoCoMoBenchmark -v -s --timeout=3600" 4200; then
        passed_benchmarks=$((passed_benchmarks + 1))
    else
        exit_code=$?
        if [ $exit_code -eq 124 ]; then
            timeout_benchmarks=$((timeout_benchmarks + 1))
        else
            failed_benchmarks=$((failed_benchmarks + 1))
        fi
    fi
else
    echo "跳过 LoCoMo 基准 (使用 --full 运行完整基准)"
fi

# 生成总结报告
echo ""
echo "=================================================="
echo "基准测试总结"
echo "=================================================="
echo "时间戳: $TIMESTAMP"
echo "总测试数: $total_benchmarks"
echo "通过: $passed_benchmarks"
echo "失败: $failed_benchmarks"
echo "超时: $timeout_benchmarks"
echo ""

# 计算通过率
if [ $total_benchmarks -gt 0 ]; then
    pass_rate=$((passed_benchmarks * 100 / total_benchmarks))
else
    pass_rate=0
fi

echo "通过率: ${pass_rate}%"

# 保存摘要
cat > "$SUMMARY_FILE" <<EOF
BMAM 性能基准测试摘要
=====================
测试时间: $(date)
时间戳: $TIMESTAMP

总计: $total_benchmarks
通过: $passed_benchmarks
失败: $failed_benchmarks
超时: $timeout_benchmarks
通过率: ${pass_rate}%

详细报告: $REPORT_FILE
EOF

echo ""
echo "摘要已保存: $SUMMARY_FILE"

# 生成 JSON 报告
cat > "$REPORT_FILE" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "date": "$(date -Iseconds)",
  "summary": {
    "total": $total_benchmarks,
    "passed": $passed_benchmarks,
    "failed": $failed_benchmarks,
    "timeout": $timeout_benchmarks,
    "pass_rate": $pass_rate
  },
  "environment": {
    "os": "$(uname -s)",
    "python_version": "$(python3 --version)",
    "hostname": "$(hostname)"
  },
  "status": "$([ $pass_rate -ge 80 ] && echo 'PASS' || echo 'FAIL')"
}
EOF

echo "JSON 报告已保存: $REPORT_FILE"

# 决定退出码
echo ""
if [ $pass_rate -ge 80 ]; then
    echo "✅ 基准测试通过 (>= 80%)"
    exit 0
elif [ $pass_rate -ge 60 ]; then
    echo "⚠️  基准测试部分通过 (60-79%)"
    exit 0
else
    echo "❌ 基准测试失败 (< 60%)"
    exit 1
fi
