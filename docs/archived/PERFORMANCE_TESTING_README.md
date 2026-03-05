# 性能与稳健性测试框架

## 概述

BMAM 项目包含全面的性能和稳健性测试框架，用于确保系统在高负载和故障条件下的稳定性。

## 📁 文件结构

```
BMAM/
├── tests/
│   ├── test_memory_system_suite.py              # 基础功能测试
│   ├── test_batch_consolidation_stress.py       # 批量巩固 + 长会话压力测试
│   └── test_fault_injection.py                  # 故障注入测试
│
├── scripts/
│   ├── run_performance_benchmark.sh             # 性能基准测试脚本
│   └── generate_performance_report.py           # 报告生成器
│
├── .github/workflows/
│   ├── memory_system_tests.yml                  # 常规CI（每次提交）
│   └── nightly_performance_tests.yml            # Nightly性能测试
│
├── benchmark_reports/                            # 测试报告目录（自动生成）
│   ├── benchmark_*.json                         # JSON报告
│   ├── latest_summary.txt                       # 最新摘要
│   └── dashboard.html                           # HTML仪表盘
│
└── 文档/
    ├── PERFORMANCE_TESTING_GUIDE.md             # 完整测试指南
    ├── PERFORMANCE_TESTING_DELIVERABLE.md       # 交付物说明
    └── QUICK_REFERENCE_PERFORMANCE_TESTING.md   # 快速参考卡片
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install pytest pytest-asyncio pytest-timeout
pip install -r requirements.txt
```

### 2. 设置环境变量

```bash
export OPENAI_API_KEY='your-api-key-here'
```

### 3. 运行测试

#### 快速测试（5分钟）
```bash
./run_memory_tests.sh
```

#### 压力测试（20分钟）
```bash
./run_memory_tests.sh --stress
```

#### 完整基准测试（1小时）
```bash
./scripts/run_performance_benchmark.sh
```

#### 查看报告
```bash
python3 scripts/generate_performance_report.py
open benchmark_reports/dashboard.html
```

## 📊 测试类型

### 1. 批量巩固压力测试

测试系统批量处理大量记忆的能力。

**测试用例**:
- ✅ 100条记忆批量巩固
- ✅ 巩固队列管理和优先级
- ✅ 并发巩固场景
- ✅ 500条记忆容量极限

**运行方式**:
```bash
pytest tests/test_batch_consolidation_stress.py::TestBatchConsolidationStress -v -s
```

**关键指标**:
- 巩固成功率: >= 60%
- 平均耗时: < 0.5秒/条
- 系统稳定性: 无崩溃

### 2. 长会话场景测试

测试长期对话中的性能稳定性。

**测试用例**:
- ✅ 50轮连续对话
- ✅ 100轮记忆累积
- ✅ 高负载检索性能

**运行方式**:
```bash
pytest tests/test_batch_consolidation_stress.py::TestLongSessionStress -v -s
```

**关键指标**:
- 平均响应时间: < 5秒
- 性能退化: < 50%
- 记忆管理: 自动清理有效

### 3. 故障注入测试

测试系统在异常情况下的稳健性。

**测试用例**:
- ✅ 数据库故障（连接失败、超时、数据损坏）
- ✅ API故障（调用失败、间歇性故障30%、慢速响应）
- ✅ 并发故障（竞争条件、写入冲突）
- ✅ 内存溢出
- ✅ 自动恢复和优雅降级

**运行方式**:
```bash
pytest tests/test_fault_injection.py -v -s -m fault_injection
```

**关键指标**:
- 系统不崩溃
- 错误正确捕获
- 自动恢复有效

## 🎯 使用场景

### 场景1: 开发时验证
在开发新功能或修改核心代码后：

```bash
# 运行快速功能测试
./run_memory_tests.sh

# 如果修改了记忆巩固相关代码，运行压力测试
./run_memory_tests.sh --stress
```

### 场景2: PR前验证
提交 Pull Request 前：

```bash
# 运行完整测试
./run_memory_tests.sh --full

# 或运行性能基准测试
./scripts/run_performance_benchmark.sh
```

### 场景3: 性能分析
需要分析系统性能或检测性能退化时：

