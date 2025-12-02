"""
Habit Learner - 习惯学习器
对应脑区: 基底节 (Basal Ganglia)

功能:
1. 策略评分: 记录策略的成功率
2. 强化学习: 根据反馈更新策略分数
3. 习惯推荐: 推荐高分策略
"""

import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class HabitLearner:
    """
    习惯学习器
    
    基于简单的强化学习维护策略分数
    """
    
    def __init__(self, persistence_path: Optional[str] = "data/habits.json"):
        self.persistence_path = Path(persistence_path) if persistence_path else None
        
        # 策略分数: {context_key: {strategy_id: score}}
        self.policy_scores: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        
        # 策略使用次数: {context_key: {strategy_id: count}}
        self.policy_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        self._load_state()
        
    def update_policy(self, context: str, strategy_id: str, reward: float):
        """
        更新策略分数 (强化/惩罚)
        
        Args:
            context: 上下文标识 (如 "search_failure", "user_correction")
            strategy_id: 策略ID (如 "expand_query", "ask_clarification")
            reward: 奖励值 (-1.0 to 1.0)
        """
        current_score = self.policy_scores[context][strategy_id]
        count = self.policy_counts[context][strategy_id]
        
        # 增量平均更新
        # NewScore = OldScore + alpha * (Reward - OldScore)
        alpha = 0.1  # 学习率
        new_score = current_score + alpha * (reward - current_score)
        
        self.policy_scores[context][strategy_id] = new_score
        self.policy_counts[context][strategy_id] = count + 1
        
        logger.debug(f"Updated policy {strategy_id} in {context}: {current_score:.2f} -> {new_score:.2f} (reward={reward})")
        
        self._save_state()
        
    def recommend_strategy(self, context: str, available_strategies: List[str]) -> Optional[str]:
        """
        推荐最佳策略
        
        Args:
            context: 上下文
            available_strategies: 可选策略列表
            
        Returns:
            推荐的策略ID
        """
        if not available_strategies:
            return None
            
        scores = self.policy_scores[context]
        
        # 探索与利用 (Epsilon-Greedy)
        # 这里简化为直接选最高分，但在分数接近时随机
        
        best_strategy = max(available_strategies, key=lambda s: scores.get(s, 0.0))
        best_score = scores.get(best_strategy, 0.0)
        
        if best_score < -0.5:
            # 如果最佳策略也是负分，可能需要尝试新策略或随机
            return None
            
        return best_strategy
        
    def get_policy_stats(self) -> Dict[str, Any]:
        """获取策略统计"""
        return {
            "contexts": len(self.policy_scores),
            "total_updates": sum(sum(c.values()) for c in self.policy_counts.values())
        }
        
    def _save_state(self):
        """保存状态"""
        if not self.persistence_path:
            return
            
        try:
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                "scores": {k: dict(v) for k, v in self.policy_scores.items()},
                "counts": {k: dict(v) for k, v in self.policy_counts.items()}
            }
            with open(self.persistence_path, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save habit state: {e}")
            
    def _load_state(self):
        """加载状态"""
        if not self.persistence_path or not self.persistence_path.exists():
            return
            
        try:
            with open(self.persistence_path, 'r') as f:
                state = json.load(f)
                
            self.policy_scores = defaultdict(lambda: defaultdict(float), {
                k: defaultdict(float, v) for k, v in state.get("scores", {}).items()
            })
            self.policy_counts = defaultdict(lambda: defaultdict(int), {
                k: defaultdict(int, v) for k, v in state.get("counts", {}).items()
            })
        except Exception as e:
            logger.error(f"Failed to load habit state: {e}")
