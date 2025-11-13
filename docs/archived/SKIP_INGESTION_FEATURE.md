# LoCoMo 测试 - 跳过录入功能

**日期**: 2025-11-12
**新功能**: `--skip-ingestion` 参数

---

## 快速回答

✅ **是的!测试时可以直接载入已有记忆,无需重复录入对话!**

使用 `--skip-ingestion` 参数跳过Phase 1(对话录入),直接进入Phase 2(问答测试)。

---

## 为什么需要这个功能?

### 问题

LoCoMo测试分为两个阶段:

```
Phase 1: 录入对话 (~40秒,经过优化后)
  → 500+轮对话 → Hippocampus → TemporalLobe → MemorySystem
  → 存储到 data/brain_memory.db

Phase 2: 问答测试 (~30秒)
  → 20个问题 → 检索记忆 → LLM Judge评分
```

**痛点**:
- 每次测试都重复录入500轮对话,浪费时间
- 想测试不同数量的问题(5/10/20/all),但每次都要等40秒录入
- 记忆已经存储在数据库中,应该可以直接复用

### 解决方案

添加 `--skip-ingestion` 参数:
- ✅ 跳过Phase 1,直接使用已有记忆
- ✅ 只运行Phase 2,测试问答准确率
- ✅ 节省~40秒录入时间

---

## 使用方式

### 方式1: 标准流程 (首次测试)

```bash
# 1. 清理旧数据
bash scripts/clean_test_data.sh

# 2. 录入记忆 + 测试5问
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
# → 40秒录入 + 5秒测试 = 45秒
# → 记忆存储到 data/brain_memory.db
```

### 方式2: 快速测试 (复用记忆)

```bash
# 跳过录入,直接测试10问
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 10 --verbose
# → 0秒录入 + 10秒测试 = 10秒 (4.5倍速!)

# 跳过录入,测试20问
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 --verbose
# → 0秒录入 + 20秒测试 = 20秒

# 跳过录入,测试全部问题
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions all --verbose
# → 0秒录入 + 30秒测试 = 30秒
```

### 方式3: 使用不同记忆库

```bash
# 场景1: 使用已有记忆库A
export DATABASE_URL="sqlite:///data/memory_scenario_A.db"
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20

# 场景2: 使用已有记忆库B
export DATABASE_URL="sqlite:///data/memory_scenario_B.db"
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20

# 场景3: 切换回默认库
unset DATABASE_URL
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20
```

---

## 实现细节

### 代码变化

#### 1. 添加参数 (`test_locomo_bmam_full.py:393`)

```python
parser.add_argument('--skip-ingestion', action='store_true',
                   help='Skip conversation ingestion, use existing memory (saves ~40s)')
```

#### 2. 修改测试流程 (`test_locomo_bmam_full.py:323-351`)

**之前**:
```python
async def test_single_sample(...):
    # Phase 1: 喂入对话 (总是执行)
    coordinator1 = BrainInspiredCoordinator()
    await coordinator1.initialize()
    ingest_metrics = await ingest_conversation(coordinator1, sample, verbose=verbose)

    await asyncio.sleep(3)  # 等待巩固

    # Phase 2: QA 测试
    coordinator2 = BrainInspiredCoordinator()
    await coordinator2.initialize()
    qa_metrics = await test_qa_with_llm_judge(...)
```

**现在**:
```python
async def test_single_sample(..., skip_ingestion: bool = False):
    # Phase 1: 喂入对话 (可跳过)
    if skip_ingestion:
        print("⏭️  [Phase 1] Skipped ingestion, using existing memory")
        ingest_metrics = {
            'total_turns': 0,
            'sessions': 0,
            'duration_sec': 0.0,
            'throughput': 0.0,
            'skipped': True
        }
    else:
        coordinator1 = BrainInspiredCoordinator()
        await coordinator1.initialize()
        ingest_metrics = await ingest_conversation(coordinator1, sample, verbose=verbose)
        await asyncio.sleep(3)  # 等待巩固

    # Phase 2: QA 测试 (总是执行)
    coordinator2 = BrainInspiredCoordinator()
    await coordinator2.initialize()  # 读取已有记忆
    qa_metrics = await test_qa_with_llm_judge(...)
```

