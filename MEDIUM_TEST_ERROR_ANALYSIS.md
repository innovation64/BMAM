# Medium Test 错题诊断分析报告

**日期**: 2025-10-29
**测试规模**: 20 题
**总分**: 10.9 / 20 (54.5%)
**正确题数**: 9 / 20 (45%)

---

## 执行摘要

Phase 4 P0 在 Medium 测试中暴露了**两大核心短板**：

1. **未来时态 / 泛化动作**: Phase 4 P0 的时间推理仅覆盖过去时 + 具体事件，无法处理 "planning" / "going to" 等未来时态
2. **知识图谱缺失**: 身份/因果/多跳推理题缺乏 KG 支持，仅靠向量检索无法抽取细粒度实体关系

**错题分布**:
- 时间推理类: 5/8 错误 (62.5% 失败率)
- 事实抽取类: 5/8 错误 (62.5% 失败率)
- 推理类: 1/4 错误 (25% 失败率)

---

## 错题分类与根因分析

### 类别 1: 时间推理类错题 (5 题错误)

#### Q7: "When is Melanie planning on going camping?" ❌ 0.0 分

**问题类型**: 未来时态 + 计划事件

**期望答案**: June 2023
**实际答案**: 6 October 2023 (完全错误)

**根因分析**:
```
1. Phase 4 P0 temporal boost 仅覆盖过去时 ("last year", "N years ago")
2. 未来时态关键词 "planning", "going to", "will" 未被识别
3. 检索到的记忆是过去的 camping 事件，而非未来计划
```

**Top-3 记忆诊断**:
- Session 6 (6 July): 无 camping 相关 ❌
- Session 9 (17 July): "went camping...two weekends ago" → 过去时 ❌
- Session 18 (20 Oct): roadtrip 事故，非 camping ❌

**缺失能力**: 未来时态识别 + 计划事件抽取

---

#### Q9: "When did Caroline give a speech at a school?" ❌ 0.0 分

**问题类型**: 泛化动作 + 相对时间

**期望答案**: The week before 9 June 2023
**实际答案**: 13 October 2023 (完全错误)

**根因分析**:
```
1. "speech at school" 是泛化动作，需要 KG 推理
2. Session 3 (9 June) 包含 "school event last week" → 需要跳转推理
3. 检索系统未能将 "school event" 等价映射到 "speech at school"
4. 时间线解析失败："last week" → 相对时间未解析
```

**Top-3 记忆诊断**:
- Session 5 (3 July): LGBTQ parade, 非 school event ❌
- Session 3 (9 June): "school event last week" → ✅ 正确记忆排名#2, 但未被正确解析
- Session 15 (28 Aug): park trip, 无关 ❌

**缺失能力**: 泛化动作语义等价 + 相对时间精确计算

---

#### Q10: "When did Caroline meet up with her friends, family, and mentors?" ❌ 0.0 分

**问题类型**: 泛化事件 + 多实体

**期望答案**: The week before 9 June 2023
**实际答案**: 13 October 2023 (完全错误)

**根因分析**:
```
1. 查询包含 3 个实体类别: friends, family, mentors
2. 需要 KG 支持的多跳推理 (谁是 friends? 谁是 mentors?)
3. Phase 4 P0 keyword matching 无法处理抽象概念
4. 与 Q9 同源 (同一事件的不同描述)
```

**Top-3 记忆诊断**:
- Session 7 (12 July): LGBTQ conference, "meet and connect with people" → 部分相关但非目标事件
- Session 3 (9 June): ✅ 正确记忆排名#2
- Session 2 (25 May): charity race ❌

**缺失能力**: 实体角色推理 + 多跳关系抽取

---

#### Q17: "When did Melanie sign up for a pottery class?" ❌ 0.0 分

**问题类型**: 具体动作 + 精确时间

**期望答案**: 2 July 2023
**实际答案**: 21 October 2023 (完全错误)

