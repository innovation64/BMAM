"""
Prefrontal Agent Package
前额叶智能体包 - 工作记忆与执行控制

Directory Structure:
- data_models.py: Data models (WorkingMemoryItem)
- core_operations.py: Core operations (store, retrieve, clear, capacity, item_to_dict)
- task_coordination.py: Task coordination (coordinate_task, reflect, get_status, get_statistics)
- confidence_assessment.py: Confidence assessment (assess_confidence + 5 helpers)
- conflict_detection.py: Conflict detection (detect_conflicts + 5 helpers)
- memory_compression.py: Memory compression (compress + 3 helpers)
- prefrontal_agent.py: Main agent class
"""

from .data_models import WorkingMemoryItem
from .prefrontal_agent import PrefrontalAgent

__all__ = ['PrefrontalAgent', 'WorkingMemoryItem']
