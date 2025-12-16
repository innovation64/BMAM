#!/usr/bin/env python3
"""
迁移脚本: 从现有 hippocampus_state.json 迁移事件到 StoryArc

用于 V2.0 升级 - 补充历史数据到时间线索引
"""

import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.story_arc import get_story_arc_manager, reset_story_arc_manager


async def migrate_memories_to_story_arc():
    """从 hippocampus_state.json 迁移记忆到 StoryArc"""

    state_file = Path("data/hippocampus_state.json")
    if not state_file.exists():
        print("❌ hippocampus_state.json 不存在")
        return

    with open(state_file) as f:
        state = json.load(f)

    memories = state.get('memories', [])
    print(f"📂 加载 {len(memories)} 条记忆")

    # 重置 StoryArc (清理可能存在的旧数据)
    reset_story_arc_manager()
    story_arc = get_story_arc_manager()

    # 统计
    migrated = 0
    skipped_no_time = 0
    skipped_low_confidence = 0

    HIGH_CONFIDENCE_METHODS = ('relative', 'absolute', 'explicit', 'metadata', 'inherited')

    for mem in memories:
        metadata = mem.get('metadata', {})
        content = mem.get('content', '')
        memory_id = mem.get('id', '')

        # 检查是否有事件时间
        event_time_str = metadata.get('event_time')
        if not event_time_str:
            skipped_no_time += 1
            continue

        # 检查提取方法的置信度
        extraction_method = metadata.get('event_time_extraction', 'unknown')
        if extraction_method not in HIGH_CONFIDENCE_METHODS:
            skipped_low_confidence += 1
            continue

        # 解析事件时间
        try:
            event_time = datetime.fromisoformat(event_time_str)
        except ValueError:
            skipped_no_time += 1
            continue

        # 添加到 StoryArc
        event = await story_arc.add_event_from_memory(
            memory_id=memory_id,
            content=content,
            event_time=event_time,
            metadata={
                'extraction_method': extraction_method,
                'entities': mem.get('entities', []),
                'importance': mem.get('importance', 0.5)
            }
        )

        if event:
            migrated += 1

    # 保存并显示统计
    print(f"\n✅ 迁移完成:")
    print(f"   - 成功迁移: {migrated}")
    print(f"   - 跳过 (无时间): {skipped_no_time}")
    print(f"   - 跳过 (低置信度): {skipped_low_confidence}")

    stats = story_arc.get_statistics()
    print(f"\n📊 StoryArc 统计:")
    print(f"   - 总事件数: {stats['total_events']}")
    print(f"   - 唯一日期: {stats['unique_dates']}")
    print(f"   - 唯一实体: {stats['unique_entities']}")
    print(f"   - 事件类型: {stats['event_types']}")


if __name__ == '__main__':
    asyncio.run(migrate_memories_to_story_arc())
