#!/usr/bin/env python3
"""
灵魂可迁移性测试 (Soul Portability Test)

验证 BMAM 记忆系统的"灵魂"特性:
1. 记忆存档完整性 - 所有脑区状态正确保存
2. 记忆恢复一致性 - 恢复后回答与原始一致
3. 跨实例迁移 - 记忆可在不同实例间迁移

测试流程:
  Phase 1: 塑造记忆 (Shaping)
    - 加载测试对话并塑造记忆
    - 回答一组测试问题，记录答案
  Phase 2: 存档导出 (Export)
    - 导出完整记忆存档 (.bma)
    - 验证存档完整性
  Phase 3: 清空并恢复 (Clear & Restore)
    - 完全清空记忆
    - 从存档恢复记忆
  Phase 4: 一致性验证 (Consistency)
    - 用相同问题测试
    - 计算答案一致率

使用:
  python test_soul_portability.py                    # 默认测试
  python test_soul_portability.py --questions 20    # 指定问题数
  python test_soul_portability.py --verbose         # 详细输出
"""

import asyncio
import json
import os
import sys
import argparse
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
import logging
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.WARNING)
for name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss']:
    logging.getLogger(name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Paths
DATA_DIR = PROJECT_ROOT / 'data'
MEMORY_DIR = DATA_DIR / 'memory'
STATE_DIR = DATA_DIR / 'state'
CACHE_DIR = DATA_DIR / 'cache'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'soul_portability'
ARCHIVE_DIR = RESULTS_DIR / 'archives'

# LoCoMo dataset
_locomo_env = os.getenv('LOCOMO_DATASET_PATH')
LOCOMO_PATH = Path(_locomo_env) if _locomo_env else DATA_DIR / 'datasets' / 'locomo' / 'locomo10.json'


@dataclass
class SoulPortabilityResult:
    """灵魂可迁移性测试结果"""
    # Phase 1: Shaping
    shaping_success: bool = False
    memories_count: int = 0
    original_answers: Dict[str, str] = field(default_factory=dict)

    # Phase 2: Export
    export_success: bool = False
    archive_path: str = ""
    archive_size_bytes: int = 0
    brain_regions_exported: List[str] = field(default_factory=list)

    # Phase 3: Restore
    restore_success: bool = False
    restore_memories_count: int = 0
    brain_regions_restored: List[str] = field(default_factory=list)

    # Phase 4: Consistency
    restored_answers: Dict[str, str] = field(default_factory=dict)
    consistency_rate: float = 0.0
    identical_answers: int = 0
    semantic_matches: int = 0
    total_questions: int = 0

    # Metrics
    soul_integrity_score: float = 0.0  # 综合灵魂完整性分数
    elapsed_seconds: float = 0.0


def clear_memory():
    """彻底清空所有记忆"""
    # 数据库文件
    db_files = ['brain_memory.db', 'temporal_lobe.db', 'working_memory.db', 'kv_value_store.db',
                'memory_vectors.index', 'memory_vectors_mappings.json']
    for f in db_files:
        p = MEMORY_DIR / f
        if p.exists():
            p.unlink()

    # 状态文件
    state_files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
                   'amygdala_state.json', 'story_arc_state.json', 'calibration_state.json']
    for f in state_files:
        p = STATE_DIR / f
        if p.exists():
            p.unlink()

    # 缓存目录
    for d in ['embedding', 'knowledge_graph', 'faiss_index']:
        p = CACHE_DIR / d
        if p.exists():
            shutil.rmtree(p)

    # 旧版缓存路径
    for d in ['embedding_cache', 'knowledge_graph', 'faiss_index']:
        p = MEMORY_DIR / d
        if p.exists():
            shutil.rmtree(p)

    # 重置 StoryArc 单例
    try:
        from src.memory.story_arc import reset_story_arc_manager
        reset_story_arc_manager()
    except ImportError:
        pass


def parse_date(s: str) -> datetime:
    if not s:
        return datetime.now()
    try:
        from dateutil import parser
        return parser.parse(s, fuzzy=True)
    except:
        return datetime.now()


async def create_coordinator():
    """创建 coordinator"""
    from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
    from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()
    return coord


def normalize_answer(answer: str) -> str:
    """标准化答案用于比较"""
    if not answer:
        return ""
    # 移除空白、标点，转小写
    import re
    normalized = re.sub(r'[^\w\s]', '', answer.lower())
    normalized = ' '.join(normalized.split())
    return normalized


