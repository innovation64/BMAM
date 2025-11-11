# BMAM 性能与稳健性测试指南

本指南介绍 BMAM 项目的性能和稳健性测试框架，包括批量巩固、长会话场景和故障注入测试。

## 📋 目录

1. [测试概述](#测试概述)
2. [快速开始](#快速开始)
3. [测试类型](#测试类型)
4. [运行测试](#运行测试)
5. [CI/CD 集成](#cicd-集成)
6. [报告和仪表盘](#报告和仪表盘)
7. [故障排查](#故障排查)

---

## 测试概述

BMAM 性能测试框架设计用于确保系统在高负载和故障条件下的稳健性，防止长流程退化。

### 测试目标

- ✅ **批量巩固**: 验证系统处理大量记忆的能力（100+记忆）
- ✅ **长会话场景**: 测试长期对话中的性能稳定性（50+轮）
- ✅ **故障注入**: 确保系统在异常情况下优雅降级
- ✅ **性能基准**: 建立性能基线并追踪趋势

### 测试架构

```
BMAM/
├── tests/
│   ├── test_memory_system_suite.py          # 基础功能测试
│   ├── test_batch_consolidation_stress.py    # 压力测试
│   └── test_fault_injection.py               # 故障注入测试
├── scripts/
│   ├── run_performance_benchmark.sh          # 性能基准脚本
│   └── generate_performance_report.py        # 报告生成器
├── .github/workflows/
│   ├── memory_system_tests.yml               # 常规 CI
│   └── nightly_performance_tests.yml         # Nightly 性能测试
└── benchmark_reports/                         # 测试报告目录
```

---

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install pytest pytest-asyncio pytest-timeout
pip install -r requirements.txt

# 设置 API Key
export OPENAI_API_KEY='your-api-key-here'
```

### 2. 运行快速测试

```bash
# 运行基础功能测试
./run_memory_tests.sh

# 运行快速压力测试
pytest tests/test_batch_consolidation_stress.py -v -m stress
```

### 3. 运行完整基准测试

```bash
# 标准基准测试（约1小时）
./scripts/run_performance_benchmark.sh

# 完整基准测试（包括 LoCoMo，约3小时）
./scripts/run_performance_benchmark.sh --full
```

---

## 测试类型

### 1. 批量巩固压力测试

**文件**: `tests/test_batch_consolidation_stress.py`

测试系统批量处理记忆的能力：

```python
# 测试类
- TestBatchConsolidationStress
  - test_batch_consolidation_100_memories()     # 100条记忆批量巩固
  - test_consolidation_queue_management()       # 队列管理
  - test_concurrent_consolidation()             # 并发巩固

- TestMemoryCapacityLimits
  - test_capacity_limit_500_memories()          # 500条记忆容量测试
  - test_memory_overflow_handling()             # 溢出处理
```

**运行方式**:

```bash
# 运行所有批量巩固测试
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress -v -s

# 运行单个测试
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress::test_batch_consolidation_100_memories -v -s
```

**关键指标**:

- 巩固率: >= 60%
- 平均耗时: < 0.5秒/记忆
- 系统稳定性: 无崩溃

### 2. 长会话压力测试

**文件**: `tests/test_batch_consolidation_stress.py`

测试长期对话中的性能稳定性：

```python
# 测试类
- TestLongSessionStress
  - test_50_turn_conversation()                 # 50轮对话
  - test_long_session_memory_accumulation()     # 记忆累积测试
  - test_retrieval_performance_under_load()     # 高负载检索
```

**运行方式**:

```bash
pytest tests/test_batch_consolidation_stress.py::TestLongSessionStress -v -s
```

**关键指标**:

- 平均响应时间: < 5秒
- 性能退化: < 50%
- 记忆管理: 自动清理机制有效

### 3. 故障注入测试

**文件**: `tests/test_fault_injection.py`

测试系统在异常情况下的稳健性：

```python
# 测试类
- TestDatabaseFaultInjection        # 数据库故障
- TestAPIFaultInjection             # API 调用故障
- TestConcurrencyFaults             # 并发竞争故障
- TestMemoryOverflowFaults          # 内存溢出故障
- TestRecoveryMechanisms            # 恢复机制测试
```

**故障类型**:

1. **数据库故障**
   - 连接失败
   - 超时
   - 数据损坏

2. **API 故障**
   - 调用失败
   - 间歇性故障（30%概率）
   - 慢速响应

3. **并发故障**
   - 竞争条件
   - 写入冲突

4. **恢复机制**
   - 自动恢复
   - 优雅降级

**运行方式**:

```bash
# 运行所有故障注入测试
pytest tests/test_fault_injection.py -v -s -m fault_injection

# 运行特定类别
pytest tests/test_fault_injection.py::TestDatabaseFaultInjection -v -s
```

---

## 运行测试

### 本地测试

#### 1. 基础功能验证

```bash
# 快速功能测试（< 5分钟）
pytest tests/test_memory_system_suite.py -v -m "not slow"
```

#### 2. 压力测试

```bash
# 批量巩固压力测试（约30分钟）
pytest tests/test_batch_consolidation_stress.py -v -s --timeout=1800

# 长会话压力测试（约30分钟）
pytest tests/test_batch_consolidation_stress.py::TestLongSessionStress -v -s
```

#### 3. 故障注入测试

```bash
# 所有故障注入测试（约20分钟）
pytest tests/test_fault_injection.py -v -s --timeout=600
```

#### 4. 完整基准测试

```bash
# 使用脚本运行完整基准测试
cd BMAM
./scripts/run_performance_benchmark.sh

# 查看报告
cat benchmark_reports/latest_summary.txt
```

### 测试标记

使用 pytest markers 过滤测试：

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

---

## CI/CD 集成

### GitHub Actions Workflows

#### 1. 常规 CI（每次提交）

**文件**: `.github/workflows/memory_system_tests.yml`

触发条件：
- Push 到 main/master/develop
- Pull Request

测试内容：
- ✅ 快速功能测试
- ✅ 基础 KG 和推理测试
- ⚠️ 慢速测试（continue-on-error）

#### 2. Nightly 性能测试

**文件**: `.github/workflows/nightly_performance_tests.yml`

触发条件：
- 每天凌晨 2:00 UTC
- 手动触发（workflow_dispatch）

测试阶段：

```yaml
Phase 1: 快速功能验证 (5分钟)
Phase 2: 压力测试 (90分钟)
  - 批量巩固
  - 长会话
  - 容量极限
Phase 3: 故障注入 (40分钟)
  - 数据库故障
  - API 故障
  - 并发故障
  - 恢复机制
Phase 4: LoCoMo 基准 (60分钟，可选)
```

### 手动触发 Nightly Job

在 GitHub Actions 页面：

1. 选择 "Nightly Performance & Robustness Tests"
2. 点击 "Run workflow"
3. 选择是否运行完整基准（包括 LoCoMo）
4. 点击 "Run workflow" 确认

---

## 报告和仪表盘

### 1. 生成报告

```bash
# 运行基准测试（自动生成报告）
./scripts/run_performance_benchmark.sh

# 手动生成 HTML 仪表盘
python3 scripts/generate_performance_report.py
```

### 2. 查看报告

```bash
# 查看最新摘要
cat benchmark_reports/latest_summary.txt

# 查看 JSON 报告
cat benchmark_reports/benchmark_*.json

# 打开 HTML 仪表盘
open benchmark_reports/dashboard.html
```

### 3. 报告内容

HTML 仪表盘包含：

- **最新结果**: 总测试数、通过率、失败数
- **性能趋势**: 最近 7 次测试的趋势图
- **测试历史**: 详细历史记录表格
- **测试分类**: 各类测试概览
- **环境信息**: OS、Python 版本等

### 4. CI Artifacts

在 GitHub Actions 中：

1. 进入 Workflow Run 页面
2. 滚动到底部 "Artifacts" 部分
3. 下载 `nightly-benchmark-reports-*`
4. 解压查看详细报告

保留时间：30天

---

## 故障排查

### 常见问题

#### 1. 测试超时

**症状**: 测试运行超过预期时间

**解决方案**:

```bash
# 增加超时时间
pytest tests/test_batch_consolidation_stress.py --timeout=3600

# 或修改 pytest.ini
[pytest]
timeout = 3600
```

#### 2. API 调用失败

**症状**: `OPENAI_API_KEY` 相关错误

**解决方案**:

```bash
# 确认 API Key 已设置
echo $OPENAI_API_KEY

# 重新设置
export OPENAI_API_KEY='your-key-here'
```

#### 3. 内存不足

**症状**: 系统崩溃或 OOM 错误

**解决方案**:

```bash
# 减少并发测试数量
pytest tests/ -n 1  # 单进程运行

# 或跳过容量极限测试
pytest tests/ -v -k "not capacity"
```

#### 4. 数据库连接问题

**症状**: 数据库连接失败

**解决方案**:

```bash
# 检查数据库配置
# 确保 db_manager 正确初始化

# 清理旧数据
rm -rf data/test_memories.db
```

### 调试技巧

#### 1. 详细输出

```bash
# 使用 -s 显示 print 输出
pytest tests/test_batch_consolidation_stress.py -v -s

# 使用 --log-cli-level 显示日志
pytest tests/ -v --log-cli-level=DEBUG
```

#### 2. 单独运行测试

```bash
# 运行单个测试函数
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress::test_batch_consolidation_100_memories -v -s
```

#### 3. 使用 pdb 调试

```python
# 在测试中添加断点
import pdb; pdb.set_trace()
```

```bash
# 运行时自动进入失败的测试
pytest tests/ --pdb
```

### 性能分析

#### 1. 性能剖析

```bash
# 使用 pytest-profiling
pip install pytest-profiling
pytest tests/ --profile
```

#### 2. 内存分析

```bash
# 使用 memory-profiler
pip install memory-profiler
python -m memory_profiler tests/test_batch_consolidation_stress.py
```

---

## 最佳实践

### 1. 测试开发

- ✅ 保持测试独立（不依赖外部状态）
- ✅ 使用 fixtures 共享设置
- ✅ 清理测试数据（teardown）
- ✅ 使用合理的超时时间
- ✅ 添加详细的日志输出

### 2. CI/CD

- ✅ 快速测试在 PR 中运行
- ✅ 慢速测试在 nightly job 中运行
- ✅ 保留测试 artifacts（30天）
- ✅ 监控测试趋势
- ✅ 设置性能阈值

### 3. 报告

- ✅ 定期查看 nightly 报告
- ✅ 关注性能退化趋势
- ✅ 建立性能基线
- ✅ 记录重大变更

---

## 附录

### A. 测试配置

**pytest.ini**:

```ini
[pytest]
markers =
    stress: marks tests as stress tests
    fault_injection: marks tests as fault injection tests
    slow: marks tests as slow tests
    asyncio: marks tests as async
timeout = 300
asyncio_mode = auto
```

### B. 性能阈值

| 指标 | 阈值 | 说明 |
|------|------|------|
| 巩固率 | >= 60% | 批量巩固成功率 |
| 响应时间 | < 5秒 | 平均查询响应时间 |
| 性能退化 | < 50% | 长会话性能退化 |
| 通过率 | >= 80% | 总体测试通过率 |

### C. 联系方式

- **问题反馈**: 创建 GitHub Issue
- **测试改进建议**: 提交 Pull Request
- **紧急问题**: 联系测试负责人

---

**最后更新**: 2025-01-11
**版本**: 1.0.0
**维护者**: BMAM Team