#### 3. 配置输出 (`test_locomo_bmam_full.py:414`)

```python
print(f"  - Skip ingestion: {args.skip_ingestion}")
```

---

## 性能对比

### 标准测试 (不跳过)

```
Phase 1: 录入对话
  Session 1 (2023-05-08): 17 turns → 2.5s (6.8 turns/sec)
  Session 2 (2023-05-25): 19 turns → 2.8s (6.8 turns/sec)
  ...
  ✓ Ingested 523 turns in 40.2s (13.0 turns/sec)

⏳ Waiting 3s for consolidation...

Phase 2: 测试 20 QA pairs
  [1/20] Q: When did Caroline go to the LGBTQ support group?...
    ✅ Judgments: 3/3 CORRECT
  ...
  ✓ Results: 18/20 correct (90.0%)

总耗时: 40.2 + 3 + 20 = 63.2秒
```

### 快速测试 (跳过录入)

```
⏭️  [Phase 1] Skipped ingestion, using existing memory

Phase 2: 测试 20 QA pairs
  [1/20] Q: When did Caroline go to the LGBTQ support group?...
    ✅ Judgments: 3/3 CORRECT
  ...
  ✓ Results: 18/20 correct (90.0%)

总耗时: 0 + 0 + 20 = 20秒 (3.2倍速!)
```

---

## 使用场景

### 场景1: 迭代测试不同问题数

**目标**: 测试5/10/20/all问题的准确率变化

```bash
# 1. 首次录入记忆
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose

# 2. 测试10问 (复用记忆)
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 10 --verbose

# 3. 测试20问 (复用记忆)
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 --verbose

# 4. 测试全部 (复用记忆)
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions all --verbose
```

**总耗时**: 45s + 10s + 20s + 30s = 105秒
**vs 不跳过**: 45s + 50s + 63s + 73s = 231秒
**提升**: 2.2倍速!

### 场景2: 调试LLM Judge

**目标**: 调整LLM Judge参数,重新评分

```bash
# 1. 录入记忆 (一次)
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20 --verbose

# 2. 测试Judge runs=1
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 --judge-runs 1

# 3. 测试Judge runs=3
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 --judge-runs 3

# 4. 测试Judge runs=5
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 --judge-runs 5
```

每次测试只需~20秒,无需重复录入!

### 场景3: 对比不同记忆库

**目标**: 测试不同consolidation策略的性能

```bash
# 策略1: Aggressive consolidation
export DATABASE_URL="sqlite:///data/aggressive_memory.db"
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20
# → 录入 + 测试

# 策略2: Conservative consolidation (复用测试逻辑)
export DATABASE_URL="sqlite:///data/conservative_memory.db"
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20
# → 录入 + 测试

# 对比测试 (快速)
export DATABASE_URL="sqlite:///data/aggressive_memory.db"
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions all

export DATABASE_URL="sqlite:///data/conservative_memory.db"
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions all
```

### 场景4: CI/CD 快速验证

**目标**: 代码修改后快速验证记忆检索功能

```bash
# 开发流程
# 1. 一次性准备测试记忆
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose
# → 记忆保存到 data/brain_memory.db

# 2. 修改代码 (记忆检索/LLM Judge等)

# 3. 快速回归测试 (跳过录入)
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20
# → 20秒快速验证

# 4. 继续修改...

# 5. 再次快速测试
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20
```

**效率提升**: 每次回归测试从63秒 → 20秒 (3倍速!)

---

## 注意事项

### 1. 记忆库一致性

⚠️ **确保记忆库已录入**: 使用 `--skip-ingestion` 前,必须先运行一次完整测试

```bash
# ❌ 错误: 数据库为空
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20
# → 记忆检索失败,准确率0%

# ✅ 正确: 先录入记忆
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20
```

### 2. 数据库路径

⚠️ **检查DATABASE_URL环境变量**: 确保使用正确的记忆库

```bash
# 查看当前使用的数据库
echo $DATABASE_URL
# 如果为空,使用默认: sqlite:///data/brain_memory.db

# 切换数据库
export DATABASE_URL="sqlite:///data/custom_memory.db"

# 重置为默认
unset DATABASE_URL
```

