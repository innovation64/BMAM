# BMAM - Brain-inspired Multi-Agent Memory System

**生物启发式多智能体记忆系统**

一个模拟人脑记忆机制的AI记忆管理系统，实现了从感知编码、短期记忆、长期巩固到主动遗忘的完整记忆闭环。

---

## 🧠 核心特性

### 五脑区架构 (Five Brain Regions)
- **Hippocampus** (海马体) - 情节记忆存储与检索
- **Temporal Lobe** (颞叶) - 语义记忆与知识图谱
- **Amygdala** (杏仁核) - 情绪标记与调节
- **Prefrontal Cortex** (前额叶) - 工作记忆与任务规划
- **Basal Ganglia** (基底节) - 程序记忆与技能学习

### 完整的记忆闭环
- **感知编码** (Encoding) - 自动提取实体和关系
- **巩固流程** (Consolidation) - Hippocampus → Temporal Lobe
- **记忆检索** (Retrieval) - 混合检索策略 (BM25 + 向量 + 知识图谱)
- **自动持久化** (Persistence) - SQLite + JSON 双重保存
- **记忆塑造** (Memory Shaping) - 自适应巩固与遗忘
- **检查点管理** (Checkpoint) - 版本管理与时间旅行

---

## 🎯 最新状态 (2025-11-13)

### ✅ Phase 4 P1 完成: 关键Bug修复

**修复内容**:
- ✅ 实体关系提取逻辑修复 (从metadata正确读取)
- ✅ AgentStorageProxy属性访问安全性增强
- ✅ 配置文件补全 (relational_keywords, relation_keywords)
- ✅ 统一KG架构实现 (LightweightKnowledgeGraph跨脑区共享)
- ✅ KG API兼容层 (add_triple方法)

**端到端验证**:
- 批量巩固测试: 20条记忆, 100%成功率 ✅
- 实体提取: 平均4.0个实体/记忆 ✅
- KG增长: +17节点, 统一实例工作正常 ✅
- 回归测试: 9/9通过 ✅

**当前记忆状态**:
- Hippocampus: 137条情节记忆
- TemporalLobe: 44条语义记忆 (包含实体和关系)
- Unified KG: 1045节点, 963边
- Amygdala: 31条情绪记忆
- **所有记忆跨重启持久保存** ✅

---

## 📊 性能指标

### LoCoMo 长上下文记忆基准

| 指标 | Phase 3a | Phase 4 P0 | 改进 |
|------|---------|------------|------|
| **5Q平均准确率** | 78% | **94%** | +16% ⬆️ |
| Q2 时间推理 | 79% | **93%** | +14% |
| Q3 多跳推理 | 81% | **95%** | +14% |
| Q4 汇总能力 | 73% | **94%** | +21% |

**测试集**: LoCoMo-10 子集 (10 sessions, 1,986轮QA)

---

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 基础使用
```python
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

# 初始化系统 (自动加载历史记忆)
coordinator = BrainInspiredCoordinator()
await coordinator.start_system()

# 处理用户输入
result = await coordinator.process_user_input("你好，记住我的名字是李阳")

# 系统会自动:
# 1. 存储到 Hippocampus (情节记忆)
# 2. 提取实体和关系
# 3. 触发情绪标记 (如果有情绪内容)
# 4. 累积达到阈值后巩固到 TemporalLobe
# 5. 自动持久化到数据库
```

### 记忆检查点管理
```python
from src.memory.memory_version_manager import MemoryVersionManager

vm = MemoryVersionManager(coordinator=coordinator)

# 创建检查点 (备份当前记忆状态)
checkpoint = await vm.create_checkpoint(
    name="stable_day30",
    description="30天后的稳定状态",
    tags=["stable", "milestone"]
)

# 切换到历史检查点 (会自动备份当前状态)
await vm.restore_from_checkpoint("stable_day30")

# 列出所有检查点
checkpoints = vm.list_checkpoints()
```

### 运行测试
```bash
# 记忆巩固测试
python test_consolidation_debug.py

# LoCoMo评测
python scripts/evaluation/run_bmam_memos_eval.py
```

---

## 📂 项目结构