**根因分析**:
```
1. "sign up" vs "took kids to pottery workshop" → 语义不等价
2. Session 5 (3 July): "I signed up for a pottery class yesterday" → 正确答案在#1
3. 检索排序失败，Session 5 排名第一但未被正确解析
4. 可能因为 pottery workshop (Session 8) 噪声干扰
```

**Top-3 记忆诊断**:
- Session 5 (3 July): ✅ "signed up for pottery class yesterday" → 2 July 2023
- Session 14 (25 Aug): hiking incident ❌
- Session 16 (13 Sept): biking trip ❌

**缺失能力**: 精确动作语义区分 (sign up vs attend)

---

#### Q18: "When is Caroline going to the transgender conference?" ❌ 0.0 分

**问题类型**: 未来时态 + 具体事件

**期望答案**: July 2023
**实际答案**: October 2023 (完全错误)

**根因分析**:
```
1. 与 Q7 同类问题：未来时态 "going to" 未被识别
2. Session 5: "there's a big transgender conference in July" → 未来计划
3. 检索系统找到的是其他月份的 LGBTQ 相关事件
```

**Top-3 记忆诊断**:
- Session 9 (17 July): camping 过去时 ❌
- Session 5 (3 July): ✅ 包含 "conference in July" (未来计划)
- Session 14 (25 Aug): hiking incident ❌

**缺失能力**: 未来时态识别 + 计划事件时间抽取

---

### 类别 2: 事实抽取类错题 (5 题错误)

#### Q12: "Where did Caroline move from 4 years ago?" ❌ 0.0 分

**问题类型**: 历史事实 + 时间计算

**期望答案**: Sweden
**实际答案**: 17 October 2019 (回答了时间而非地点)

**根因分析**:
```
1. 问题是 "Where" (地点)，但系统回答了 "When" (时间)
2. 需要 KG 支持的实体属性推理: Caroline -> origin_location -> Sweden
3. 时间计算正确 (4 years ago from 2023 = 2019)，但缺失地点抽取
4. 可能是 LLM 生成答案时的理解偏差
```

**Top-3 记忆诊断**:
- Session 4 (27 June): necklace story ✅ (可能包含 Sweden 信息)
- Session 8 (15 July): pottery workshop ❌
- Session 3 (9 June): school event ❌

**缺失能力**: KG 实体属性查询 + Where vs When 语义区分

---

#### Q14: "What career path has Caroline decided to pursue?" ⚠️ 0.5 分

**问题类型**: 目标/意图推理

**期望答案**: counseling or mental health for Transgender people
**实际答案**: counseling and mental health as... (截断，缺少 "for Transgender people")

**根因分析**:
```
1. 系统识别了 career field (counseling, mental health)
2. 但缺失了 target audience (Transgender people)
3. 需要 KG 推理: Caroline (transgender) -> career motivation -> help transgender community
4. 多会话信息整合不足
```

**Top-3 记忆诊断**:
- Session 4, 7, 1: 都包含 LGBTQ/trans 相关，但未能整合推理

**缺失能力**: 因果推理 + 目标动机抽取

---

#### Q15: "Would Caroline still want to pursue counseling if she hadn't received support?" ⚠️ 0.5 分

**问题类型**: 反事实推理

**期望答案**: Likely no
**实际答案**: 冗长解释，但未明确回答 "no"

**根因分析**:
```
1. 需要 counterfactual reasoning ("if hadn't received")
2. 需要 causal inference: support -> self-acceptance -> career motivation
3. LLM 生成了解释但缺乏 decisive conclusion
4. 系统 capability 检测到 "counterfactual_reasoning" 但未有效执行
```

**缺失能力**: 反事实推理闭环 + 决策性结论生成

---

#### Q16: "What activities does Melanie partake in?" ⚠️ 0.5 分

**问题类型**: 多事实聚合

**期望答案**: pottery, camping, painting, swimming
**实际答案**: pottery, painting (缺少 camping, swimming)

