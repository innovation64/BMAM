#!/usr/bin/env python3
"""
BMAM Memory Metadata Repair Script
修复记忆元数据，解决巩固无法执行的问题

问题:
1. 所有记忆的 metadata 为空 (hit_count, confidence 等)
2. 导致巩固条件检查失败，记忆无法迁移到其他脑区
3. 事件时间覆盖率低 (0% 高置信度)

修复:
1. 补全 metadata 默认值
2. 重新推断事件时间
3. 更新 StoryArc 索引

Usage:
    python scripts/repair_memory_metadata.py [--dry-run]
"""

import json
import sys
import re
import asyncio
from pathlib import Path
from datetime import datetime, date
from typing import Dict, Any, Optional, List
import argparse

# 直接使用路径，避免导入 BMAM 模块触发初始化覆盖文件
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATE_DIR = DATA_DIR / "state"
HIPPOCAMPUS_STATE = STATE_DIR / "hippocampus_state.json"
STORY_ARC_STATE = STATE_DIR / "story_arc_state.json"


def parse_date_from_content(content: str, context_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    从内容中解析事件时间

    Returns:
        {'date': date, 'confidence': float, 'method': str} or None
    """
    content_lower = content.lower()

    # 1. 显式日期格式 (高置信度)
    # Format: "May 7, 2023" or "7 May 2023" or "2023-05-07"
    date_patterns = [
        (r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})', 'dmy'),
        (r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}),?\s+(\d{4})', 'mdy'),
        (r'(\d{4})-(\d{2})-(\d{2})', 'iso'),
    ]

    month_map = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    for pattern, fmt in date_patterns:
        match = re.search(pattern, content_lower)
        if match:
            try:
                if fmt == 'dmy':
                    day, month_str, year = match.groups()
                    d = date(int(year), month_map[month_str], int(day))
                elif fmt == 'mdy':
                    month_str, day, year = match.groups()
                    d = date(int(year), month_map[month_str], int(day))
                else:  # iso
                    year, month, day = match.groups()
                    d = date(int(year), int(month), int(day))

                return {'date': d, 'confidence': 0.9, 'method': 'explicit_date'}
            except ValueError:
                continue

    # 2. 相对时间 (中等置信度)
    if context_date:
        try:
            ctx = datetime.fromisoformat(context_date.replace('Z', '+00:00'))
            ctx_date = ctx.date()
        except:
            ctx_date = date.today()

        relative_patterns = [
            (r'yesterday', -1),
            (r'the day before', -2),
            (r'two days ago', -2),
            (r'three days ago', -3),
            (r'last week', -7),
            (r'a week ago', -7),
        ]

        for pattern, delta in relative_patterns:
            if re.search(pattern, content_lower):
                from datetime import timedelta
                d = ctx_date + timedelta(days=delta)
                return {'date': d, 'confidence': 0.7, 'method': 'relative_date'}

    # 3. 季节/月份提示 (低置信度)
    season_patterns = [
        (r'in (early |late )?(january|february|march|april|may|june|july|august|september|october|november|december)', 0.5),
        (r'last (summer|winter|spring|fall|autumn)', 0.4),
        (r'this (summer|winter|spring|fall|autumn)', 0.4),
    ]

    for pattern, conf in season_patterns:
        match = re.search(pattern, content_lower)
        if match:
            # 返回低置信度，不推断具体日期
            return {'date': None, 'confidence': conf, 'method': 'seasonal_hint'}

    return None


def repair_memory_metadata(memory: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    修复单条记忆的 metadata
    """
    metadata = memory.get('metadata', {})
    content = memory.get('content', '')

    # 1. 补全基本 metadata
    if 'hit_count' not in metadata:
        metadata['hit_count'] = 1  # 默认至少被访问1次

    if 'confidence' not in metadata:
        metadata['confidence'] = 0.6  # 默认中等置信度

    if 'keyword_coverage' not in metadata:
        metadata['keyword_coverage'] = 0.5  # 默认中等覆盖

    if 'shaping_method' not in metadata:
        metadata['shaping_method'] = 'repaired'

    if 'created_at' not in metadata:
        metadata['created_at'] = memory.get('timestamp', datetime.now().isoformat())

    # 2. 尝试推断事件时间
    context_date = memory.get('timestamp') or metadata.get('created_at')
    date_info = parse_date_from_content(content, context_date)

    if date_info:
        if date_info['date']:
            metadata['event_time'] = date_info['date'].isoformat()
            metadata['event_time_method'] = date_info['method']
        metadata['extraction_confidence'] = date_info['confidence']
    else:
        # 使用对话时间作为事件时间 (低置信度)
        if context_date:
            try:
                ctx = datetime.fromisoformat(context_date.replace('Z', '+00:00'))
                metadata['event_time'] = ctx.date().isoformat()
                metadata['event_time_method'] = 'context_fallback'
                metadata['extraction_confidence'] = 0.3
            except:
                pass

    # 3. 标记为已修复
    metadata['repaired_at'] = datetime.now().isoformat()
    metadata['repair_version'] = '1.0'

    memory['metadata'] = metadata
    return memory


def update_story_arc_stats(memories: List[Dict[str, Any]]):
    """
    统计 StoryArc 相关信息（不导入 BMAM 模块，避免覆盖）
    """
    high_confidence_count = 0

    for mem in memories:
        metadata = mem.get('metadata', {})
        confidence = metadata.get('extraction_confidence', 0)

        if confidence >= 0.7:
            high_confidence_count += 1

    print(f"\n📊 StoryArc 统计:")
    print(f"  高置信度事件时间: {high_confidence_count}/{len(memories)} ({high_confidence_count/len(memories)*100:.1f}%)")
    print(f"  注意: StoryArc 索引需要单独更新")


def main():
    parser = argparse.ArgumentParser(description='Repair BMAM memory metadata')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')
    args = parser.parse_args()

    print("=" * 60)
    print("BMAM Memory Metadata Repair Script")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 60)
    print()

    # 1. 加载 Hippocampus 状态
    hippocampus_file = HIPPOCAMPUS_STATE
    if not hippocampus_file.exists():
        print(f"❌ Hippocampus state file not found: {hippocampus_file}")
        return 1

    with open(hippocampus_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    memories = data.get('memories', [])
    print(f"📂 Loaded {len(memories)} memories from Hippocampus")

    # 2. 统计修复前状态
    before_stats = {
        'missing_hit_count': 0,
        'missing_confidence': 0,
        'missing_event_time': 0,
        'high_confidence_time': 0,
    }

    for mem in memories:
        meta = mem.get('metadata', {})
        if 'hit_count' not in meta:
            before_stats['missing_hit_count'] += 1
        if 'confidence' not in meta:
            before_stats['missing_confidence'] += 1
        if 'event_time' not in meta:
            before_stats['missing_event_time'] += 1
        if meta.get('extraction_confidence', 0) >= 0.7:
            before_stats['high_confidence_time'] += 1

    print(f"\n📊 修复前状态:")
    print(f"  缺失 hit_count: {before_stats['missing_hit_count']}/{len(memories)}")
    print(f"  缺失 confidence: {before_stats['missing_confidence']}/{len(memories)}")
    print(f"  缺失 event_time: {before_stats['missing_event_time']}/{len(memories)}")
    print(f"  高置信度时间: {before_stats['high_confidence_time']}/{len(memories)}")

    # 3. 执行修复
    print(f"\n🔧 修复中...")
    repaired_memories = []
    for i, mem in enumerate(memories):
        repaired = repair_memory_metadata(mem, i)
        repaired_memories.append(repaired)

        if (i + 1) % 100 == 0:
            print(f"  进度: {i + 1}/{len(memories)}")

    # 4. 统计修复后状态
    after_stats = {
        'with_hit_count': 0,
        'with_confidence': 0,
        'with_event_time': 0,
        'high_confidence_time': 0,
    }

    for mem in repaired_memories:
        meta = mem.get('metadata', {})
        if 'hit_count' in meta:
            after_stats['with_hit_count'] += 1
        if 'confidence' in meta:
            after_stats['with_confidence'] += 1
        if 'event_time' in meta:
            after_stats['with_event_time'] += 1
        if meta.get('extraction_confidence', 0) >= 0.7:
            after_stats['high_confidence_time'] += 1

    print(f"\n📊 修复后状态:")
    print(f"  有 hit_count: {after_stats['with_hit_count']}/{len(memories)}")
    print(f"  有 confidence: {after_stats['with_confidence']}/{len(memories)}")
    print(f"  有 event_time: {after_stats['with_event_time']}/{len(memories)}")
    print(f"  高置信度时间: {after_stats['high_confidence_time']}/{len(memories)} ({after_stats['high_confidence_time']/len(memories)*100:.1f}%)")

    # 5. 保存或预览
    if args.dry_run:
        print(f"\n⚠️ DRY RUN - 未保存任何更改")
        print("  移除 --dry-run 参数以实际执行修复")
    else:
        # 备份原文件
        backup_file = hippocampus_file.with_suffix('.json.bak')
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 备份原文件到: {backup_file}")

        # 保存修复后的数据
        data['memories'] = repaired_memories
        data['repaired_at'] = datetime.now().isoformat()

        with open(hippocampus_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ 已保存修复后的数据到: {hippocampus_file}")

        # 统计 StoryArc 信息
        update_story_arc_stats(repaired_memories)

    print("\n" + "=" * 60)
    print("修复完成!")
    print("=" * 60)

    # 6. 建议下一步
    print("\n📋 建议下一步:")
    print("  1. 运行诊断: python scripts/diagnose_memory_health.py")
    print("  2. 手动触发巩固: coordinator.trigger_consolidation()")
    print("  3. 重新评测时间推理准确率")

    return 0


if __name__ == "__main__":
    sys.exit(main())
