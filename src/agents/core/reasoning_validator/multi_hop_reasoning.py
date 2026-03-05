"""
Multi-hop Reasoning Mixin
多跳推理模块

🔥 Phase 3 Enhancement:
- Explicit depth limit (max 3 hops by default)
- Cycle detection (prevent processing same query twice)
- Timeout/budget control
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)

# 🔥 NEW: Configuration for multi-hop reasoning limits
MULTI_HOP_CONFIG = {
    'max_depth': 3,           # Maximum reasoning depth (hops)
    'max_time_seconds': 30,   # Maximum total time for reasoning
    'max_memories_per_hop': 5,  # Maximum new memories to fetch per hop
    'min_confidence_to_stop': 0.85,  # Stop early if confidence is high enough
}


class MultiHopReasoningMixin:
    """多跳推理Mixin"""

    # 🔥 NEW: Class-level tracking for cycle detection
    _active_queries: Set[str] = set()

    async def _multi_hop_reasoning(
        self,
        query: str,
        memories: List[Dict],
        hippocampus: Optional[Any] = None,
        memories_by_region: Optional[Dict] = None,
        current_depth: int = 0,  # 🔥 NEW: Track current depth
        start_time: Optional[float] = None,  # 🔥 NEW: Track start time
        visited_memory_ids: Optional[Set[str]] = None  # 🔥 NEW: Cycle detection
    ) -> Dict[str, Any]:
        """
        Multi-hop推理: 需要连接多条证据

        🧠 NEW: 协作推理架构
        - Reflection Agent: 识别抽象pattern,跨记忆推理 (如Q3: "community group" → "helping profession")
        - Reasoning Validator: 验证和综合reflection结果

        🔥 Phase 3 Enhancements:
        - Explicit depth limit (default: 3 hops)
        - Time budget control (default: 30 seconds)
        - Cycle detection (prevent infinite loops)

        Args:
            query: The question to answer
            memories: Available evidence
            hippocampus: For fetching additional memories
            memories_by_region: Region-organized memories
            current_depth: Current recursion depth (for limit checking)
            start_time: When reasoning started (for timeout)
            visited_memory_ids: Already processed memory IDs (cycle detection)
        """
        # 🔥 Initialize tracking on first call
        if start_time is None:
            start_time = time.time()
        if visited_memory_ids is None:
            visited_memory_ids = set()

        # 🔥 Depth limit check
        if current_depth >= MULTI_HOP_CONFIG['max_depth']:
            logger.warning(f"⚠️ Multi-hop depth limit reached ({current_depth}/{MULTI_HOP_CONFIG['max_depth']})")
            return {
                'answer': None,
                'confidence': 0.3,
                'reasoning_chain': [f'Depth limit reached at hop {current_depth}'],
                'depth_limited': True
            }

        # 🔥 Time budget check
        elapsed = time.time() - start_time
        if elapsed > MULTI_HOP_CONFIG['max_time_seconds']:
            logger.warning(f"⚠️ Multi-hop time budget exceeded ({elapsed:.1f}s/{MULTI_HOP_CONFIG['max_time_seconds']}s)")
            return {
                'answer': None,
                'confidence': 0.3,
                'reasoning_chain': [f'Time budget exceeded at {elapsed:.1f}s'],
                'timeout': True
            }

        # 🔥 Cycle detection - track processed memory IDs
        current_memory_ids = set(m.get('id', str(i)) for i, m in enumerate(memories))
        new_memory_ids = current_memory_ids - visited_memory_ids
        if not new_memory_ids and current_depth > 0:
            logger.debug(f"📊 No new memories at depth {current_depth}, stopping")
            return {
                'answer': None,
                'confidence': 0.4,
                'reasoning_chain': ['No new evidence found'],
                'no_new_evidence': True
            }
        visited_memory_ids.update(current_memory_ids)

        logger.debug(f"🔄 Multi-hop reasoning: depth={current_depth}, memories={len(memories)}, elapsed={elapsed:.1f}s")

        # 🧠 Step 1: 调用Reflection进行pattern-based推理 (针对Q3)
        reflection_result = None
        if self.reflection_agent and memories:
            try:
                from ...base import AgentMessage
                logger.debug("🧠 Calling Reflection Agent for pattern-based reasoning...")

                reflection_result = await self.reflection_agent.process_message(
                    AgentMessage(
                        sender="reasoning_validator",
                        receiver="reflection",
                        message_type="request",
                        content={
                            'action': 'infer_from_patterns',
                            'memories': memories,
                            'query': query
                        }
                    )
                )

                if reflection_result and reflection_result.get('confidence', 0) >= 0.7:
                    logger.debug(f"✅ Reflection Agent inferred: {reflection_result.get('answer')}")
                    # 如果reflection高置信度,直接使用其结果
                    return {
                        'answer': reflection_result.get('answer'),
                        'confidence': reflection_result.get('confidence'),
                        'reasoning_chain': reflection_result.get('patterns_identified', []),
                        'evidence_quality': 'strong',
                        'pattern_matched': reflection_result.get('abstract_connection', ''),
                        'collaboration': 'reflection_agent'
                    }
            except Exception as e:
                logger.warning(f"Reflection collaboration failed: {e}")

        memories_text = self._format_memories(memories)

        reasoning_prompt = f"""Perform multi-hop reasoning to answer the question.

