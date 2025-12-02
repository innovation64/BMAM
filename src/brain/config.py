"""
Brain Configuration - Centralized Parameters for Cognitive Architecture
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional

@dataclass
class BrainConfig:
    """
    Centralized configuration for the Brain-Inspired Cognitive Architecture.
    Replaces hardcoded values to enable algorithmic constraints and dynamic tuning.
    """

    # --- Activation Dynamics ---
    activation_decay_rate: float = 0.7
    activation_input_weight: float = 0.3
    activation_threshold: float = 0.5
    
    # --- Convergence Criteria ---
    convergence_threshold: float = 0.8
    convergence_conversation_offset: float = 0.1  # conversation_threshold = convergence_threshold - offset
    max_iterations: int = 5
    spreading_step_delay: float = 0.0  # 每次扩散迭代的可调延迟(秒)，默认0避免无谓等待
    
    # --- Plasticity ---
    min_connection_weight: float = 0.1
    max_connection_weight: float = 1.0
    
    # --- Active Learning (Curiosity) ---
    active_learning_enabled: bool = True
    active_learning_threshold: float = 0.4  # Confidence below this triggers curiosity check
    curiosity_level: float = 0.7  # Probability of asking question when confidence is low
    
    # --- Default Connection Weights (Source, Target) -> Weight ---
    # Based on neuroscience principles (e.g., Anderson 1983, Rumelhart 1986)
    default_connections: Dict[Tuple[str, str], float] = field(default_factory=lambda: {
        # Perception Pathway
        ('perception_encoding', 'short_term_memory'): 0.9,
        ('perception_encoding', 'memory_retrieval'): 0.7,
        
        # Memory System
        ('short_term_memory', 'memory_retrieval'): 0.8,
        ('memory_retrieval', 'short_term_memory'): 0.9,
        ('memory_retrieval', 'reasoning_validator'): 0.9,
        ('reasoning_validator', 'memory_retrieval'): 0.8,
        
        # Reasoning & Execution
        ('reasoning_validator', 'executive_control'): 0.9,
        ('reasoning_validator', 'conversation'): 0.8,
        ('executive_control', 'conversation'): 0.7,
        
        # Reflection Loop
        ('conversation', 'reflection'): 0.6,
        ('reflection', 'reasoning_validator'): 0.7,
        
        # Emotion Influence
        ('stress_response', 'executive_control'): 0.5,
        ('stress_response', 'memory_retrieval'): 0.4,
    })
    
    # --- Weak Connections ---
    # Global monitoring connection strength (e.g., to Executive Control)
    global_monitoring_weight: float = 0.2

    def get_connection_weight(self, source: str, target: str) -> Optional[float]:
        """Get default weight for a connection, or None if no default exists."""
        return self.default_connections.get((source, target))
