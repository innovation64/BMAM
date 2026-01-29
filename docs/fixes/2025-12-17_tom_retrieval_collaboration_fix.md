# ToM-检索协作机制修复

**日期**: 2025-12-17
**问题**: conv-41 假阳性对抗检测导致准确率下降

## 问题分析

### 原始问题

| 类别 | 准确率 | 问题 |
|------|--------|------|
| single-hop | 58.1% (18/31) | 检索召回不足 |
| multi-hop | 63.0% (17/27) | 检索召回不足 |
| open-domain | 62.8% (54/86) | 检索召回不足 |
| adversarial | 58.5% (24/41) | Gold为空的评测问题 |

### 根因分析

1. **检索-ToM耦合断裂**
   - ToM只使用3个facts做判断（太少）
   - 检索不充分时仍运行ToM导致误判
   - ToM说"无证据"时没有反馈给检索扩展搜索

2. **信息存在但检索失败**
   ```
   yoga: 25条记忆存在 → 系统说 "no information"
   writing class: 2条记忆存在 → 系统说 "no mention"
   ```

3. **协作闭环缺失**
   ```
   当前(开环): Query → Hippocampus检索 → ToM判断 → 拒答
   应该(闭环): Query → 检索 → 质量评估 → [不足则扩展] → ToM → [无证据则反馈] → 重新检索
   ```

## 修复方案

### 1. ToM检索充分性门控 (`adversarial_reasoning.py`)

**新增方法**: `_evaluate_retrieval_sufficiency()`

评估维度:
- 数量充分性: 至少5条记忆
- 覆盖度: 查询关键词覆盖率 >= 30%
- 相关性: 平均相关性分数 >= 0.4

**修改**: `check_adversarial_before_reasoning()`
- 检索不充分时跳过ToM，避免误判
- facts数量从3个提升到10个
- 必须有明确的`violated_facts`才能触发拒答

### 2. 动态检索增强 (`brain_coordinator_refactored.py`)

- k值从固定10提升到动态15-20（事实型问题用20）
- 事实型查询强制使用慢路径（迭代检索）
- 前额叶质量评估集成（`PrefrontalFeedbackSystem`）
- StoryArc兜底查询集成（时间相关问题）

### 3. 输出侧Fail-safe (`result_arbiter.py`)

**新增方法**: `check_tom_fallback()`

检测条件:
- 回答包含ToM拒答模式（"no evidence", "assumption"等）
- 但没有具体的`violated_facts`
- 且记忆中有相关内容（>=3条非空记忆）

触发后回落到正常推理。

## 技术细节

### 修改文件

1. `src/agents/core/reasoning_validator/adversarial_reasoning.py`
   - 新增: `_evaluate_retrieval_sufficiency()` (70行)
   - 修改: `check_adversarial_before_reasoning()` (20行改动)

2. `src/coordination/brain_coordinator_refactored.py`
   - 修改: 检索k值动态化 (12行改动)
   - 新增: 前额叶质量评估集成 (30行)
   - 新增: StoryArc兜底查询 (15行)
   - 新增: Fail-safe检查集成 (20行)

3. `src/coordination/result_arbiter.py`
   - 新增: `check_tom_fallback()` (80行)

### 协作流程（修复后）

```
Query
  ↓
Hippocampus检索 (k=15-20, 事实型强制慢路径)
  ↓
PrefrontalFeedback 质量评估
  ↓
质量充分?
  │
  ├─ No → 跳过ToM，正常推理
  │
  └─ Yes → ToM判断
            ↓
        is_adversarial?
            │
            ├─ No → 正常推理
            │
            └─ Yes → has_violated_facts?
                        │
                        ├─ No → 跳过拒答，正常推理 (soft signal)
                        │
                        └─ Yes → 对抗性拒答
                                  ↓
                            Fail-safe检查
                                  ↓
                            should_fallback?
                                  │
                                  ├─ Yes → 正常推理
                                  │
                                  └─ No → 输出拒答
```

## 预期效果

1. **减少假阳性**: 检索不充分时不触发ToM拒答
2. **提升召回率**: 动态k值和迭代检索
3. **时间问题兜底**: StoryArc直接查询事件时间
4. **Fail-safe保护**: 输出前最后检查

## 验证方法

运行小规模回归测试:
```bash
cd .
python3 experiments/benchmarks/locomo/test_sequential.py --groups 1 --questions 30
```

## 后续建议

1. **重塑时间记忆**: 补齐event_time元数据
2. **LLM Judge修复**: adversarial问题的Gold为空时需要特殊处理
3. **监控指标**: 添加ToM门控触发率监控
