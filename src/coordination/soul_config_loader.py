"""
Soul Config Loader - 灵魂塑造配置加载器

通用记忆框架的可适配可扩展设计：
1. 从JSON配置文件加载情绪/技能/时间模式
2. 支持运行时注册新模式
3. 支持多语言
4. 支持插件扩展
"""

import json
import logging
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SoulConfigLoader:
    """
    灵魂配置加载器 - 可适配可扩展的核心

    使用方式：
        config = SoulConfigLoader()
        config.load()

        # 获取情绪词汇
        joy_keywords = config.get_emotion_keywords('joy')

        # 获取情绪意义
        meaning = config.get_emotion_meaning('joy')

        # 运行时扩展
        config.register_emotion_type('nostalgia', {...})
    """

    DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / 'config' / 'soul_config.json'

    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.config: Dict[str, Any] = {}
        self._loaded = False

        # 运行时扩展存储
        self._runtime_emotions: Dict[str, Dict] = {}
        self._runtime_skills: Dict[str, Dict] = {}

    def load(self) -> bool:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self._loaded = True
                logger.info(f"✅ Soul config loaded from {self.config_path}")
                return True
            else:
                logger.warning(f"⚠️ Soul config not found at {self.config_path}, using defaults")
                self._use_defaults()
                return True
        except Exception as e:
            logger.error(f"❌ Failed to load soul config: {e}")
            self._use_defaults()
            return False

    def _use_defaults(self):
        """使用默认配置"""
        self.config = {
            'emotion_lexicon': {
                'joy': {'keywords': ['happy', 'excited', 'love', 'great']},
                'sadness': {'keywords': ['sad', 'unhappy', 'miss', 'lost']},
                'anger': {'keywords': ['angry', 'mad', 'hate', 'frustrated']},
                'fear': {'keywords': ['scared', 'afraid', 'worried', 'anxious']},
                'surprise': {'keywords': ['surprised', 'amazed', 'shocked']},
                'anticipation': {'keywords': ['hope', 'expect', 'eager']}
            },
            'emotion_meanings': {
                '_default': {
                    'meaning': '情绪体验',
                    'value_signal': '自我觉察',
                    'growth_direction': '理解自己'
                }
            }
        }
        self._loaded = True

    def ensure_loaded(self):
        """确保配置已加载"""
        if not self._loaded:
            self.load()

    # ========== 情绪相关 ==========

    def get_emotion_lexicon(self) -> Dict[str, Dict]:
        """获取完整情绪词汇表"""
        self.ensure_loaded()
        lexicon = self.config.get('emotion_lexicon', {})
        # 合并运行时扩展
        lexicon.update(self._runtime_emotions)
        return lexicon

    def get_emotion_keywords(self, emotion_type: str, language: str = 'en') -> List[str]:
        """
        获取指定情绪类型的关键词

        Args:
            emotion_type: 情绪类型 (joy/sadness/anger/fear/surprise/anticipation)
            language: 语言 ('en' 或 'zh')

        Returns:
            关键词列表
        """
        self.ensure_loaded()
        lexicon = self.get_emotion_lexicon()
        emotion_config = lexicon.get(emotion_type, {})

        if language == 'zh':
            return emotion_config.get('keywords_zh', [])
        return emotion_config.get('keywords', [])

    def get_all_emotion_keywords(self, language: str = 'en') -> Dict[str, List[str]]:
        """获取所有情绪类型的关键词"""
        self.ensure_loaded()
        lexicon = self.get_emotion_lexicon()
        result = {}
        for emotion_type, config in lexicon.items():
            if emotion_type.startswith('_'):
                continue
            if language == 'zh':
                result[emotion_type] = config.get('keywords_zh', [])
            else:
                result[emotion_type] = config.get('keywords', [])
        return result

    def get_emotion_meaning(self, emotion_type: str) -> Dict[str, str]:
        """
        获取情绪的深层意义

        Returns:
            {
                'meaning': str,
                'value_signal': str,
                'growth_direction': str
            }
        """
        self.ensure_loaded()
        meanings = self.config.get('emotion_meanings', {})
        return meanings.get(emotion_type, meanings.get('_default', {}))

    def register_emotion_type(
        self,
        emotion_type: str,
        keywords: List[str],
        keywords_zh: List[str] = None,
        meaning: str = None,
        value_signal: str = None,
        growth_direction: str = None
    ):
        """
        运行时注册新的情绪类型

        Args:
            emotion_type: 情绪类型名称
            keywords: 英文关键词
            keywords_zh: 中文关键词
            meaning: 情绪意义
            value_signal: 价值信号
            growth_direction: 成长方向
        """
        self._runtime_emotions[emotion_type] = {
            'keywords': keywords,
            'keywords_zh': keywords_zh or []
        }

        if meaning:
            if 'emotion_meanings' not in self.config:
                self.config['emotion_meanings'] = {}
            self.config['emotion_meanings'][emotion_type] = {
                'meaning': meaning,
                'value_signal': value_signal or '自我觉察',
                'growth_direction': growth_direction or '理解自己'
            }

        logger.info(f"✅ Registered new emotion type: {emotion_type}")

    # ========== 技能相关 ==========

    def get_skill_markers(self) -> Dict[str, Dict]:
        """获取技能识别标记"""
        self.ensure_loaded()
        return self.config.get('skill_markers', {})

    def get_skill_keywords(self, marker_type: str, language: str = 'en') -> List[str]:
        """
        获取技能关键词

        Args:
            marker_type: 'step_keywords', 'method_keywords', 'action_verbs'
            language: 'en' 或 'zh'
        """
        markers = self.get_skill_markers()
        marker_config = markers.get(marker_type, {})
        return marker_config.get(language, [])

    def register_skill_pattern(
        self,
        pattern_name: str,
        keywords_en: List[str],
        keywords_zh: List[str] = None
    ):
        """运行时注册新的技能模式"""
        self._runtime_skills[pattern_name] = {
            'en': keywords_en,
            'zh': keywords_zh or []
        }
        logger.info(f"✅ Registered new skill pattern: {pattern_name}")

    # ========== 时间模式相关 ==========

    def get_time_patterns(self, language: str = 'en') -> List[str]:
        """获取时间表达模式（正则表达式）"""
        self.ensure_loaded()
        patterns = self.config.get('time_patterns', {})
        return patterns.get(language, [])

    # ========== 强度标记相关 ==========

    def get_intensity_boosters(self, language: str = 'en') -> List[str]:
        """获取情绪强度助词"""
        self.ensure_loaded()
        markers = self.config.get('intensity_markers', {})
        boosters = markers.get('boosters', {})
        return boosters.get(language, [])

    def get_punctuation_weights(self) -> Dict[str, float]:
        """获取标点符号权重"""
        self.ensure_loaded()
        markers = self.config.get('intensity_markers', {})
        return markers.get('punctuation_weight', {})

    # ========== 自我反思标记 ==========

    def get_self_reflection_markers(self) -> Dict[str, str]:
        """获取自我反思标记"""
        self.ensure_loaded()
        return self.config.get('self_reflection_markers', {
            'user_prefix': '',
            'assistant_prefix': '[自我觉察] ',
            'value_prefix': '[内在共鸣] ',
            'growth_prefix': '[自我成长] '
        })

    # ========== 扩展性 ==========

    def is_runtime_extension_allowed(self) -> bool:
        """检查是否允许运行时扩展"""
        self.ensure_loaded()
        ext = self.config.get('extensibility', {})
        return ext.get('allow_runtime_extension', True)

    def save_config(self, path: str = None):
        """保存配置（包括运行时扩展）"""
        save_path = Path(path) if path else self.config_path
        try:
            # 合并运行时扩展到配置
            if self._runtime_emotions:
                self.config['emotion_lexicon'].update(self._runtime_emotions)
            if self._runtime_skills:
                self.config['skill_markers'].update(self._runtime_skills)

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Soul config saved to {save_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save soul config: {e}")


# 全局单例
_soul_config: Optional[SoulConfigLoader] = None


def get_soul_config() -> SoulConfigLoader:
    """获取全局配置实例"""
    global _soul_config
    if _soul_config is None:
        _soul_config = SoulConfigLoader()
        _soul_config.load()
    return _soul_config