Question: {query}

Available Evidence:
{memories_text}

Task: Connect multiple pieces of information to infer the answer.

Step 1 - Identify Required Hops:
What pieces of information need to be connected?

Step 2 - Extract Each Hop:
Hop 1: [Extract info A]
Hop 2: [Extract info B]
Hop 3: [Connect A + B → C]

Step 3 - Validate Chain:
Does each hop logically follow? Are there gaps?

Output JSON only:
{{
    "hops": [
        {{"hop": 1, "info": "extracted", "source": "memory X"}},
        {{"hop": 2, "info": "extracted", "source": "memory Y"}},
        {{"hop": 3, "info": "inferred", "reasoning": "A + B → C"}}
    ],
    "answer": "final inferred answer",
    "confidence": 0.0-1.0,
    "reasoning_chain": ["hop1", "hop2", "conclusion"],
    "missing_info": ["what info is missing, if any"],
    "refined_query": "query for missing info (else null)"
}}
"""

        try:
            full_prompt = f"You are a multi-hop reasoning expert. Output valid JSON only.\n\n{reasoning_prompt}"
            content = await self.call_llm(
                prompt=full_prompt,
                temperature=0.4,
                max_tokens=600
            )
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)

            # 🔥 Early stop if confidence is high enough
            if result.get('confidence', 0) >= MULTI_HOP_CONFIG['min_confidence_to_stop']:
                logger.debug(f"✅ Multi-hop early stop: confidence={result.get('confidence'):.2f} >= {MULTI_HOP_CONFIG['min_confidence_to_stop']}")
                result['early_stop'] = True
                return result

            # 双向反馈: Multi-hop最需要反馈
            # 🔥 FIX: Proper depth tracking and limits
            if result.get('missing_info') and hippocampus and current_depth < MULTI_HOP_CONFIG['max_depth'] - 1:
                max_fetch = MULTI_HOP_CONFIG['max_memories_per_hop']
                logger.debug(f"🔄 Multi-hop depth {current_depth}: Missing {len(result['missing_info'])} pieces, fetching up to {max_fetch}")

                fetched_count = 0
                for missing in result['missing_info'][:2]:  # 最多补充2个查询
                    if fetched_count >= max_fetch:
                        break
                    # 修复: hippocampus.retrieve -> hippocampus.search_memories
                    search_result = await hippocampus.search_memories(missing, k=max_fetch - fetched_count)
                    more_memories = search_result.get('memories', []) if isinstance(search_result, dict) else search_result
                    if more_memories:
                        memories.extend(more_memories)
                        fetched_count += len(more_memories)

                # 🔥 FIX: Recursive call with proper depth tracking
                return await self._multi_hop_reasoning(
                    query,
                    memories,
                    hippocampus,
                    memories_by_region,
                    current_depth=current_depth + 1,
                    start_time=start_time,
                    visited_memory_ids=visited_memory_ids
                )

            logger.debug(f"✅ Multi-hop reasoning: {result.get('answer')} (confidence={result.get('confidence', 0):.2f})")
            return result

        except Exception as e:
            import traceback
            logger.error(f"Multi-hop reasoning error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {'answer': None, 'confidence': 0.0, 'reasoning_chain': [f'Error: {str(e)}']}