```bash
# 运行基准测试并生成报告
./scripts/run_performance_benchmark.sh
python3 scripts/generate_performance_report.py

# 查看HTML仪表盘
open benchmark_reports/dashboard.html
```

### 场景4: CI/CD集成
系统已配置自动化测试：

- **每次提交**: 运行快速功能测试（5分钟）
- **每天凌晨2点**: 运行完整性能测试（2-3小时）
- **手动触发**: 可在 GitHub Actions 中手动触发

## 📈 性能基准

### 阈值标准

| 指标 | 目标阈值 | 说明 |
|------|---------|------|
| 巩固成功率 | >= 60% | 批量巩固测试成功率 |
| 平均响应时间 | < 5秒 | 长会话场景平均响应 |
| 性能退化 | < 50% | 长会话后期vs前期性能 |
| 总体通过率 | >= 80% | 所有测试整体通过率 |
| 最大响应时间 | < 15秒 | 单次查询最大响应 |

### 报告内容

生成的报告包含：

1. **实时状态**: 最新测试结果、通过率
2. **性能趋势**: 最近7次测试的趋势图
3. **测试历史**: 详细历史记录表格
4. **环境信息**: OS、Python版本等

## 🔧 高级用法

### 自定义超时

```bash
# 增加超时时间（秒）
pytest tests/ --timeout=3600
```

### 选择性运行

```bash
# 只运行压力测试
pytest -v -m stress

# 只运行故障注入测试
pytest -v -m fault_injection

# 跳过慢速测试
pytest -v -m "not slow"
```

### 调试模式

```bash
# 显示详细输出
pytest tests/ -v -s

# 显示DEBUG日志
pytest tests/ -v --log-cli-level=DEBUG

# 失败时进入pdb
pytest tests/ --pdb
```

## 📝 添加新测试

### 1. 创建测试类

在 `tests/test_batch_consolidation_stress.py` 或 `tests/test_fault_injection.py` 中：

```python
class TestNewFeature:
    @pytest.mark.asyncio
    @pytest.mark.stress  # 或 fault_injection
    async def test_new_scenario(self):
        coordinator = BrainInspiredCoordinator()

        # 测试实现
        ...

        await coordinator.stop_system()
```

### 2. 添加到基准脚本

编辑 `scripts/run_performance_benchmark.sh`：

```bash
total_benchmarks=$((total_benchmarks + 1))
if run_benchmark "新测试" "pytest tests/... --timeout=600" 900; then
    passed_benchmarks=$((passed_benchmarks + 1))
fi
```

### 3. 更新CI workflow

编辑 `.github/workflows/nightly_performance_tests.yml`：

```yaml
- name: Phase X - New Test
  run: pytest tests/... -v -s --timeout=600
  continue-on-error: true
```

## 🐛 故障排查

### 常见问题

1. **测试超时**
   ```bash
   pytest tests/ --timeout=3600  # 增加超时
   ```

2. **API Key错误**
   ```bash
   export OPENAI_API_KEY='your-key-here'
   echo $OPENAI_API_KEY  # 验证
   ```

3. **内存不足**
   ```bash
   pytest tests/ -n 1  # 单进程运行
   pytest tests/ -k "not capacity"  # 跳过容量测试
   ```

4. **数据库问题**
   ```bash
   rm -rf data/test_memories.db  # 清理旧数据
   ```

### 获取帮助

- **完整指南**: `PERFORMANCE_TESTING_GUIDE.md`
- **快速参考**: `QUICK_REFERENCE_PERFORMANCE_TESTING.md`
- **交付说明**: `PERFORMANCE_TESTING_DELIVERABLE.md`

## 📞 支持

- **问题反馈**: 创建 GitHub Issue
- **改进建议**: 提交 Pull Request
- **文档更新**: 编辑相关 Markdown 文件

---

## 🎉 总结

本测试框架提供：

- ✅ 全面的压力测试（批量巩固、长会话）
- ✅ 完整的故障注入测试（8种故障类型）
- ✅ 自动化CI/CD集成（Nightly Job）
- ✅ 可视化报告和仪表盘
- ✅ 详细的使用文档

**确保 BMAM 在高负载和故障条件下保持稳健，长流程不退化。**

---

**版本**: 1.0.0
**最后更新**: 2025-01-11
**维护者**: BMAM Team
