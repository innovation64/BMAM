# 配置合并计划

## 当前配置文件清单 (2025-12-19 更新)

| 文件 | 行数 | 职责 | 状态 |
|------|------|------|------|
| `src/utils/config.py` | 456 | 环境变量 + 日志 + get_logger | ✅ 核心，保留 |
| `src/core/config.py` | 235 | MemorySystemConfig + AgentConfig | ✅ 核心，保留 |
| ~~`src/brain/config.py`~~ | ~~68~~ | ~~BrainConfig~~ | ❌ 已删除(死代码) |
| ~~`src/utils/config_manager.py`~~ | ~~60~~ | ~~持久化管理~~ | ❌ 已删除(死代码) |
| `src/utils/memory_signal_config.py` | 199 | 记忆信号阈值 | ⚠️ 待评估 |
| `src/utils/pattern_config.py` | 339 | 查询模式匹配 | ⚠️ 待评估 |
| `src/utils/i18n_config.py` | 421 | 国际化模式 | ✅ 保留 |
| `src/utils/experiment_config.py` | 365 | 实验参数 | ✅ 保留 |
| `src/agents/core/mbti_config.py` | 416 | MBTI人格配置 | ✅ 领域特定 |
| `src/coordination/kg_merge_config.py` | 521 | KG合并配置 | ✅ 领域特定 |
| `src/coordination/soul_config_loader.py` | 289 | Soul配置加载 | ⚠️ 有fallback |

**当前: 9个文件, 3241行 (已删除 128 行死代码)**

---

## 合并策略

### Phase 1: 低风险合并 (可立即执行)

#### 1.1 删除 `src/brain/config.py` → 合并到 `src/core/config.py`
- **原因**: BrainConfig 只有68行，可直接移入 core/config.py
- **测试**: `python -c "from src.brain.brain_network import BrainNetwork"`

#### 1.2 删除 `src/utils/config_manager.py` → 合并到 `src/core/config.py`
- **原因**: BrainConfigManager 只有60行，与 core/config.py 职责相近
- **测试**: `python -c "from src.utils.config_manager import BrainConfigManager"`

### Phase 2: 中风险合并

#### 2.1 `src/utils/config.py` 保留核心功能
- 保留: `init_environment()`, `setup_logging()`, `get_logger()`
- 移除: 可能的重复功能

#### 2.2 `src/coordination/soul_config_loader.py` → 评估是否仍需要
- 检查调用者
- 如果只被 SoulState 使用，可考虑内联

### Phase 3: 高风险合并 (需要重构)

#### 3.1 合并领域配置
- `memory_signal_config.py` + `pattern_config.py` → `src/core/signal_patterns.py`
- 需要更新所有依赖

#### 3.2 MBTI/KG 配置保持独立
- 这些是领域特定配置，保持分离更清晰

---

## 合并进度追踪

| 任务 | 状态 | 日期 | 备注 |
|------|------|------|------|
| Phase 1.1 brain/config.py | ✅ 删除 | 2025-12-19 | 死代码，从未被引用 |
| Phase 1.2 config_manager.py | ✅ 删除 | 2025-12-19 | 死代码，从未被引用 |
| Phase 2.1 utils/config.py | ⬜ 保留 | | 核心模块，被广泛使用 |
| Phase 2.2 soul_config_loader | ⬜ 保留 | | 有fallback，非关键但有用 |
| Phase 3 | ⬜ 待评估 | | |

---

## 每次合并的检查清单

1. [ ] 记录原文件内容
2. [ ] 更新所有 import 语句
3. [ ] 运行: `python -c "from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator"`
4. [ ] 运行: `python scripts/diagnose_memory_health.py`
5. [ ] 如果失败，回滚
