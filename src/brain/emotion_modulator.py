"""
Emotion Modulator - 情感调制器
对应脑区: 杏仁核 (Amygdala)

功能:
1. 情感加权: 根据情绪强度调整记忆重要性
2. 检索调制: 高情绪记忆优先检索
3. 遗忘保护: 高情绪记忆更难遗忘
4. 🔥 2025-12-16: 情绪一致性效应 (Mood Congruency) - 悲伤时更易想起悲伤的事
"""

import logging
from typing import Dict, List, Any, Optional
import math

logger = logging.getLogger(__name__)

# 🔥 2025-12-16: 情绪类别及其向量表示 (用于计算情绪相似度)
# 基于 Russell's Circumplex Model: Valence (效价) x Arousal (唤醒度)
EMOTION_VECTORS = {
    # 高唤醒-正效价
    'excited': (0.8, 0.9),
    'happy': (0.7, 0.6),
    'joyful': (0.8, 0.7),
    'surprised': (0.3, 0.8),
    'curious': (0.4, 0.6),

    # 高唤醒-负效价
    'angry': (-0.7, 0.8),
    'anxious': (-0.5, 0.7),
    'fearful': (-0.6, 0.8),
    'stressed': (-0.4, 0.6),
    'frustrated': (-0.5, 0.6),

    # 低唤醒-正效价
    'calm': (0.3, -0.3),
    'relaxed': (0.4, -0.4),
    'content': (0.5, -0.2),
    'peaceful': (0.4, -0.5),

    # 低唤醒-负效价
    'sad': (-0.6, -0.4),
    'depressed': (-0.7, -0.5),
    'bored': (-0.2, -0.6),
    'tired': (-0.3, -0.7),
    'lonely': (-0.5, -0.3),

    # 中性
    'neutral': (0.0, 0.0),
}

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
        
    def modulate_retrieval_score(
        self,
        base_score: float,
        emotion_intensity: float,
        current_mood: Optional[str] = None,
        memory_emotion: Optional[str] = None
    ) -> float:
        """
        根据情绪强度调整检索分数

        Args:
            base_score: 基础检索分数
            emotion_intensity: 记忆的情绪强度
            current_mood: 当前系统情绪 (用于情绪一致性效应)
            memory_emotion: 记忆的情绪类型 (用于情绪一致性效应)

        Returns:
            调整后的分数
        """
        # 1. 情绪显著性效应: 高情绪记忆更容易被检索
        salience_boost = emotion_intensity * 0.2

        # 2. 🔥 2025-12-16: 情绪一致性效应 (Mood Congruency)
        # 当前情绪与记忆情绪一致时，检索增强 - "悲伤时更易想起悲伤的事"
        congruency_boost = self._calculate_mood_congruency(current_mood, memory_emotion)

        return base_score * (1.0 + salience_boost + congruency_boost)

    def _calculate_mood_congruency(
        self,
        current_mood: Optional[str],
        memory_emotion: Optional[str]
    ) -> float:
        """
        🔥 2025-12-16: 计算情绪一致性增益

        基于 Russell's Circumplex Model，计算当前情绪与记忆情绪在
        Valence-Arousal 空间中的相似度

        Args:
            current_mood: 当前系统情绪
            memory_emotion: 记忆的情绪类型

        Returns:
            一致性增益 (0.0 - 0.3)
        """
        if not current_mood or not memory_emotion:
            return 0.0

        # 标准化情绪名称
        current_mood = current_mood.lower().strip()
        memory_emotion = memory_emotion.lower().strip()

        # 获取情绪向量
        current_vec = EMOTION_VECTORS.get(current_mood)
        memory_vec = EMOTION_VECTORS.get(memory_emotion)

        if not current_vec or not memory_vec:
            # 未知情绪，尝试模糊匹配
            current_vec = self._fuzzy_match_emotion(current_mood)
            memory_vec = self._fuzzy_match_emotion(memory_emotion)

        if not current_vec or not memory_vec:
            return 0.0

        # 计算余弦相似度 (在 Valence-Arousal 空间)
        dot_product = current_vec[0] * memory_vec[0] + current_vec[1] * memory_vec[1]
        norm_current = math.sqrt(current_vec[0]**2 + current_vec[1]**2)
        norm_memory = math.sqrt(memory_vec[0]**2 + memory_vec[1]**2)

        if norm_current == 0 or norm_memory == 0:
            return 0.0

        similarity = dot_product / (norm_current * norm_memory)

        # 将相似度 (-1 to 1) 映射到增益 (0 to 0.3)
        # 只有正相似度才产生增益
        if similarity > 0:
            congruency_boost = similarity * 0.3
            logger.debug(f"Mood congruency: {current_mood} ↔ {memory_emotion} = +{congruency_boost:.2f}")
            return congruency_boost

        return 0.0

    def _fuzzy_match_emotion(self, emotion: str) -> Optional[tuple]:
        """模糊匹配情绪到最接近的已知类别"""
        # 简单的关键词匹配
        emotion_keywords = {
            'happy': ['happy', 'joy', 'glad', 'pleased', 'delighted'],
            'sad': ['sad', 'unhappy', 'sorrowful', 'melancholy', 'down'],
            'angry': ['angry', 'mad', 'furious', 'irritated', 'annoyed'],
            'anxious': ['anxious', 'worried', 'nervous', 'uneasy'],
            'excited': ['excited', 'thrilled', 'enthusiastic', 'eager'],
            'calm': ['calm', 'serene', 'tranquil', 'composed'],
            'fearful': ['fear', 'afraid', 'scared', 'terrified'],
            'surprised': ['surprised', 'shocked', 'amazed', 'astonished'],
        }

        for base_emotion, keywords in emotion_keywords.items():
            if any(kw in emotion for kw in keywords):
                return EMOTION_VECTORS.get(base_emotion)

        return None
        
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
