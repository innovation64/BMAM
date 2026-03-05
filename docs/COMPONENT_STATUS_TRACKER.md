# BMAM 组件状态追踪表

> 更新时间: 2026-01-26
> 基于脚手架流程创建

---

## 1. 核心功能状态

| 功能 | 状态 | 问题描述 | 优先级 |
|------|------|---------|--------|
| 基本存储 | ✅ | 正常 | - |
| 基本检索 | ✅ | 正常 | - |
| **多轮即时检索** | ❌ | 存储后无法立即检索到新记忆 | **P0** |
| LoCoMo 测试 | ✅ 79% | 因为等待3秒巩固后再检索 | - |

### 多轮记忆问题分析

**根因**: 存储后向量索引未实时同步
- LoCoMo 测试: `await asyncio.sleep(3)` 等待巩固后才测试 → 79%
- 即时测试: 存储后立即检索 → 失败

---

## 2. 类脑机制激活状态

### 2.1 已激活 ✅

| 机制 | 文件位置 | 激活位置 | 说明 |
|------|---------|---------|------|
| ConsolidationAgent | `src/agents/core/consolidation/` | brain_coordinator_refactored.py:776 | 巩固机制正常 |
| BackgroundMemoryProcesses | `src/memory/background_memory_processes.py` | brain_coordinator_refactored.py:331 | 后台进程正常 |
| AdaptiveMemoryShaping | `src/memory/adaptive_memory_shaping.py` | brain_coordinator_refactored.py:301 | 自适应塑造正常 |
| HippocampalPrefrontalLoop | `src/brain/hippocampal_loop.py` | brain_coordinator_refactored.py:269 | HP循环正常 |
| PreferenceAwareRetrieval | `src/memory/preference_aware_retrieval.py` | brain_coordinator_refactored.py:578 | 偏好感知正常 |

### 2.2 未激活 ❌ (需修复)

| 机制 | 文件位置 | 问题 | 优先级 |
|------|---------|------|--------|
| ~~FeedbackLoop~~ | `src/learning/feedback_loop.py` | ✅ 2026-01-26 已激活 (FIX-012) | **完成** |
| ~~ForgettingCoordinator~~ | `src/memory/forgetting_coordinator.py` | ✅ 2026-01-26 已激活 (FIX-013) | **完成** |
| **VectorDB实时同步** | `src/memory/storage_adapter.py` | 存储后向量未实时加入FAISS | **P0** |

### 2.3 部分激活 ⚠️

| 机制 | 文件位置 | 问题 | 优先级 |
|------|---------|------|--------|
| ContrastiveKeyOptimizer | `src/memory/contrastive_key_optimizer.py` | 在PreferenceAwareRetrieval中启用，但未接收反馈信号 | P1 |
| MetamemoryMonitor | `src/memory/metamemory.py` | 启用但缺少反馈闭环 | P1 |

---

## 3. 待修复问题清单

### P0 - 必须立即修复

| # | 问题 | 影响 | 修复方案 |
|---|------|------|---------|
| 1 | **多轮即时检索失败** | 用户体验差 | 存储时同步加入FAISS索引 |
| 2 | **FeedbackLoop未激活** | 无反馈闭环，无法为环境Agent打基础 | 在coordinator中实例化并调用 |
| 3 | **Emotion Congruency禁用** | 情绪一致性记忆增强无效 | 实现mood-emotion相似度计算 |

### P1 - 应该修复

| # | 问题 | 影响 | 修复方案 |
|---|------|------|---------|
| 4 | ForgettingCoordinator未激活 | 遗忘机制分散，无统一协调 | 在MemoryCoordinator中集成 |
| 5 | ContrastiveKeyOptimizer无反馈 | Hebbian学习无实际数据 | 连接FeedbackLoop |
| 6 | Prefrontal route_query空实现 | 查询路由失效 | 实现路由逻辑 |

---

## 4. 修复计划 (按脚手架流程)

### Phase 1: 修复多轮即时检索 (P0)

```bash
# 1. 备份
/backup multi_turn_fix

# 2. 修改 storage_adapter.py
#    - 在 store_memory() 后立即调用 vector_db.add_vector()

# 3. 验证
/test quick
```

### Phase 2: 激活反馈闭环 (P0)

```bash
# 1. 备份
/backup feedback_loop_activation

# 2. 修改 brain_coordinator_refactored.py
#    - 导入 FeedbackLoop
#    - 在 __init__ 中实例化
#    - 在检索完成后调用 on_retrieval_complete()

# 3. 验证
/check && /test quick
```

### Phase 3: 激活遗忘协调器 (P1)

```bash
# 1. 备份
/backup forgetting_activation

# 2. 修改 memory_coordinator.py
#    - 导入 ForgettingCoordinator
#    - 定期调用 maybe_forget()

# 3. 验证
/test benchmark  # 遗忘会影响基准分数
```

---

## 5. 与脚手架待激活清单对比

| 脚手架列出 | 当前状态 | 差距 |
|-----------|---------|------|
| ContrastiveKeyOptimizer | ⚠️ 部分激活 | 缺少反馈信号输入 |
| FeedbackLoop | ❌ 未激活 | 完全未使用 |
| ForgettingCoordinator | ❌ 未激活 | 完全未使用 |

---

## 6. 环境Agent准备状态

为后期接入环境Agent，需要先完成：

- [x] 基础存储/检索架构
- [ ] **反馈闭环** ← 当前阻塞项
- [ ] 遗忘与巩固机制协调
- [ ] 外部数据源接口

反馈闭环是环境Agent的基础，必须先激活。
