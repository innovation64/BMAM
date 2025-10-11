"""
Personality Version Manager
人格版本管理器 - 用于A/B测试和版本切换
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PersonalityVersionManager:
    """管理PersonalityAgent版本切换"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/personality_version.json")
        self.config = self._load_config()

        # 实验统计
        self.experiment_stats = {
            'original': {
                'total_responses': 0,
                'avg_response_time': 0.0,
                'user_ratings': []
            },
            'mbti': {
                'total_responses': 0,
                'avg_response_time': 0.0,
                'user_ratings': []
            }
        }

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                logger.info(f"Loaded personality version config: {config['version']}")
                return config
            else:
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                return {
                    'version': 'original',
                    'experiment_settings': {'enable_logging': True}
                }
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {'version': 'original', 'experiment_settings': {}}

    def get_current_version(self) -> str:
        """获取当前版本"""
        return self.config.get('version', 'original')

    def set_version(self, version: str) -> Tuple[bool, str]:
        """切换版本"""
        valid_versions = ['original', 'mbti']

        if version not in valid_versions:
            return False, f"Invalid version: {version}. Must be one of {valid_versions}"

        self.config['version'] = version
        self._save_config()

        logger.info(f"Switched personality version to: {version}")
        return True, f"Successfully switched to {version} version"

    def _save_config(self):
        """保存配置文件"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved personality version config")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def create_personality_agent(self, **kwargs):
        """根据当前版本创建PersonalityAgent"""
        version = self.get_current_version()

        if version == 'mbti':
            return self._create_mbti_agent(**kwargs)
        else:
            return self._create_original_agent(**kwargs)

    def _create_original_agent(self, **kwargs):
        """创建原始PersonalityAgent"""
        from ..agents.core.personality import PersonalityAgent

        agent = PersonalityAgent(
            client=kwargs.get('client'),
            llm_service=kwargs.get('llm_service'),
            persona_memory_agent=kwargs.get('persona_memory_agent')
        )

        logger.info("Created original PersonalityAgent (摇光明明)")
        return agent

    def _create_mbti_agent(self, **kwargs):
        """创建MBTI集成的PersonalityAgent"""
        from ..agents.core.mbti_integration import MBTIIntegratedPersonalityAgent

        agent = MBTIIntegratedPersonalityAgent(
            client=kwargs.get('client'),
            llm_service=kwargs.get('llm_service'),
            persona_memory_agent=kwargs.get('persona_memory_agent'),
            config_path=Path("config/mbti_personality.json"),
            name=kwargs.get('name', '摇光明明')
        )

        logger.info(f"Created MBTI PersonalityAgent (default: {agent.config_manager.config.current_personality})")
        return agent

    def record_response(self, version: str, response_time: float, quality_score: Optional[float] = None):
        """记录响应数据用于对比"""
        if not self.config.get('experiment_settings', {}).get('enable_logging', False):
            return

        if version in self.experiment_stats:
            stats = self.experiment_stats[version]
            stats['total_responses'] += 1

            # 更新平均响应时间
            n = stats['total_responses']
            stats['avg_response_time'] = (
                stats['avg_response_time'] * (n - 1) + response_time
            ) / n

            # 记录质量评分
            if quality_score is not None:
                stats['user_ratings'].append(quality_score)

    def get_experiment_report(self) -> Dict[str, Any]:
        """生成实验对比报告"""
        report = {
            'current_version': self.get_current_version(),
            'timestamp': datetime.now().isoformat(),
            'comparison': {}
        }

        for version, stats in self.experiment_stats.items():
            if stats['total_responses'] > 0:
                avg_rating = (
                    sum(stats['user_ratings']) / len(stats['user_ratings'])
                    if stats['user_ratings'] else None
                )

                report['comparison'][version] = {
                    'total_responses': stats['total_responses'],
                    'avg_response_time': f"{stats['avg_response_time']:.3f}s",
                    'avg_user_rating': f"{avg_rating:.2f}" if avg_rating else "N/A",
                    'rating_count': len(stats['user_ratings'])
                }

        return report

    def get_version_info(self) -> Dict[str, Any]:
        """获取版本详细信息"""
        current_version = self.get_current_version()
        available = self.config.get('available_versions', {})

        return {
            'current': current_version,
            'current_details': available.get(current_version, {}),
            'available_versions': available,
            'experiment_enabled': self.config.get('experiment_settings', {}).get('enable_logging', False)
        }


# 全局实例
_version_manager = None

def get_version_manager() -> PersonalityVersionManager:
    """获取全局版本管理器实例"""
    global _version_manager
    if _version_manager is None:
        _version_manager = PersonalityVersionManager()
    return _version_manager