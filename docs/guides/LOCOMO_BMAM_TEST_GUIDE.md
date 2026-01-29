# LoCoMo BMAM 完整测试指南

## 测试脚本说明

**文件**: `tests/test_locomo_bmam_full.py`

这是一个完整的 LoCoMo 基准测试脚本,专门为 BMAM 记忆框架设计,使用 LLM Judge 评分标准(参考 MemOS)。

## 主要特性

### 1. 自动适配问题数量
- ✅ **每组问题数量不固定** - 自动检测每个sample的QA数量
- ✅ **支持测试全部问题** - 使用 `--questions all`
- ✅ **支持指定数量** - 使用 `--questions N` (如果超过可用数量会自动截断)

### 2. LLM Judge 评分
- ✅ **参考 MemOS 标准** - 使用相同的评分逻辑和prompt
- ✅ **多次运行取平均** - 默认3次运行(可配置)
- ✅ **多数投票机制** - 多次判断取多数结果
- ✅ **Fallback机制** - 如果LLM Judge不可用,自动降级为字符串匹配

### 3. 记忆框架特性
- ✅ **非RAG模式** - 直接通过 `process_user_input()` 生成回答
- ✅ **记录记忆检索** - 追踪每个问题检索到多少条记忆
- ✅ **完整metrics** - 记录时间、tokens、记忆数量等

### 4. 完整数据记录
- ✅ **每个问题的详细结果** - question, gold_answer, generated_answer, judgments
- ✅ **Category统计** - 按category (single hop, multi hop, temporal reasoning, open domain)
- ✅ **时间统计** - ingestion时间、QA测试时间
- ✅ **结构化JSON输出** - 方便后续分析和改进

## 使用方法

### 前置条件

1. 安装依赖:
```bash
pip install openai python-dotenv
```

2. 配置 OpenAI API (用于 LLM Judge):
```bash
# 在 BMAM/.env 文件中配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选
```

### 测试命令

#### 0. 清理测试数据 (推荐每次测试前运行)
```bash
bash scripts/clean_test_data.sh
```

**为什么需要清理?**
- Agent buffers会在长时间测试中累积变大(可达10MB+)
- 损坏的buffer文件会导致JSON解析错误
- 清理后可以保证干净的测试环境

#### 1. 快速测试 (1组前5问)
```bash
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
```

#### 2. 标准测试 (1组前20问)
```bash
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20 --verbose
```

#### 3. 单组全部问题
```bash
python3 tests/test_locomo_bmam_full.py --samples 1 --questions all --verbose
```

#### 4. 10组全部问题 (完整benchmark)
```bash
python3 tests/test_locomo_bmam_full.py --samples 10 --questions all --verbose
```

#### 5. 自定义LLM Judge运行次数
```bash
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20 --judge-runs 5
```

### 参数说明

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--samples` | 测试多少个样本 (1-10) | 1 | `--samples 10` |
| `--questions` | 每个样本测试多少问题 ("all"或数字) | 20 | `--questions all` |
| `--judge-runs` | LLM Judge运行次数 | 3 | `--judge-runs 5` |
| `--verbose` | 详细输出 | False | `--verbose` |

## 输出说明

### 1. 终端输出

**测试进度**:
```
================================================================================
Testing Sample 1: conv-26
  QA pairs: 20/199
================================================================================

[Phase 1] Ingesting conversation...
  Session 1 (2023-05-08): 17 turns
  Session 2 (2023-05-25): 19 turns
  ...
✓ Ingested 523 turns in 45.2s

⏳ Waiting 3s for consolidation...

[Phase 2] Testing 20 QA pairs with LLM Judge...
  [1/20] Q: When did Caroline go to the LGBTQ support group?...
    ✅ Judgments: 3/3 CORRECT
    Expected: 7 May 2023
    Got: Caroline went to the LGBTQ support group on 7 May 2023...
  ...
```

**最终结果**:
```
================================================================================
FINAL RESULTS
================================================================================
Samples tested: 1
Total questions: 20
Total correct: 15
Overall accuracy: 75.00%
LLM Judge score: 0.7500 ± 0.0100
Time elapsed: 125.3s (2.1 min)
================================================================================

Category Breakdown:
  multi hop: 70.0% (7/10)
  temporal reasoning: 80.0% (4/5)
  open domain: 75.0% (3/4)
  single hop: 100.0% (1/1)
