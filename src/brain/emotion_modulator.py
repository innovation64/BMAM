"""
Emotion Modulator - 情感调制器
对应脑区: 杏仁核 (Amygdala)

功能:
1. 情感加权: 根据情绪强度调整记忆重要性
2. 检索调制: 高情绪记忆优先检索
3. 遗忘保护: 高情绪记忆更难遗忘
"""

import logging
from typing import Dict, List, Any, Optional
import math

logger = logging.getLogger(__name__)

class EmotionModulator:
    """
    情感调制器
    
    负责计算情绪对记忆和检索的影响
    """
    
    def __init__(self, base_weight: float = 1.0):
        self.base_weight = base_weight
        
    def modulate_importance(self, base_importance: float, emotion_intensity: float) -> float:
        """
        根据情绪强度调整记忆重要性
        
        Args:
            base_importance: 基础重要性 (0.0-1.0)
            emotion_intensity: 情绪强度 (0.0-1.0)
            
        Returns:
            调整后的重要性
        """
        # 情绪增强效应: 情绪越强，重要性越高
        # 公式: importance = base + (1 - base) * intensity * 0.5
        boost = (1.0 - base_importance) * emotion_intensity * 0.5
        return min(1.0, base_importance + boost)
        
    def modulate_retrieval_score(self, base_score: float, emotion_intensity: float, current_mood: Optional[str] = None) -> float:
        """
        根据情绪强度调整检索分数
        
        Args:
            base_score: 基础检索分数
            emotion_intensity: 记忆的情绪强度
            current_mood: 当前系统情绪 (用于情绪一致性效应)
            
        Returns:
            调整后的分数
        """
        # 1. 情绪显著性效应: 高情绪记忆更容易被检索
        salience_boost = emotion_intensity * 0.2
        
        # 2. 情绪一致性效应 (Mood Congruency): 当前情绪与记忆情绪一致时，检索增强
        # TODO: 需要更复杂的情绪匹配逻辑，这里简化处理
        congruency_boost = 0.0
        
        return base_score * (1.0 + salience_boost + congruency_boost)
        
    def calculate_forgetting_threshold(self, base_threshold: float, emotion_intensity: float) -> float:
        """
        计算遗忘阈值
        
        高情绪记忆的遗忘阈值更低 (更难被遗忘)
        
        Args:
            base_threshold: 基础遗忘阈值
            emotion_intensity: 情绪强度
            
        Returns:
            调整后的阈值
        """
        # 情绪保护效应: 强度越高，阈值越低
        protection = emotion_intensity * 0.3
        return max(0.1, base_threshold - protection)
