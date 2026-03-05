# 优化计划: FIX-008 ToM模块安全集成

**日期**: 2026-01-24
**目标组件**: TheoryOfMindAgent, BrainCoordinatorRefactored
**风险等级**: [ ] 低 / [ ] 中 / [x] 高

---

## 1. 目标

### 1.1 当前问题
Theory of Mind (ToM) 模块被硬编码禁用，原因是其 adversarial detection 功能误判正常问题。

**禁用代码** (`brain_coordinator_refactored.py:2108-2116`):
```python
# 🎭 3.4 Theory of Mind - 已禁用错误的 adversarial detection
# 2025-12-25: 当前实现不是真正的心智理论，会误判正常问题
# 正确的 ToM 应该用于：
#   1) 用户信念建模 (UserBeliefState) - 用户认为世界是什么样的
#   2) 意图推断 (IntentInference) - 用户问这个问题的真正目的
#   3) 视角切换 (PerspectiveTaking) - 从用户视角组织答案
#   4) 信念不匹配处理 - 当用户信念与事实不符时温和纠正
# TODO: 重新设计 ToM 为上述正确功能
adversarial_result = None  # 保留变量避免后续代码报错
```

**问题根因**:
1. `ADVERSARIAL_PATTERNS` (行115-137) 过于宽泛，将正常问题误判为对抗性
2. `infer_intent()` 中的 LLM prompt 也包含对抗检测逻辑
3. 启用现有代码会导致大量 false positive

### 1.2 安全方案
**不启用** 现有的 adversarial detection，而是添加 **安全子集** 功能：

1. **简单意图分类** (不含adversarial检测):
   - informational: 询问事实
   - temporal: 询问时间
   - preference: 询问偏好
   - relational: 询问关系

2. **用户信念追踪** (从记忆推断):
   - 记录用户认为的事实 (may conflict with actual facts)
   - 用于温和纠正信念不匹配

### 1.3 期望效果
- 增强查询意图理解
- 不引入 false positive 误判
- 为后续完整 ToM 实现打基础

### 1.4 成功指标
- [ ] 意图分类准确率 > 80% (人工抽样10条)
- [ ] LoCoMo基准无回归（保持 >= 77%）
- [ ] 无 adversarial false positive

---

## 2. 风险分析

### 2.1 高风险点
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 意图分类影响检索策略 | 可能降低准确率 | 意图分类只用于logging，不影响检索 |
| LLM调用增加延迟 | 响应变慢 | 使用简单规则分类，不调LLM |
| 与现有代码冲突 | 回归 | 新增代码，不修改现有流程 |

### 2.2 建议
鉴于高风险，建议 **阶段实施**：
- **Phase A**: 添加简单意图分类（规则based，无LLM）
- **Phase B**: 添加用户信念追踪
- **Phase C**: (后续) 完整ToM重新设计

本计划仅实施 **Phase A**。

---

## 3. 详细步骤 (Phase A: 简单意图分类)

### 步骤1: 添加安全意图分类器
**文件**: `src/coordination/brain_coordinator_refactored.py`
**位置**: 在 `adversarial_result = None` 后添加

**新增代码**:
```python
# FIX-008 Phase A: 安全的意图分类（规则based，无adversarial检测）
# 用于logging和理解查询，不影响检索策略
query_intent = self._classify_query_intent_safe(user_input)
logger.info(f"🎯 Query intent: {query_intent['type']} (confidence={query_intent['confidence']:.2f})")
```

### 步骤2: 实现安全意图分类方法
**文件**: `src/coordination/brain_coordinator_refactored.py`
**位置**: 在类中添加新方法

**新增方法**:
```python
def _classify_query_intent_safe(self, query: str) -> Dict[str, Any]:
    """
    FIX-008 Phase A: 安全的意图分类

    特点：
    - 基于规则，不调用LLM
    - 不包含adversarial检测
    - 只用于logging和理解，不影响检索策略

    Returns:
        {
            'type': 'informational|temporal|preference|relational|unknown',
            'confidence': 0.0-1.0,
            'keywords_matched': [...]
        }
    """
    query_lower = query.lower().strip()

    # 意图模式定义
    intent_patterns = {
        'temporal': {
            'keywords': ['when', 'what date', 'what day', 'how long', 'how many days',
                        'how many years', 'duration', 'before', 'after', 'ago'],
            'confidence': 0.8
        },
        'preference': {
            'keywords': ['like', 'prefer', 'favorite', 'enjoy', 'love', 'hate',
                        'best', 'worst', 'rather'],
            'confidence': 0.8
        },
        'relational': {
            'keywords': ['who is', 'relationship', 'friend', 'family', 'partner',
                        'married', 'knows', 'met'],
            'confidence': 0.7
        },
        'location': {
            'keywords': ['where', 'location', 'place', 'live', 'work', 'go to'],
            'confidence': 0.7
        },
        'informational': {
            'keywords': ['what', 'how', 'why', 'tell me', 'explain'],
            'confidence': 0.6  # 较低置信度因为这是catch-all
        }
    }

    # 匹配检测
    for intent_type, pattern in intent_patterns.items():
        matched_keywords = [kw for kw in pattern['keywords'] if kw in query_lower]
        if matched_keywords:
            return {
                'type': intent_type,
                'confidence': pattern['confidence'],
                'keywords_matched': matched_keywords
            }

    return {
        'type': 'unknown',
        'confidence': 0.3,
        'keywords_matched': []
    }
```