```

### 2. JSON输出文件

**位置**: `metrics/locomo_bmam_full/results_{samples}samples_{questions}q_{timestamp}.json`

**结构**:
```json
{
  "config": {
    "num_samples": 1,
    "questions_per_sample": "20",
    "num_judge_runs": 3,
    "llm_judge_available": true,
    "total_qa_tested": 20
  },
  "summary": {
    "total_correct": 15,
    "total_questions": 20,
    "overall_accuracy": 0.75,
    "llm_judge_mean": 0.7500,
    "llm_judge_std": 0.0100,
    "elapsed_seconds": 125.3,
    "category_stats": {
      "1": {"correct": 7, "total": 10},
      "2": {"correct": 4, "total": 5}
    }
  },
  "per_sample_results": [
    {
      "sample_id": "conv-26",
      "ingest_metrics": {
        "total_turns": 523,
        "sessions": 18,
        "duration_sec": 45.2
      },
      "qa_metrics": {
        "results": [
          {
            "question": "When did Caroline go to the LGBTQ support group?",
            "gold_answer": "7 May 2023",
            "generated_answer": "Caroline went to the LGBTQ support group on 7 May 2023...",
            "category": 2,
            "judgments": [true, true, true],
            "reasonings": ["...", "...", "..."],
            "memories_retrieved": 5,
            "response_duration_ms": 1234.5,
            "answer_length": 120
          }
        ],
        "correct_count": 15,
        "total_questions": 20,
        "accuracy": 0.75,
        "llm_judge_scores": [0.75, 0.75, 0.75],
        "total_duration_sec": 80.1
      }
    }
  ],
  "timestamp": "2025-11-11T17:00:00",
  "framework": "BMAM"
}
```

## 数据记录说明

### 每个问题记录的数据

| 字段 | 说明 |
|------|------|
| `question` | 原始问题 |
| `gold_answer` | 标准答案 |
| `generated_answer` | BMAM生成的答案 |
| `category` | 问题类别 (1-4) |
| `judgments` | LLM Judge的多次判断结果 (bool列表) |
| `reasonings` | LLM Judge的推理过程 (string列表) |
| `memories_retrieved` | 检索到的记忆数量 |
| `response_duration_ms` | 生成回答的时间(毫秒) |
| `answer_length` | 回答长度(字符数) |

### 整体统计数据

| 字段 | 说明 |
|------|------|
| `total_correct` | 正确回答数量 |
| `total_questions` | 总问题数量 |
| `overall_accuracy` | 总体准确率 |
| `llm_judge_mean` | LLM Judge平均分数 |
| `llm_judge_std` | LLM Judge标准差 |
| `elapsed_seconds` | 总耗时(秒) |
| `category_stats` | 按类别的统计 |

## LLM Judge 评分标准

参考 MemOS 的评分标准:

1. **宽松匹配**: 只要生成的答案涉及相同主题,即可算作正确
2. **时间灵活**: 允许不同的时间格式 ("May 7th" vs "7 May")
3. **相对时间**: 理解相对时间引用 ("last Tuesday" vs "2023-05-02")
4. **多数投票**: 多次运行取多数结果,提高稳定性

### Judge Prompt 示例

```
Your task is to label an answer to a question as 'CORRECT' or 'WRONG'.

Question: When did Caroline go to the LGBTQ support group?
Gold answer: 7 May 2023
Generated answer: Caroline went to the LGBTQ support group on 7 May 2023...

Be generous with your grading - as long as it touches on the same topic as the gold answer,
it should be counted as CORRECT.

For time related questions, be flexible with formats and relative references.
```

## 与 MemOS 的对比

### 相同点
- ✅ 使用相同的 LLM Judge 评分标准
- ✅ 使用相同的 locomo10.json 数据集
- ✅ 计算相同的 metrics (accuracy, category breakdown)
- ✅ 多次运行取平均

### 不同点
- ❌ **不使用 RAG**: BMAM是记忆框架,不提供search context
- ✅ **使用记忆检索**: 通过 `smart_retrieve()` 检索相关记忆
- ✅ **记录记忆metrics**: 追踪检索到的记忆数量
- ✅ **两阶段测试**: Phase 1喂入对话, Phase 2测试QA (模拟跨会话)

## 预期结果

### 目标指标 (参考MemOS)

| 指标 | MemOS | BMAM目标 |
|------|-------|----------|
| Overall Accuracy | ~70% | ≥50% (初期) |
| Single Hop | ~90% | ≥70% |
| Multi Hop | ~65% | ≥45% |
| Temporal Reasoning | ~55% | ≥40% |
| Open Domain | ~60% | ≥45% |

### 性能指标

| 指标 | 预期值 |
|------|--------|
| Ingestion速度 | ~10-15 turns/sec |
| QA响应时间 | ~1-3s per question |
| 记忆检索数量 | ~3-5 memories per query |

## Troubleshooting

### 1. LLM Judge 不可用

**问题**: `⚠️ OpenAI not available, will use simple string matching`

**解决**:
```bash
pip install openai python-dotenv
# 配置 .env 文件
echo "OPENAI_API_KEY=your_key" > .env
```

### 2. 记忆检索失败

**问题**: `⚠️ Memory retrieval failed: ...`

**原因**: memory_coordinator未正确初始化

**解决**: 检查 `BrainInspiredCoordinator.initialize()` 是否正常执行

### 3. Buffer文件损坏 (JSONDecodeError)

**问题**: `JSONDecodeError: Extra data: line 247321 column 2`

**原因**: Agent buffer文件在长时间测试中累积过大(10MB+)并损坏

**解决**:
```bash
# 清理所有buffer文件
bash scripts/clean_test_data.sh

# 或手动删除
rm -rf data/agent_buffers/*.json
```

**预防**: 每次测试前运行清理脚本

### 4. 测试超时

**问题**: 测试运行很久没有输出

**原因**:
- 对话太长 (500+ turns)
- LLM Judge 调用慢
- 网络问题

**解决**:
- 先测试小规模 (`--samples 1 --questions 5`)
- 减少 judge runs (`--judge-runs 1`)
- 检查网络连接

## 后续改进方向

根据测试结果,可以针对性改进:

1. **提高准确率**:
   - 改进记忆检索算法
   - 优化巩固策略
   - 增强时间推理能力

2. **提高性能**:
   - 优化ingestion速度
   - 减少QA响应时间
   - 并行处理多个问题

3. **扩展测试**:
   - 增加更多test samples
   - 测试更长的对话
   - 测试更复杂的推理

## 相关文件

- **测试脚本**: `tests/test_locomo_bmam_full.py`
- **原始数据**: `MemOS/evaluation/data/locomo/locomo10.json`
- **MemOS评分脚本**: `MemOS/evaluation/scripts/locomo/locomo_eval.py`
- **结果目录**: `metrics/locomo_bmam_full/`

## 联系与反馈

如果测试过程中遇到问题或有改进建议,请记录在 GitHub Issues 或相关文档中。

---

**准备就绪! 可以开始运行测试了!** 🚀

建议先运行快速测试验证:
```bash
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
```