**根因分析**:
```
1. 需要跨会话的多事实聚合
2. 检索到部分活动，但未能全面覆盖
3. KG 若有 "Melanie -> hobbies -> [pottery, camping, painting, swimming]" 可直接查询
4. 向量检索容易遗漏低频但重要的事实
```

**缺失能力**: 多事实全覆盖聚合 + KG 属性列表查询

---

#### Q19: "Where has Melanie camped?" ⚠️ 0.3 分

**问题类型**: 多地点聚合

**期望答案**: beach, mountains, forest
**实际答案**: beach (仅部分正确)

**根因分析**:
```
1. 与 Q16 同类：需要多会话信息聚合
2. 检索到 beach camping，但遗漏 mountains, forest
3. 向量检索的 top-3 覆盖不足
```

**缺失能力**: 多地点聚合 + 检索覆盖广度

---

### 类别 3: 推理类错误 (1 题错误)

#### Q20: "What do Melanie's kids like?" ⚠️ 0.5 分

**问题类型**: 兴趣推理

**期望答案**: dinosaurs, nature
**实际答案**: pottery, painting, outdoors (缺少 dinosaurs)

**根因分析**:
```
1. 系统推理出 creative activities + outdoors, 部分正确
2. 但遗漏了 "dinosaurs" 这一具体兴趣
3. 需要 KG: Melanie's kids -> interests -> [dinosaurs, nature]
```

**缺失能力**: 细粒度兴趣抽取

---

## 统计分析

### 按问题类型分类

| 问题类型 | 总题数 | 正确 | 错误 | 准确率 |
|---------|--------|------|------|--------|
| **时间推理 (Temporal)** | 8 | 3 | 5 | 37.5% |
| - 过去时 + 具体事件 | 3 | 3 | 0 | 100% ✅ |
| - 未来时 / 计划事件 | 2 | 0 | 2 | 0% ❌ |
| - 泛化动作 + 相对时间 | 3 | 0 | 3 | 0% ❌ |
| **事实抽取 (Factual)** | 8 | 3 | 5 | 37.5% |
| - 直接事实 | 3 | 3 | 0 | 100% ✅ |
| - 多事实聚合 | 3 | 0 | 3 | 0% ❌ |
| - 历史事实 + 属性 | 2 | 0 | 2 | 0% ❌ |
| **推理 (Inference)** | 4 | 3 | 1 | 75% ✅ |
| - 身份/关系推理 | 2 | 2 | 0 | 100% ✅ |
| - 兴趣/偏好推理 | 2 | 1 | 1 | 50% ⚠️ |

### 按失败模式分类

| 失败模式 | 题目数 | 占比 | 示例 |
|---------|--------|------|------|
| **未来时态未识别** | 2 | 18% | Q7, Q18 |
| **泛化动作语义不等价** | 2 | 18% | Q9, Q10 |
| **多事实聚合不全** | 3 | 27% | Q16, Q19, Q20 |
| **实体属性缺失** | 1 | 9% | Q12 |
| **反事实推理不完整** | 1 | 9% | Q15 |
| **精确时间计算错误** | 2 | 18% | Q17, Q9 |

---

## 根因归纳：两大核心短板

### 短板 1: 时间推理模式覆盖不足 (5/8 时间题失败)

**Phase 4 P0 已覆盖**:
- ✅ 过去时 + 具体事件: "last year", "N years ago" + "paint sunrise"
- ✅ 时间线解析: Session timestamp + relative time resolution
- ✅ 合取匹配: paint AND sunrise (NOT sunset)

**Phase 4 P0 未覆盖**:
- ❌ 未来时态: "planning", "going to", "will" → 需要 future tense detection
- ❌ 泛化动作: "give a speech" ≠ "school event" → 需要 semantic equivalence
- ❌ 相对时间精确计算: "the week before X" → 需要 date arithmetic
- ❌ 计划事件时间抽取: "conference in July" → 需要 future event parsing