def compute_answer_similarity(ans1: str, ans2: str) -> float:
    """计算两个答案的相似度 (0-1)"""
    n1, n2 = normalize_answer(ans1), normalize_answer(ans2)

    # 完全相同
    if n1 == n2:
        return 1.0

    # 空答案
    if not n1 or not n2:
        return 0.0

    # Jaccard 相似度
    words1, words2 = set(n1.split()), set(n2.split())
    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)
    jaccard = intersection / union if union > 0 else 0

    # 包含关系加分
    if n1 in n2 or n2 in n1:
        jaccard = max(jaccard, 0.8)

    return jaccard


async def phase1_shaping(coord, sample: Dict, num_questions: int = 20) -> Tuple[bool, Dict[str, str], int]:
    """Phase 1: 塑造记忆并回答测试问题"""
    print("\n📝 Phase 1: 塑造记忆")
    print("-" * 40)

    # 塑造记忆
    conv = sample['conversation']
    obs = sample.get('observation', {})
    sessions = []
    i = 1
    while f'session_{i}' in conv:
        sessions.append((
            conv[f'session_{i}'],
            conv.get(f'session_{i}_date_time', ''),
            obs.get(f'session_{i}_observation', {})
        ))
        i += 1

    print(f"  塑造 {len(sessions)} 个会话...")
    memory_count = 0

    for idx, (dialogs, date, ob) in enumerate(sessions, 1):
        ts = parse_date(date)

        for t in dialogs:
            if t.get('text'):
                await coord.store_memory_with_timestamp(
                    f"{t['speaker']}: {t['text']}", ts, t['speaker'], 0.6
                )
                memory_count += 1

        for spk, items in ob.items():
            for it in items:
                if isinstance(it, list) and it:
                    await coord.store_memory_with_timestamp(
                        f"[Event] {spk}: {it[0]}", ts, spk, 0.8
                    )
                    memory_count += 1

        print(f"\r  Session {idx}/{len(sessions)}", end='', flush=True)

    print(f" ✓ (共 {memory_count} 条记忆)")

    # 等待巩固
    print("  ⏳ 等待巩固...", end='', flush=True)
    await asyncio.sleep(3)
    print(" done")

    # 回答测试问题
    qas = sample['qa'][:num_questions]
    print(f"  回答 {len(qas)} 个测试问题...")

    original_answers = {}
    for i, qa in enumerate(qas, 1):
        q = qa['question']
        context = {'skip_memory_store': True, 'evaluation_mode': True}
        r = await coord.process_user_input(q, context=context)
        answer = r.response if hasattr(r, 'response') else str(r)
        original_answers[q] = answer
        print(f"\r  问题 {i}/{len(qas)}", end='', flush=True)

    print(" ✓")
    return True, original_answers, memory_count


async def phase2_export(coord, archive_name: str) -> Tuple[bool, str, int, List[str]]:
    """Phase 2: 导出记忆存档"""
    print("\n💾 Phase 2: 导出记忆存档")
    print("-" * 40)

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        from src.coordination.memory_archive_manager import MemoryArchiveManager

        # 获取 base coordinator
        base_coord = coord.base_coordinator if hasattr(coord, 'base_coordinator') else coord

        archive_manager = MemoryArchiveManager(base_coord)
        result = archive_manager.export_archive(
            archive_name=archive_name,
            output_dir=ARCHIVE_DIR,
            description="Soul Portability Test Archive",
            tags=["test", "soul_portability"],
            include_faiss=True
        )

        if not result['success']:
            print(f"  ✗ 导出失败: {result.get('error', 'Unknown error')}")
            return False, "", 0, []

        archive_path = str(result['archive_path'])
        size_bytes = result.get('size_bytes', 0)
        brain_regions = result.get('brain_regions', [])

        print(f"  ✓ 存档路径: {archive_path}")
        print(f"  ✓ 存档大小: {size_bytes / 1024:.1f} KB")
        print(f"  ✓ 脑区状态: {brain_regions}")

        return True, archive_path, size_bytes, brain_regions

    except Exception as e:
        print(f"  ✗ 导出异常: {e}")
        import traceback
        traceback.print_exc()
        return False, "", 0, []


