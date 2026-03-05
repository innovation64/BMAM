"""
Hippocampus Agent HRM Extension - 海马体智能体HRM扩展
Hierarchical Reasoning Model (HRM) Enhancements for Hippocampus

Adds HRM's L module (fast, reactive) capabilities:
1. Fast timescale iterations (every step)
2. State reset from H module (prefrontal cortex)
3. Guided memory retrieval based on strategic guidance
4. Local convergence detection

Key Design:
- L module: Updates every step with fast memory retrieval
- Receives reset signals from H module (Prefrontal)
- Iterates until local convergence or H module intervenes
- Maintains working memory for current retrieval context
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RetrievalContext:
    """
    Retrieval Context (L Module State)
    检索上下文（L模块状态）
    """
    query: str
    guidance: Optional[Dict[str, Any]] = None  # From H module
    focus_areas: List[str] = None
    search_strategy: str = 'broad_search'
    confidence_threshold: float = 0.8
    iteration: int = 0


@dataclass
class MemoryRetrievalResult:
    """
    Memory Retrieval Result
    记忆检索结果
    """
    memories: List[Dict[str, Any]]
    confidence: float
    converged: bool
    iteration: int
    search_strategy_used: str


class HippocampusHRMExtension:
    """
    HRM Extension for Hippocampus Agent
    海马体智能体的HRM扩展

    Mixin class that adds HRM L module (fast) capabilities to
    the existing HippocampusAgent.

    Usage:
        class HippocampusAgentV2(HippocampusHRMExtension, HippocampusAgentCore):
            pass

    HRM Features:
    1. fast_iteration() - Fast timescale memory retrieval
    2. reset_from_prefrontal() - Accept reset signals from H module
    3. check_local_convergence() - Detect when retrieval is complete
    4. guided_retrieval() - Retrieve with strategic guidance
    """

    def __init__(self, *args, **kwargs):
        """Initialize HRM extension"""
        super().__init__(*args, **kwargs)

        # HRM-specific state
        self.retrieval_context: Optional[RetrievalContext] = None
        self.working_memory: List[Dict[str, Any]] = []  # Current retrieval results
        self.iteration_count = 0
        self.prefrontal_guidance: Optional[Dict[str, Any]] = None

        # Convergence tracking
        self.previous_results: List[List[str]] = []  # Track memory IDs across iterations
        self.convergence_window = 3  # Check convergence over last 3 iterations

        # Performance metrics
        self.hrm_metrics = {
            'fast_iterations': 0,
            'resets_received': 0,
            'local_convergences': 0,
            'avg_iterations_to_convergence': 0.0
        }

        logger.info("HippocampusHRMExtension initialized (L module, fast timescale)")

    async def fast_iteration(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast Iteration (L Module - Fast Timescale)
        快速迭代（L模块 - 快时间尺度）

        Called every step by Thalamus.
        Performs fast memory retrieval with optional guidance from H module.

        Args:
            input_data: Input dictionary with:
                - query: Search query
                - reset_guidance: Optional guidance from prefrontal (after reset)
                - context: Additional context

        Returns:
            Dictionary with:
            - memories: Retrieved memories
            - confidence: Confidence in results
            - converged: Whether local convergence achieved
            - iteration: Current iteration number
        """
        self.iteration_count += 1
        self.hrm_metrics['fast_iterations'] += 1

        query = input_data.get('query', '')

        # Check for reset guidance from H module
        if 'reset_guidance' in input_data:
            # H module has provided new guidance - use it
            self.prefrontal_guidance = input_data['reset_guidance']
            logger.debug(f"Hippocampus received reset guidance: {self.prefrontal_guidance}")

        # Initialize or update retrieval context
        if not self.retrieval_context:
            self.retrieval_context = RetrievalContext(
                query=query,
                guidance=self.prefrontal_guidance,
                focus_areas=self.prefrontal_guidance.get('focus_areas', []) if self.prefrontal_guidance else [],
                search_strategy=self.prefrontal_guidance.get('search_strategy', 'broad_search') if self.prefrontal_guidance else 'broad_search',
                confidence_threshold=self.prefrontal_guidance.get('confidence_threshold', 0.8) if self.prefrontal_guidance else 0.8,
                iteration=self.iteration_count
            )
        else:
            self.retrieval_context.iteration = self.iteration_count

        logger.debug(f"Hippocampus L module iteration {self.iteration_count} with strategy: {self.retrieval_context.search_strategy}")

        # Perform guided retrieval
        retrieval_result = await self._guided_retrieval(
            query=query,
            guidance=self.prefrontal_guidance,
            iteration=self.iteration_count
        )

        # Update working memory
        self.working_memory = retrieval_result.memories

        # Track results for convergence detection
        memory_ids = [m.get('id', str(i)) for i, m in enumerate(retrieval_result.memories)]
        self.previous_results.append(memory_ids)
        if len(self.previous_results) > self.convergence_window:
            self.previous_results.pop(0)

        # Check for local convergence
        converged = self._check_local_convergence()

        if converged:
            self.hrm_metrics['local_convergences'] += 1
            logger.info(f"Hippocampus achieved local convergence at iteration {self.iteration_count}")

        return {
            'memories': retrieval_result.memories,
            'confidence': retrieval_result.confidence,
            'converged': converged,
            'iteration': self.iteration_count,
            'search_strategy': retrieval_result.search_strategy_used,
            'response': self._format_memory_response(retrieval_result.memories)
        }

    async def _guided_retrieval(
        self,
        query: str,
        guidance: Optional[Dict[str, Any]],
        iteration: int
    ) -> MemoryRetrievalResult:
        """
        Guided Memory Retrieval
        引导式记忆检索

        Retrieves memories based on query and strategic guidance from H module.

        Args:
            query: Search query
            guidance: Strategic guidance from prefrontal cortex
            iteration: Current iteration number

        Returns:
            MemoryRetrievalResult
        """
        # Determine search strategy
        if guidance:
            strategy = guidance.get('search_strategy', 'broad_search')
            focus_areas = guidance.get('focus_areas', [])
            confidence_threshold = guidance.get('confidence_threshold', 0.8)
        else:
            strategy = 'broad_search'
            focus_areas = []
            confidence_threshold = 0.8

        # Apply search strategy
        if strategy == 'broad_search':
            memories = await self._broad_search(query, k=10)
        elif strategy == 'focused_refinement':
            memories = await self._focused_refinement(query, focus_areas, k=7)
        elif strategy == 'verification':
            memories = await self._verification_search(query, k=5)
        else:
            # Fallback to standard search
            memories = await self._standard_search(query, k=10)

        # Calculate confidence in results
        confidence = self._calculate_retrieval_confidence(memories, query)

        # Check convergence
        converged = confidence >= confidence_threshold and iteration >= 2

        return MemoryRetrievalResult(
            memories=memories,
            confidence=confidence,
            converged=converged,
            iteration=iteration,
            search_strategy_used=strategy
        )

    async def _broad_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """
        Broad search strategy - cast wide net
        广泛搜索策略 - 广撒网

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of memory dictionaries
        """
        # Use existing search_memories method if available
        if hasattr(self, 'search_memories'):
            result = await self.search_memories(query=query, k=k * 2)  # Get more for diversity
            memories = result.get('memories', [])
        else:
            # Fallback: simple keyword search
            memories = self._keyword_search(query, k * 2)

        # Return diverse subset
        return self._diversify_results(memories, k)

    async def _focused_refinement(
        self,
        query: str,
        focus_areas: List[str],
        k: int
    ) -> List[Dict[str, Any]]:
        """
        Focused refinement strategy - narrow down based on focus areas
        聚焦精炼策略 - 基于焦点区域缩小范围

        Args:
            query: Search query
            focus_areas: Keywords to focus on
            k: Number of results

        Returns:
            List of memory dictionaries
        """
        # Enhance query with focus areas
        enhanced_query = f"{query} {' '.join(focus_areas)}"

        if hasattr(self, 'search_memories'):
            result = await self.search_memories(query=enhanced_query, k=k)
            memories = result.get('memories', [])
        else:
            memories = self._keyword_search(enhanced_query, k)

        # Filter to focus areas
        focused_memories = [
            m for m in memories
            if any(area.lower() in str(m.get('content', '')).lower() for area in focus_areas)
        ]

        # If too few, add some from general search
        if len(focused_memories) < k:
            focused_memories.extend(memories[:k - len(focused_memories)])

        return focused_memories[:k]

    async def _verification_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """
        Verification search strategy - double-check existing results
        验证搜索策略 - 复核现有结果

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of memory dictionaries
        """
        # Return high-confidence memories from working memory
        if self.working_memory:
            return self.working_memory[:k]

        # Fallback to focused search
        if hasattr(self, 'search_memories'):
            result = await self.search_memories(query=query, k=k)
            return result.get('memories', [])

        return self._keyword_search(query, k)

    async def _standard_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """
        Standard search fallback
        标准搜索回退

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of memory dictionaries
        """
        if hasattr(self, 'search_memories'):
            result = await self.search_memories(query=query, k=k)
            return result.get('memories', [])

        return self._keyword_search(query, k)

    def _keyword_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """
        Simple keyword-based search fallback
        简单的关键词搜索回退

        Args:
            query: Search query
            k: Number of results

        Returns:
            List of memory dictionaries
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        # Search in memory_dict if available
        if hasattr(self, 'memory_dict') and self.memory_dict:
            matches = []
            for mem_id, mem_obj in self.memory_dict.items():
                content = str(mem_obj.content if hasattr(mem_obj, 'content') else mem_obj).lower()
                # Calculate overlap
                content_words = set(content.split())
                overlap = len(query_words & content_words)

                if overlap > 0:
                    matches.append((mem_id, mem_obj, overlap))

            # Sort by overlap and return top k
            matches.sort(key=lambda x: x[2], reverse=True)

            return [
                {
                    'id': mem_id,
                    'content': mem_obj.content if hasattr(mem_obj, 'content') else str(mem_obj),
                    'score': overlap / len(query_words)
                }
                for mem_id, mem_obj, overlap in matches[:k]
            ]

        return []

    def _diversify_results(
        self,
        memories: List[Dict[str, Any]],
        k: int
    ) -> List[Dict[str, Any]]:
        """
        Diversify search results to avoid redundancy
        使结果多样化以避免冗余

        Args:
            memories: List of memories
            k: Desired number of diverse results

        Returns:
            Diversified list of memories
        """
        if len(memories) <= k:
            return memories

        # Simple diversification: skip similar consecutive results
        diversified = [memories[0]] if memories else []

        for mem in memories[1:]:
            if len(diversified) >= k:
                break

            # Check if sufficiently different from last added
            if not self._is_too_similar(mem, diversified[-1]):
                diversified.append(mem)

        # Fill remaining slots if needed
        if len(diversified) < k:
            for mem in memories:
                if mem not in diversified:
                    diversified.append(mem)
                    if len(diversified) >= k:
                        break

        return diversified[:k]

    def _is_too_similar(self, mem1: Dict[str, Any], mem2: Dict[str, Any]) -> bool:
        """
        Check if two memories are too similar
        检查两个记忆是否过于相似

        Args:
            mem1, mem2: Memory dictionaries

        Returns:
            True if too similar
        """
        content1 = str(mem1.get('content', '')).lower()
        content2 = str(mem2.get('content', '')).lower()

        if not content1 or not content2:
            return False

        # Simple similarity: check word overlap
        words1 = set(content1.split())
        words2 = set(content2.split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        union = len(words1 | words2)

        jaccard = overlap / union if union > 0 else 0

        return jaccard > 0.7  # >70% similarity

    def _calculate_retrieval_confidence(
        self,
        memories: List[Dict[str, Any]],
        query: str
    ) -> float:
        """
        Calculate confidence in retrieval results
        计算检索结果的置信度

        Args:
            memories: Retrieved memories
            query: Original query

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not memories:
            return 0.0

        # Factors:
        # 1. Number of results
        num_factor = min(1.0, len(memories) / 5.0)  # Ideal: 5+ memories

        # 2. Average relevance score
        scores = [m.get('score', 0.5) for m in memories]
        avg_score = sum(scores) / len(scores) if scores else 0.5

        # 3. Result stability (if we have history)
        stability = self._calculate_result_stability()

        # Combine
        confidence = (num_factor * 0.3 + avg_score * 0.5 + stability * 0.2)

        return max(0.0, min(1.0, confidence))

    def _calculate_result_stability(self) -> float:
        """
        Calculate stability of results across recent iterations
        计算近期迭代结果的稳定性

        Returns:
            Stability score (0.0 to 1.0)
        """
        if len(self.previous_results) < 2:
            return 0.5  # Not enough history

        # Compare last two result sets
        recent = self.previous_results[-2:]
        set1 = set(recent[0])
        set2 = set(recent[1])

        if not set1 and not set2:
            return 0.5

        # Calculate Jaccard similarity
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        stability = intersection / union if union > 0 else 0.0

        return stability

    def _check_local_convergence(self) -> bool:
        """
        Check for local convergence (L module)
        检查局部收敛（L模块）

        Convergence criteria:
        1. Results stable over convergence window
        2. High confidence in results
        3. Minimum iterations reached

        Returns:
            True if converged
        """
        # Need minimum iterations
        if self.iteration_count < 2:
            return False

        # Need sufficient history
        if len(self.previous_results) < 2:
            return False

        # Check stability across convergence window
        if len(self.previous_results) >= self.convergence_window:
            # All results in window should be similar
            window_results = self.previous_results[-self.convergence_window:]

            # Check pairwise similarity
            similarities = []
            for i in range(len(window_results) - 1):
                set1 = set(window_results[i])
                set2 = set(window_results[i + 1])

                if set1 or set2:
                    intersection = len(set1 & set2)
                    union = len(set1 | set2)
                    sim = intersection / union if union > 0 else 0
                    similarities.append(sim)

            if similarities:
                avg_similarity = sum(similarities) / len(similarities)
                return avg_similarity > 0.8  # 80% stability
        else:
            # Check last two iterations
            return self._calculate_result_stability() > 0.8

        return False

    async def reset_from_prefrontal(self, guidance: Dict[str, Any]) -> None:
        """
        Reset from Prefrontal Cortex (H Module)
        从前额叶皮层重置（H模块）

        Called when H module (prefrontal) sends a reset signal.
        Clears working memory and updates guidance.

        Args:
            guidance: Strategic guidance from prefrontal cortex
        """
        self.hrm_metrics['resets_received'] += 1

        logger.info(f"Hippocampus receiving reset signal from prefrontal (iteration {self.iteration_count})")

        # Clear working state
        self.working_memory = []
        self.previous_results = []
        self.iteration_count = 0
        self.retrieval_context = None

        # Update guidance from H module
        self.prefrontal_guidance = guidance

        logger.debug(f"Hippocampus reset complete with new guidance: {guidance}")

    def _format_memory_response(self, memories: List[Dict[str, Any]]) -> str:
        """
        Format memories into response string
        将记忆格式化为响应字符串

        Args:
            memories: List of memory dictionaries

        Returns:
            Formatted response string
        """
        if not memories:
            return "No relevant memories found."

        # Format top memories
        formatted = []
        for i, mem in enumerate(memories[:5], 1):
            content = mem.get('content', str(mem))
            score = mem.get('score', 0.0)
            formatted.append(f"{i}. [{score:.2f}] {content[:100]}")

        return "\n".join(formatted)

    def get_hrm_status(self) -> Dict[str, Any]:
        """
        Get HRM-specific status
        获取HRM特定状态

        Returns:
            Status dictionary
        """
        return {
            'iteration_count': self.iteration_count,
            'working_memory_size': len(self.working_memory),
            'has_prefrontal_guidance': self.prefrontal_guidance is not None,
            'local_convergence': self._check_local_convergence(),
            'result_stability': self._calculate_result_stability(),
            'metrics': self.hrm_metrics,
            'retrieval_context': {
                'query': self.retrieval_context.query if self.retrieval_context else None,
                'strategy': self.retrieval_context.search_strategy if self.retrieval_context else None,
                'iteration': self.retrieval_context.iteration if self.retrieval_context else 0
            } if self.retrieval_context else None
        }
