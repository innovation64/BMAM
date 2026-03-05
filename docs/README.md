# BMAM Documentation Index

Brain-inspired Multi-Agent Memory Framework Documentation

---

## Quick Links

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](QUICKSTART.md) | Get started in 5 minutes |
| [API.md](API.md) | Complete API reference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design & neuroscience basis |
| [BENCHMARKS.md](BENCHMARKS.md) | Evaluation results & reproducibility |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Contribution guidelines |

---

## 📂 Directory Structure

```
docs/
├── API.md             # API Reference
├── ARCHITECTURE.md    # System Architecture
├── BENCHMARKS.md      # Evaluation Results
├── QUICKSTART.md      # Quick Start Guide
├── archived/          # Historical documents
├── guides/            # Usage guides
├── development/       # Development docs
└── reports/           # Evaluation reports
```

---

## 📖 Reading Path

### New Users
1. [Quick Start Guide](QUICKSTART.md) - 5 minutes to get started
2. [Main README](../README.md) - Project overview
3. [API Reference](API.md) - How to use the system

### Developers
1. [Architecture](ARCHITECTURE.md) - System design
2. [API Reference](API.md) - Interface documentation
3. [Contributing Guide](../CONTRIBUTING.md) - How to contribute

### Researchers
1. [Architecture](ARCHITECTURE.md) - Neuroscience foundations
2. [Benchmarks](BENCHMARKS.md) - LoCoMo evaluation
3. [Phase 1-4 Reports](archived/) - Development history

---

## 📚 文档分类

### 🗂️ archived/ - 历史文档

**开发阶段报告** (51个文档):
- Phase 1-4 开发总结
- Session summaries (每日工作记录)
- 重构历史记录
- 功能完成报告

**用途**:
- 了解项目演化历史
- 查找特定功能的实现细节
- 追溯设计决策

### 📘 guides/ - 使用指南

**包含** (9个文档):
- 快速开始指南
- 记忆管理指南
- 模块化指南
- MBTI人格参考
- LoCoMo测试指南

**用途**:
- 快速上手系统
- 学习核心功能使用
- 参考最佳实践

### 🛠️ development/ - 开发文档

**包含** (7个文档):
- 系统架构设计
- 记忆归档格式
- 记忆快照设计
- 自动持久化实现
- 代码结构说明

**用途**:
- 理解系统设计
- 扩展新功能
- 贡献代码

### 📊 reports/ - 评测报告

**包含** (5个文档):
- LoCoMo benchmark结果
- 记忆系统验证报告
- 性能测试报告
- 多脑区验证报告

**用途**:
- 了解系统性能
- 验证功能完整性
- 对比版本差异

---

## 🔍 快速查找

### 想了解...

**"系统是如何工作的?"**
→ [架构设计](development/MEMORY_SYSTEM_ARCHITECTURE.md)

**"如何运行测试?"**
→ [LoCoMo测试指南](guides/LOCOMO_BMAM_TEST_GUIDE.md)

**"记忆是如何持久化的?"**
→ [自动持久化实现](development/AUTO_PERSISTENCE_IMPLEMENTATION.md)

**"系统性能如何?"**
→ [LoCoMo验证报告](reports/LOCOMO_100_PERCENT_VALIDATION.md)

**"如何创建检查点?"**
→ [记忆管理指南](guides/MEMORY_MANAGER_GUIDE.md)

**"系统经历了哪些重构?"**
→ [重构历史](archived/) - 查看各个Phase报告

---

## 📝 文档贡献

### 添加新文档时

1. **确定类别**:
   - 使用指南 → `guides/`
   - 设计文档 → `development/`
   - 测试报告 → `reports/`
   - 历史记录 → `archived/`

2. **命名规范**:
   - 使用大写+下划线: `MY_DOCUMENT.md`
   - 包含日期(如果是报告): `REPORT_2025-11-13.md`
   - 描述性名称: `MEMORY_CONSOLIDATION_GUIDE.md`

3. **更新索引**: 在本文件中添加相应链接

---

## 🔄 文档维护

### 定期任务
- 每个Phase结束时归档完成报告
- 更新guides/中的快速参考文档
- 清理过时的临时文档

### 文档清理规则
- **Session summaries** → 每月归档一次
- **Status reports** → 保留最新3个，其余归档
- **TODO lists** → 完成后立即归档
- **临时分析文档** → 提取要点后归档

---

## 📌 重要文档

### 必读文档 (Top 5)
1. [主README](../README.md) - 项目概述
2. [记忆系统架构](development/MEMORY_SYSTEM_ARCHITECTURE.md)
3. [LoCoMo测试指南](guides/LOCOMO_BMAM_TEST_GUIDE.md)
4. [记忆管理指南](guides/MEMORY_MANAGER_GUIDE.md)
5. [Phase 4 完成报告](archived/PHASE_4_HRM_COMPLETION_REPORT.md)

### 技术深入 (Top 3)
1. [记忆归档格式](development/MEMORY_ARCHIVE_FORMAT_DESIGN.md)
2. [自动持久化实现](development/AUTO_PERSISTENCE_IMPLEMENTATION.md)
3. [模块化指南](guides/MEMORY_MODULARITY_GUIDE.md)

---

## 🎯 文档状态

| 类别 | 文档数 | 状态 | 最后更新 |
|------|--------|------|---------|
| archived | 51 | ✅ 已整理 | 2025-11-13 |
| guides | 9 | ✅ 最新 | 2025-11-13 |
| development | 7 | ✅ 最新 | 2025-11-13 |
| reports | 5 | ✅ 最新 | 2025-11-13 |

**总计**: 72个文档已整理

---

**最后更新**: 2025-11-13
**整理人**: Claude Code
**状态**: ✅ 文档结构清晰
