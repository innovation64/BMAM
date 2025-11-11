"""
Conflict Detection for Prefrontal Agent
冲突检测模块
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConflictDetectionMixin:
    """Conflict detection mixin for PrefrontalAgent"""

    async def detect_conflicts(
        self,
        multi_source_results: Dict[str, List[Dict]]
    ) -> List[Dict[str, Any]]:
        """
        冲突检测: 检测多源记忆中的矛盾

        理论依据:
        - Botvinick et al. (2001) - Conflict Monitoring in ACC
        - Yeung et al. (2004) - ACC signals prediction errors
        - Carter & van Veen (2007) - Anterior Cingulate Cortex conflict detection

        冲突类型:
        1. **时间冲突** (Temporal Conflict): "Caroline昨天去了A" vs "Caroline昨天去了B"
        2. **事实冲突** (Factual Conflict): "Caroline是工程师" vs "Caroline是心理咨询师"
        3. **来源冲突** (Source Conflict): 内部记忆 vs 外部文档不一致

        Args:
            multi_source_results: {
                'episodic': [...],  # 来自Hippocampus
                'semantic': [...],  # 来自TemporalLobe
                'external': [...]   # 来自ExternalMemory (如果有)
            }

        Returns:
            [
                {
                    'conflict_type': 'temporal|factual|source',
                    'source1': {'type': 'episodic', 'content': '...', 'timestamp': '...'},
                    'source2': {'type': 'semantic', 'content': '...'},
                    'severity': float (0-1),
                    'explanation': str
                },
                ...
            ]
        """

        conflicts = []

        # Step 1: 收集所有记忆
        all_memories = []
        for source_type, memories in multi_source_results.items():
            # 跳过非列表类型的值 (如retrieval_time_ms等metadata)
            if not isinstance(memories, list):
                continue

            for mem in memories:
                # 兼容不同数据类型 (dict or str)
                if isinstance(mem, str):
                    all_memories.append({
                        'source_type': source_type,
                        'content': mem,
                        'timestamp': None,
                        'entities': [],
                        'metadata': {}
                    })
                elif isinstance(mem, dict):
                    content = mem.get('content', '')
                    if isinstance(content, dict):
                        content = str(content)

                    all_memories.append({
                        'source_type': source_type,
                        'content': content,
                        'timestamp': mem.get('timestamp'),
                        'entities': mem.get('entities', []),
                        'metadata': mem.get('metadata', {})
                    })
                else:
                    # 其他类型,转换为字符串
                    all_memories.append({
                        'source_type': source_type,
                        'content': str(mem),
                        'timestamp': None,
                        'entities': [],
                        'metadata': {}
                    })

        # Step 2: 两两比较检测冲突
        for i in range(len(all_memories)):
            for j in range(i + 1, len(all_memories)):
                mem1 = all_memories[i]
                mem2 = all_memories[j]

                # 2.1 时间冲突检测
                temporal_conflict = self._detect_temporal_conflict(mem1, mem2)
                if temporal_conflict:
                    conflicts.append(temporal_conflict)

                # 2.2 事实冲突检测
                factual_conflict = self._detect_factual_conflict(mem1, mem2)
                if factual_conflict:
                    conflicts.append(factual_conflict)

                # 2.3 来源冲突检测 (内部 vs 外部)
                if mem1['source_type'] != mem2['source_type']:
                    source_conflict = self._detect_source_conflict(mem1, mem2)
                    if source_conflict:
                        conflicts.append(source_conflict)

        # Step 3: 按严重性排序
        conflicts.sort(key=lambda x: x['severity'], reverse=True)

        if conflicts:
            logger.warning(f"⚠️ Detected {len(conflicts)} conflicts in multi-source memories")
            for conflict in conflicts[:3]:
                logger.warning(f"   - {conflict['conflict_type']}: {conflict['explanation']}")

        return conflicts

    def _detect_temporal_conflict(self, mem1: Dict, mem2: Dict) -> Optional[Dict]:
        """检测时间冲突"""
        # 如果两条记忆都有timestamp,且时间非常接近 (< 1小时)
        # 但描述的事件明显不同 (entity overlap < 0.3)
        if not (mem1.get('timestamp') and mem2.get('timestamp')):
            return None

        from datetime import datetime
        try:
            t1 = datetime.fromisoformat(str(mem1['timestamp']).replace('Z', '+00:00'))
            t2 = datetime.fromisoformat(str(mem2['timestamp']).replace('Z', '+00:00'))
            time_diff = abs((t1 - t2).total_seconds()) / 3600  # hours

            if time_diff < 1.0:  # 1小时内
                # 检查内容相似度
                overlap = self._entity_overlap(mem1.get('entities', []), mem2.get('entities', []))
                if overlap < 0.3:
                    return {
                        'conflict_type': 'temporal',
                        'source1': mem1,
                        'source2': mem2,
                        'severity': 1.0 - overlap,
                        'explanation': f"Two different events described at similar times ({time_diff:.1f}h apart)"
                    }
        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"Failed to detect temporal conflict: {e}")

        return None

    def _detect_factual_conflict(self, mem1: Dict, mem2: Dict) -> Optional[Dict]:
        """检测事实冲突"""
        # 使用简单的否定词检测
        content1 = str(mem1.get('content', '')).lower()
        content2 = str(mem2.get('content', '')).lower()

        # 简化版: 检测否定词 + 相同实体
        entities1 = set(mem1.get('entities', []))
        entities2 = set(mem2.get('entities', []))
        entities_overlap = entities1 & entities2

        if not entities_overlap:
            return None

        # 检测否定模式
        negation_patterns = [
            ('is', 'is not'),
            ('was', 'was not'),
            ('has', 'has not'),
            ('did', 'did not'),
        ]

        for pos, neg in negation_patterns:
            if (pos in content1 and neg in content2) or (neg in content1 and pos in content2):
                return {
                    'conflict_type': 'factual',
                    'source1': mem1,
                    'source2': mem2,
                    'severity': 0.8,
                    'explanation': f"Contradictory statements about {list(entities_overlap)[0] if entities_overlap else 'entities'}"
                }

        return None

    def _detect_source_conflict(self, mem1: Dict, mem2: Dict) -> Optional[Dict]:
        """检测来源冲突 (内部记忆 vs 外部文档)"""
        # 如果一个来自internal (episodic/semantic), 另一个来自external
        # 且内容相似但不完全一致
        internal_types = {'episodic', 'semantic', 'hippocampus', 'temporal'}
        external_types = {'external'}

        is_cross_source = (
            (mem1['source_type'] in internal_types and mem2['source_type'] in external_types) or
            (mem1['source_type'] in external_types and mem2['source_type'] in internal_types)
        )

        if not is_cross_source:
            return None

        # 检查实体重叠 (有共同关注点但描述不一致)
        entities1 = set(mem1.get('entities', []))
        entities2 = set(mem2.get('entities', []))
        entities_overlap = entities1 & entities2

        if len(entities_overlap) > 0:
            similarity = self._content_similarity(
                str(mem1.get('content', '')),
                str(mem2.get('content', ''))
            )
            if 0.3 < similarity < 0.7:  # 中等相似度 (既不完全相同,也不完全不同)
                return {
                    'conflict_type': 'source',
                    'source1': mem1,
                    'source2': mem2,
                    'severity': 0.6,
                    'explanation': f"Internal and external sources provide different information about {list(entities_overlap)[0] if entities_overlap else 'topic'}"
                }

        return None

    def _entity_overlap(self, entities1: List[str], entities2: List[str]) -> float:
        """计算实体重叠率"""
        if not entities1 or not entities2:
            return 0.0

        set1 = set([e.lower() for e in entities1])
        set2 = set([e.lower() for e in entities2])
        intersection = set1 & set2
        union = set1 | set2

        return len(intersection) / len(union) if union else 0.0

    def _content_similarity(self, content1: str, content2: str) -> float:
        """简单的内容相似度 (可以用embedding替代)"""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0

    # ============================================================
    # 🔥 Phase 4: 大规模文档处理 (Large-scale Document Processing)
    # ============================================================
