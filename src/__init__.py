"""
MA-CMM Source Package
"""

__version__ = "2.0.0"
__author__ = "MA-CMM Team"

# Import key components for easier access
from .core.ma_cmm_framework import MACMMFramework, MACMMConfig
from .optimized_answer_extraction_v8 import OptimizedFrameworkV8

__all__ = [
    'MACMMFramework',
    'MACMMConfig',
    'OptimizedFrameworkV8'
]