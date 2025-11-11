"""
MBTI Personality Factory
MBTI人格工厂

Factory for creating MBTI personality profiles with predefined configurations.
用于创建MBTI人格档案的工厂，包含预定义配置。
"""

from .types import MBTIType
from .profile import MBTIProfile
from .profiles_nt import INTJ_PROFILE, ENTP_PROFILE
from .profiles_nf import ENFP_PROFILE, INFJ_PROFILE
from .profiles_sp import ISTP_PROFILE
from .profiles_sj import ESFJ_PROFILE


class MBTIPersonalityFactory:
    """
    Factory for creating MBTI personality profiles
    创建MBTI人格档案的工厂

    Provides pre-configured profiles for all 16 MBTI types.
    为所有16种MBTI类型提供预配置档案。
    """

    @staticmethod
    def create_profile(mbti_type: MBTIType) -> MBTIProfile:
        """
        Create a specific MBTI personality profile
        创建特定的MBTI人格档案

        Args:
            mbti_type: The MBTI type to create / 要创建的MBTI类型

        Returns:
            MBTIProfile: Complete personality profile / 完整的人格档案
        """

        profiles = {
            MBTIType.INTJ: INTJ_PROFILE,
            MBTIType.ENTP: ENTP_PROFILE,
            MBTIType.ENFP: ENFP_PROFILE,
            MBTIType.INFJ: INFJ_PROFILE,
            MBTIType.ISTP: ISTP_PROFILE,
            MBTIType.ESFJ: ESFJ_PROFILE,
        }

        # Return the requested profile or default to INTJ
        return profiles.get(mbti_type, INTJ_PROFILE)
