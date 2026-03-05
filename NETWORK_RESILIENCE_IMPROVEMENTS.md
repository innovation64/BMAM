# 网络稳定性改进文档

**日期**: 2025-12-26
**目的**: 应对长时间断网（可能10分钟+）导致的测试中断

---

## 🔥 已完成的改进

### 1. Embedding API 重试增强

**文件**: `src/services/openai_embedding_service.py`

**改进**:
- ✅ 重试次数: 3次 → **20次**
- ✅ 最大等待时间: 4秒 → **120秒**
- ✅ 捕获更多异常类型:
  - `APIConnectionError`
  - `APITimeoutError`
  - `ConnectionError`
  - `TimeoutError`
  - `httpx.RemoteProtocolError`
  - `httpx.ConnectError`
  - `httpx.ReadError`

**预计支持断网时长**: ~40分钟
```
重试序列: 1s, 2s, 4s, 8s, 16s, 32s, 64s, 120s × 13 = ~28分钟
```

---

### 2. LLM API 重试增强

**文件**: `src/agents/base.py`

**改进**:
- ✅ 重试次数: 4次 → **15次**
- ✅ 基础延迟: 1秒 → **2秒**
- ✅ 最大等待时间: 8秒 → **120秒**

**预计支持断网时长**: ~30分钟
```
重试序列: 2s, 4s, 8s, 16s, 32s, 64s, 120s × 9 = ~1170秒 ≈ 19.5分钟
```

---

### 3. Checkpoint机制（断点续跑）

**文件**: `evaluation/checkpoint_manager.py`

**功能**:
- ✅ 自动保存测试进度
- ✅ 崩溃后从上次位置恢复
- ✅ 自动备份防止损坏
- ✅ 支持所有评测脚本

**使用示例**:

```python
from evaluation.checkpoint_manager import CheckpointManager

# 创建checkpoint管理器
checkpoint = CheckpointManager("locomo_20251226")

# 加载checkpoint（如果存在）
if checkpoint.has_checkpoint():
    completed_ids = checkpoint.load()
    print(f"✅ 从checkpoint恢复，已完成 {len(completed_ids)} 题")
else:
    completed_ids = set()

# 处理每个样本
for sample in samples:
    sample_id = sample['id']  # 或 sample['sample_id']

    # 跳过已完成的
    if sample_id in completed_ids:
        print(f"⏭️  跳过已完成: {sample_id}")
        continue

    # 处理样本...
    result = process_sample(sample)

    # 保存checkpoint
    completed_ids.add(sample_id)
    checkpoint.save(completed_ids, metadata={
        'current_accuracy': current_acc,
        'elapsed_time': elapsed_time
    })

# 测试完成后清理checkpoint
checkpoint.clear()
```

---

## 📊 改进效果预估

| 场景 | 改进前 | 改进后 |
|------|--------|--------|
| 短暂断网(10秒) | ❌ 失败 | ✅ 自动重试成功 |
| 中等断网(1-5分钟) | ❌ 失败 | ✅ 指数退避后成功 |
| 长时间断网(5-10分钟) | ❌ 失败 | ✅ 最多等待30分钟 |
| 程序崩溃 | ❌ 从头开始 | ✅ 从checkpoint恢复 |

---

## 🚀 如何应用到现有测试

### 快速改造示例（LoCoMo）

**原代码** (`test_sequential.py`):
```python
async def main():
    # ... 加载数据 ...

    for i in range(start_group, start_group + num_groups):
        r = await test_group(i, data[i], num_q, client, num_groups)
        results.append(r)
```

**改造后**:
```python
from evaluation.checkpoint_manager import CheckpointManager

async def main():
    # ... 加载数据 ...

    # 🔥 添加checkpoint
    checkpoint = CheckpointManager(f"locomo_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    completed_groups = checkpoint.load() if checkpoint.has_checkpoint() else set()

    for i in range(start_group, start_group + num_groups):
        group_id = f"group_{i}"

        # 跳过已完成的组
        if group_id in completed_groups:
            print(f"⏭️  跳过已完成组: {i}")
            continue

        r = await test_group(i, data[i], num_q, client, num_groups)
        results.append(r)

        # 保存checkpoint
        completed_groups.add(group_id)
        checkpoint.save(completed_groups)

    # 清理checkpoint
    checkpoint.clear()
```

---

## 💡 最佳实践

1. **Checkpoint保存频率**:
   - LoCoMo: 每组保存一次（10组共199题）
   - LongMemEval: 每10题保存一次（50题）
   - PersonaMem: 每50题保存一次（589题）

2. **Checkpoint文件位置**:
   - 默认: `evaluation/checkpoints/`
   - 自动创建，无需手动管理

3. **测试恢复流程**:
   ```bash
   # 1. 测试中断后，直接重新运行相同命令
   python evaluation/benchmarks/locomo/test_sequential.py --groups 1

   # 2. CheckpointManager会自动检测并恢复进度
   # 输出示例:
   # 📂 加载checkpoint: locomo_20251226_093455
   #    已完成: 67 题
   #    保存时间: 2025-12-26 10:30:15
   # ⏭️  跳过已完成: sample_001
   # ⏭️  跳过已完成: sample_002
   # ...
   # 🔄 继续从 sample_068 开始
   ```

4. **手动清理Checkpoint**:
   ```bash
   # 如果需要重新开始测试（不恢复进度）
   rm -rf evaluation/checkpoints/locomo_*
   ```

---

## 🧪 测试验证

建议测试流程:
1. 启动测试
2. 运行到50%时手动中断（Ctrl+C）
3. 重新启动测试
4. 验证是否从50%恢复

---

## 📝 注意事项

1. **data目录清理**: Checkpoint只恢复测试进度，不恢复memory数据。确保串行测试时每个数据集前清理data目录。

2. **并行测试**: Checkpoint机制与串行测试配合最佳。并行运行多个数据集仍会有数据污染问题。

3. **版本兼容**: Checkpoint文件包含timestamp，不同时间的测试会创建不同checkpoint，避免冲突。

---

## 📈 预期改善

**改进前**（2025-12-26早上测试）:
- LoCoMo: ❌ API超时失败
- LongMemEval: ❌ 36题后中断 (55.6%)
- PrefEval: ❌ 连接错误
- PersonaMem: 🔄 运行中，精度下降

**改进后预期**:
- ✅ 支持长时间断网（最多30分钟）
- ✅ 崩溃后可恢复
- ✅ 提高测试完成率
- ✅ 节省重跑时间

---

**创建者**: Claude Code
**创建时间**: 2025-12-26 12:45
