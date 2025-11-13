# BMA格式多脑区支持 - 待完成

**日期**: 2025-11-12
**状态**: ⚠️  当前实现不完整 - 仅支持单一数据库
**优先级**: P1 - 核心功能缺失

## 🔴 当前问题

### 问题描述
当前BMA格式实现只支持单一的`brain_memory.db`（TemporalLobe的长期记忆），**没有**支持BMAM框架的多脑区分层存储架构。

### 受影响的脑区

1. **❌ Hippocampus** (海马体) - 短期记忆
   - 当前: 内存存储（字典/列表）
   - 需要: 独立持久化文件

2. **✅ TemporalLobe** (颞叶) - 长期记忆
   - 当前: `brain_memory.db` ✓
   - 状态: 已支持

3. **❌ PrefrontalCortex** (前额叶) - 工作记忆
   - 当前: 内存存储（`working_memory`列表）
   - 需要: `prefrontal_working_memory.json`

4. **❌ Amygdala** (杏仁核) - 情绪记忆
   - 当前: 内存存储（`emotional_buffer`列表）
   - 需要: `amygdala_emotional.json`

5. **❌ BasalGanglia** (基底神经节) - 程序性记忆/习惯
   - 当前: 内存存储（`skills`字典）
   - 需要: `basal_ganglia_skills.json`

## 📐 设计方案

### 改进后的BMA格式结构

```
my_memory.bma/
├── manifest.json                    # 归档元数据
├── brain_regions/                   # 脑区存储目录
│   ├── temporal_lobe.db            # 长期记忆 (SQLite)
│   ├── hippocampus.json            # 短期记忆 (JSON)
│   ├── prefrontal.json             # 工作记忆 (JSON)
│   ├── amygdala.json               # 情绪记忆 (JSON)
│   ├── basal_ganglia.json          # 程序性记忆 (JSON)
│   └── thalamus.json               # 感知路由 (JSON, 可选)
├── faiss_index/                     # 向量索引
│   └── ...
├── checksums.json                   # 完整性校验
└── README.md                        # 说明文档
```

### Manifest更新

```json
{
  "format_version": "2.0.0",  // 升级版本号
  "archive_type": "bmam_memory_archive",
  "brain_regions": {
    "temporal_lobe": {
      "file": "brain_regions/temporal_lobe.db",
      "format": "sqlite",
      "required": true,
      "memory_count": 523
    },
    "hippocampus": {
      "file": "brain_regions/hippocampus.json",
      "format": "json",
      "required": false,
      "memory_count": 150
    },
    "prefrontal": {
      "file": "brain_regions/prefrontal.json",
      "format": "json",
      "required": false,
      "working_memory_slots": 10
    },
    "amygdala": {
      "file": "brain_regions/amygdala.json",
      "format": "json",
      "required": false,
      "emotional_memories": 45
    },
    "basal_ganglia": {
      "file": "brain_regions/basal_ganglia.json",
      "format": "json",
      "required": false,
      "skills_count": 23
    }
  }
}
```

## ✅ 已完成的工作

1. ✅ 基础BMA格式定义
2. ✅ TemporalLobe支持（brain_memory.db）
3. ✅ FAISS向量索引支持
4. ✅ Manifest元数据
5. ✅ 完整性校验（SHA256）
6. ✅ Export/Load/Validate方法
7. ✅ Coordinator集成
8. ✅ 基础测试通过

## 🔧 需要完成的工作

### Phase 1: 脑区存储接口标准化 (P1)

为每个脑区添加`export_state()`和`load_state()`方法：

```python
class BrainAgent:
    def export_state(self) -> Dict[str, Any]:
        """导出当前脑区状态为JSON可序列化格式"""
        raise NotImplementedError

    def load_state(self, state: Dict[str, Any]):
        """从字典加载脑区状态"""
        raise NotImplementedError
```

#### 需要实现的Agent

- [ ] `HippocampusAgent.export_state()` / `load_state()`
- [ ] `PrefrontalAgent.export_state()` / `load_state()`
- [ ] `AmygdalaAgent.export_state()` / `load_state()`
- [ ] `BasalGangliaAgent.export_state()` / `load_state()`

