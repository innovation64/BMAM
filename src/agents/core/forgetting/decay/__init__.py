"""
Decay Module
衰减模块

Combines passive decay and Ebbinghaus forgetting curve functionality.
结合被动衰减和艾宾浩斯遗忘曲线功能。

Module structure:
- passive_decay.py: Passive decay implementation
- ebbinghaus.py: Ebbinghaus forgetting curve
"""

from .passive_decay import PassiveDecayMixin
from .ebbinghaus import EbbinghausMixin


class DecayMixin(PassiveDecayMixin, EbbinghausMixin):
    """
    Decay Mixin - combines all decay functionality
    衰减混入类 - 结合所有衰减功能

    Inherits from:
    - PassiveDecayMixin: Passive decay based on time elapsed
    - EbbinghausMixin: Ebbinghaus forgetting curve
    """
    pass


__all__ = [
    'DecayMixin',
    'PassiveDecayMixin',
    'EbbinghausMixin',
]
