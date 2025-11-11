"""
Memory Coordinator Module
Handles memory storage, retrieval, consolidation, and forgetting operations
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from .clean_agent_system import AgentMessage
from ..memory.memory_system import memory_system
from ..utils.config import get_logger

logger = get_logger(__name__)


class MemoryCoordinator:
    """Coordinates memory operations across brain regions"""

    def __init__(self, hippocampus, temporal_lobe, consolidation_agent,
                 forgetting_agent, agent_lifecycle_manager):
        """
        Initialize Memory Coordinator

        Args:
            hippocampus: Hippocampus agent instance
            temporal_lobe: Temporal lobe agent instance
            consolidation_agent: Consolidation agent instance
            forgetting_agent: Forgetting agent instance
            agent_lifecycle_manager: Agent lifecycle manager for activation
        """
        self.hippocampus = hippocampus
        self.temporal_lobe = temporal_lobe
        self.consolidation_agent = consolidation_agent
        self.forgetting_agent = forgetting_agent
        self.agent_lifecycle = agent_lifecycle_manager


    async def store_memory_with_timestamp(
        self,
        content: str,
        timestamp: datetime,
        speaker: str = None,
        importance: float = 0.5
    ) -> Dict[str, Any]:
        """
        Store memory with custom timestamp (for learning historical conversations)

        Args:
            content: Memory content
            timestamp: Custom timestamp
            speaker: Speaker name
            importance: Importance score (0.0-1.0)

        Returns:
            {
                'memory_id': str,
                'event_id': str,
                'is_new_event': bool
            }
        """
        result = await self.hippocampus.store_memory_with_event_segmentation(
            content=content,
            timestamp=timestamp,
            speaker=speaker,
            importance=importance
        )


        return result

    async def store_memory_if_needed(
        self,
        user_input: str,
        response: str,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Store memory based on input type and context

        Args:
            user_input: User input text
            response: Assistant response
            context: Context dict

        Returns:
            True if memory was stored
        """
        if context is None:
            context = {}

        try:
            # Check if this is a simple Q&A that shouldn't pollute memory
            # Add your detection logic here

            # Store to hippocampus
            await self.hippocampus.store_memory(
                content=f"User: {user_input}\nAssistant: {response}",
                metadata={
                    'type': 'conversation',
                    'importance': context.get('importance', 0.5),
                    'timestamp': datetime.now().isoformat()
                }
            )

            return True

        except Exception as e:
            logger.error(f"❌ Failed to store memory: {e}")
            return False

    async def trigger_consolidation(
        self,
        strategy: str = 'batch',
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        Manually trigger memory consolidation

        Args:
            strategy: Consolidation strategy
                - 'batch': Batch consolidation (extract N memories from Hippocampus)
                - 'system': System-wide consolidation (evaluate all memories)
                - 'sleep': Sleep consolidation (simulate sleep-time consolidation)
            batch_size: Number of memories to process in batch mode

        Returns:
            Dict with consolidation results
        """

        action_map = {
            'batch': 'batch_consolidation',
            'system': 'system_consolidation',
            'sleep': 'sleep_consolidation'
        }

        action = action_map.get(strategy, 'batch_consolidation')

        content = {'action': action}
        if strategy == 'batch':
            content['batch_size'] = batch_size

        result = await self.agent_lifecycle.activate_agent(
            'consolidation',
            AgentMessage(
                sender='coordinator',
                receiver='consolidation',
                message_type='request',
                content=content
            )
        )

        return result

    async def consolidate_memories(self) -> Dict[str, Any]:
        """
        Consolidate memories from Hippocampus to Temporal Lobe

        Returns:
            Consolidation result dict
        """
        try:

            # Get memories from hippocampus for consolidation
            candidates = await self.hippocampus.get_consolidation_candidates()

            if not candidates:
                return {'consolidated': 0, 'message': 'No candidates'}

            # Transfer to temporal lobe
            consolidated_count = 0
            for memory in candidates:
                try:
                    await self.temporal_lobe.store_consolidated_memory(memory)
                    consolidated_count += 1
                except Exception as e:
                    logger.warning(f"Failed to consolidate memory: {e}")


            return {
                'consolidated': consolidated_count,
                'candidates': len(candidates),
                'success': True
            }

        except Exception as e:
            logger.error(f"❌ Consolidation failed: {e}")
            return {'consolidated': 0, 'error': str(e), 'success': False}

    async def trigger_forgetting(self, region: str) -> Dict[str, Any]:
        """
        Trigger forgetting process for specified brain region

        Args:
            region: Brain region name ('hippocampus', 'temporal_lobe', etc.)

        Returns:
            Forgetting result dict
        """

        try:
            # Get forgetting candidates from region
            if region == 'hippocampus':
                candidates = await self.hippocampus.get_forgetting_candidates(
                    bottom_percentile=0.2
                )
                brain_region_agent = self.hippocampus
            elif region == 'temporal_lobe':
                return {
                    'forgotten': 0,
                    'message': 'TemporalLobe uses internal forgetting logic'
                }
            else:
                logger.warning(f"Unknown brain region: {region}")
                return {
                    'forgotten': 0,
                    'error': f'Unknown region: {region}'
                }

            if not candidates:
                return {
                    'forgotten': 0,
                    'message': 'No candidates for forgetting'
                }


            # Evaluate retention value
            to_forget = []
            forgetting_threshold = 0.3

            for candidate in candidates:
                importance = candidate.get('importance', 0.5)
                access_count = candidate.get('access_count', 0)

                # Calculate retention score
                retention_score = importance * 0.7 + min(access_count / 10, 0.3)

                if retention_score < forgetting_threshold:
                    to_forget.append(candidate)

            if not to_forget:
                return {
                    'forgotten': 0,
                    'candidates': len(candidates),
                    'message': 'All memories above retention threshold'
                }


            # Execute forgetting
            forgotten_ids = [mem['id'] for mem in to_forget]

            if region == 'hippocampus':
                forgotten_count = await brain_region_agent.forget_memories(forgotten_ids)
            else:
                forgotten_count = 0


            return {
                'forgotten': forgotten_count,
                'candidates': len(candidates),
                'region': region,
                'threshold': forgetting_threshold,
                'message': f'Successfully forgot {forgotten_count} memories'
            }

        except Exception as e:
            logger.error(f"❌ Forgetting error for {region}: {e}")
            return {
                'forgotten': 0,
                'error': str(e)
            }

    async def smart_retrieve(
        self,
        query: str,
        k: int = 10,
        strategy: str = 'auto',
        context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Smart memory retrieval with automatic strategy selection

        Args:
            query: Query text
            k: Number of results
            strategy: Retrieval strategy ('auto', 'episodic', 'semantic', 'hybrid')
            context: Optional context dict

        Returns:
            List of retrieved memories
        """
        if context is None:
            context = {}

        try:
            # Auto-select strategy if needed
            if strategy == 'auto':
                # Use routing manager to decide
                # For now, default to hybrid
                strategy = 'hybrid'


            # Route to appropriate retrieval method
            if strategy == 'episodic':
                result = await self.hippocampus.search_memories(query, k=k)
                memories = result.get('memories', []) if isinstance(result, dict) else result
                # Add source label
                for mem in memories:
                    mem['source'] = 'hippocampus'
            elif strategy == 'semantic':
                result = await self.temporal_lobe.search_memories(query, k=k)
                memories = result.get('memories', []) if isinstance(result, dict) else result
                # Add source label
                for mem in memories:
                    mem['source'] = 'temporal_lobe'
            elif strategy == 'hybrid':
                # Combine hippocampus and temporal lobe
                episodic_result = await self.hippocampus.search_memories(query, k=k//2)
                semantic_result = await self.temporal_lobe.search_memories(query, k=k//2)

                # Extract memories from results (handle Dict return type)
                episodic_memories = episodic_result.get('memories', []) if isinstance(episodic_result, dict) else episodic_result
                semantic_memories = semantic_result.get('memories', []) if isinstance(semantic_result, dict) else semantic_result

                # Add source labels
                for mem in episodic_memories:
                    mem['source'] = 'hippocampus'
                for mem in semantic_memories:
                    mem['source'] = 'temporal_lobe'

                # Combine memory lists
                memories = episodic_memories + semantic_memories
                # Sort by score/relevance
                memories.sort(key=lambda x: x.get('relevance', x.get('score', 0)), reverse=True)
                memories = memories[:k]
            else:
                # Default to hippocampus
                result = await self.hippocampus.search_memories(query, k=k)
                memories = result.get('memories', []) if isinstance(result, dict) else result
                # Add source label
                for mem in memories:
                    mem['source'] = 'hippocampus'

            return memories

        except Exception as e:
            logger.error(f"❌ Smart retrieve failed: {e}")
            return []

    async def extract_semantic_from_episodes(
        self,
        episodes: List[Dict[str, Any]],
        date: str
    ) -> Optional[str]:
        """
        Extract semantic knowledge from episodic memories

        Uses LLM to understand common patterns and core knowledge

        Args:
            episodes: List of episodic memories
            date: Date label

        Returns:
            Extracted semantic knowledge string, or None if extraction fails
        """
        # Combine content
        combined_content = "\n".join([
            f"- {ep.get('content', '')[:200]}"
            for ep in episodes[:10]  # Limit to avoid token overflow
        ])

        # Use consolidation agent's LLM capability
        prompt = f"""从以下{len(episodes)}条情节记忆中提取核心的语义知识:

日期: {date}

情节记忆:
{combined_content}

请提取:
1. 核心事实和知识点
2. 共同的主题或模式
3. 重要的实体关系

以简洁的语义知识形式输出 (2-3句话)。"""

        try:
            response = await self.consolidation_agent.call_llm(
                prompt=prompt,
                max_tokens=300,
                temperature=0.3
            )

            semantic_knowledge = response.strip()

            if len(semantic_knowledge) < 10:
                return None

            return f"[{date}] {semantic_knowledge}"

        except Exception as e:
            logger.warning(f"Failed to extract semantic knowledge: {e}")
            return None
