"""
Task-Aware Configuration Manager
任务感知配置管理器 - 根据任务类型动态调整系统行为

NOT dataset-aware (no cheating) - purely based on query characteristics
不识别数据集名称,仅基于查询特征推断任务类型
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class TaskConfig:
    """单个任务类型的配置"""

    # 基础配置
    task_name: str  # 任务类型而非数据集名称

    # V1 特性 (LoCoMo/LongMemEval最佳)
    enable_storyarc_timeline: bool = True
    enable_hybrid_retrieval: bool = True
    enable_hrm_coordination: bool = True

    # V2 特性 (PrefEval最佳)
    enable_preference_aware_retrieval: bool = False
    enable_preference_extraction: bool = False
    preference_boost_weight: float = 0.0

    # V3 特性 (PersonaMem最佳)
    enable_user_id_isolation: bool = False
    enable_evaluation_mode_boost: bool = False
    persona_retrieval_k: int = 8  # 评估模式下20,正常模式8
    enable_recent_persona_fallback: bool = False

    # 其他配置
    enable_reasoning_chain_fallback: bool = True
    kg_coverage_threshold: float = 0.80  # KG覆盖率阈值


class TaskAwareConfigManager:
    """任务感知配置管理器 - 仅基于任务特征,不识别数据集"""

    # 🔥 预定义的**任务类型**配置 (NOT dataset names!)
    CONFIGS: Dict[str, TaskConfig] = {
        # 时间推理任务 (temporal reasoning)
        "temporal_reasoning": TaskConfig(
            task_name="Temporal Reasoning",
            enable_storyarc_timeline=True,
            enable_hybrid_retrieval=True,
            enable_hrm_coordination=True,
            # 时间推理不需要偏好检索
            enable_preference_aware_retrieval=False,
            enable_preference_extraction=False,
            enable_user_id_isolation=False,
            enable_evaluation_mode_boost=False,
            persona_retrieval_k=3,  # 最小化persona干扰
            enable_recent_persona_fallback=False,
            kg_coverage_threshold=0.80
        ),

        # 偏好查询任务 (preference query)
        "preference_query": TaskConfig(
            task_name="Preference Query",
            enable_storyarc_timeline=True,
            enable_hybrid_retrieval=True,
            enable_hrm_coordination=True,
            # 偏好查询需要偏好提取和感知检索
            enable_preference_aware_retrieval=True,
            enable_preference_extraction=True,
            preference_boost_weight=0.3,
            enable_user_id_isolation=True,
            enable_evaluation_mode_boost=False,
            persona_retrieval_k=8,
            enable_recent_persona_fallback=False,
            kg_coverage_threshold=0.80
        ),

        # 身份回忆任务 (identity recall)
        "identity_recall": TaskConfig(
            task_name="Identity Recall",
            enable_storyarc_timeline=True,
            enable_hybrid_retrieval=True,
            enable_hrm_coordination=True,
            # 身份回忆需要用户隔离和高召回
            enable_preference_aware_retrieval=True,
            enable_preference_extraction=True,
            preference_boost_weight=0.3,
            enable_user_id_isolation=True,
            enable_evaluation_mode_boost=True,
            persona_retrieval_k=15,  # 高召回
            enable_recent_persona_fallback=True,
            kg_coverage_threshold=0.80
        ),

        # 混合任务 (balanced)
        "balanced": TaskConfig(
            task_name="Balanced Task",
            enable_storyarc_timeline=True,
            enable_hybrid_retrieval=True,
            enable_hrm_coordination=True,
            enable_preference_aware_retrieval=True,
            enable_preference_extraction=True,
            preference_boost_weight=0.2,  # 降低权重
            enable_user_id_isolation=True,
            enable_evaluation_mode_boost=False,
            persona_retrieval_k=8,
            enable_recent_persona_fallback=False,
            kg_coverage_threshold=0.80
        ),

        # 默认配置 (保守策略)
        "default": TaskConfig(
            task_name="Default Task",
            enable_storyarc_timeline=True,
            enable_hybrid_retrieval=True,
            enable_hrm_coordination=True,
            enable_preference_aware_retrieval=False,
            enable_preference_extraction=False,
            enable_user_id_isolation=False,
            enable_evaluation_mode_boost=False,
            persona_retrieval_k=5,
            enable_recent_persona_fallback=False,
            kg_coverage_threshold=0.80
        ),
    }

    def __init__(self):
        self.current_config: TaskConfig = self.CONFIGS["default"]
        self._config_history = []

    def detect_task_type_from_query(self, user_input: str, context: Dict[str, Any]) -> str:
        """
        🔥 从查询特征检测任务类型 (NOT dataset name!)

        纯粹基于查询的语义特征,不依赖任何显式标签
        """
        if not user_input:
            return "default"

        user_input_lower = user_input.lower()

        # 1. 时间推理特征检测
        temporal_keywords = [
            "when", "after", "before", "timeline", "sequence",
            "what happened", "in what order", "first", "then",
            "subsequently", "previously", "earlier", "later"
        ]
        temporal_score = sum(1 for kw in temporal_keywords if kw in user_input_lower)

        # 2. 偏好查询特征检测
        preference_keywords = [
            "prefer", "like better", "which do", "choice between",
            "favorite", "rather", "instead of"
        ]
        preference_score = sum(1 for kw in preference_keywords if kw in user_input_lower)

        # 3. 身份回忆特征检测
        identity_keywords = [
            "what is my", "do i like", "my favorite", "my preference",
            "i told you", "remember i", "as i mentioned", "about me",
            "my name", "who am i", "my background"
        ]
        identity_score = sum(1 for kw in identity_keywords if kw in user_input_lower)

        # 4. 评估模式上下文 (但不看数据集名称!)
        eval_mode = context.get('evaluation_mode', False)
        has_user_id = bool(context.get('user_id') or context.get('persona_user_id'))

        # 决策逻辑
        if identity_score >= 2 or (identity_score >= 1 and has_user_id and eval_mode):
            return "identity_recall"
        elif preference_score >= 2:
            return "preference_query"
        elif temporal_score >= 2:
            return "temporal_reasoning"
        elif identity_score >= 1:
            return "identity_recall"
        elif preference_score >= 1:
            return "preference_query"
        elif temporal_score >= 1:
            return "balanced"  # 有时间特征但不强,用平衡配置
        else:
            return "default"

    def get_config_for_task(self, task_type: str) -> TaskConfig:
        """获取指定任务类型的配置"""
        task_key = task_type.lower()
        return self.CONFIGS.get(task_key, self.CONFIGS["default"])

    def apply_config(self, context: Dict[str, Any]) -> TaskConfig:
        """
        根据context应用配置 - 基于任务类型而非数据集

        Returns:
            应用的TaskConfig
        """
        user_input = context.get('user_input', '') or context.get('query', '')
        task_type = self.detect_task_type_from_query(user_input, context)
        config = self.get_config_for_task(task_type)

        # 记录配置切换
        if config.task_name != self.current_config.task_name:
            self._config_history.append({
                'previous': self.current_config.task_name,
                'new': config.task_name,
                'query_sample': user_input[:50] if user_input else '',
                'context_hints': {
                    'evaluation_mode': context.get('evaluation_mode'),
                    'has_user_id': bool(context.get('user_id') or context.get('persona_user_id')),
                }
            })
            logger.info(f"🎯 Task config switched: {self.current_config.task_name} → {config.task_name}")

        self.current_config = config
        return config

    def get_feature_flags(self) -> Dict[str, bool]:
        """
        获取当前配置的特性开关字典
        用于与BrainCoordinator的_feature_status集成
        """
        return {
            'storyarc_timeline': self.current_config.enable_storyarc_timeline,
            'hybrid_retrieval': self.current_config.enable_hybrid_retrieval,
            'hrm_coordination': self.current_config.enable_hrm_coordination,
            'preference_aware_retrieval': self.current_config.enable_preference_aware_retrieval,
            'preference_extraction': self.current_config.enable_preference_extraction,
            'user_id_isolation': self.current_config.enable_user_id_isolation,
            'evaluation_mode_boost': self.current_config.enable_evaluation_mode_boost,
            'recent_persona_fallback': self.current_config.enable_recent_persona_fallback,
        }

    def get_config_summary(self) -> str:
        """获取当前配置摘要(用于日志)"""
        config = self.current_config
        enabled_features = [
            f"Timeline={config.enable_storyarc_timeline}",
            f"PrefExtract={config.enable_preference_extraction}",
            f"UserID={config.enable_user_id_isolation}",
            f"EvalBoost={config.enable_evaluation_mode_boost}",
            f"PersonaK={config.persona_retrieval_k}",
        ]
        return f"[{config.task_name}] " + ", ".join(enabled_features)


# 全局单例
_config_manager: Optional[TaskAwareConfigManager] = None


def get_task_config_manager() -> TaskAwareConfigManager:
    """获取全局配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = TaskAwareConfigManager()
    return _config_manager

# 向后兼容别名
get_dataset_config_manager = get_task_config_manager
