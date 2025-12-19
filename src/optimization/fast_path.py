"""
Fast Path Detection for Simple Queries
快速路径检测 - 简单问题不需要完整推理

核心思想:
1. Direct fact retrieval: 已知事实直接返回,无需推理
2. Pattern matching: 识别常见query patterns
3. Confidence thresholding: 高confidence记忆直接使用

脑区对应: BasalGanglia (自动化程序) + Hippocampus (直接提取)
"""

from typing import Dict, List, Optional, Any, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class FastPathDetector:
    """
    快速路径检测器

    识别可以跳过复杂推理的query类型:
    - Simple fact queries: "What is X?", "When did Y happen?"
    - Direct memory retrieval: High confidence exact match
    - Yes/No questions with clear evidence
    """

    def __init__(self):
        # Query patterns that indicate simple factual retrieval
        self.simple_patterns = [
            # Temporal queries
            (r"when (did|was|is)", "temporal_fact"),
            (r"what (time|date|year|month)", "temporal_fact"),

            # Identity queries
            (r"who (is|was|are)", "identity_fact"),
            (r"what is .* (name|identity)", "identity_fact"),

            # Attribute queries
            (r"what (is|was|are) .* (work|job|field|profession)", "attribute_fact"),
            (r"where (did|does|do|is|was)", "location_fact"),

            # Existence queries
            (r"did .* (happen|occur|take place)", "existence_check"),
        ]

        self.stats = {
            'fast_path_detected': 0,
            'slow_path_required': 0,
            'confidence_bypass': 0
        }


    def detect_fast_path(
        self,
        query: str,
        retrieved_memories: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        检测是否可以使用fast path

        Returns:
            {
                'can_use_fast_path': bool,
                'path_type': str,  # 'simple_fact', 'high_confidence', 'direct_match'
                'direct_answer': str | None,
                'confidence': float,
                'reasoning': str
            }
            or None if slow path required
        """

        # 1️⃣ Check if query matches simple pattern
        path_type = self._match_simple_pattern(query)
        if path_type:
            # Try direct answer extraction
            direct_answer = self._try_direct_extraction(
                query, retrieved_memories, path_type
            )

            if direct_answer:
                self.stats['fast_path_detected'] += 1

                return {
                    'can_use_fast_path': True,
                    'path_type': path_type,
                    'direct_answer': direct_answer['answer'],
                    'confidence': direct_answer['confidence'],
                    'reasoning': f"Direct {path_type} extraction from high-confidence memory"
                }

        # 2️⃣ Check for high-confidence exact match
        high_conf_result = self._check_high_confidence_match(retrieved_memories)
        if high_conf_result:
            self.stats['confidence_bypass'] += 1

            return {
                'can_use_fast_path': True,
                'path_type': 'high_confidence',
                'direct_answer': high_conf_result['content'],
                'confidence': high_conf_result['confidence'],
                'reasoning': 'High-confidence direct memory match'
            }

        # 3️⃣ Slow path required
        self.stats['slow_path_required'] += 1
        return None

    def _match_simple_pattern(self, query: str) -> Optional[str]:
        """匹配简单query patterns"""
        query_lower = query.lower().strip()

        for pattern, path_type in self.simple_patterns:
            if re.search(pattern, query_lower):
                return path_type

        return None

    def _try_direct_extraction(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        path_type: str
    ) -> Optional[Dict[str, Any]]:
        """尝试从记忆中直接提取答案"""

        if not memories:
            return None

        # Sort by relevance/importance
        sorted_memories = sorted(
            memories,
            key=lambda m: m.get('relevance', 0) * m.get('importance', 0.5),
            reverse=True
        )

        # Try to extract from top memory
        top_memory = sorted_memories[0]
        content = top_memory.get('content', '')
        relevance = top_memory.get('relevance', 0)
        metadata = top_memory.get('metadata', {})

        # Only use if high relevance
        if relevance < 0.6:
            return None

        # Extract answer based on path_type
        answer = None
        confidence = relevance

        if path_type == 'temporal_fact':
            # 🔥 FIX: Extract temporal info with metadata support
            # Order: 1) Check for relative dates → force slow path if found
            #        2) Extract explicit dates from content (PRIORITIZED)
            #        3) Fallback to session_date metadata only if no content date AND query isn't event-specific
            answer = self._extract_temporal_info(content, metadata, query)
        elif path_type == 'identity_fact':
            # Identity questions require full context - use slow path
            return None
        elif path_type == 'attribute_fact':
            answer = self._extract_attribute_info(content, query)
        elif path_type == 'location_fact':
            answer = self._extract_location_info(content)
        elif path_type == 'existence_check':
            answer = f"Yes, {content}"
            confidence = 0.7

        if answer:
            return {
                'answer': answer,
                'confidence': confidence,
                'source_memory': content
            }

        return None

    def _extract_temporal_info(
        self,
        content: str,
        metadata: Dict[str, Any] = None,
        query: str = ""
    ) -> Optional[str]:
        """
        提取时间信息 - 优先从content匹配完整日期

        🔥 NEW: 对于需要推理的日期（如 "when born" 需要从 "yesterday" + session_date 推算），
        禁用fast path，让slow path (hippocampus) 处理

        Args:
            content: 记忆内容
            metadata: 记忆元数据（包含 session_date）
            query: 用户查询（用于判断是否是事件特定查询）
        """
        if metadata is None:
            metadata = {}

        query_lower = (query or '').lower()
        # Heuristic signals for event-specific queries (no hard-coded verb list)
        has_past_action = bool(re.search(r'\b(did|was|were)\s+\w+\s+\w+(ed|en|t|d)\b', query_lower))
        has_when_verb = bool(re.search(r'\bwhen\s+(did|was|were|has|have|had)\s+', query_lower))
        is_event_query = has_past_action or has_when_verb

        session_date = metadata.get('session_date')

        # 🔥 检测相对日期表达式 - 这些需要slow path推理
        relative_date_patterns = [
            r'\b(yesterday|today|tomorrow)\b',
            r'\b(last|next)\s+(week|month|year|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
            r'\b\d+\s+(days?|weeks?|months?|years?)\s+(ago|from now|before|after)\b',
            r'\bjust\s+(recently|now)\b',
            r'\ba\s+few\s+(days?|weeks?|months?)\s+ago\b',
        ]

        content_lower = content.lower()
        for pattern in relative_date_patterns:
            if re.search(pattern, content_lower):
                return None  # Force slow path for relative → absolute conversion

        # Match EXPLICIT date patterns in content - ORDERED from most specific to least specific
        patterns = [
            # Full dates with day, month, year (e.g., "8 May, 2023" or "May 8, 2023")
            r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',

            # Month and year (e.g., "May 2023")
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',

            # Year only (LAST resort - least specific)
            r'\d{4}',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                extracted_date = match.group(0)
                # Avoid prematurely returning conversation date for event-style queries
                if session_date and is_event_query and self._dates_equivalent(extracted_date, session_date):
                    continue
                return extracted_date

        # 🔥 NEW: If no explicit date in content, check metadata session_date as fallback
        # But use heuristics to detect if this is an event-specific query that needs content dates
        if session_date and session_date != 'Unknown date' and session_date != 'Unknown':
            # If query looks event-specific, force slow path for reasoning
            if is_event_query:
                return None  # Force slow path for event queries without explicit dates

            # Otherwise, safe to use session_date for general temporal context
            return session_date

        return None

    @staticmethod
    def _dates_equivalent(date_a: str, date_b: str) -> bool:
        """Rough check if two date strings refer to the same calendar date."""
        if not date_a or not date_b:
            return False

        def normalize(s: str) -> str:
            return re.sub(r'[^a-z0-9]', '', s.lower())

        norm_a = normalize(date_a)
        norm_b = normalize(date_b)
        if not norm_a or not norm_b:
            return False

        return norm_a in norm_b or norm_b in norm_a

    def _extract_identity_info(self, content: str) -> Optional[str]:
        """提取身份信息"""
        # Look for "is a/an" patterns
        patterns = [
            r'(is|was|identifies as)\s+(a|an)?\s*(\w+(?:\s+\w+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(3)

        return None

    def _extract_attribute_info(self, content: str, query: str) -> Optional[str]:
        """提取属性信息"""
        # Look for work/field mentions
        if 'work' in query.lower() or 'field' in query.lower():
            patterns = [
                r'works in\s+([^,\.]+)',
                r'field of\s+([^,\.]+)',
                r'profession[ally]?\s+([^,\.]+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    return match.group(1).strip()

        return None

    def _extract_location_info(self, content: str) -> Optional[str]:
        """提取地点信息"""
        # Look for location patterns
        patterns = [
            r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
            r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)

        return None

    def _check_high_confidence_match(
        self,
        memories: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """检查是否有高confidence的直接匹配"""

        if not memories:
            return None

        # Check top memory
        top_memory = memories[0]
        relevance = top_memory.get('relevance', 0)
        importance = top_memory.get('importance', 0.5)

        # Combined confidence
        confidence = relevance * importance

        # High confidence threshold
        if confidence >= 0.85:
            return {
                'content': top_memory.get('content', ''),
                'confidence': confidence
            }

        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total = self.stats['fast_path_detected'] + self.stats['slow_path_required']
        fast_path_rate = (self.stats['fast_path_detected'] / total * 100) if total > 0 else 0.0

        return {
            'fast_path_detected': self.stats['fast_path_detected'],
            'slow_path_required': self.stats['slow_path_required'],
            'confidence_bypass': self.stats['confidence_bypass'],
            'fast_path_rate': round(fast_path_rate, 1)
        }


# ============================================================
# Singleton Pattern with Thread Safety
# ============================================================
import threading

class FastPathDetectorSingleton:
    """
    Thread-safe singleton for FastPathDetector

    Pattern: Singleton with lazy initialization and thread safety
    Why: Stateful service that tracks fast path statistics
    """
    _instance: Optional['FastPathDetector'] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'FastPathDetector':
        """获取全局fast path detector实例 (thread-safe)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = FastPathDetector()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset singleton instance (mainly for testing)"""
        with cls._lock:
            cls._instance = None


def get_fast_path_detector() -> FastPathDetector:
    """获取全局fast path detector实例 (backward compatible)"""
    return FastPathDetectorSingleton.get_instance()

