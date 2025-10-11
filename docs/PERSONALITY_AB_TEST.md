# PersonalityAgent A/B测试指南

## 概述

系统现在支持两个PersonalityAgent版本的A/B测试：
- **Original版本**：简化的"摇光明明"人格系统（当前使用）
- **MBTI版本**：基于MBTI 16型人格的完整心理学模型

---

## 快速开始

### 查看当前版本
```python
from src.coordination.personality_version_manager import get_version_manager

manager = get_version_manager()
print(manager.get_version_info())
```

### 切换到MBTI版本
```python
manager = get_version_manager()
success, message = manager.set_version('mbti')
print(message)
# 输出: Successfully switched to mbti version

# 重启系统以应用更改
```

### 切换回Original版本
```python
manager.set_version('original')
# 重启系统以应用更改
```

---

## 两个版本的详细对比

### 版本1: Original (默认)

**特点**：
- 固定的"摇光明明"人格
- 简单的特质参数系统
- 轻量级实现，响应快速
- 已经过优化的语气调节

**适用场景**：
- 需要稳定一致的对话体验
- 追求快速响应时间
- 不需要复杂的人格切换

**人格参数**：
```python
traits = {
    "温暖": 0.9,
    "智慧": 0.8,
    "好奇心": 0.9,
    "同理心": 0.85,
    "幽默感": 0.7,
    "可靠性": 0.9,
    "创造力": 0.8,
    "耐心": 0.8
}

speech_style = {
    "正式程度": 0.5,
    "幽默感": 0.4,
    "表情符号使用": 0.2,
    "语气亲切度": 0.7,
    "详细程度": 0.4,
    "提问倾向": 0.3
}
```

---

### 版本2: MBTI

**特点**：
- 支持16种MBTI人格类型
- 基于心理学的认知功能栈（Ni-Te-Fi-Se等）
- 可根据用户偏好动态切换
- 更丰富的人格特征和行为模式

**适用场景**：
- 需要个性化的对话体验
- 用户希望选择喜欢的交互风格
- 研究不同人格对对话效果的影响

**默认人格：ENFP（竞选者）**

**ENFP特征**：
```python
traits = {
    "enthusiastic": 0.95,      # 热情
    "creative": 0.90,          # 创造力
    "social": 0.85,            # 社交性
    "optimistic": 0.90,        # 乐观
    "spontaneous": 0.85,       # 自发性
    "empathetic": 0.85,        # 同理心
    "curious": 0.90,           # 好奇心
    "flexible": 0.80           # 灵活性
}

communication_style = {
    "directness": 0.6,
    "formality": 0.3,
    "logic_focus": 0.4,
    "emotional_expression": 0.9,
    "detail_oriented": 0.4,
    "big_picture": 0.8
}

cognitive_functions = [
    "Ne (外向直觉)",    # 主导
    "Fi (内向情感)",    # 辅助
    "Te (外向思维)",    # 第三
    "Si (内向感觉)"     # 劣势
]
```

---

## 可用的MBTI人格类型

### 分析师 (NT) - 理性思考
- **INTJ（建筑师）**：战略性、独立、追求效率
- **INTP（思考者）**：逻辑性、好奇、分析型
- **ENTJ（指挥官）**：果断、领导力、目标导向
- **ENTP（辩论家）**：创新、挑战性、智慧型

### 外交家 (NF) - 情感直觉
- **INFJ（提倡者）**：理想主义、洞察力、富有同情心
- **INFP（调停者）**：理想主义、富有创造力、价值驱动
- **ENFJ（主人公）**：魅力型、鼓舞人心、组织能力
- **ENFP（竞选者）**：热情、创造性、社交型（默认）

### 守护者 (SJ) - 实用稳重
- **ISTJ（物流师）**：可靠、实际、有条理
- **ISFJ（守卫者）**：保护性、细心、有责任感
- **ESTJ（总经理）**：高效、传统、组织能力
- **ESFJ（执政官）**：热心、合作、关心他人

### 探险家 (SP) - 灵活实践
- **ISTP（鉴赏家）**：实用、灵活、技术型
- **ISFP（探险家）**：艺术性、灵活、温和
- **ESTP（企业家）**：活力、行动派、适应性强
- **ESFP（表演者）**：外向、友好、享受当下

---

## 切换MBTI人格类型

修改 `config/mbti_personality.json`：

```json
{
  "current_personality": "INTJ",  // 改为你想要的类型
  "personality_mode": "fixed",
  "allow_personality_switching": true,
  // ... 其他配置
}
```

重启系统后生效。

---

## 实验对比方法

### 1. 准备测试场景

创建一组标准测试问题：

```python
test_scenarios = [
    # 场景1: 记忆回忆
    {
        "setup": "请记住我喜欢喝绿茶",
        "questions": [
            "我刚才说我喜欢什么？",
            "基于我的偏好推荐饮品"
        ]
    },

    # 场景2: 情感支持
    {
        "question": "今天工作压力很大，感觉很焦虑",
        "expected": "同理心和建议"
    },

    # 场景3: 知识解释
    {
        "question": "什么是神经可塑性？",
        "expected": "清晰准确的解释"
    },

    # 场景4: 创意建议
    {
        "question": "帮我想一些周末活动的点子",
        "expected": "有创意的建议"
    }
]
```