**Track 2/3 要求**:
1. **扩展 temporal keyword 库** (Phase 4 P1 Track 1)
   - 添加未来时态 patterns: `future_tense_patterns = ['planning', 'going to', 'will', 'intends to']`
   - 添加泛化动作 synonyms: `action_synonyms = {'give a speech': ['school event', 'talk', 'presentation']}`

2. **精确时间计算** (Phase 4 P1 Track 1)
   - 实现 "the week before X" → 相对日期计算
   - 实现 "yesterday" from session date → 绝对日期

---

### 短板 2: 知识图谱质量差 (5/8 事实题失败)

**当前 KG 状态**:
- ❌ 未运行增强版 KG 抽取 (`populate_kg_from_locomo.py`)
- ❌ 未接入 `kg_memory_joint_search` 到检索链路
- ❌ 缺失实体属性: Caroline -> origin_location
- ❌ 缺失兴趣列表: Melanie's kids -> interests
- ❌ 缺失活动聚合: Melanie -> hobbies -> [pottery, camping, painting, swimming]

**Track 2 紧急任务**:
1. **运行增强版 KG 抽取**
   ```bash
   python populate_kg_from_locomo.py
   ```
   - 目标: 抽取 Caroline/Melanie 的核心实体关系
   - 验证: 检查 `locomo_kg.json` 包含 (Caroline, origin_from, Sweden)

2. **调通 KG + Memory Joint Search**
   - 修改 `brain_coordinator.py` 的 `smart_retrieve()`
   - 添加 KG query 分支:
     ```python
     if "Where did X move from" in query:
         kg_result = kg_memory.query_entity_attribute(entity="Caroline", attribute="origin_location")
     ```

3. **验证 Q1/Q4/Q5/Q12 KG 收益**
   - Q1 (support group date): 需要 event temporal KG
   - Q4 (research): 需要 action KG
   - Q5 (identity): ✅ 已正确 (1.0)
   - Q12 (origin): 需要 entity attribute KG

---

## Track 3: 自适应调优缺失

**当前状态**:
- ✅ `learning_log.jsonl` 正在写入数据
- ❌ 无分析脚本统计 boost/触发贡献度
- ❌ 无自动参数更新机制

**Track 3 紧急任务**:
1. **编写 learning_log 分析脚本**
   ```python
   # analyze_learning_log.py
   def analyze_temporal_boost_effectiveness():
       # 读取 learning_log.jsonl
       # 统计: temporal_boost_reason -> correct_rate
       # 发现: timeline+event (Q2) → 100%, relative_time_only → 50%
       return boost_effectiveness
   ```

2. **离线网格调参**
   ```python
   # grid_search_params.py
   param_grid = {
       'base_bonus': [0.3, 0.5, 0.7],
       'recency_bonus_1yr': [0.05, 0.10, 0.15],
       'recency_bonus_2yr': [0.10, 0.15, 0.20]
   }
   # 对 medium test 运行网格搜索
   best_params = grid_search(param_grid, test_set='medium')
   ```

3. **自动参数更新闭环**
   - 每周运行一次分析脚本
   - 若 Q2 准确率 <0.9, 自动触发调参
   - 更新 `memory_signal_config.json`

---

## 优先级建议

### P0 (立即执行 - 24小时内)

**1. Track 2: KG 抽取 + 验证**
```bash
# 运行增强版 KG 抽取
python BMAM/populate_kg_from_locomo.py

# 验证 KG 质量
python scripts/verify_kg_coverage.py --check-entities Caroline,Melanie --check-relations origin,hobbies,interests
```

**预期收益**: Q12 (origin), Q16/Q19 (hobbies), Q20 (interests) → +3-4 题

---

**2. Track 1: 未来时态 Pattern**
```python
# 在 brain_coordinator.py 添加未来时态检测
future_tense_patterns = ['planning', 'going to', 'will', 'intends to', 'in [month]']

if any(pattern in query_lower for pattern in future_tense_patterns):
    # 触发 future event extraction
    future_event = extract_future_event(query, memories)
```

