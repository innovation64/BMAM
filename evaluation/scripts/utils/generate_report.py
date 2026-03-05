#!/usr/bin/env python3
"""
BMAM vs MemOS 对比报告生成器

汇总所有评估结果，生成对比报告
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import glob

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results'
EXPERIMENTS_DIR = PROJECT_ROOT / 'experiments' / 'results'


# MemOS 官方结果 (从论文/官方仓库获取)
MEMOS_RESULTS = {
    'locomo': {
        'accuracy': 0.7331,  # 73.31%
        'source': 'MemOS Paper'
    },
    'longmemeval': {
        'accuracy': None,  # 需要从论文获取
        'source': 'MemOS Paper'
    },
    'personamem': {
        'accuracy': None,
        'source': 'MemOS Paper'
    },
    'prefeval': {
        'accuracy': None,
        'source': 'MemOS Paper'
    }
}


def load_latest_result(result_dir: Path, pattern: str) -> Optional[Dict]:
    """加载最新的结果文件"""
    files = sorted(glob.glob(str(result_dir / pattern)), reverse=True)
    if files:
        with open(files[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_locomo_results() -> Optional[Dict]:
    """加载 LoCoMo 结果"""
    # 从现有实验目录加载
    result_dir = EXPERIMENTS_DIR / 'sequential'
    result = load_latest_result(result_dir, 'result_*.json')
    if result:
        return {
            'accuracy': result.get('summary', {}).get('acc', 0),
            'correct': result.get('summary', {}).get('correct', 0),
            'total': result.get('summary', {}).get('total', 0),
            'details': result
        }
    return None


def load_longmemeval_results() -> Optional[Dict]:
    """加载 LongMemEval 结果"""
    result_dir = RESULTS_DIR / 'longmemeval'
    result = load_latest_result(result_dir, 'bmam_longmemeval_*.json')
    if result and 'metrics' in result:
        return {
            'accuracy': result['metrics']['overall']['accuracy'],
            'correct': result['metrics']['overall']['correct'],
            'total': result['metrics']['overall']['total'],
            'by_category': result['metrics'].get('by_category', {}),
            'latency': result['metrics'].get('latency', {}),
            'details': result
        }
    return None


def load_personamem_results() -> Optional[Dict]:
    """加载 PersonaMem 结果"""
    result_dir = RESULTS_DIR / 'personamem'
    result = load_latest_result(result_dir, 'bmam_personamem_*.json')
    if result and 'metrics' in result:
        return {
            'accuracy': result['metrics']['overall']['accuracy'],
            'correct': result['metrics']['overall']['correct'],
            'total': result['metrics']['overall']['total'],
            'by_question_type': result['metrics'].get('by_question_type', {}),
            'latency': result['metrics'].get('latency', {}),
            'details': result
        }
    return None


def load_prefeval_results() -> Optional[Dict]:
    """加载 PrefEval 结果"""
    result_dir = RESULTS_DIR / 'prefeval'
    result = load_latest_result(result_dir, 'bmam_prefeval_*.json')
    if result and 'metrics' in result:
        return {
            'mean_score': result['metrics']['overall'].get('mean_score', 0),
            'acc_at_0.5': result['metrics']['overall'].get('acc@0.5', 0),
            'total': result['metrics']['overall'].get('total', 0),
            'latency': result['metrics'].get('latency', {}),
            'details': result
        }
    return None


def load_ablation_results() -> Optional[Dict]:
    """加载消融实验结果"""
    result_dir = RESULTS_DIR / 'ablation'
    result = load_latest_result(result_dir, 'ablation_*.json')
    if result:
        return result.get('summary', {})
    return None


def generate_comparison_table(bmam_results: Dict, memos_results: Dict) -> str:
    """生成对比表格"""
    lines = []
    lines.append("## BMAM vs MemOS 性能对比")
    lines.append("")
    lines.append("| Benchmark | BMAM | MemOS | 差异 |")
    lines.append("|-----------|------|-------|------|")

    for benchmark in ['locomo', 'longmemeval', 'personamem', 'prefeval']:
        bmam = bmam_results.get(benchmark)
        memos = memos_results.get(benchmark, {})

        if bmam and 'accuracy' in bmam:
            bmam_acc = f"{bmam['accuracy']*100:.2f}%"
        elif bmam and 'mean_score' in bmam:
            bmam_acc = f"{bmam['mean_score']*100:.2f}%"
        else:
            bmam_acc = "N/A"

        if memos and memos.get('accuracy'):
            memos_acc = f"{memos['accuracy']*100:.2f}%"
        else:
            memos_acc = "N/A"

        # 计算差异
        if bmam and memos and memos.get('accuracy') and bmam.get('accuracy'):
            diff = (bmam['accuracy'] - memos['accuracy']) * 100
            diff_str = f"{diff:+.2f}%"
        else:
            diff_str = "-"

        lines.append(f"| {benchmark.title()} | {bmam_acc} | {memos_acc} | {diff_str} |")

    return "\n".join(lines)


def generate_ablation_table(ablation_results: Dict) -> str:
    """生成消融实验表格"""
    if not ablation_results:
        return "消融实验结果不可用"

    lines = []
    lines.append("## 消融实验结果")
    lines.append("")
    lines.append("| 配置 | 准确率 | 与完整系统差异 |")
    lines.append("|------|--------|----------------|")

    full_acc = ablation_results.get('full', {}).get('accuracy', 0)

    for config, result in ablation_results.items():
        acc = result.get('accuracy', 0)
        diff = (full_acc - acc) * 100
        diff_str = f"{diff:+.2f}%" if config != 'full' else "-"
        lines.append(f"| {config} | {acc*100:.2f}% | {diff_str} |")

    return "\n".join(lines)


def generate_report():
    """生成完整报告"""
    print("加载评估结果...")

    bmam_results = {
        'locomo': load_locomo_results(),
        'longmemeval': load_longmemeval_results(),
        'personamem': load_personamem_results(),
        'prefeval': load_prefeval_results()
    }

    ablation_results = load_ablation_results()

    # 生成报告
    report_lines = []
    report_lines.append("# BMAM 评估报告")
    report_lines.append("")
    report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    # 概要
    report_lines.append("## 概要")
    report_lines.append("")

    available_count = sum(1 for v in bmam_results.values() if v is not None)
    report_lines.append(f"- 完成的评估: {available_count}/4 个 benchmark")
    report_lines.append("")

    # 对比表格
    report_lines.append(generate_comparison_table(bmam_results, MEMOS_RESULTS))
    report_lines.append("")

    # 各 benchmark 详情
    for benchmark, result in bmam_results.items():
        if result:
            report_lines.append(f"### {benchmark.title()} 详情")
            report_lines.append("")

            if 'accuracy' in result:
                report_lines.append(f"- 准确率: {result['accuracy']*100:.2f}%")
            if 'correct' in result and 'total' in result:
                report_lines.append(f"- 正确/总数: {result['correct']}/{result['total']}")
            if 'latency' in result:
                lat = result['latency']
                report_lines.append(f"- 延迟 (ms): mean={lat.get('mean', 0):.0f}, "
                                    f"p50={lat.get('p50', 0):.0f}, p95={lat.get('p95', 0):.0f}")

            # 按类别
            if 'by_category' in result:
                report_lines.append("")
                report_lines.append("**按类别准确率:**")
                for cat, stats in result['by_category'].items():
                    acc = stats.get('accuracy', 0) * 100
                    report_lines.append(f"- {cat}: {acc:.1f}%")

            report_lines.append("")

    # 消融实验
    if ablation_results:
        report_lines.append(generate_ablation_table(ablation_results))
        report_lines.append("")

    # 保存报告
    report_content = "\n".join(report_lines)

    report_file = RESULTS_DIR / f"BMAM_Evaluation_Report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(f"\n报告已保存到: {report_file}")
    print("\n" + "=" * 60)
    print(report_content)


if __name__ == '__main__':
    generate_report()