---

## 4. 验证计划

### 4.1 语法检查
```bash
cd BMAM && python -m py_compile src/coordination/brain_coordinator_refactored.py
```

### 4.2 意图分类测试
```bash
cd BMAM && python -c "
from src.coordination.brain_coordinator_refactored import BrainCoordinatorRefactored

# 创建协调器实例
bc = BrainCoordinatorRefactored.__new__(BrainCoordinatorRefactored)

# 测试意图分类
test_cases = [
    ('When did John get married?', 'temporal'),
    ('What is Mary\\'s favorite food?', 'preference'),
    ('Who is John\\'s friend?', 'relational'),
    ('Where does Sarah live?', 'location'),
    ('Tell me about the project', 'informational'),
]

for query, expected in test_cases:
    result = bc._classify_query_intent_safe(query)
    status = '✅' if result['type'] == expected else '❌'
    print(f'{status} \"{query}\" → {result[\"type\"]} (expected: {expected})')
"
```

### 4.3 回归测试
```bash
# 清理
rm -f BMAM/data/memory/*.db BMAM/data/memory/*.index BMAM/data/memory/*.json
rm -rf BMAM/data/cache/embedding BMAM/data/cache/faiss_index BMAM/data/cache/knowledge_graph

# 测试
python BMAM/evaluation/benchmarks/locomo/test_sequential.py --groups 3
```

---

## 5. 回滚计划

### 5.1 备份位置
`backups/20260124_fix008_tom_safe/`

### 5.2 回滚命令
```bash
cp BMAM/backups/20260124_fix008_tom_safe/brain_coordinator_refactored.py BMAM/src/coordination/
```

---

## 6. 执行记录

### 6.1 实际执行时间
- 开始: 2026-01-24 18:30
- 结束: 2026-01-24 18:33

### 6.2 实际修改
修改 `src/coordination/brain_coordinator_refactored.py`:
1. 新增 `_classify_query_intent_safe()` 方法 (line 972-1028)
   - 基于规则的意图分类
   - 支持 temporal/preference/relational/location/informational/unknown 6种类型
   - 支持中英文关键词
2. 在 `process_user_input()` 中调用意图分类 (line 2183-2185)
   - 位于 ToM 禁用注释之后
   - 结果仅用于日志记录，不影响检索策略

### 6.3 验证结果
| 测试类型 | 结果 | 备注 |
|---------|------|------|
| 语法检查 | ✅ PASS | |
| 意图分类测试 | ✅ 5/6 | "Hello how are you"→informational (边缘情况) |
| 回归测试 | ❌ 显著回归 | 74.65% vs 76.66% baseline (-2.01%) |

**意图分类测试详情**:
| Query | Expected | Actual | Conf |
|-------|----------|--------|------|
| When did John get married? | temporal | temporal | 0.80 |
| What is Mary's favorite food? | preference | preference | 0.80 |
| Who is John's friend? | relational | relational | 0.70 |
| Where does Sarah live? | location | location | 0.70 |
| Tell me about the project | informational | informational | 0.60 |
| Hello how are you | unknown | informational | 0.60 |

**基准测试详情 (3组)**:
| Group | FIX-008 Result | FIX-007 Baseline | Change |
|-------|---------------|------------------|--------|
| conv-26 | 70.9% (141/199) | 79.4% (158/199) | **-8.5%** |
| conv-30 | 75.2% (79/105) | 73.3% (77/105) | +1.9% |
| conv-41 | 78.2% (151/193) | 75.6% (146/193) | +2.6% |
| **总计** | **74.65%** (371/497) | **76.66%** (381/497) | **-2.01%** |

**回归分析**:
- conv-26 出现显著回归 (-8.5%)，原因未明
- conv-30/41 略有提升，但无法弥补 conv-26 的损失
- 意图分类虽然设计为"仅logging"，但仍产生了负面影响

---

## 7. 结论

### 7.1 最终状态
- [ ] Phase A 成功完成
- [ ] 部分完成
- [x] 回滚

### 7.2 回滚原因
1. 基准测试显著回归 (-2.01%)
2. conv-26 组回归严重 (-8.5%)
3. 虽然意图分类功能正常，但对整体性能有负面影响

### 7.3 后续工作建议
1. 分析 conv-26 回归的具体原因（可能与特定问题类型相关）
2. 考虑将意图分类完全移出主流程，改为异步或后处理
3. **Phase B/C 暂缓**，直到找到不影响性能的实现方式

### 7.4 经验教训
- **"仅logging"代码也可能有副作用**：即使不影响检索策略，额外的计算和方法调用也可能影响整体行为
- **不同数据集反应不同**：conv-26 显著下降而 conv-30/41 上升，说明变更对特定查询模式敏感
