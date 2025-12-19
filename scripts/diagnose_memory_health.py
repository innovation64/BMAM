#!/usr/bin/env python3
"""
BMAM Memory Health Diagnostic Script
诊断记忆系统健康状态，输出真实数据而非估计值

Usage:
    python scripts/diagnose_memory_health.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# 🔥 直接使用路径，避免导入 BMAM 模块触发初始化覆盖文件
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STATE_DIR = DATA_DIR / "state"


class BMAMPaths:
    """Minimal path class to avoid import side effects"""
    HIPPOCAMPUS_STATE = STATE_DIR / "hippocampus_state.json"
    STORY_ARC_STATE = STATE_DIR / "story_arc_state.json"
    AMYGDALA_STATE = STATE_DIR / "amygdala_state.json"
    PREFRONTAL_STATE = STATE_DIR / "prefrontal_state.json"
    BASAL_GANGLIA_STATE = STATE_DIR / "basal_ganglia_state.json"


def load_json_safe(path: Path) -> dict:
    """安全加载 JSON 文件"""
    if not path.exists():
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️ Failed to load {path.name}: {e}")
        return {}


def analyze_hippocampus(data: dict) -> dict:
    """分析海马体记忆"""
    memories = data.get('memories', [])
    if not memories:
        return {'count': 0, 'with_event_time': 0, 'shaping_methods': {}}

    with_event_time = 0
    shaping_methods = defaultdict(int)
    high_confidence_time = 0

    for mem in memories:
        metadata = mem.get('metadata', {})

        # 检查事件时间
        if mem.get('event_time') or metadata.get('event_time'):
            with_event_time += 1

        # 检查时间提取置信度 (支持多种键名)
        extraction_conf = metadata.get('extraction_confidence', 0)
        event_time_conf = metadata.get('event_time_confidence', '')

        # 处理字符串类型的置信度
        if isinstance(event_time_conf, str):
            conf_map = {'high': 0.9, 'medium': 0.6, 'low': 0.3}
            extraction_conf = max(extraction_conf, conf_map.get(event_time_conf, 0))

        if extraction_conf >= 0.7:
            high_confidence_time += 1

        # 统计塑造方法
        method = metadata.get('shaping_method', 'unknown')
        shaping_methods[method] += 1

    return {
        'count': len(memories),
        'with_event_time': with_event_time,
        'high_confidence_time': high_confidence_time,
        'shaping_methods': dict(shaping_methods)
    }


def analyze_story_arc(data: dict) -> dict:
    """分析 StoryArc 时间线"""
    events = data.get('events', [])
    if not events:
        return {'count': 0, 'entities': set(), 'event_types': {}}

    entities = set()
    event_types = defaultdict(int)
    dates = set()

    for event in events:
        for entity in event.get('entities', []):
            entities.add(entity.lower())
        event_types[event.get('event_type', 'unknown')] += 1
        if event.get('event_date'):
            dates.add(event['event_date'])

    return {
        'count': len(events),
        'unique_entities': len(entities),
        'entities': list(entities),
        'unique_dates': len(dates),
        'event_types': dict(event_types)
    }


def analyze_amygdala(data: dict) -> dict:
    """分析杏仁核情绪标记"""
    emotions = data.get('emotional_memories', data.get('emotions', []))
    if isinstance(emotions, dict):
        return {'count': len(emotions), 'emotions': list(emotions.keys())[:10]}
    return {'count': len(emotions) if isinstance(emotions, list) else 0}


def analyze_prefrontal(data: dict) -> dict:
    """分析前额叶工作记忆"""
    items = data.get('working_memory', data.get('items', []))
    return {'count': len(items) if isinstance(items, list) else 0}


def analyze_basal_ganglia(data: dict) -> dict:
    """分析基底神经节程序性记忆"""
    patterns = data.get('patterns', data.get('habits', []))
    return {'count': len(patterns) if isinstance(patterns, list) else 0}


def main():
    print("=" * 60)
    print("BMAM Memory Health Diagnostic")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # 1. 加载各脑区数据
    print("Loading brain region states...")

    hippocampus_data = load_json_safe(BMAMPaths.HIPPOCAMPUS_STATE)
    story_arc_data = load_json_safe(BMAMPaths.STORY_ARC_STATE)
    amygdala_data = load_json_safe(BMAMPaths.AMYGDALA_STATE)
    prefrontal_data = load_json_safe(BMAMPaths.PREFRONTAL_STATE)
    basal_ganglia_data = load_json_safe(BMAMPaths.BASAL_GANGLIA_STATE)

    # 2. 分析各脑区
    print()
    print("=" * 60)
    print("BRAIN REGION MEMORY DISTRIBUTION")
    print("=" * 60)

    hip_stats = analyze_hippocampus(hippocampus_data)
    arc_stats = analyze_story_arc(story_arc_data)
    amy_stats = analyze_amygdala(amygdala_data)
    pfc_stats = analyze_prefrontal(prefrontal_data)
    bg_stats = analyze_basal_ganglia(basal_ganglia_data)

    total_memories = hip_stats['count'] + amy_stats['count'] + pfc_stats['count'] + bg_stats['count']

    print(f"""