### 2. 运行对比测试

```python
from src.coordination.personality_version_manager import get_version_manager
from src.coordination.brain_coordinator import BrainInspiredCoordinator
import asyncio

async def run_ab_test():
    manager = get_version_manager()

    # 测试Original版本
    manager.set_version('original')
    coordinator_original = BrainInspiredCoordinator()
    await coordinator_original.initialize()

    print("=== Testing Original Version ===")
    for scenario in test_scenarios:
        result = await coordinator_original.process_user_input(scenario['question'])
        print(f"Q: {scenario['question']}")
        print(f"A: {result.response}\n")

    await coordinator_original.stop_system()

    # 测试MBTI版本
    manager.set_version('mbti')
    coordinator_mbti = BrainInspiredCoordinator()
    await coordinator_mbti.initialize()

    print("=== Testing MBTI Version (ENFP) ===")
    for scenario in test_scenarios:
        result = await coordinator_mbti.process_user_input(scenario['question'])
        print(f"Q: {scenario['question']}")
        print(f"A: {result.response}\n")

    await coordinator_mbti.stop_system()

# 运行测试
asyncio.run(run_ab_test())
```

### 3. 评估指标

对比以下维度：

| 维度 | Original | MBTI | 说明 |
|------|----------|------|------|
| **响应速度** | | | 平均响应时间(秒) |
| **记忆准确性** | | | 记忆回忆的准确率 |
| **语气一致性** | | | 人格特征的稳定性 |
| **情感共鸣** | | | 对情感的理解和回应 |
| **创意性** | | | 建议的创新性 |
| **专业性** | | | 解释的准确性和深度 |
| **用户满意度** | | | 主观评分(1-5) |

### 4. 记录实验数据

```python
# 获取实验报告
manager = get_version_manager()
report = manager.get_experiment_report()
print(report)
```

输出示例：
```json
{
  "current_version": "mbti",
  "timestamp": "2025-09-30T16:30:00",
  "comparison": {
    "original": {
      "total_responses": 50,
      "avg_response_time": "1.234s",
      "avg_user_rating": "4.20",
      "rating_count": 50
    },
    "mbti": {
      "total_responses": 50,
      "avg_response_time": "1.456s",
      "avg_user_rating": "4.35",
      "rating_count": 50
    }
  }
}
```

---

## 推荐的测试流程

### 第1天：熟悉Original版本
1. 设置版本为 `original`
2. 进行20-30轮对话
3. 记录优点和不足

### 第2天：体验MBTI版本（默认ENFP）
1. 设置版本为 `mbti`
2. 使用相同的对话场景
3. 对比响应风格

### 第3天：尝试不同MBTI类型
1. 测试INTJ（理性）
2. 测试INFJ（理想主义）
3. 测试ESFJ（温暖）
4. 找出最适合的人格类型

### 第4天：深度对比
1. 使用标准测试集
2. 记录量化指标
3. 得出结论

---

## 常见问题

### Q1: 切换版本后需要重启吗？
**A**: 是的，修改配置文件后需要重启系统才能生效。

### Q2: MBTI版本会影响记忆系统吗？
**A**: 不会。两个版本共享相同的记忆系统，只是响应风格不同。

### Q3: 可以动态切换MBTI类型吗？
**A**: 当前需要修改配置文件并重启。未来可以支持运行时切换。

### Q4: 哪个版本响应更快？
**A**: Original版本理论上更快，因为逻辑更简单。实际差异需要通过测试确认。

### Q5: 如何判断哪个版本更好？
**A**: 没有绝对的"更好"，取决于你的需求：
- 如果追求稳定和速度 → Original
- 如果追求个性化和丰富性 → MBTI

---

## 配置文件位置

```
BMAM/
├── config/
│   ├── personality_version.json    # 版本选择配置
│   └── mbti_personality.json       # MBTI人格配置
└── src/
    └── coordination/
        └── personality_version_manager.py  # 版本管理器
```

---

## 技术实现细节

### 版本管理器工作原理

1. **加载配置**：读取 `personality_version.json` 确定当前版本
2. **创建Agent**：根据版本调用不同的构造函数
   - `original` → `PersonalityAgent`
   - `mbti` → `MBTIIntegratedPersonalityAgent`
3. **透明切换**：coordinator无需修改，自动适配
4. **统计收集**：记录响应时间和质量评分

### 扩展性

如果未来要添加新版本：

```python
# 在 personality_version_manager.py 中添加
def _create_new_version_agent(self, **kwargs):
    from ..agents.core.new_agent import NewPersonalityAgent
    return NewPersonalityAgent(**kwargs)
```

---

## 反馈和改进

完成A/B测试后，请记录：
1. 你更喜欢哪个版本？为什么？
2. MBTI版本中，哪种人格类型最适合？
3. 有哪些具体的改进建议？

可以通过修改配置文件微调人格参数，找到最佳配置。

---

## 总结

- **Original**: 简单、快速、稳定 ✅ 当前默认
- **MBTI**: 丰富、个性化、可定制 🆕 实验性

根据实际使用效果选择最适合的版本！