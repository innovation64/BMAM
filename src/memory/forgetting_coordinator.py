"""
Forgetting Coordinator - 遗忘协调器
统一海马体和全局系统的遗忘策略
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class MemoryProtectionAdvice:
    """
    Memory Protection Advice
    记忆保护建议
    
    海马体提供的保护建议，用于指导全局遗忘决策
    """
    memory_id: str
    should_protect: bool
    confidence: float  # 0.0-1.0
    reason: str
    importance: float
    access_count: int
    age_hours: float
    emotion_intensity: float


@dataclass
class ForgettingDecision:
    """
    Forgetting Decision
    遗忘决策
    
    全局系统基于多方建议做出的最终决策
    """
    memory_id: str
    should_forget: bool
    reason: str
    sources: List[str]  # ["hippocampus_advice", "capacity_pressure", "time_decay"]


class ForgettingCoordinator:
    """
    Forgetting Coordinator
    遗忘协调器
    
    统一管理遗忘策略，协调海马体建议和全局容量管理：
    1. 收集海马体的保护建议
    2. 综合容量压力、时间衰减等因素
    3. 做出最终的遗忘决策
    4. 在所有存储位置执行删除（FAISS、DB、海马体列表）
    
    这消除了双重遗忘逻辑的冲突。
    """
    
    def __init__(self, memory_system, hippocampus_agent=None, basal_ganglia_agent=None):
        """
        Initialize Forgetting Coordinator

        Args:
            memory_system: Global memory system (MemorySystem instance)
            hippocampus_agent: Optional hippocampus agent for advice
            basal_ganglia_agent: Optional basal ganglia for fixed-point detection (HRM)
        """
        self.memory_system = memory_system
        self.hippocampus = hippocampus_agent
        self.basal_ganglia = basal_ganglia_agent  # ✅ HRM integration

        # Statistics
        self.total_decisions = 0
        self.total_forgotten = 0
        self.advice_overrides = 0  # Times we overrode hippocampus advice
        self.fixed_point_detections = 0  # HRM: Fixed-point based decisions

        logger.info(
            f"ForgettingCoordinator initialized "
            f"(hippocampus={'yes' if hippocampus_agent else 'no'}, "
            f"basal_ganglia={'yes' if basal_ganglia_agent else 'no'})"
        )
    
    async def trigger_forgetting(
        self,
        capacity_threshold: float = 0.8,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger Unified Forgetting Process (HRM-aware)
        触发统一的遗忘流程（HRM感知）

        Args:
            capacity_threshold: Capacity ratio to trigger forgetting (0.0-1.0)
            force: Force forgetting even if below threshold

        Returns:
            Statistics about the forgetting process
        """
        # Step 0: HRM - Check if system reached fixed-point (stable state)
        fixed_point_detected = False
        if self.basal_ganglia and hasattr(self.basal_ganglia, 'detect_fixed_point'):
            try:
                fixed_point_info = await self.basal_ganglia.detect_fixed_point()
                fixed_point_detected = fixed_point_info.get('is_stable', False)

                if fixed_point_detected:
                    self.fixed_point_detections += 1
                    logger.info(
                        f"🎯 Fixed-point detected (occurrence #{fixed_point_info.get('occurrences', 1)}): "
                        f"System stable, reducing forgetting pressure"
                    )
                    # Increase threshold when system is stable
                    capacity_threshold = min(capacity_threshold * 1.2, 0.95)

            except Exception as e:
                logger.warning(f"Failed to check fixed-point: {e}")

        # Step 1: Check if forgetting is needed
        current_capacity = await self._get_capacity_status()
        capacity_ratio = current_capacity['used'] / current_capacity['total']

        if not force and capacity_ratio < capacity_threshold:
            logger.debug(
                f"Capacity {capacity_ratio:.1%} below threshold "
                f"{capacity_threshold:.1%}, skipping forgetting"
            )
            return {
                'triggered': False,
                'reason': 'below_threshold',
                'capacity_ratio': capacity_ratio,
                'fixed_point_detected': fixed_point_detected
            }

        logger.info(
            f"Triggering forgetting: capacity {capacity_ratio:.1%} "
            f"(threshold: {capacity_threshold:.1%}, "
            f"fixed_point: {'yes' if fixed_point_detected else 'no'})"
        )
        
        # Step 2: Collect protection advice from hippocampus
        advice_map = {}
        if self.hippocampus:
            advice_map = await self._collect_hippocampus_advice()
            logger.info(f"Collected advice for {len(advice_map)} memories")
        
        # Step 3: Make final forgetting decisions
        decisions = await self._make_forgetting_decisions(
            advice_map=advice_map,
            capacity_ratio=capacity_ratio
        )
        
        # Step 4: Execute deletions across all storage
        forgotten_ids = await self._execute_forgetting(decisions)
        
        # Step 5: Update statistics
        self.total_decisions += len(decisions)
        self.total_forgotten += len(forgotten_ids)
        
        return {
            'triggered': True,
            'capacity_ratio': capacity_ratio,
            'advice_collected': len(advice_map),
            'decisions_made': len(decisions),
            'memories_forgotten': len(forgotten_ids),
            'forgotten_ids': forgotten_ids,
            'fixed_point_detected': fixed_point_detected,  # HRM
            'hrm_optimization': fixed_point_detected  # HRM reduced pressure
        }
    
    async def _get_capacity_status(self) -> Dict[str, int]:
        """Get current capacity status"""
        # Query from global memory system
        stats = self.memory_system.get_system_stats()
        
        return {
            'used': stats.get('total_memories', 0),
            'total': stats.get('max_capacity', 100000)
        }
    
    async def _collect_hippocampus_advice(
        self
    ) -> Dict[str, MemoryProtectionAdvice]:
        """
        Collect Protection Advice from Hippocampus
        收集海马体的保护建议
        
        Returns:
            Dict mapping memory_id to MemoryProtectionAdvice
        """
        if not self.hippocampus:
            return {}
        
        advice_map = {}
        
        # Get all memories from hippocampus
        memories = getattr(self.hippocampus, 'memories', [])
        
        for memory in memories:
            # Calculate age
            age_hours = (datetime.now() - memory.timestamp).total_seconds() / 3600
            
            # Get hippocampus judgment
            should_protect = await self._get_hippocampus_protection_judgment(
                memory, age_hours
            )
            
            advice = MemoryProtectionAdvice(
                memory_id=memory.id,
                should_protect=should_protect['protect'],
                confidence=should_protect.get('confidence', 0.5),
                reason=should_protect.get('reason', 'N/A'),
                importance=memory.importance,
                access_count=memory.access_count,
                age_hours=age_hours,
                emotion_intensity=memory.emotion_intensity
            )
            
            advice_map[memory.id] = advice
        
        return advice_map
    
    async def _get_hippocampus_protection_judgment(
        self,
        memory,
        age_hours: float
    ) -> Dict[str, Any]:
        """
        Get protection judgment from hippocampus
        从海马体获取保护判断
        
        Uses hippocampus's LLM-based protection logic
        """
        # Check if hippocampus has the method
        if hasattr(self.hippocampus, '_should_protect_from_forgetting'):
            should_protect = await self.hippocampus._should_protect_from_forgetting(
                memory, age_hours
            )
            return {
                'protect': should_protect,
                'confidence': 0.8,
                'reason': 'hippocampus_llm_judgment'
            }
        
        # Fallback: Use simple rules
        if memory.access_count >= 3 or memory.emotion_intensity > 0.8:
            return {
                'protect': True,
                'confidence': 0.9,
                'reason': 'high_access_or_emotion'
            }
        
        if memory.importance > 0.7:
            return {
                'protect': True,
                'confidence': 0.7,
                'reason': 'high_importance'
            }
        
        return {
            'protect': False,
            'confidence': 0.5,
            'reason': 'no_strong_protection_factor'
        }
    
    async def _make_forgetting_decisions(
        self,
        advice_map: Dict[str, MemoryProtectionAdvice],
        capacity_ratio: float
    ) -> List[ForgettingDecision]:
        """
        Make Final Forgetting Decisions
        做出最终的遗忘决策
        
        Combines hippocampus advice with global factors:
        - Capacity pressure
        - Time decay
        - Importance scores
        
        Args:
            advice_map: Protection advice from hippocampus
            capacity_ratio: Current capacity usage ratio
        
        Returns:
            List of ForgettingDecision objects
        """
        decisions = []
        
        # Calculate how many memories to forget
        total_memories = len(advice_map)
        if total_memories == 0:
            return decisions
        
        # Dynamic forget ratio based on capacity pressure
        if capacity_ratio > 0.95:
            forget_ratio = 0.3  # High pressure: forget 30%
        elif capacity_ratio > 0.85:
            forget_ratio = 0.2  # Medium pressure: forget 20%
        else:
            forget_ratio = 0.1  # Low pressure: forget 10%
        
        target_forget_count = max(1, int(total_memories * forget_ratio))
        
        logger.info(
            f"Target: forget {target_forget_count}/{total_memories} "
            f"({forget_ratio:.0%}) based on capacity {capacity_ratio:.1%}"
        )
        
        # Sort memories by forgettability (least important first)
        forgettable_list = []
        protected_count = 0
        
        for memory_id, advice in advice_map.items():
            if advice.should_protect and advice.confidence > 0.7:
                # Strong protection - respect hippocampus advice
                protected_count += 1
                continue
            
            # Calculate forgettability score (higher = more forgettable)
            forgettability = self._calculate_forgettability(advice)
            forgettable_list.append((memory_id, advice, forgettability))
        
        # Sort by forgettability (descending)
        forgettable_list.sort(key=lambda x: x[2], reverse=True)
        
        # Make decisions
        for i, (memory_id, advice, forgettability) in enumerate(forgettable_list):
            should_forget = i < target_forget_count
            
            sources = ['capacity_pressure']
            if not advice.should_protect:
                sources.append('hippocampus_advice')
            if advice.age_hours > 168:  # > 1 week
                sources.append('time_decay')
            
            reason = f"Forgettability: {forgettability:.2f}"
            if should_forget and advice.should_protect:
                reason += " (overriding hippocampus advice due to capacity)"
                self.advice_overrides += 1
            
            decision = ForgettingDecision(
                memory_id=memory_id,
                should_forget=should_forget,
                reason=reason,
                sources=sources
            )
            decisions.append(decision)
        
        logger.info(
            f"Decisions: {target_forget_count} to forget, "
            f"{protected_count} protected, "
            f"{self.advice_overrides} advice overrides"
        )
        
        return decisions
    
    def _calculate_forgettability(self, advice: MemoryProtectionAdvice) -> float:
        """
        Calculate Forgettability Score
        计算遗忘度分数
        
        Higher score = more forgettable
        
        Factors:
        - Low importance → high forgettability
        - Low access count → high forgettability
        - Old age → high forgettability
        - Low emotion → high forgettability
        """
        # Base forgettability from importance (inverted)
        importance_factor = 1.0 - advice.importance
        
        # Access frequency factor (normalize to 0-1)
        access_factor = 1.0 / (1.0 + advice.access_count)
        
        # Time decay factor (normalize age to 0-1 scale)
        # Memories older than 30 days get max age factor
        age_factor = min(1.0, advice.age_hours / (30 * 24))
        
        # Emotion factor (inverted)
        emotion_factor = 1.0 - advice.emotion_intensity
        
        # Weighted average
        forgettability = (
            importance_factor * 0.4 +  # Importance is key
            access_factor * 0.3 +       # Access frequency matters
            age_factor * 0.2 +          # Age contributes
            emotion_factor * 0.1        # Emotion is minor factor
        )
        
        return forgettability
    
    async def _execute_forgetting(
        self,
        decisions: List[ForgettingDecision]
    ) -> List[str]:
        """
        Execute Forgetting Across All Storage
        在所有存储位置执行遗忘
        
        Deletes from:
        1. FAISS vector database
        2. SQLAlchemy database
        3. Hippocampus memory list
        
        This ensures consistency across all systems.
        
        Returns:
            List of forgotten memory IDs
        """
        forgotten_ids = []
        
        for decision in decisions:
            if not decision.should_forget:
                continue
            
            memory_id = decision.memory_id
            
            try:
                # Delete from global memory system (FAISS + DB)
                if self.memory_system:
                    await self.memory_system.delete_memory(memory_id)

                # Delete from hippocampus list
                if self.hippocampus:
                    await self._delete_from_hippocampus(memory_id)
                
                forgotten_ids.append(memory_id)
                logger.debug(f"Forgot memory {memory_id}: {decision.reason}")
                
            except Exception as e:
                logger.error(f"Failed to forget memory {memory_id}: {e}")
        
        logger.info(f"Forgot {len(forgotten_ids)} memories successfully")
        return forgotten_ids
    
    async def _delete_from_hippocampus(self, memory_id: str) -> None:
        """Delete memory from hippocampus internal list"""
        if not self.hippocampus:
            return
        
        # Remove from memories list
        memories = getattr(self.hippocampus, 'memories', [])
        self.hippocampus.memories = [
            m for m in memories if m.id != memory_id
        ]
        
        # Remove from memory_dict
        memory_dict = getattr(self.hippocampus, 'memory_dict', {})
        if memory_id in memory_dict:
            del memory_dict[memory_id]
        
        # Rebuild indexes
        if hasattr(self.hippocampus, '_rebuild_indexes'):
            self.hippocampus._rebuild_indexes()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics (HRM-aware)"""
        return {
            'total_decisions': self.total_decisions,
            'total_forgotten': self.total_forgotten,
            'advice_overrides': self.advice_overrides,
            'override_rate': (
                self.advice_overrides / self.total_decisions
                if self.total_decisions > 0 else 0.0
            ),
            # HRM stats
            'fixed_point_detections': self.fixed_point_detections,
            'hrm_enabled': self.basal_ganglia is not None
        }