### Phase 2: 更新MemoryArchive类 (P1)

```python
class MemoryArchive:
    @classmethod
    def create(cls, coordinator: BrainInspiredCoordinator, ...):
        """
        更新create方法以支持多脑区导出

        1. 遍历coordinator.agents
        2. 调用每个agent的export_state()
        3. 保存到brain_regions/目录
        4. 更新manifest
        """
        pass

    def load(self, coordinator: BrainInspiredCoordinator, ...):
        """
        更新load方法以支持多脑区加载

        1. 从brain_regions/加载各个文件
        2. 调用对应agent的load_state()
        3. 验证加载成功
        """
        pass
```

### Phase 3: 向后兼容性 (P2)

支持v1.0.0格式（只有单一db文件）：

```python
def _detect_format_version(archive_path: Path) -> str:
    """检测归档格式版本"""
    manifest = json.load(open(archive_path / "manifest.json"))
    return manifest.get("format_version", "1.0.0")

def _migrate_v1_to_v2(archive_path: Path):
    """将v1.0.0格式迁移到v2.0.0"""
    # 创建brain_regions/目录
    # 移动memories.db -> brain_regions/temporal_lobe.db
    # 更新manifest
    pass
```

### Phase 4: 测试 (P1)

```python
# test_bma_multi_region.py

async def test_multi_region_export():
    """测试多脑区导出"""
    # 1. 创建coordinator并写入各个脑区
    # 2. 导出BMA
    # 3. 验证所有脑区文件存在
    pass

async def test_multi_region_load():
    """测试多脑区加载"""
    # 1. 加载BMA
    # 2. 验证各个脑区状态正确
    # 3. 测试记忆检索功能
    pass

async def test_selective_region_load():
    """测试选择性脑区加载（插拔功能）"""
    # 1. 只加载temporal_lobe和hippocampus
    # 2. 跳过prefrontal等
    # 3. 验证部分加载成功
    pass
```

## 💡 设计优势

### 1. 可插拔性
```python
# 只加载长期记忆和情绪记忆
coordinator.load_memory_archive(
    archive_path=Path("archives/baseline.bma"),
    regions=["temporal_lobe", "amygdala"]  # 选择性加载
)
```

### 2. 独立替换
```python
# 替换工作记忆，保留其他脑区
coordinator.load_brain_region(
    region="prefrontal",
    source=Path("archives/high_capacity_wm.json")
)
```

### 3. 混合配置
```python
# 组合不同来源的脑区
coordinator.load_memory_archive("baseline.bma", regions=["temporal_lobe"])
coordinator.load_brain_region("amygdala", "emotional_expert.json")
coordinator.load_brain_region("basal_ganglia", "habit_master.json")
```

## 📊 实现工作量估算

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| Phase 1: 脑区接口 | 4-6小时 | P1 |
| Phase 2: Archive更新 | 3-4小时 | P1 |
| Phase 3: 向后兼容 | 2-3小时 | P2 |
| Phase 4: 测试 | 2-3小时 | P1 |
| 文档更新 | 1-2小时 | P2 |
| **总计** | **12-18小时** | - |

## 🚀 快速解决方案 (临时)

在完整实现之前，可以先：

1. **手动导出**: 用户自己调用各个agent的方法保存状态
2. **脚本辅助**: 提供独立脚本导出各个脑区到JSON
3. **文档说明**: 在README中说明当前限制

## 📝 相关文件

- `src/memory/memory_archive.py` - 需要更新
- `src/agents/brain_regions/*/` - 需要添加export/load方法
- `src/coordination/brain_coordinator_refactored.py` - 需要更新load方法
- `MEMORY_ARCHIVE_FORMAT_DESIGN.md` - 需要更新设计文档

## 🎯 下一步行动

1. [ ] 用户确认设计方案
2. [ ] 实施Phase 1（脑区接口）
3. [ ] 实施Phase 2（Archive更新）
4. [ ] 编写测试
5. [ ] 更新文档
6. [ ] 发布v2.0.0

---

**创建时间**: 2025-11-12
**最后更新**: 2025-11-12
**负责人**: BMAM Framework Team
**审核状态**: 待用户确认