async def phase3_restore(archive_path: str) -> Tuple[bool, int, List[str]]:
    """Phase 3: 清空并恢复记忆"""
    print("\n🔄 Phase 3: 清空并恢复记忆")
    print("-" * 40)

    # 彻底清空记忆
    print("  清空所有记忆...")
    clear_memory()
    print("  ✓ 记忆已清空")

    # 创建新的 coordinator
    print("  创建新实例...")
    coord = await create_coordinator()

    try:
        from src.coordination.memory_archive_manager import MemoryArchiveManager

        base_coord = coord.base_coordinator if hasattr(coord, 'base_coordinator') else coord
        archive_manager = MemoryArchiveManager(base_coord)

        # 恢复存档
        print(f"  从存档恢复: {archive_path}")
        result = archive_manager.load_archive(
            archive_path=Path(archive_path),
            validate=True,
            force=False
        )

        if not result['success']:
            print(f"  ✗ 恢复失败: {result.get('error', 'Unknown error')}")
            return False, 0, []

        stats = result.get('statistics', {})
        memories_count = stats.get('total_memories', 0)
        brain_regions = result.get('brain_regions', [])

        print(f"  ✓ 恢复记忆: {memories_count} 条")
        print(f"  ✓ 恢复脑区: {brain_regions}")

        return True, memories_count, brain_regions

    except Exception as e:
        print(f"  ✗ 恢复异常: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, []


async def phase4_consistency(coord, original_answers: Dict[str, str]) -> Tuple[Dict[str, str], float, int, int]:
    """Phase 4: 一致性验证"""
    print("\n🔍 Phase 4: 一致性验证")
    print("-" * 40)

    questions = list(original_answers.keys())
    print(f"  测试 {len(questions)} 个问题...")

    restored_answers = {}
    identical = 0
    semantic_matches = 0

    for i, q in enumerate(questions, 1):
        context = {'skip_memory_store': True, 'evaluation_mode': True}
        r = await coord.process_user_input(q, context=context)
        answer = r.response if hasattr(r, 'response') else str(r)
        restored_answers[q] = answer

        # 比较答案
        original = original_answers[q]
        similarity = compute_answer_similarity(original, answer)

        if similarity == 1.0:
            identical += 1
            semantic_matches += 1
        elif similarity >= 0.6:
            semantic_matches += 1

        print(f"\r  问题 {i}/{len(questions)} (相似度: {similarity:.2f})", end='', flush=True)

    print(" ✓")

    consistency_rate = semantic_matches / len(questions) if questions else 0

    print(f"\n  📊 一致性结果:")
    print(f"     完全相同: {identical}/{len(questions)} ({identical/len(questions)*100:.1f}%)")
    print(f"     语义匹配: {semantic_matches}/{len(questions)} ({consistency_rate*100:.1f}%)")

    return restored_answers, consistency_rate, identical, semantic_matches


def compute_soul_integrity_score(result: SoulPortabilityResult) -> float:
    """计算综合灵魂完整性分数"""
    # 各阶段权重
    weights = {
        'shaping': 0.1,
        'export': 0.2,
        'restore': 0.2,
        'consistency': 0.5  # 一致性最重要
    }

    score = 0.0

    # Phase 1: Shaping
    if result.shaping_success:
        score += weights['shaping']

    # Phase 2: Export
    if result.export_success:
        regions_score = len(result.brain_regions_exported) / 5  # 假设5个脑区
        score += weights['export'] * min(1.0, regions_score)

    # Phase 3: Restore
    if result.restore_success:
        if result.memories_count > 0:
            restore_ratio = result.restore_memories_count / result.memories_count
            score += weights['restore'] * min(1.0, restore_ratio)

    # Phase 4: Consistency
    score += weights['consistency'] * result.consistency_rate

    return score


async def run_soul_portability_test(
    sample: Dict,
    num_questions: int = 20,
    verbose: bool = False
) -> SoulPortabilityResult:
    """运行完整的灵魂可迁移性测试"""

    result = SoulPortabilityResult()
    start_time = datetime.now()

    # 清空记忆
    clear_memory()

    # 创建 coordinator
    coord = await create_coordinator()

    try:
        # Phase 1: 塑造记忆
        success, original_answers, memory_count = await phase1_shaping(
            coord, sample, num_questions
        )
        result.shaping_success = success
        result.memories_count = memory_count
        result.original_answers = original_answers
        result.total_questions = len(original_answers)

        if not success:
            return result

        # Phase 2: 导出存档
        archive_name = f"soul_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        success, archive_path, size_bytes, brain_regions = await phase2_export(
            coord, archive_name
        )
        result.export_success = success
        result.archive_path = archive_path
        result.archive_size_bytes = size_bytes
        result.brain_regions_exported = brain_regions

        if not success:
            return result

        # 停止当前 coordinator
        if hasattr(coord, 'stop_system'):
            await coord.stop_system()

        # Phase 3: 清空并恢复
        success, restore_count, restored_regions = await phase3_restore(archive_path)
        result.restore_success = success
        result.restore_memories_count = restore_count
        result.brain_regions_restored = restored_regions

        if not success:
            return result

        # 重新创建 coordinator 进行测试
        coord = await create_coordinator()

        # Phase 4: 一致性验证
        restored_answers, consistency_rate, identical, semantic_matches = await phase4_consistency(
            coord, original_answers
        )
        result.restored_answers = restored_answers
        result.consistency_rate = consistency_rate
        result.identical_answers = identical
        result.semantic_matches = semantic_matches

    finally:
        if hasattr(coord, 'stop_system'):
            try:
                await coord.stop_system()
            except:
                pass

    result.elapsed_seconds = (datetime.now() - start_time).total_seconds()
    result.soul_integrity_score = compute_soul_integrity_score(result)

    return result


