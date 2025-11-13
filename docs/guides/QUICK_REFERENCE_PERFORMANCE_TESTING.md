# BMAM 性能测试快速参考卡片

## 🚀 快速命令

### 基础测试（5分钟）
```bash
export OPENAI_API_KEY='your-key-here'
./run_memory_tests.sh
```

### 压力测试（20分钟）
```bash
./run_memory_tests.sh --stress
```

### 完整测试（2-3小时）
```bash
./run_memory_tests.sh --full
```

### 性能基准测试（1小时）
```bash
./scripts/run_performance_benchmark.sh
```

### 生成报告
```bash
python3 scripts/generate_performance_report.py
open benchmark_reports/dashboard.html
```

---

## 📝 常用测试命令

### 批量巩固测试
```bash
# 快速测试（队列管理）
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress::test_consolidation_queue_management -v

# 100条记忆批量巩固
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress::test_batch_consolidation_100_memories -v -s

# 所有批量巩固测试
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress -v -s
```

### 长会话测试
```bash
# 50轮对话
pytest tests/test_batch_consolidation_stress.py::TestLongSessionStress::test_50_turn_conversation -v -s

# 100轮记忆累积
pytest tests/test_batch_consolidation_stress.py::TestLongSessionStress::test_long_session_memory_accumulation -v -s

# 高负载检索
pytest tests/test_batch_consolidation_stress.py::TestLongSessionStress::test_retrieval_performance_under_load -v -s
```

### 故障注入测试
```bash
# 数据库故障
pytest tests/test_fault_injection.py::TestDatabaseFaultInjection -v -s

# API故障
pytest tests/test_fault_injection.py::TestAPIFaultInjection -v -s

# 并发故障
pytest tests/test_fault_injection.py::TestConcurrencyFaults -v -s

# 恢复机制
pytest tests/test_fault_injection.py::TestRecoveryMechanisms -v -s

# 所有故障注入测试
pytest tests/test_fault_injection.py -v -s -m fault_injection
```

### 容量测试
```bash
# 500条记忆容量测试
pytest tests/test_batch_consolidation_stress.py::TestMemoryCapacityLimits::test_capacity_limit_500_memories -v -s

# 溢出处理
pytest tests/test_batch_consolidation_stress.py::TestMemoryCapacityLimits::test_memory_overflow_handling -v -s
```

---

## 🏷️ Pytest 标记

### 按标记运行
```bash
# 只运行压力测试
pytest -v -m stress

# 只运行故障注入测试
pytest -v -m fault_injection

# 跳过慢速测试
pytest -v -m "not slow"

# 组合标记
pytest -v -m "stress and not slow"
```

### 按关键字过滤
```bash
# 运行包含 "consolidation" 的测试
pytest -v -k "consolidation"

# 运行包含 "fault" 的测试
pytest -v -k "fault"

# 排除容量测试
pytest -v -k "not capacity"
```

---

## ⏱️ 超时控制

```bash
# 设置5分钟超时
pytest tests/ --timeout=300

# 设置30分钟超时
pytest tests/ --timeout=1800

# 设置1小时超时
pytest tests/ --timeout=3600
```

---

## 📊 查看报告

### 本地报告
```bash
# 查看最新摘要
cat benchmark_reports/latest_summary.txt

# 查看详细日志
tail -100 benchmark_reports/benchmark_*.json

# 打开HTML仪表盘
open benchmark_reports/dashboard.html  # macOS
xdg-open benchmark_reports/dashboard.html  # Linux
```

### CI报告
1. 访问 GitHub Actions
2. 选择 "Nightly Performance & Robustness Tests"
3. 点击最新的 workflow run
4. 滚动到 "Artifacts" 部分
5. 下载 `nightly-benchmark-reports-*`

---

## 🔧 调试技巧

### 详细输出
```bash
# 显示print输出
pytest tests/ -v -s

# 显示DEBUG日志
pytest tests/ -v --log-cli-level=DEBUG

# 失败时进入调试器
pytest tests/ --pdb
```

### 单独运行
```bash
# 运行单个测试文件
pytest tests/test_batch_consolidation_stress.py -v

# 运行单个测试类
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress -v

# 运行单个测试函数
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress::test_batch_consolidation_100_memories -v
```

---

## 📈 关键指标

| 指标 | 阈值 | 命令 |
|------|------|------|
| 巩固成功率 | >= 60% | 查看批量巩固测试输出 |
| 平均响应时间 | < 5秒 | 查看长会话测试输出 |
| 性能退化 | < 50% | 查看长会话测试输出 |
| 总体通过率 | >= 80% | 查看测试摘要 |

---

## 🎯 常见场景

### 场景1：验证新代码不破坏性能
```bash
# 运行快速压力测试
./run_memory_tests.sh --stress

# 检查通过率 >= 80%
```

### 场景2：完整性能验证
```bash
# 运行完整基准测试
./scripts/run_performance_benchmark.sh

# 生成报告
python3 scripts/generate_performance_report.py

# 查看仪表盘
open benchmark_reports/dashboard.html
```

### 场景3：调试故障注入问题
```bash
# 运行单个故障注入测试（详细输出）
pytest tests/test_fault_injection.py::TestDatabaseFaultInjection::test_database_connection_failure -v -s

# 如果失败，使用调试器
pytest tests/test_fault_injection.py::TestDatabaseFaultInjection::test_database_connection_failure -v -s --pdb
```

### 场景4：检查长会话性能退化
```bash
# 运行50轮对话测试
pytest tests/test_batch_consolidation_stress.py::TestLongSessionStress::test_50_turn_conversation -v -s

# 查看输出中的性能统计
# 平均响应时间、性能退化百分比
```

---

## 🔄 CI/CD 触发

### 手动触发 Nightly Job
1. 访问 GitHub → Actions
2. 选择 "Nightly Performance & Robustness Tests"
3. 点击 "Run workflow"
4. 选择选项：
   - `full_benchmark`: true/false（是否运行LoCoMo）
5. 点击 "Run workflow" 确认

### 自动触发
- **定时**: 每天凌晨 2:00 UTC
- **事件**: Push 到 main/master（仅快速测试）

---

## 📞 需要帮助？

- **文档**: `PERFORMANCE_TESTING_GUIDE.md`
- **交付物说明**: `PERFORMANCE_TESTING_DELIVERABLE.md`
- **问题反馈**: GitHub Issues
- **改进建议**: Pull Request

---

**版本**: 1.0.0
**更新**: 2025-01-11
