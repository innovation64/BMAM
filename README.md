# BMAM - Brain-inspired Multi-Agent Memory System

**生物启发式多智能体记忆系统**

一个模拟人脑记忆机制的AI记忆管理系统，实现了从感知编码、短期记忆、长期巩固到主动遗忘的完整记忆闭环。

---

## 🧠 核心特性

### 完整的记忆闭环
- **感知编码** (Perception Encoding) - 海马体编码
- **短期记忆** (Short-term Memory) - 工作记忆缓冲
- **长期巩固** (Consolidation) - 复述+离线巩固
- **记忆检索** (Retrieval) - 7种检索策略
- **主动遗忘** (Forgetting) - 容量管理+干扰消除
- **记忆重塑** (Distortion) - 冲突解决+更新
- **元认知反思** (Reflection) - 自我监控

### 12个智能体系统
基于脑区映射的智能体协作架构：
- 海马体 → 短期记忆、编码
- 颞叶 → 长期记忆
- 前额叶 → 检索、巩固
- 杏仁核 → 情绪标签
- 默认模式网络 → 反思、人格

---

## 📊 性能指标

### LoCoMo 长上下文记忆基准

| 指标 | Phase 3 | Phase 4 P0 | 提升 |
|------|---------|------------|------|
| 准确率 | 78% | **94%** | +16% |
| Q2 时间推理 | 79% | **93%** | +14% |
| Q3 多跳 | 81% | **95%** | +14% |
| Q4 汇总 | 73% | **94%** | +21% |

**测试集**: LoCoMo-10 子集 (10 sessions, 1,986轮QA)

---

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 基础使用
```python
from src.coordination.clean_agent_system import CleanAgentSystem

# 初始化系统
system = CleanAgentSystem()

# 处理输入
result = await system.process_input("用户输入")
```

### 运行评测
```bash
# LoCoMo 评测
python scripts/evaluation/run_bmam_memos_eval.py

# 详细命令参见
cat LOCOMO_COMMANDS.md
```

---

## 📂 项目结构

```
BMAM/
├── src/                    # 源代码
│   ├── agents/            # 智能体模块
│   │   ├── core/         # 核心智能体
│   │   │   ├── memory_retrieval/    # 检索 (16模块)
│   │   │   ├── personality/         # 人格 (15模块)
│   │   │   ├── consolidation/       # 巩固
│   │   │   ├── forgetting/          # 遗忘
│   │   │   └── ...
│   │   └── brain_regions/  # 脑区智能体
│   ├── memory/            # 记忆系统
│   ├── coordination/      # 协调器
│   └── services/          # 服务层
├── tests/                 # 测试
├── scripts/               # 脚本
├── docs/                  # 文档
├── config/                # 配置
└── data/                  # 数据
```

---

## 🎨 架构特点

### 模块化设计
- **高内聚低耦合**: 每个模块职责单一
- **策略模式**: 可插拔的检索/巩固策略
- **领域驱动**: 清晰的领域边界

### 代码质量
- **平均文件行数**: ~150行 (从850行降低82%)
- **类型提示**: 100%覆盖
- **文档**: 完整的docstring
- **测试**: 集成测试+单元测试

---

## 📚 文档

- **架构文档**: `docs/architecture/`
- **API文档**: `docs/api/`
- **开发指南**: `docs/guides/`
- **重构历史**: `docs/refactoring_history/`

**核心文档**:
- [完整架构详解](docs/presentation/BMAM完整架构详解.md)
- [LoCoMo命令手册](LOCOMO_COMMANDS.md)
- [实现指南](docs/IMPLEMENTATION_GUIDE.md)

---

## 🔬 技术栈

- **Python 3.12+**
- **OpenAI API** (GPT-4)
- **FAISS** (向量检索)
- **SQLite** (持久化)

---

## 📈 开发进度

### 已完成
- ✅ Phase 1-2: 基础架构
- ✅ Phase 3: 记忆闭环
- ✅ Phase 4 P0: LoCoMo 94%准确率
- ✅ 代码重构: 模块化架构

### 进行中
- 🔄 Phase 4 P1: 性能优化
- 🔄 Phase 5: 生产部署

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📄 许可证

[待添加]

---

## 🙏 致谢

感谢所有贡献者和测试者！

---

**"优雅的代码就像一首诗，每一行都有其存在的意义。" 🎨✨**