┌─────────────────────────────────────────────────────────┐
│  Brain Region          │  Count  │  Percentage         │
├─────────────────────────────────────────────────────────┤
│  Hippocampus           │  {hip_stats['count']:>5}  │  {hip_stats['count']/max(total_memories,1)*100:>6.1f}%            │
│  Amygdala              │  {amy_stats['count']:>5}  │  {amy_stats['count']/max(total_memories,1)*100:>6.1f}%            │
│  Prefrontal            │  {pfc_stats['count']:>5}  │  {pfc_stats['count']/max(total_memories,1)*100:>6.1f}%            │
│  Basal Ganglia         │  {bg_stats['count']:>5}  │  {bg_stats['count']/max(total_memories,1)*100:>6.1f}%            │
├─────────────────────────────────────────────────────────┤
│  TOTAL                 │  {total_memories:>5}  │  100.0%            │
└─────────────────────────────────────────────────────────┘
""")

    # 3. 时间推理覆盖率
    print("=" * 60)
    print("TEMPORAL REASONING COVERAGE")
    print("=" * 60)

    event_time_rate = hip_stats['with_event_time'] / max(hip_stats['count'], 1) * 100
    high_conf_rate = hip_stats['high_confidence_time'] / max(hip_stats['count'], 1) * 100
    story_arc_coverage = arc_stats['count'] / max(hip_stats['count'], 1) * 100

    print(f"""
┌─────────────────────────────────────────────────────────┐
│  Metric                          │  Value               │
├─────────────────────────────────────────────────────────┤
│  Memories with event_time        │  {hip_stats['with_event_time']:>5} / {hip_stats['count']:<5} ({event_time_rate:>5.1f}%)  │
│  High-confidence time (>=0.7)    │  {hip_stats['high_confidence_time']:>5} / {hip_stats['count']:<5} ({high_conf_rate:>5.1f}%)  │
│  StoryArc indexed events         │  {arc_stats['count']:>5}                     │
│  StoryArc coverage               │  {story_arc_coverage:>5.1f}%                   │
│  Unique entities in StoryArc     │  {arc_stats['unique_entities']:>5}                     │
│  Unique dates in StoryArc        │  {arc_stats['unique_dates']:>5}                     │
└─────────────────────────────────────────────────────────┘
""")

    # 4. 塑造方法分布
    print("=" * 60)
    print("MEMORY SHAPING METHOD DISTRIBUTION")
    print("=" * 60)

    shaping = hip_stats.get('shaping_methods', {})
    if shaping:
        print()
        for method, count in sorted(shaping.items(), key=lambda x: -x[1]):
            pct = count / max(hip_stats['count'], 1) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"  {method:<20} {bar} {count:>4} ({pct:>5.1f}%)")
        print()
    else:
        print("  No shaping method data available")
        print()

    # 5. StoryArc 事件类型分布
    if arc_stats.get('event_types'):
        print("=" * 60)
        print("STORY ARC EVENT TYPES")
        print("=" * 60)
        print()
        for etype, count in sorted(arc_stats['event_types'].items(), key=lambda x: -x[1]):
            print(f"  {etype:<25} {count:>4}")
        print()

    # 6. 健康评分
    print("=" * 60)
    print("OVERALL HEALTH SCORE")
    print("=" * 60)

    # 计算健康分数
    distribution_score = 100 - (hip_stats['count'] / max(total_memories, 1) * 100 - 40) if total_memories > 0 else 0
    distribution_score = max(0, min(100, distribution_score))

    temporal_score = high_conf_rate

    story_arc_score = min(100, story_arc_coverage * 2)  # 50% coverage = 100 score

    overall = (distribution_score * 0.3 + temporal_score * 0.4 + story_arc_score * 0.3)

    print(f"""
┌─────────────────────────────────────────────────────────┐
│  Category                   │  Score    │  Status      │
├─────────────────────────────────────────────────────────┤
│  Memory Distribution        │  {distribution_score:>5.1f}/100 │  {'✅ Good' if distribution_score > 60 else '⚠️ Imbalanced'}     │
│  Temporal Coverage          │  {temporal_score:>5.1f}/100 │  {'✅ Good' if temporal_score > 50 else '⚠️ Low'}     │
│  StoryArc Coverage          │  {story_arc_score:>5.1f}/100 │  {'✅ Good' if story_arc_score > 50 else '⚠️ Low'}     │
├─────────────────────────────────────────────────────────┤
│  OVERALL HEALTH             │  {overall:>5.1f}/100 │  {'✅ Healthy' if overall > 60 else '⚠️ Needs Work'}  │
└─────────────────────────────────────────────────────────┘
""")

    # 7. 建议
    print("=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print()

    if hip_stats['count'] / max(total_memories, 1) > 0.9:
        print("  ⚠️  Memory heavily concentrated in Hippocampus")
        print("      → Consider redistributing to other brain regions")
        print()

    if pfc_stats['count'] == 0:
        print("  ⚠️  Prefrontal cortex is EMPTY")
        print("      → Working memory not being utilized")
        print()

    if high_conf_rate < 20:
        print("  ⚠️  Low temporal confidence (<20%)")
        print("      → Improve event time extraction in shaping")
        print()

    if story_arc_coverage < 10:
        print("  ⚠️  StoryArc coverage very low (<10%)")
        print("      → Re-run migration or improve event extraction")
        print()

    if not any([
        hip_stats['count'] / max(total_memories, 1) > 0.9,
        pfc_stats['count'] == 0,
        high_conf_rate < 20,
        story_arc_coverage < 10
    ]):
        print("  ✅ No critical issues detected")

    print()
    print("=" * 60)
    print("Diagnostic complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