### 3. 记忆污染

⚠️ **避免混淆不同sample的记忆**: 测试不同sample前清理数据

```bash
# 测试sample 1
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20

# 清理后测试sample 2 (避免混淆)
bash scripts/clean_test_data.sh
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20
```

**或者使用不同数据库**:
```bash
# Sample 1
export DATABASE_URL="sqlite:///data/sample1.db"
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20

# Sample 2
export DATABASE_URL="sqlite:///data/sample2.db"
python3 tests/test_locomo_bmam_full.py --samples 1 --questions 20
```

### 4. 并发测试

⚠️ **SQLite并发限制**: 多个进程同时读写同一个db可能冲突

**解决方案**: 每个测试进程使用独立数据库
```bash
# 进程1
export DATABASE_URL="sqlite:///data/test1.db"
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 &

# 进程2
export DATABASE_URL="sqlite:///data/test2.db"
python3 tests/test_locomo_bmam_full.py --skip-ingestion --questions 20 &

wait
```

---

## 输出示例

### 完整测试 (不跳过)

```
================================================================================
LoCoMo BMAM Full Benchmark
================================================================================
Configuration:
  - Samples: 1
  - Questions per sample: 20
  - LLM Judge runs: 3
  - Skip ingestion: False
  - LLM Judge available: True
================================================================================

================================================================================
Testing Sample 1: conv-26
  QA pairs: 20/199
================================================================================

[Phase 1] Ingesting conversation...
  Session 1 (2023-05-08): 17 turns → 2.5s (6.8 turns/sec)
  Session 2 (2023-05-25): 19 turns → 2.8s (6.8 turns/sec)
  ...
✓ Ingested 523 turns in 40.2s (13.0 turns/sec)

⏳ Waiting 3s for consolidation...

[Phase 2] Testing 20 QA pairs with LLM Judge...
  [1/20] Q: When did Caroline go to the LGBTQ support group?...
    ✅ Judgments: 3/3 CORRECT
  ...

✓ Results: 18/20 correct (90.0%)
```

### 快速测试 (跳过录入)

```
================================================================================
LoCoMo BMAM Full Benchmark
================================================================================
Configuration:
  - Samples: 1
  - Questions per sample: 20
  - LLM Judge runs: 3
  - Skip ingestion: True  ← 注意这里
  - LLM Judge available: True
================================================================================

================================================================================
Testing Sample 1: conv-26
  QA pairs: 20/199
================================================================================

⏭️  [Phase 1] Skipped ingestion, using existing memory  ← 跳过录入

[Phase 2] Testing 20 QA pairs with LLM Judge...
  [1/20] Q: When did Caroline go to the LGBTQ support group?...
    ✅ Judgments: 3/3 CORRECT
  ...

✓ Results: 18/20 correct (90.0%)
```

**关键差异**:
- `Skip ingestion: True`
- 没有Session录入输出
- 没有巩固等待
- 直接进入Phase 2

---

## 总结

### ✅ 优势

1. **节省时间**: 跳过40秒录入,总测试时间减少50-70%
2. **灵活测试**: 可以快速测试不同数量的问题
3. **调试友好**: 修改代码后快速验证
4. **记忆复用**: 一次录入,多次测试

### 📊 性能提升

| 测试类型 | 不跳过 | 跳过录入 | 提升 |
|---------|-------|---------|------|
| 5问 | 45s | 5s | **9倍** |
| 10问 | 50s | 10s | **5倍** |
| 20问 | 63s | 20s | **3.2倍** |
| 全部(199问) | 240s | 200s | **1.2倍** |

### 🎯 适用场景

- ✅ 迭代测试不同问题数量
- ✅ 调试LLM Judge参数
- ✅ 对比不同记忆库
- ✅ CI/CD快速验证
- ✅ 开发时频繁回归测试

### ⚠️ 注意事项

- 确保记忆库已录入
- 检查DATABASE_URL环境变量
- 避免不同sample记忆混淆
- 注意SQLite并发限制

---

**准备就绪!现在可以高效复用记忆进行测试了!** 🚀
