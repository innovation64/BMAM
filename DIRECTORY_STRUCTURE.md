# BMAM 目录结构说明

**最后更新**: 2025-11-10

---

## 📂 顶层目录结构

```
BMAM/
├── README.md                      # 项目主文档
├── LOCOMO_COMMANDS.md             # LoCoMo评测命令手册
├── DIRECTORY_STRUCTURE.md         # 本文档
│
├── src/                           # 源代码 ⭐
├── tests/                         # 测试代码
├── scripts/                       # 脚本工具
├── docs/                          # 文档
├── config/                        # 配置文件
├── data/                          # 数据文件
├── archived/                      # 归档文件
└── project_management/            # 项目管理
```

---

## 📁 详细目录说明

### `src/` - 源代码

```
src/
├── __init__.py
│
├── agents/                        # 智能体模块
│   ├── base.py                   # 基类定义
│   ├── core/                     # 核心智能体 ⭐
│   │   ├── memory_retrieval/     # 记忆检索 (16模块)
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── memory_retrieval.py  # 主编排器
│   │   │   ├── strategies/       # 7种检索策略
│   │   │   ├── cache/            # LRU缓存
│   │   │   └── confidence/       # 置信度计算
│   │   │
│   │   ├── personality/          # 人格智能体 (15模块)
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── core.py           # 主编排器
│   │   │   ├── emotion/          # 情绪管理
│   │   │   ├── traits/           # 人格特质
│   │   │   ├── style/            # 对话风格
│   │   │   └── adaptation/       # 自适应学习
│   │   │
│   │   ├── consolidation/        # 巩固智能体
│   │   ├── forgetting/           # 遗忘智能体 (Mixin模式)
│   │   ├── reflection/           # 反思智能体
│   │   ├── memory_distortion/    # 记忆重塑
│   │   ├── stress_response/      # 压力响应
│   │   ├── short_term_memory.py  # 短期记忆
│   │   ├── long_term_memory.py   # 长期记忆
│   │   ├── perception_encoding.py # 感知编码
│   │   └── persona_memory.py     # 人设记忆
│   │
│   └── brain_regions/            # 脑区映射智能体
│       ├── prefrontal_agent.py   # 前额叶
│       ├── hippocampal_agent.py  # 海马体
│       └── ...
│
├── memory/                        # 记忆系统
│   ├── memory_system.py          # 记忆系统主类
│   ├── memory_item.py            # 记忆项数据结构
│   ├── knowledge_graph.py        # 知识图谱
│   └── brain_regions/            # 脑区特定记忆
│
├── coordination/                  # 协调器
│   ├── clean_agent_system.py    # 12智能体系统 ⭐
│   ├── memory_coordinator.py     # 记忆协调器
│   ├── routing_manager.py        # 路由管理
│   └── ...
│
├── services/                      # 服务层
│   ├── llm_service.py            # LLM服务
│   ├── embedding_service.py      # 嵌入服务
│   └── ...
│
├── optimization/                  # 性能优化
│   ├── query_cache.py            # 查询缓存
│   ├── capacity_manager.py       # 容量管理
│   └── ...
│
└── ui/                            # 用户界面
    └── web_ui_server/            # Web UI
```

---

### `tests/` - 测试代码

```
tests/
├── unit/                          # 单元测试
├── integration/                   # 集成测试
│   └── test_external_exploration_integration.py
├── test_phase5_*.py              # Phase 5测试
└── evaluation/                   # 评测相关
```

---

### `scripts/` - 脚本工具

```
scripts/
├── cleanup_project.sh            # 项目清理脚本
├── evaluation/                   # 评测脚本
│   └── run_bmam_memos_eval.py   # LoCoMo评测
└── ...
```

---

### `docs/` - 文档

```
docs/
├── architecture/                 # 架构文档
├── api/                          # API文档
├── guides/                       # 开发指南
├── presentation/                 # 演示文档
│   └── BMAM完整架构详解.md       # 核心架构文档 ⭐
├── refactoring_history/          # 重构历史 (16个文档)
│   ├── FILE_SPLIT_*.md
│   ├── MEMORY_RETRIEVAL_*.md
│   ├── PERSONALITY_*.md
│   └── ...
└── technical/                    # 技术文档
```

---

### `config/` - 配置文件

```
config/
├── agent_config.yaml             # 智能体配置
├── memory_config.yaml            # 记忆系统配置
└── ...
```

---

### `data/` - 数据文件

```
data/
├── memories.db                   # 记忆数据库
├── vector_index/                 # 向量索引
└── ...
```

---

### `archived/` - 归档文件

```
archived/
├── memory_retrieval.py.bak_20251110    # 旧版单体文件
├── personality.py.bak_20251110         # 旧版单体文件
└── ...
```

---

## 🎯 关键文件快速导航

### 启动入口
- **主系统**: `src/coordination/clean_agent_system.py`
- **Web UI**: `src/ui/web_ui_server/server.py`

### 核心智能体
- **记忆检索**: `src/agents/core/memory_retrieval/`
- **人格系统**: `src/agents/core/personality/`
- **巩固**: `src/agents/core/consolidation/`
- **遗忘**: `src/agents/core/forgetting/`

### 配置和数据
- **配置**: `config/agent_config.yaml`
- **数据库**: `data/memories.db`

### 测试和评测
- **LoCoMo评测**: `scripts/evaluation/run_bmam_memos_eval.py`
- **集成测试**: `tests/integration/`

### 文档
- **架构文档**: `docs/presentation/BMAM完整架构详解.md`
- **命令手册**: `LOCOMO_COMMANDS.md`
- **项目主页**: `README.md`

---

## 📊 目录统计

| 类别 | 数量 | 说明 |
|------|------|------|
| 顶层目录 | 11个 | 结构清晰 |
| Python文件 | ~150个 | 模块化程度高 |
| 平均文件行数 | ~150行 | 易于维护 |
| 智能体模块 | 12个 | 对应脑区 |
| 文档文件 | ~30个 | 文档完善 |

---

## 🔍 目录设计原则

### 1. 模块化
- 每个目录职责单一
- 子模块独立可测试

### 2. 分层清晰
```
应用层 → coordination/
领域层 → agents/
基础设施层 → memory/, services/
```

### 3. 易于导航
- 直观的命名
- 清晰的层级
- README文档

### 4. 可扩展
- 预留扩展空间
- 插件化设计

---

## 🚫 不应该出现的目录/文件

❌ **已清理**:
- ~~`BMAM/` 子目录~~ (多余，已删除)
- ~~16个根目录.md文档~~ (已移至 docs/refactoring_history/)
- ~~`__pycache__/` 目录~~ (已清理)
- ~~旧版单体文件~~ (已备份至 archived/)

❌ **应避免**:
- 不要在src/中创建临时文件
- 不要在根目录堆积文档
- 不要保留废弃代码

---

## 💡 使用建议

### 开发时
1. 所有代码放在 `src/`
2. 测试放在 `tests/` (镜像src/结构)
3. 文档放在 `docs/` (按类别归档)

### 添加新功能
1. 在 `src/agents/core/` 创建新智能体
2. 在 `tests/` 添加对应测试
3. 在 `docs/` 更新相关文档

### 查找文件
1. 使用本文档快速导航
2. 使用IDE的文件搜索
3. 参考 `README.md`

---

## 📚 相关文档

- **README.md** - 项目主页
- **LOCOMO_COMMANDS.md** - 命令手册
- **docs/presentation/BMAM完整架构详解.md** - 架构详解

---

**目录结构清晰、组织良好，易于维护和扩展！** 🎯✨