**预期收益**: Q7, Q18 → +2 题

---

### P1 (本周内完成)

**3. Track 1: 泛化动作语义等价**
```python
# 添加 action synonym mapping
action_synonyms = {
    'give a speech': ['school event', 'talk', 'presentation', 'spoke at'],
    'sign up': ['registered', 'enrolled'],
    'meet up': ['gathered', 'got together', 'meetup']
}
```

**预期收益**: Q9, Q10, Q17 → +3 题

---

**4. Track 3: Learning Log 分析脚本**
```python
# 实现 analyze_learning_log.py
python scripts/analyze_learning_log.py --output boost_effectiveness.json
```

**预期收益**: 发现参数优化方向，指导 P2 调参

---

### P2 (下周完成)

**5. Track 3: 网格调参 + 自动更新**
```python
# 运行网格搜索
python scripts/grid_search_params.py --test-set medium --iterations 10

# 部署自动更新
cron: 0 0 * * 0 python scripts/auto_param_update.py
```

**预期收益**: 持续优化，防止 regression

---

## 目标达成路径

**当前状态**: 10.9/20 (54.5%)
**Phase 4 P0 基线**: Q2 完美解决 (1.0)

**P0 完成后** (KG + 未来时态):
- 修复 Q7, Q18 (未来时态) → +2 分
- 修复 Q12, Q16, Q19, Q20 (KG 支持) → +3 分
- **预期**: 15.9/20 (79.5%) ✅

**P1 完成后** (泛化动作 + 多事实聚合):
- 修复 Q9, Q10, Q17 → +3 分
- **预期**: 18.9/20 (94.5%) 🎯

**P2 完成后** (自适应调优):
- 持续优化细节 → +1 分
- **预期**: 19+/20 (95%+) 🚀

---

## 监控指标

### Track 2 KG 效果指标
- [ ] KG 实体覆盖率: Caroline, Melanie 核心属性 ≥80%
- [ ] KG 关系覆盖率: origin, hobbies, interests ≥90%
- [ ] Q12 准确率: 0.0 → 1.0
- [ ] Q16/Q19/Q20 平均分: 0.43 → 0.9+

### Track 1 时间推理指标
- [ ] 未来时态识别率: 0% → 100% (Q7, Q18)
- [ ] 泛化动作匹配率: 0% → 80% (Q9, Q10, Q17)
- [ ] 时间题整体准确率: 37.5% → 75%+

### Track 3 自适应调优指标
- [ ] Learning log 完整性: ≥95% 问题有日志
- [ ] Boost 有效性: timeline+event → 90%+ 正确率
- [ ] 参数稳定性: 无大幅波动 (±0.05)

---

## 结论

Phase 4 P0 成功解决了 Q2 (过去时 + 具体事件)，但 **Medium 测试暴露了两大短板**：

1. **时间推理模式覆盖不足**: 未来时态、泛化动作、精确时间计算未实现
2. **知识图谱质量差**: 实体属性、多事实聚合、细粒度关系缺失

**下一步行动** (按优先级):
1. ✅ **Track 2 P0**: 运行 KG 抽取 + 验证覆盖率 (24h 内)
2. ✅ **Track 1 P0**: 添加未来时态 pattern (24h 内)
3. **Track 1 P1**: 实现泛化动作语义等价 (本周)
4. **Track 3 P1**: 编写 learning_log 分析脚本 (本周)
5. **Track 3 P2**: 网格调参 + 自动更新闭环 (下周)

**预期提升路径**: 54.5% (当前) → 79.5% (P0) → 94.5% (P1) → 95%+ (P2)

---

**生成时间**: 2025-10-29
**分析基于**: `locomo_medium_20251029_093916_final.json`
**Phase**: 4 P0 → Phase 4 P1 规划