```
BMAM/
├── src/                          # 源代码
│   ├── agents/                   # 智能体模块
│   │   ├── brain_regions/       # 五脑区智能体
│   │   │   ├── hippocampus_agent/      # 海马体
│   │   │   ├── temporal_lobe_agent/    # 颞叶
│   │   │   ├── amygdala_agent.py       # 杏仁核
│   │   │   ├── prefrontal_agent/       # 前额叶
│   │   │   └── basal_ganglia_agent.py  # 基底节
│   │   └── core/                # 核心智能体
│   ├── memory/                   # 记忆系统
│   │   ├── memory_consolidation_pipeline.py
│   │   ├── adaptive_memory_shaping.py
│   │   ├── background_memory_processes.py
│   │   ├── memory_version_manager.py
│   │   └── agent_storage_proxy.py
│   ├── coordination/             # 协调器
│   │   └── brain_coordinator_refactored.py
│   └── services/                 # 服务层
├── data/                         # 数据目录
│   ├── hippocampus_state.json   # 海马体状态
│   ├── temporal_lobe.db         # 颞叶数据库
│   ├── amygdala_state.json      # 杏仁核状态
│   ├── prefrontal_state.json    # 前额叶状态
│   ├── basal_ganglia_state.json # 基底节状态
│   └── checkpoints/             # 检查点归档
├── docs/                         # 文档
│   ├── archived/                # 历史文档
│   ├── guides/                  # 使用指南
│   ├── development/             # 开发文档
│   └── reports/                 # 评测报告
├── tests/                        # 测试
└── scripts/                      # 脚本
```

---

## 🎨 架构特点

### 1. 生物启发式设计
- **脑区映射**: 每个智能体对应真实脑区功能
- **记忆分层**: 情节记忆 (Hippocampus) → 语义记忆 (Temporal Lobe)
- **情绪调节**: Amygdala 标记重要记忆
- **工作记忆**: Prefrontal 管理短期任务

### 2. 自动持久化机制
- **实时保存**: 每次操作立即写入数据库
- **启动加载**: 自动恢复所有历史记忆
- **跨会话**: 记忆在程序重启后保留
- **版本管理**: 支持创建检查点和时间旅行

### 3. 记忆塑造 (Memory Shaping)
- **AdaptiveShaping**: 根据记忆累积量自适应触发巩固
- **BackgroundProcesses**: 定期巩固、遗忘、重巩固
- **双重触发**: 事件驱动 + 定时兜底

### 4. 代码质量
- **模块化**: 高内聚低耦合
- **类型提示**: 100%覆盖
- **文档**: 完整的docstring
- **测试**: 集成测试 + 单元测试

---

## 📚 文档导航

### 快速入门
- [快速开始指南](docs/guides/) - 5分钟上手
- [检查点管理指南](docs/guides/) - 记忆版本控制

### 开发文档
- [架构设计](docs/development/) - 系统架构详解
- [记忆系统实现](docs/development/) - 巩固流程实现
- [持久化机制](docs/development/) - 数据库设计

### 评测报告
- [LoCoMo评测报告](docs/reports/) - 94%准确率验证
- [记忆塑造验证](docs/reports/) - 功能完整性测试

### 历史文档
- [Phase 1-4 报告](docs/archived/) - 开发历史记录

---

## 🔬 技术栈

- **Python 3.12+**
- **OpenAI API** (GPT-4, text-embedding-3-small)
- **FAISS** (向量检索)
- **SQLite** (持久化存储)
- **BM25** (关键词检索)

---

## 📈 开发路线图

### ✅ 已完成
- Phase 1-2: 基础架构
- Phase 3: 记忆闭环
- Phase 4 P0: LoCoMo 94%准确率
- **Phase 4 P1: 关键Bug修复与统一KG** ← 最新完成

### 🔄 进行中
- Phase 4 P2: 配置优化 (pattern configs)
- Phase 5: 统一知识图谱

### 📋 计划中
- Phase 6: 性能优化与生产部署
- Phase 7: 多模态记忆扩展

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📄 许可证

[MIT License]

---

## 🙏 致谢

感谢所有贡献者和测试者！

---

**"记忆塑造人格，代码塑造系统。" 🧠✨**

---

## 📌 重要提醒

1. **首次运行**: 系统会自动创建 `data/` 目录并初始化数据库
2. **记忆持久化**: 所有记忆自动保存，程序重启后自动加载
3. **检查点备份**: 建议定期创建检查点备份重要状态
4. **环境变量**: 需要设置 `OPENAI_API_KEY`

---

**最后更新**: 2025-11-13
**版本**: Phase 4 P1 (Critical Bugs Fixed + Unified KG)
**状态**: ✅ Production Ready

**变更日志**: 详见 [CHANGELOG.md](CHANGELOG.md)
**技术分析**: 详见 [docs/development/CONSENSUS_FIX_ANALYSIS.md](docs/development/CONSENSUS_FIX_ANALYSIS.md)
