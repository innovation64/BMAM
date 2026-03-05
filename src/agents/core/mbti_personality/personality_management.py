"""
Personality Management
人格管理

Mixin for switching personalities and getting personality information.
用于切换人格和获取人格信息的混入类。
"""

import logging
from typing import Dict, Any

from .types import MBTIType
from .factory import MBTIPersonalityFactory

logger = logging.getLogger(__name__)


class PersonalityManagementMixin:
    """
    Mixin for personality management operations
    人格管理操作混入类

    Handles personality switching and information retrieval.
    处理人格切换和信息检索。
    """

    async def _switch_personality(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Switch to a different MBTI personality type
        切换到不同的MBTI人格类型

        Args:
            content: Request content with new_type / 包含new_type的请求内容

        Returns:
            Dict containing switch results / 包含切换结果的字典
        """

        new_type_str = content.get('new_type', '')

        try:
            new_type = MBTIType[new_type_str.upper()]
            old_type = self.profile.mbti_type

            # Create new profile
            self.profile = MBTIPersonalityFactory.create_profile(new_type)

            # Update system prompt
            self.system_prompt = self._build_mbti_system_prompt()

            # Reset cognitive function usage
            self.cognitive_function_usage = {
                self.profile.dominant: 0.4,
                self.profile.auxiliary: 0.3,
                self.profile.tertiary: 0.2,
                self.profile.inferior: 0.1
            }

            return {
                'success': True,
                'old_type': old_type.value,
                'new_type': new_type.value,
                'description': self.profile.description,
                'message': f'Personality switched from {old_type.value} to {new_type.value}'
            }

        except KeyError:
            return {
                'success': False,
                'error': f'Invalid MBTI type: {new_type_str}',
                'valid_types': [t.value for t in MBTIType]
            }

    def _get_personality_info(self) -> Dict[str, Any]:
        """
        Get current personality information
        获取当前人格信息

        Returns:
            Dict containing personality info / 包含人格信息的字典
        """

        return {
            'mbti_type': self.profile.mbti_type.value,
            'title': self.profile.title,
            'description': self.profile.description,
            'cognitive_functions': {
                'dominant': self.profile.dominant.value,
                'auxiliary': self.profile.auxiliary.value,
                'tertiary': self.profile.tertiary.value,
                'inferior': self.profile.inferior.value
            },
            'cognitive_function_usage': {
                func.value: usage for func, usage in self.cognitive_function_usage.items()
            },
            'top_traits': dict(sorted(self.profile.traits.items(), key=lambda x: x[1], reverse=True)[:5]),
            'communication_style': self.profile.communication_style,
            'strengths': self.profile.strengths,
            'weaknesses': self.profile.weaknesses,
            'core_values': self.profile.core_values,
            'interaction_count': len(self.interaction_history)
        }
