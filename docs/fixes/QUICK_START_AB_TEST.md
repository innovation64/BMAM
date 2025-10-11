# PersonalityAgent A/B测试 - 快速开始

## 🎯 目标

对比两个PersonalityAgent版本，找出最适合你的配置：
- **Original**: 简化的摇光明明人格（当前默认）
- **MBTI**: 16型人格心理学模型（实验性）

---

## ⚡ 快速测试（推荐）

### 1. 运行自动对比测试

```bash
cd /Users/liyang/Desktop/testversion/BMAM
python scripts/test_personality_comparison.py
```

这个脚本会：
- ✅ 自动测试两个版本
- ✅ 运行相同的对话场景
- ✅ 对比响应时间和记忆使用
- ✅ 生成对比报告

**预计耗时**: 约5-10分钟

---

## 🔧 手动切换版本

### 查看当前版本

```bash
python scripts/switch_personality_version.py info
```

输出示例：
```
============================================================
PersonalityAgent 版本信息
============================================================
当前版本: original
版本详情:
  名称: 原始PersonalityAgent
  描述: 使用简化的摇光明明人格系统
  ...
```

### 切换到MBTI版本

```bash
python scripts/switch_personality_version.py mbti
```

### 切换回Original版本

```bash
python scripts/switch_personality_version.py original
```

### 设置MBTI人格类型

```bash
# 直接切换到MBTI并设置人格类型
python scripts/switch_personality_version.py mbti INTJ

# 或者只修改MBTI类型（已经是mbti版本时）
python scripts/switch_personality_version.py mbti ENFP
```

**⚠️ 重要**: 切换版本后需要重启系统！

---

## 📝 手动测试步骤

### 第1步：测试Original版本

```bash
# 1. 确认版本
python scripts/switch_personality_version.py info

# 2. 启动系统
python main.py  # 或 python src/ui/voice_interface.py

# 3. 测试以下对话：
```

**测试对话**：
```
你: 请记住我喜欢喝绿茶，每天下午3点左右。
Bot: [记录响应A1]

你: 我刚才说我什么时候喝什么茶？
Bot: [记录响应A2]

你: 基于我的偏好，推荐一些适合下午的饮品。
Bot: [记录响应A3]

你: 今天工作压力很大，感觉很焦虑。
Bot: [记录响应A4]
```

### 第2步：测试MBTI版本

```bash
# 1. 切换版本
python scripts/switch_personality_version.py mbti

# 2. 重启系统
python main.py

# 3. 运行相同的测试对话
```

**测试对话**（相同问题）：
```
你: 请记住我喜欢喝绿茶，每天下午3点左右。
Bot: [记录响应B1]

你: 我刚才说我什么时候喝什么茶？
Bot: [记录响应B2]

你: 基于我的偏好，推荐一些适合下午的饮品。
Bot: [记录响应B3]

你: 今天工作压力很大，感觉很焦虑。
Bot: [记录响应B4]
```

### 第3步：对比评估

填写对比表格：

| 指标 | Original | MBTI | 哪个更好？ |
|------|----------|------|-----------|
| **记忆准确性** | A2的答案 | B2的答案 | |
| **推荐相关性** | A3的答案 | B3的答案 | |
| **情感共鸣** | A4的答案 | B4的答案 | |
| **语气自然度** | 1-5分 | 1-5分 | |
| **响应速度** | 快/慢 | 快/慢 | |
| **整体满意度** | 1-5分 | 1-5分 | |

---

## 🎨 尝试不同的MBTI人格

MBTI版本支持16种人格，每种都有独特风格：

### 推荐尝试：

```bash
# 1. ENFP（默认）- 热情活泼
python scripts/switch_personality_version.py mbti ENFP

# 2. INTJ - 理性严谨
python scripts/switch_personality_version.py mbti INTJ

# 3. INFJ - 理想主义，富有洞察
python scripts/switch_personality_version.py mbti INFJ

# 4. ESFJ - 温暖友善
python scripts/switch_personality_version.py mbti ESFJ
```

### 人格速查表：

| 类型 | 风格 | 适合场景 |
|------|------|----------|
| **ENFP** | 热情、创意、社交 | 日常对话、创意建议 |
| **INTJ** | 理性、战略、独立 | 技术讨论、系统分析 |
| **INFJ** | 理想、洞察、同理心 | 情感支持、深度对话 |
| **ESFJ** | 温暖、关怀、传统 | 日常关怀、实用建议 |
| **INTP** | 逻辑、好奇、分析 | 知识探索、问题解决 |
| **ENTP** | 辩论、创新、挑战 | 头脑风暴、讨论辩论 |

完整16种人格说明见: `docs/PERSONALITY_AB_TEST.md`

---

## 📊 查看实验统计

如果启用了实验追踪，可以查看统计数据：

```python
from src.coordination.personality_version_manager import get_version_manager

manager = get_version_manager()
report = manager.get_experiment_report()
print(report)
```

---

## 🔍 故障排查

### 问题1: 切换版本后没有变化

**解决**: 确认已重启系统。配置文件修改后必须重启。

### 问题2: MBTI版本报错

**检查**:
```bash
# 确认MBTI配置文件存在
ls config/mbti_personality.json

# 确认MBTI模块正常
python -c "from src.agents.core.mbti_integration import MBTIIntegratedPersonalityAgent; print('OK')"
```

### 问题3: 不知道选哪个版本

**建议**:
1. 先用Original版本一周，熟悉基线表现
2. 再切换到MBTI版本一周，对比体验
3. 尝试3-4种不同MBTI人格类型
4. 最终选择你最满意的配置

---

## 💡 实验建议

### 科学的测试方法：

1. **保持变量控制**：每次只改变版本或人格类型，其他保持不变
2. **使用相同场景**：用标准问题测试，便于对比
3. **记录主观感受**：不仅看数据，也要记录你的直观感受
4. **多次测试**：同一配置测试多次，避免偶然性

### 推荐测试时长：

- **快速测试**: 30分钟（自动化脚本）
- **深度测试**: 3-5天（每天换一个配置）
- **生产验证**: 2周（稳定在最终选择的版本）

---

## 🎓 详细文档

- 完整A/B测试指南: `docs/PERSONALITY_AB_TEST.md`
- MBTI人格详解: `docs/PERSONALITY_AB_TEST.md#可用的mbti人格类型`
- 配置文件说明: `config/personality_version.json`

---

## 📧 反馈

完成测试后，请记录：
1. 最终选择的版本和原因
2. 如果选择MBTI，具体使用哪种人格类型
3. 改进建议

---

**祝测试顺利！找到最适合你的PersonalityAgent配置！** 🚀