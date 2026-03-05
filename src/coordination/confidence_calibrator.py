"""
Confidence Calibrator Module
跨脑区检索置信度校准

🔥 Phase 3: 解决跨脑区检索分数尺度不一致问题

核心功能:
1. 历史校准: 基于检索结果反馈学习每个脑区的校准因子
2. 动态调整: 根据成功/失败率实时调整置信度
3. 持久化: 保存校准参数供下次启动使用

神经科学基础:
- 类似人脑的"元认知校准" - 学会对不同来源的信息给予不同权重
- 基底神经节的奖励学习机制
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


# 🔥 校准配置
CALIBRATION_CONFIG = {
    'learning_rate': 0.1,          # 校准因子学习率
    'min_factor': 0.5,             # 最小校准因子
    'max_factor': 2.0,             # 最大校准因子
    'initial_factor': 1.0,         # 初始校准因子
    'success_boost': 0.05,         # 成功时的提升
    'failure_penalty': 0.08,       # 失败时的惩罚
    'min_samples_for_calibration': 5,  # 最少样本数才开始校准
    'ema_alpha': 0.3,              # 指数移动平均系数
}


@dataclass
class RegionCalibrationState:
    """单个脑区的校准状态"""
    region_name: str
    calibration_factor: float = 1.0
    success_count: int = 0
    failure_count: int = 0
    total_queries: int = 0
    avg_raw_score: float = 0.5
    avg_calibrated_score: float = 0.5
    last_updated: str = ""

    # 历史记录（用于EMA计算）
    score_history: List[float] = field(default_factory=list)
    outcome_history: List[bool] = field(default_factory=list)  # True=success, False=failure

    def success_rate(self) -> float:
        """计算成功率"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        return self.success_count / total

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典（排除大型历史列表）"""
        return {
            'region_name': self.region_name,
            'calibration_factor': self.calibration_factor,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'total_queries': self.total_queries,
            'avg_raw_score': self.avg_raw_score,
            'avg_calibrated_score': self.avg_calibrated_score,
            'last_updated': self.last_updated,
            'success_rate': self.success_rate()
        }


class ConfidenceCalibrator:
    """
    跨脑区置信度校准器

    功能:
    1. calibrate_scores(): 对多脑区检索结果进行置信度校准
    2. record_outcome(): 记录检索结果用于学习
    3. save/load_calibration(): 持久化校准状态
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化校准器

        Args:
            data_dir: 校准数据存储目录
        """
        self.config = CALIBRATION_CONFIG.copy()

        # 各脑区的校准状态
        self.region_states: Dict[str, RegionCalibrationState] = {}

        # 初始化所有脑区
        self._init_region_states()

        # 🔥 使用 BMAMPaths 统一路径管理
        from ..utils.paths import BMAMPaths
        if data_dir:
            self.data_path = Path(data_dir) / "calibration_state.json"
        else:
            self.data_path = BMAMPaths.CALIBRATION_STATE

        # 尝试加载历史校准数据
        self._load_calibration()

    def _init_region_states(self):
        """初始化所有脑区的校准状态"""
        regions = [
            'hippocampus',      # 海马体 - 情节记忆
            'temporal_lobe',    # 颞叶 - 语义记忆
            'prefrontal',       # 前额叶 - 工作记忆
            'amygdala',         # 杏仁核 - 情绪记忆
            'basal_ganglia'     # 基底神经节 - 程序性记忆
        ]

        for region in regions:
            if region not in self.region_states:
                self.region_states[region] = RegionCalibrationState(
                    region_name=region,
                    calibration_factor=self.config['initial_factor']
                )

    def calibrate_scores(
        self,
        region_memories: Dict[str, List[Dict]],
        query: str
    ) -> Dict[str, List[Dict]]:
        """
        对多脑区检索结果进行置信度校准

        Args:
            region_memories: {region_name: [memory_dict, ...]}
            query: 原始查询（用于上下文）

        Returns:
            校准后的 region_memories，每个memory增加 calibrated_score 字段
        """
        calibrated_results = {}

        for region_name, memories in region_memories.items():
            if not memories:
                calibrated_results[region_name] = []
                continue

            # 获取该脑区的校准因子
            state = self.region_states.get(region_name)
            if not state:
                state = RegionCalibrationState(
                    region_name=region_name,
                    calibration_factor=self.config['initial_factor']
                )
                self.region_states[region_name] = state

            calibration_factor = state.calibration_factor

            # 对每个记忆应用校准
            calibrated_memories = []
            for mem in memories:
                mem_copy = mem.copy() if isinstance(mem, dict) else vars(mem).copy()

                # 获取原始分数
                raw_score = self._extract_score(mem_copy)

                # 应用校准
                calibrated_score = raw_score * calibration_factor

                # 确保在有效范围内
                calibrated_score = max(0.0, min(1.0, calibrated_score))

                # 添加校准信息
                mem_copy['_calibration'] = {
                    'raw_score': raw_score,
                    'calibrated_score': calibrated_score,
                    'calibration_factor': calibration_factor,
                    'region': region_name
                }
                mem_copy['calibrated_score'] = calibrated_score

                calibrated_memories.append(mem_copy)

            calibrated_results[region_name] = calibrated_memories

            # 更新该脑区的统计
            state.total_queries += 1
            if memories:
                avg_raw = sum(self._extract_score(m) for m in memories) / len(memories)
                # EMA更新平均分
                alpha = self.config['ema_alpha']
                state.avg_raw_score = alpha * avg_raw + (1 - alpha) * state.avg_raw_score

        logger.debug(f"📊 Calibrated {sum(len(m) for m in calibrated_results.values())} memories from {len(calibrated_results)} regions")

        return calibrated_results

    def record_outcome(
        self,
        region_name: str,
        query: str,
        memories_used: List[Dict],
        success: bool,
        feedback_score: Optional[float] = None
    ) -> None:
        """
        记录检索结果用于学习校准

        Args:
            region_name: 脑区名称
            query: 查询
            memories_used: 使用的记忆列表
            success: 是否成功（答案正确）
            feedback_score: 可选的反馈分数 (0-1)
        """
        state = self.region_states.get(region_name)
        if not state:
            logger.warning(f"Unknown region: {region_name}")
            return

        # 更新成功/失败计数
        if success:
            state.success_count += 1
        else:
            state.failure_count += 1

        # 记录到历史
        state.outcome_history.append(success)
        if len(state.outcome_history) > 100:  # 限制历史长度
            state.outcome_history = state.outcome_history[-100:]

        # 只有足够样本时才更新校准因子
        total_samples = state.success_count + state.failure_count
        if total_samples >= self.config['min_samples_for_calibration']:
            self._update_calibration_factor(state, success, feedback_score)

        state.last_updated = datetime.now().isoformat()

        logger.debug(f"📈 Recorded outcome for {region_name}: success={success}, "
                    f"factor={state.calibration_factor:.3f}")

    def _update_calibration_factor(
        self,
        state: RegionCalibrationState,
        success: bool,
        feedback_score: Optional[float] = None
    ) -> None:
        """
        更新校准因子

        基于强化学习思想:
        - 成功时提升该脑区的可信度
        - 失败时降低该脑区的可信度
        """
        learning_rate = self.config['learning_rate']

        if success:
            # 成功: 提升校准因子
            boost = self.config['success_boost']
            if feedback_score is not None:
                boost *= feedback_score  # 根据反馈分数调整
            delta = boost * learning_rate
        else:
            # 失败: 降低校准因子
            penalty = self.config['failure_penalty']
            if feedback_score is not None:
                penalty *= (1.0 - feedback_score)  # 根据反馈分数调整
            delta = -penalty * learning_rate

        # 更新因子
        old_factor = state.calibration_factor
        new_factor = old_factor + delta

        # 限制在有效范围
        new_factor = max(self.config['min_factor'],
                        min(self.config['max_factor'], new_factor))

        state.calibration_factor = new_factor

        if abs(new_factor - old_factor) > 0.01:
            logger.info(f"📊 Calibration factor updated: {state.region_name} "
                       f"{old_factor:.3f} → {new_factor:.3f}")

    def get_calibration_stats(self) -> Dict[str, Any]:
        """获取所有脑区的校准统计"""
        stats = {
            'regions': {},
            'summary': {}
        }

        for region_name, state in self.region_states.items():
            stats['regions'][region_name] = state.to_dict()

        # 汇总统计
        total_queries = sum(s.total_queries for s in self.region_states.values())
        total_success = sum(s.success_count for s in self.region_states.values())
        total_failure = sum(s.failure_count for s in self.region_states.values())

        stats['summary'] = {
            'total_queries': total_queries,
            'total_success': total_success,
            'total_failure': total_failure,
            'overall_success_rate': total_success / (total_success + total_failure) if (total_success + total_failure) > 0 else 0.5
        }

        return stats

    def get_region_factor(self, region_name: str) -> float:
        """获取指定脑区的校准因子"""
        state = self.region_states.get(region_name)
        if state:
            return state.calibration_factor
        return self.config['initial_factor']

    def _extract_score(self, memory: Dict) -> float:
        """从记忆中提取分数"""
        score_keys = ['score', 'relevance', 'importance', 'similarity', 'resonance_score']
        for key in score_keys:
            if key in memory:
                val = memory[key]
                if isinstance(val, (int, float)):
                    return float(val)
        return 0.5  # 默认中等分数

    def _load_calibration(self) -> bool:
        """从文件加载校准状态"""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for region_name, state_dict in data.get('regions', {}).items():
                    if region_name in self.region_states:
                        state = self.region_states[region_name]
                        state.calibration_factor = state_dict.get('calibration_factor', 1.0)
                        state.success_count = state_dict.get('success_count', 0)
                        state.failure_count = state_dict.get('failure_count', 0)
                        state.total_queries = state_dict.get('total_queries', 0)
                        state.avg_raw_score = state_dict.get('avg_raw_score', 0.5)
                        state.last_updated = state_dict.get('last_updated', '')

                logger.info(f"📂 Loaded calibration state from {self.data_path}")
                return True
        except Exception as e:
            logger.warning(f"Failed to load calibration state: {e}")
        return False

    def save_calibration(self) -> bool:
        """保存校准状态到文件"""
        try:
            self.data_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'regions': {name: state.to_dict() for name, state in self.region_states.items()},
                'saved_at': datetime.now().isoformat(),
                'config': self.config
            }

            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Saved calibration state to {self.data_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save calibration state: {e}")
            return False


# 全局单例
_calibrator_instance: Optional[ConfidenceCalibrator] = None


def get_confidence_calibrator(data_dir: Optional[str] = None) -> ConfidenceCalibrator:
    """获取全局校准器实例"""
    global _calibrator_instance
    if _calibrator_instance is None:
        _calibrator_instance = ConfidenceCalibrator(data_dir)
    return _calibrator_instance
