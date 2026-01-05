"""
Persona Memory Agent
人格/价值观记忆智能体 - 维护价值取向与人格相关长期记忆

🔥 2025-12-25: 集成UserPortraitManager实现用户肖像持久化
"""

from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from ..base import BrainAgent, AgentMessage, BrainRegion
from .user_portrait_manager import get_user_portrait_manager

logger = logging.getLogger(__name__)


class PersonaMemoryAgent(BrainAgent):
    """
    Persona & Values Memory Agent (Default Mode / Medial Prefrontal)
    
    负责：
    - 存储人格、价值观、长期偏好等信息
    - 检索人格相关记忆，为人格智能体提供上下文
    - 记录重复提及次数，追踪价值观变动
    """

    def __init__(self, db_manager=None, embedding_service=None, vector_db=None):
        super().__init__(
            agent_id="persona_memory",
            brain_region=BrainRegion.DEFAULT_MODE,
            system_prompt="""You are the persona/value memory subsystem of a brain-inspired AI.
            Your role is to:
            1. Store stable persona, preferences and value alignment memories
            2. Provide persona-aligned memories for personality generation
            3. Track repeated mentions to understand enduring preferences
            4. Maintain metadata useful for value alignment and persona evolution"""
        )

        self.db_manager = db_manager
        self.embedding_service = embedding_service
        self.vector_db = vector_db
        self.total_persona_memories = 0

        # 🔥 2025-12-25: 初始化UserPortraitManager用于持久化用户肖像
        try:
            self.portrait_manager = get_user_portrait_manager()
            logger.info("✅ UserPortraitManager initialized for PersonaMemory")
        except Exception as e:
            logger.warning(f"⚠️ UserPortraitManager initialization failed: {e}")
            self.portrait_manager = None

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        action = message.content.get('action')

        if action == 'store_persona_memory':
            return await self._store_persona_memory(message.content.get('memory', {}))
        if action == 'retrieve_persona_memories':
            return await self._retrieve_persona_memories(
                message.content.get('query', ''),
                message.content.get('k', 5)
            )
        if action == 'recent_persona_memories':
            return await self._get_recent_persona_memories(message.content.get('limit', 5))
        if action == 'summarize_persona':
            return await self._summarize_persona_profile()

        return {'error': f'Unknown persona action: {action}'}

    async def store_persona(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Public wrapper for storing persona memories."""
        return await self._store_persona_memory(memory)

    async def retrieve_persona(
        self,
        query: str,
        k: int = 5,
        user_id: str = None,
        preference_boost: float = 0.0
    ) -> Dict[str, Any]:
        """Public wrapper for retrieving persona memories.

        Args:
            query: 检索查询
            k: 返回结果数量
            user_id: 用户ID (可选，用于过滤特定用户的记忆) - 恢复自52%版本
            preference_boost: 偏好相关记忆的加权因子 (0.0-0.5) - 🔥 2025-12-27 新增
                              由 AdaptiveConfigManager.preference_retrieval_boost 传入
        """
        return await self._retrieve_persona_memories(query, k, user_id, preference_boost)

    async def recent_persona(self, limit: int = 5, user_id: str = None) -> Dict[str, Any]:
        """Public wrapper for recent persona memories.

        Args:
            limit: 返回结果数量
            user_id: 用户ID (可选，用于过滤特定用户的记忆) - 恢复自52%版本
        """
        return await self._get_recent_persona_memories(limit, user_id)

    async def _store_persona_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        if not memory or not memory.get('content'):
            return {'error': 'Invalid persona memory payload'}

        payload = deepcopy(memory)
        payload.setdefault('memory_type', 'persona')
        payload.setdefault('importance', 0.6)
        payload.setdefault('emotion_tags', ['neutral'])

        context_tags = set(payload.get('context_tags', []))
        context_tags.update({'persona', payload.get('category', 'general_persona')})
        payload['context_tags'] = list(context_tags)

        metadata = deepcopy(payload.get('metadata', {}) or {})
        metadata.setdefault('persona_category', payload.get('category', 'general_persona'))
        metadata.setdefault('value_alignment', payload.get('value_alignment', 'neutral'))
        metadata.setdefault('source', payload.get('source', 'persona_memory_agent'))
        # 🔥 2025-12-24: 添加 user_id 支持，用于区分不同用户 (恢复自52%版本)
        metadata.setdefault('user_id', payload.get('user_id', 'default'))

        history = list(metadata.get('repeat_history', []))
        history.append({
            'timestamp': datetime.now().isoformat(),
            'content': payload.get('content', '')
        })
        metadata['repeat_history'] = history
        metadata['repeat_count'] = len(history)
        payload['metadata'] = metadata

        duplicate = await self._find_duplicate_persona(payload)
        if duplicate and duplicate.get('memory_id'):
            merged = await self._merge_persona_memory(
                duplicate['memory_id'],
                payload,
                duplicate.get('similarity', 0.0)
            )
            merged['stored'] = False
            merged['duplicate_detected'] = True
            return merged

        from ...memory.memory_system import memory_system

        memory_id = await memory_system.store_memory(
            content=payload['content'],
            memory_type=payload.get('memory_type', 'persona'),
            importance=payload.get('importance', 0.6),
            emotion_tags=payload.get('emotion_tags', []),
            context_tags=payload.get('context_tags', []),
            metadata=payload.get('metadata', {})
        )

        if memory_id:
            self.total_persona_memories += 1
            logger.debug("🧬 Persona memory stored %s: %s", memory_id, payload['content'][:60])
            await self._link_related_persona_memories(memory_id)

            # 🔥 2025-12-25: 触发用户肖像增量更新
            if self.portrait_manager:
                try:
                    user_id = metadata.get('user_id', 'default')
                    pref_type = payload.get('category', 'facts')  # 默认归类为facts
                    pref_value = payload.get('content', '')
                    original_statement = metadata.get('original_statement', '')

                    if pref_value:
                        self.portrait_manager.update_preference(
                            user_id=user_id,
                            preference_type=pref_type,
                            preference_value=pref_value[:200],  # 限制长度
                            original_statement=original_statement
                        )
                except Exception as e:
                    logger.debug(f"Portrait update skipped: {e}")

            return {
                'stored': True,
                'memory_id': memory_id,
                'duplicate_detected': False,
                'total_persona_memories': self.total_persona_memories
            }

        logger.error("Failed to store persona memory: %s", payload['content'][:60])
        return {'stored': False, 'error': 'memory_system store failed'}

    async def _retrieve_persona_memories(
        self,
        query: str,
        k: int = 5,
        user_id: str = None,
        preference_boost: float = 0.0
    ) -> Dict[str, Any]:
        """
        检索人设记忆 (增强版 - 支持结构化分类检索)

        2025-12-22: 增强版，利用结构化分类提升偏好检索效果
        2025-12-24: 添加 user_id 过滤，避免不同用户记忆混淆 (恢复自52%版本)
        2025-12-27: 添加 preference_boost 动态加权，由 AdaptiveConfigManager 传入

        Args:
            query: 检索查询
            k: 返回结果数量
            user_id: 用户ID (可选，用于过滤特定用户的记忆)
            preference_boost: 偏好相关记忆的加权因子 (0.0-0.5)
        """
        from ...memory.memory_system import memory_system

        if not query:
            return {'memories': [], 'retrieval_method': 'persona_semantic', 'count': 0}

        # 🔥 检测查询类型以决定检索策略
        query_category = self._detect_query_category(query)

        try:
            raw_results = await memory_system.search_memories(
                query,
                search_type='semantic',
                k=k * 5,  # 🔥 增大候选池以便筛选
                threshold=0.10  # 🔥 降低阈值以捕获更多相关记忆
            )
        except Exception as exc:
            logger.warning(f"Persona memory retrieval failed: {exc}")
            return {'memories': [], 'retrieval_method': 'persona_semantic', 'count': 0}

        persona_memories = []
        for item in raw_results:
            context_tags = set(item.get('context_tags', []))
            metadata = item.get('metadata', {}) or {}

            # 🔥 2025-12-24: user_id 过滤 - 但允许 'default' 用户的记忆也被检索 (恢复自52%)
            # 因为早期存储的记忆可能没有设置 user_id
            if user_id:
                mem_user_id = metadata.get('user_id', 'default')
                # 允许匹配目标用户或 'default' 用户的记忆
                if mem_user_id != user_id and mem_user_id != 'default':
                    continue

            # 基础过滤：persona 类型记忆
            if item.get('memory_type') == 'persona' or 'persona' in context_tags:
                base_score = item.get('similarity_score', 0.0)

                # 🔥 结构化分类加权 - 动态化，由 preference_boost 调制
                structured_category = metadata.get('structured_category', '')
                preference_type = metadata.get('preference_type', '')

                # 🔥 2025-12-27 FIX: 使用动态 preference_boost 而非硬编码
                # category_boost 基础值由 preference_boost 决定
                # preference_boost=0.0 → 最大category_boost=0.05
                # preference_boost=0.5 → 最大category_boost=0.20
                max_category_boost = 0.05 + preference_boost * 0.30

                category_boost = 0.0
                # 如果查询类型与记忆分类匹配，增加权重
                if query_category:
                    if structured_category == query_category:
                        category_boost = max_category_boost
                    elif preference_type in ['likes', 'interests'] and query_category in ['preference', 'recommendation']:
                        category_boost = max_category_boost * 0.7
                    elif preference_type == 'facts' and query_category == 'identity':
                        category_boost = max_category_boost * 0.9
                    elif preference_type in ['dislikes', 'constraints'] and query_category in ['suggestion', 'recommendation']:
                        # 🔥 负面偏好对建议类查询很重要
                        category_boost = max_category_boost * 0.8

                # 🔥 重要性加权 - 也由 preference_boost 调制
                importance = item.get('importance', 0.5)
                importance_scale = 0.05 + preference_boost * 0.15  # 0.05-0.20
                importance_boost = (importance - 0.5) * importance_scale

                final_score = base_score + category_boost + importance_boost

                persona_memories.append({
                    'memory': item,
                    'retrieval_confidence': final_score,
                    'base_score': base_score,
                    'category_boost': category_boost,
                    'retrieval_method': 'persona_semantic_enhanced',
                    'matched_category': structured_category
                })

        # 按增强后的分数排序
        persona_memories.sort(key=lambda x: x['retrieval_confidence'], reverse=True)
        top = persona_memories[:k]

        return {
            'memories': top,
            'retrieval_method': 'persona_semantic_enhanced',
            'query_category': query_category,
            'count': len(top)
        }

    def _detect_query_category(self, query: str) -> str:
        """
        检测查询的分类类型

        🔥 2025-12-27: 扩展分类以支持PersonaMem的7种问题类型

        Returns:
            分类名称: 'preference', 'identity', 'capability', 'behavior', 'aspiration',
                      'suggestion', 'recommendation', 'fact_recall', 'evolution'
        """
        query_lower = query.lower()

        # 🔥 建议/创意类查询 (suggest_new_ideas) - 高优先级
        suggestion_keywords = ['suggest', 'idea', 'creative', 'new way', 'how can i',
                              'what could', 'explore', 'try something', 'outlet',
                              '建议', '想法', '创意', '新方法']
        if any(kw in query_lower for kw in suggestion_keywords):
            return 'suggestion'

        # 🔥 推荐类查询 (provide_preference_aligned_recommendations) - 高优先级
        recommendation_keywords = ['recommend', 'would you suggest', 'what would you',
                                   'should i', 'best for me', 'suited for',
                                   '推荐', '适合我']
        if any(kw in query_lower for kw in recommendation_keywords):
            return 'recommendation'

        # 🔥 偏好演化追踪 (track_full_preference_evolution)
        evolution_keywords = ['decided', 'changed', 'used to', 'now i', 'stopped',
                             'started', 'no longer', 'switched', 'evolved',
                             '改变了', '不再', '开始', '放弃']
        if any(kw in query_lower for kw in evolution_keywords):
            return 'evolution'

        # 🔥 事实回忆类 (recall_user_shared_facts, recalling_facts_mentioned)
        fact_recall_keywords = ['attended', 'visited', 'went to', 'recently',
                               'yesterday', 'last week', 'remember when',
                               '参加了', '去过', '最近']
        if any(kw in query_lower for kw in fact_recall_keywords):
            return 'fact_recall'

        # 偏好类查询
        preference_keywords = ['like', 'prefer', 'favorite', 'enjoy', 'love', 'hate', 'dislike',
                               'interest', '喜欢', '偏好', '爱好']
        if any(kw in query_lower for kw in preference_keywords):
            return 'preference'

        # 身份类查询
        identity_keywords = ['who', 'background', 'born', 'work as', 'profession', 'heritage',
                            '谁', '身份', '职业', '背景']
        if any(kw in query_lower for kw in identity_keywords):
            return 'identity'

        # 能力类查询
        capability_keywords = ['can you', 'able to', 'skill', 'good at', 'expert',
                              '擅长', '会', '能力']
        if any(kw in query_lower for kw in capability_keywords):
            return 'capability'

        # 行为类查询
        behavior_keywords = ['usually', 'often', 'habit', 'routine', 'activity',
                            '经常', '习惯', '通常']
        if any(kw in query_lower for kw in behavior_keywords):
            return 'behavior'

        # 志向类查询
        aspiration_keywords = ['want', 'hope', 'goal', 'dream', 'plan',
                              '想', '希望', '目标', '梦想']
        if any(kw in query_lower for kw in aspiration_keywords):
            return 'aspiration'

        return ''  # 未分类

    async def _get_recent_persona_memories(self, limit: int = 5, user_id: str = None) -> Dict[str, Any]:
        """获取最近的 persona 记忆 (恢复自52%版本)

        Args:
            limit: 返回结果数量
            user_id: 用户ID (可选，用于过滤特定用户的记忆)
        """
        if not self.db_manager:
            return {'memories': [], 'error': 'db_manager not available'}

        # 获取更多记忆以便过滤
        fetch_limit = limit * 3 if user_id else limit

        memories = self.db_manager.load_memories_by_criteria(
            memory_type='persona',
            limit=fetch_limit
        )

        # 🔥 2025-12-24: user_id 过滤 - 允许 'default' 用户的记忆 (恢复自52%)
        if user_id:
            filtered = []
            for mem in memories:
                mem_dict = mem.to_dict() if hasattr(mem, 'to_dict') else mem
                metadata = mem_dict.get('metadata', {}) or {}
                mem_user_id = metadata.get('user_id', 'default')
                # 允许匹配目标用户或 'default' 用户的记忆
                if mem_user_id == user_id or mem_user_id == 'default':
                    filtered.append(mem_dict)
                    if len(filtered) >= limit:
                        break
            summaries = filtered
        else:
            summaries = [memory.to_dict() for memory in memories[:limit]]

        return {
            'memories': summaries,  # 统一返回格式
            'recent_persona_memories': summaries,  # 兼容旧格式
            'count': len(summaries)
        }

    async def _summarize_persona_profile(self, user_id: str = 'default') -> Dict[str, Any]:
        """
        总结用户肖像

        🔥 2025-12-25: 集成UserPortraitManager,返回持久化的肖像

        Args:
            user_id: 用户标识

        Returns:
            用户肖像摘要
        """
        # 🔥 优先使用UserPortraitManager的肖像
        if self.portrait_manager:
            try:
                portrait = self.portrait_manager.get_portrait(user_id)
                return {
                    'user_id': user_id,
                    'summary': portrait.summary or "No summary available",
                    'preferences': {
                        'likes': portrait.likes,
                        'dislikes': portrait.dislikes,
                        'interests': portrait.interests,
                        'habits': portrait.habits,
                        'skills': portrait.skills,
                        'goals': portrait.goals,
                        'facts': portrait.facts,
                    },
                    'confidence': portrait.confidence,
                    'memory_count': portrait.memory_count,
                    'last_updated': portrait.updated_at,
                    'source': 'UserPortraitManager'
                }
            except Exception as e:
                logger.warning(f"Failed to get portrait from manager: {e}")

        # Fallback: 传统方式从DB统计
        if not self.db_manager:
            return {'error': 'db_manager not available'}

        memories = self.db_manager.load_memories_by_criteria(memory_type='persona')
        preference_counter = {}
        value_counter = {}

        for memory in memories:
            metadata = memory.metadata or {}
            pref_type = metadata.get('preference_type')
            value_alignment = metadata.get('value_alignment')
            if pref_type:
                preference_counter[pref_type] = preference_counter.get(pref_type, 0) + 1
            if value_alignment:
                value_counter[value_alignment] = value_counter.get(value_alignment, 0) + 1

        return {
            'preferences': preference_counter,
            'value_alignment': value_counter,
            'total_persona_memories': len(memories),
            'source': 'database_statistics'
        }

    async def _find_duplicate_persona(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from ...memory.memory_system import memory_system

        try:
            results = await memory_system.search_memories(
                payload['content'],
                search_type='semantic',
                k=5,
                threshold=0.25
            )
        except Exception:
            return None

        best_candidate = None
        best_similarity = 0.0
        for item in results:
            if item.get('memory_type') != 'persona' and 'persona' not in set(item.get('context_tags', [])):
                continue
            similarity = item.get('similarity_score', 0.0)
            if similarity > best_similarity and similarity >= 0.85:
                best_similarity = similarity
                best_candidate = {'memory_id': item['id'], 'similarity': similarity}
        return best_candidate

    async def _merge_persona_memory(self, memory_id: str, payload: Dict[str, Any], similarity: float) -> Dict[str, Any]:
        if not self.db_manager:
            return {'error': 'db_manager not available', 'memory_id': memory_id}

        existing = self.db_manager.load_memory(memory_id)
        if not existing:
            return {'error': 'existing memory not found', 'memory_id': memory_id}

        updated = False

        # Merge context tags
        existing_tags = set(existing.context_tags or [])
        new_tags = set(payload.get('context_tags', []))
        merged_tags = existing_tags | new_tags
        if merged_tags != existing_tags:
            existing.context_tags = list(merged_tags)
            updated = True

        # Merge emotion tags
        existing_emotions = set(existing.emotion_tags or [])
        new_emotions = set(payload.get('emotion_tags', []))
        merged_emotions = existing_emotions | new_emotions
        if merged_emotions != existing_emotions:
            existing.emotion_tags = list(merged_emotions)
            updated = True

        # Merge metadata and repeat history
        metadata = deepcopy(existing.metadata or {})
        incoming_metadata = payload.get('metadata', {}) or {}

        history = list(metadata.get('repeat_history', []))
        history.append({
            'timestamp': datetime.now().isoformat(),
            'content': payload.get('content', '')
        })
        metadata['repeat_history'] = history
        metadata['repeat_count'] = len(history)

        for key, value in incoming_metadata.items():
            if key not in metadata:
                metadata[key] = value
            else:
                if isinstance(value, list) and isinstance(metadata[key], list):
                    # Filter out non-hashable items for deduplication
                    hashable_items = []
                    non_hashable_items = []
                    all_items = metadata[key] + value

                    for item in all_items:
                        try:
                            hash(item)
                            hashable_items.append(item)
                        except TypeError:
                            non_hashable_items.append(item)

                    # Deduplicate hashable items and append non-hashable items
                    merged_list = list(dict.fromkeys(hashable_items)) + non_hashable_items
                    metadata[key] = merged_list
                elif isinstance(value, dict) and isinstance(metadata[key], dict):
                    metadata[key].update(value)
                else:
                    metadata[f"alt_{key}"] = value
        existing.metadata = metadata
        updated = True

        # Importance & consolidation boost
        importance_boost = max(0.03, (1 - similarity) * 0.12)
        proposed_importance = payload.get('importance', existing.importance)
        existing.importance = min(1.0, max(existing.importance, proposed_importance) + importance_boost)
        existing.consolidation_level = min(3, existing.consolidation_level + 1)
        existing.access_frequency += 1
        existing.last_accessed = datetime.now()
        updated = True

        if updated:
            self.db_manager.save_memory(existing)
            logger.debug(
                "🔁 Persona memory merged into %s (similarity %.3f, importance %.2f)",
                memory_id,
                similarity,
                existing.importance
            )

        await self._link_related_persona_memories(memory_id)

        return {
            'memory_id': memory_id,
            'merged': True,
            'duplicate_similarity': similarity,
            'updated_importance': existing.importance,
            'consolidation_level': existing.consolidation_level
        }

    async def _link_related_persona_memories(self, memory_id: str):
        if not self.db_manager or not self.vector_db:
            return

        memory = self.db_manager.load_memory(memory_id)
        if not memory or memory.embedding is None:
            return

        similar = self.vector_db.search(memory.embedding, k=5, threshold=0.35)
        associations = []
        for other_id, score in similar:
            if other_id == memory_id:
                continue
            other = self.db_manager.load_memory(other_id)
            if not other:
                continue
            if other.memory_type != 'persona' and 'persona' not in set(other.context_tags or []):
                continue
            associations.append(other_id)

        if associations:
            memory.associations = list(dict.fromkeys((memory.associations or []) + associations))
            self.db_manager.save_memory(memory)

    def _initialize_repeat_metadata(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        metadata = deepcopy(memory.get('metadata', {}) or {})
        history = list(metadata.get('repeat_history', []))
        history.append({
            'timestamp': datetime.now().isoformat(),
            'content': memory.get('content', '')
        })
        metadata['repeat_history'] = history
        metadata['repeat_count'] = len(history)
        return metadata

    async def synthesize_user_portrait(self, user_id: str = "default") -> Dict[str, Any]:
        """
        合成用户肖像 - 将碎片化的 persona 记忆整合成统一的用户描述

        Args:
            user_id: 用户ID

        Returns:
            Dict containing:
                - portrait: 用户肖像描述 (str)
                - likes: 喜好列表 (List[str])
                - dislikes: 不喜欢列表 (List[str])
                - interests: 兴趣列表 (List[str])
                - habits: 习惯列表 (List[str])
                - skills: 技能列表 (List[str])
                - goals: 目标列表 (List[str])
                - facts: 事实列表 (List[str])
        """
        # 🔥 2025-12-26: 优先使用 UserPortraitManager
        if self.portrait_manager:
            try:
                portrait_obj = self.portrait_manager.get_portrait(user_id)
                if portrait_obj:
                    return {
                        'portrait': portrait_obj.summary,
                        'likes': portrait_obj.likes,
                        'dislikes': portrait_obj.dislikes,
                        'interests': portrait_obj.interests,
                        'habits': portrait_obj.habits,
                        'skills': portrait_obj.skills,
                        'goals': portrait_obj.goals,
                        'facts': portrait_obj.facts
                    }
            except Exception as e:
                logger.warning(f"UserPortraitManager retrieval failed: {e}, falling back to DB query")

        # Fallback: 从数据库查询并合成
        if not self.db_manager:
            return {'portrait': '', 'likes': [], 'dislikes': [], 'interests': [],
                    'habits': [], 'skills': [], 'goals': [], 'facts': []}

        # 获取该用户的所有 persona 记忆
        all_memories = self.db_manager.load_memories_by_criteria(
            memory_type='persona',
            limit=200  # 获取足够多的记忆
        )

        # 按 user_id 过滤
        user_memories = []
        for mem in all_memories:
            mem_dict = mem.to_dict() if hasattr(mem, 'to_dict') else mem
            metadata = mem_dict.get('metadata', {}) or {}
            mem_user_id = metadata.get('user_id', 'default')
            if mem_user_id == user_id or mem_user_id == 'default':
                user_memories.append(mem_dict)

        # 按分类整理
        categorized = {
            'likes': [],
            'dislikes': [],
            'interests': [],
            'habits': [],
            'skills': [],
            'goals': [],
            'facts': []
        }

        for mem_dict in user_memories:
            content = mem_dict.get('content', '')
            metadata = mem_dict.get('metadata', {}) or {}
            pref_type = metadata.get('preference_type', '')
            category = metadata.get('structured_category', '')

            # 根据 preference_type 或 category 分类
            if pref_type in categorized:
                categorized[pref_type].append(content)
            elif category in categorized:
                categorized[category].append(content)
            else:
                # 默认归类为 facts
                categorized['facts'].append(content)

        # 使用 LLM 生成肖像摘要
        portrait_summary = await self._generate_portrait_with_llm(user_id, categorized)

        return {
            'portrait': portrait_summary,
            'likes': categorized.get('likes', [])[:10],
            'dislikes': categorized.get('dislikes', [])[:5],
            'interests': categorized.get('interests', [])[:10],
            'habits': categorized.get('habits', [])[:5],
            'skills': categorized.get('skills', [])[:5],
            'goals': categorized.get('goals', [])[:5],
            'facts': categorized.get('facts', [])[:10]
        }

    async def _generate_portrait_with_llm(self, user_id: str, categorized: Dict[str, List[str]]) -> str:
        """使用 LLM 生成用户肖像描述"""

        # 构建 prompt
        parts = []
        for category, items in categorized.items():
            if items:
                parts.append(f"{category}: {', '.join(items[:5])}")

        if not parts:
            return f"User {user_id}"

        context = "\n".join(parts)

        prompt = f"""Based on the following user information, write a concise 2-3 sentence user portrait:

{context}

Portrait (2-3 sentences):"""

        try:
            response = await self.call_llm(prompt, temperature=0.3, max_tokens=150)
            return response.strip()
        except Exception as e:
            logger.error(f"LLM portrait generation failed: {e}")
            return f"User {user_id} with various preferences and interests"

    async def get_user_portrait_for_qa(self, user_id: str = "default") -> str:
        """
        获取用于问答的用户肖像上下文

        Args:
            user_id: 用户ID

        Returns:
            用户肖像上下文字符串
        """
        portrait_data = await self.synthesize_user_portrait(user_id)

        parts = []
        if portrait_data.get('portrait'):
            parts.append(portrait_data['portrait'])

        if portrait_data.get('likes'):
            parts.append(f"Likes: {', '.join(portrait_data['likes'][:5])}")

        if portrait_data.get('interests'):
            parts.append(f"Interests: {', '.join(portrait_data['interests'][:5])}")

        if portrait_data.get('facts'):
            parts.append(f"Facts: {', '.join(portrait_data['facts'][:5])}")

        return " | ".join(parts) if parts else ""