def print_final_report(result: SoulPortabilityResult):
    """打印最终报告"""
    print("\n" + "=" * 60)
    print("🎭 灵魂可迁移性测试报告")
    print("=" * 60)

    # 各阶段状态
    print("\n📋 各阶段状态:")
    print(f"   Phase 1 (塑造): {'✓' if result.shaping_success else '✗'} ({result.memories_count} 条记忆)")
    print(f"   Phase 2 (导出): {'✓' if result.export_success else '✗'} ({result.archive_size_bytes/1024:.1f} KB)")
    print(f"   Phase 3 (恢复): {'✓' if result.restore_success else '✗'} ({result.restore_memories_count} 条恢复)")
    print(f"   Phase 4 (验证): {result.consistency_rate*100:.1f}% 一致率")

    # 脑区状态
    print(f"\n🧠 脑区状态:")
    print(f"   导出脑区: {result.brain_regions_exported}")
    print(f"   恢复脑区: {result.brain_regions_restored}")

    # 一致性详情
    print(f"\n📊 一致性详情:")
    print(f"   总问题数: {result.total_questions}")
    print(f"   完全相同: {result.identical_answers} ({result.identical_answers/result.total_questions*100:.1f}%)")
    print(f"   语义匹配: {result.semantic_matches} ({result.semantic_matches/result.total_questions*100:.1f}%)")

    # 灵魂完整性分数
    print(f"\n🎯 灵魂完整性分数: {result.soul_integrity_score*100:.1f}%")

    # 评级
    if result.soul_integrity_score >= 0.9:
        grade = "A+ (完美迁移)"
    elif result.soul_integrity_score >= 0.8:
        grade = "A  (优秀)"
    elif result.soul_integrity_score >= 0.7:
        grade = "B  (良好)"
    elif result.soul_integrity_score >= 0.6:
        grade = "C  (及格)"
    else:
        grade = "F  (失败)"

    print(f"   评级: {grade}")
    print(f"\n⏱️  总耗时: {result.elapsed_seconds:.1f} 秒")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description='BMAM 灵魂可迁移性测试')
    parser.add_argument('--questions', type=int, default=20, help='测试问题数')
    parser.add_argument('--group', type=int, default=0, help='使用第几组数据 (0-9)')
    parser.add_argument('--verbose', action='store_true', help='详细输出')
    parser.add_argument('--output', type=str, default=None, help='结果输出文件')
    args = parser.parse_args()

    print("=" * 60)
    print("🎭 BMAM 灵魂可迁移性测试")
    print("=" * 60)

    # 加载数据
    if not LOCOMO_PATH.exists():
        print(f"错误: 数据集不存在: {LOCOMO_PATH}")
        sys.exit(1)

    with open(LOCOMO_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sample = data[args.group]
    print(f"\n使用数据: {sample['sample_id']}")
    print(f"测试问题: {args.questions} 个")

    # 运行测试
    result = await run_soul_portability_test(
        sample=sample,
        num_questions=args.questions,
        verbose=args.verbose
    )

    # 打印报告
    print_final_report(result)

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = args.output or (RESULTS_DIR / f"soul_portability_{ts}.json")

    # 转换为可序列化格式
    output_data = {
        'meta': {
            'timestamp': datetime.now().isoformat(),
            'sample_id': sample['sample_id'],
            'questions': args.questions
        },
        'phases': {
            'shaping': {
                'success': result.shaping_success,
                'memories_count': result.memories_count
            },
            'export': {
                'success': result.export_success,
                'archive_path': result.archive_path,
                'size_bytes': result.archive_size_bytes,
                'brain_regions': result.brain_regions_exported
            },
            'restore': {
                'success': result.restore_success,
                'memories_restored': result.restore_memories_count,
                'brain_regions': result.brain_regions_restored
            },
            'consistency': {
                'rate': result.consistency_rate,
                'identical': result.identical_answers,
                'semantic_matches': result.semantic_matches,
                'total': result.total_questions
            }
        },
        'soul_integrity_score': result.soul_integrity_score,
        'elapsed_seconds': result.elapsed_seconds
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {output_file}")


if __name__ == '__main__':
    asyncio.run(main())
