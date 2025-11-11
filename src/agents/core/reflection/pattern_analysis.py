"""
Pattern Analysis for Reflection Agent
模式分析模块 - 时间、内容、情感、访问等模式（扩展版）
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any

from ....memory.memory_item import MemoryItem

logger = logging.getLogger(__name__)


class PatternAnalysisMixin:
    """Pattern analysis mixin for ReflectionAgent (扩展版 - 12 methods)"""

    async def _analyze_behavioral_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """
        分析行为模式（主入口方法）

        分析内容：
        1. 决策模式
        2. 错误模式
        3. 成功模式
        4. 时间模式
        5. 上下文模式
        """
        # 将字典转换为MemoryItem（如果需要）
        memories = []
        for item in history:
            if isinstance(item, MemoryItem):
                memories.append(item)
            elif isinstance(item, dict) and 'content' in item:
                # 简单处理，实际应该更完整
                from ....memory.memory_item import MemoryItem as MI
                # 这里简化处理，假设已经有了MemoryItem
                pass

        patterns = {
            'recurring_errors': self._detect_recurring_errors(history),
            'success_patterns': self._identify_success_patterns(history),
            'temporal_patterns': self._analyze_temporal_patterns(memories) if memories else {},
            'context_patterns': self._analyze_context_patterns(history)
        }

        return patterns

    def _detect_recurring_errors(self, history: List[Dict]) -> List[Dict[str, Any]]:
        """
        检测重复出现的错误模式
        """
        error_patterns = defaultdict(int)
        error_details = defaultdict(list)

        for item in history:
            if isinstance(item, dict):
                # 查找错误相关的记录
                content = item.get('content', '')
                if any(word in content.lower() for word in ['error', 'failed', 'exception', 'mistake']):
                    # 提取错误类型
                    error_type = self._extract_error_type(content)
                    error_patterns[error_type] += 1
                    error_details[error_type].append({
                        'timestamp': item.get('timestamp', datetime.now()),
                        'content': content[:100]  # 前100字符
                    })

        # 返回出现2次以上的错误模式
        recurring = [
            {
                'error_type': error_type,
                'frequency': count,
                'examples': error_details[error_type][:3]  # 最多3个例子
            }
            for error_type, count in error_patterns.items()
            if count >= 2
        ]

        return sorted(recurring, key=lambda x: x['frequency'], reverse=True)

    def _identify_success_patterns(self, history: List[Dict]) -> List[Dict[str, Any]]:
        """
        识别成功模式
        """
        success_patterns = []

        # 查找高质量结果
        for item in history:
            if isinstance(item, dict):
                # 查找成功标记
                content = item.get('content', '')
                importance = item.get('importance', 0)

                if importance > 0.7 or any(word in content.lower() for word in ['success', 'achieved', 'completed', 'solved']):
                    success_patterns.append({
                        'content': content[:100],
                        'importance': importance,
                        'timestamp': item.get('timestamp', datetime.now()),
                        'context': item.get('context', [])
                    })

        return success_patterns[:10]  # Top 10 成功模式

    def _analyze_context_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """
        分析上下文模式
        """
        context_counts = defaultdict(int)

        for item in history:
            if isinstance(item, dict):
                contexts = item.get('context_tags', []) or item.get('context', [])
                for context in contexts:
                    context_counts[context] += 1

        return {
            'most_common_contexts': sorted(
                context_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            'total_unique_contexts': len(context_counts)
        }

    def _extract_error_type(self, content: str) -> str:
        """提取错误类型"""
        content_lower = content.lower()

        if 'timeout' in content_lower:
            return 'timeout_error'
        elif 'connection' in content_lower:
            return 'connection_error'
        elif 'permission' in content_lower or 'access' in content_lower:
            return 'permission_error'
        elif 'not found' in content_lower or '404' in content:
            return 'not_found_error'
        elif 'syntax' in content_lower:
            return 'syntax_error'
        elif 'memory' in content_lower:
            return 'memory_error'
        else:
            return 'general_error'

    async def _generate_pattern_insights(self, patterns: Dict[str, Any]) -> List[str]:
        """从发现的模式生成洞察"""
        insights = []

        # 从行为模式生成洞察
        if 'recurring_errors' in patterns and patterns['recurring_errors']:
            most_common_error = patterns['recurring_errors'][0]
            insights.append(
                f"Most frequent error: {most_common_error['error_type']} "
                f"(occurred {most_common_error['frequency']} times)"
            )

        # 从成功模式生成洞察
        if 'success_patterns' in patterns and patterns['success_patterns']:
            insights.append(
                f"Identified {len(patterns['success_patterns'])} successful outcomes "
                f"with high importance scores"
            )

        # 时间模式洞察
        temporal = patterns.get('temporal_patterns', {})
        if 'hourly' in temporal and temporal['hourly']:
            hourly = temporal['hourly']
            peak_hour = max(hourly, key=hourly.get) if hourly else None
            if peak_hour is not None:
                insights.append(f"Peak activity hour: {peak_hour}:00")

        # 内容主题洞察
        themes = patterns.get('content_themes', {})
        if themes:
            dominant_theme = max(themes, key=themes.get)
            insights.append(f"Dominant theme: {dominant_theme}")

        # 上下文模式洞察
        if 'context_patterns' in patterns:
            context_patterns = patterns['context_patterns']
            if context_patterns.get('most_common_contexts'):
                top_context = context_patterns['most_common_contexts'][0]
                insights.append(f"Most common context: {top_context[0]} ({top_context[1]} occurrences)")

        return insights

    def _calculate_overall_pattern_strength(self, patterns: Dict[str, Any]) -> float:
        """计算整体模式强度"""
        strength = 0.5  # 基础强度

        # 根据模式清晰度增加强度
        if patterns.get('temporal_patterns'):
            strength += 0.1
        if patterns.get('content_themes'):
            strength += 0.1
        if patterns.get('emotional_patterns'):
            strength += 0.1
        if patterns.get('consolidation_patterns'):
            strength += 0.1
        if patterns.get('recurring_errors'):
            strength += 0.1
        if patterns.get('success_patterns'):
            strength += 0.1

        return min(1.0, strength)

    def _analyze_temporal_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze temporal patterns in memory formation"""
        patterns = {}

        # Hour-of-day patterns
        hour_counts = defaultdict(int)
        for memory in memories:
            hour = memory.timestamp.hour
            hour_counts[hour] += 1
        patterns['hourly'] = dict(hour_counts)

        # Day-of-week patterns
        day_counts = defaultdict(int)
        for memory in memories:
            day = memory.timestamp.strftime('%A')
            day_counts[day] += 1
        patterns['daily'] = dict(day_counts)

        # Monthly patterns
        month_counts = defaultdict(int)
        for memory in memories:
            month = memory.timestamp.strftime('%B')
            month_counts[month] += 1
        patterns['monthly'] = dict(month_counts)

        return patterns

    def _analyze_content_themes(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze thematic content patterns"""
        themes = defaultdict(int)

        for memory in memories:
            # Simple keyword-based theme detection
            content_lower = memory.content.lower()

            # Work-related
            if any(word in content_lower for word in ['work', 'job', 'career', 'project', 'meeting']):
                themes['work'] += 1

            # Learning-related
            if any(word in content_lower for word in ['learn', 'study', 'understand', 'knowledge', 'skill']):
                themes['learning'] += 1

            # Relationship-related
            if any(word in content_lower for word in ['friend', 'family', 'relationship', 'social', 'people']):
                themes['relationships'] += 1

            # Health-related
            if any(word in content_lower for word in ['health', 'exercise', 'medical', 'wellness', 'fitness']):
                themes['health'] += 1

            # Creativity-related
            if any(word in content_lower for word in ['create', 'art', 'design', 'creative', 'innovation']):
                themes['creativity'] += 1

        return dict(themes)

    def _analyze_emotional_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze emotional patterns in memories"""
        emotions = defaultdict(int)
        intensity_sum = defaultdict(float)

        for memory in memories:
            for emotion in memory.emotion_tags:
                emotions[emotion] += 1
                intensity_sum[emotion] += memory.emotion_intensity

        # Calculate average intensities
        avg_intensities = {
            emotion: intensity_sum[emotion] / emotions[emotion]
            for emotion in emotions
        }

        return {
            'emotion_frequencies': dict(emotions),
            'average_intensities': avg_intensities,
            'dominant_emotion': max(emotions, key=emotions.get) if emotions else None
        }

    def _analyze_access_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze memory access patterns"""
        access_stats = {
            'total_accesses': sum(mem.access_frequency for mem in memories),
            'most_accessed': max(memories, key=lambda m: m.access_frequency) if memories else None,
            'average_accesses': sum(mem.access_frequency for mem in memories) / len(memories) if memories else 0
        }

        # Recent access patterns
        recent_accesses = [
            mem for mem in memories
            if mem.last_accessed and (datetime.now() - mem.last_accessed).days < 7
        ]

        access_stats['recent_access_count'] = len(recent_accesses)

        return access_stats

    def _analyze_consolidation_patterns(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze memory consolidation patterns"""
        consolidation_dist = defaultdict(int)

        for memory in memories:
            consolidation_dist[memory.consolidation_level] += 1

        return {
            'consolidation_distribution': dict(consolidation_dist),
            'average_consolidation': sum(mem.consolidation_level for mem in memories) / len(memories) if memories else 0,
            'fully_consolidated': consolidation_dist[3],
            'consolidation_rate': consolidation_dist[3] / len(memories) if memories else 0
        }

    def _analyze_association_networks(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze memory association network patterns"""
        total_associations = sum(len(mem.associations) for mem in memories)

        if not memories:
            return {'total_associations': 0, 'average_associations': 0}

        return {
            'total_associations': total_associations,
            'average_associations': total_associations / len(memories),
            'highly_connected': len([mem for mem in memories if len(mem.associations) > 5]),
            'isolated_memories': len([mem for mem in memories if len(mem.associations) == 0])
        }

    def _analyze_importance_trends(self, memories: List[MemoryItem]) -> Dict[str, Any]:
        """Analyze importance trends over time"""
        # Sort by timestamp
        sorted_memories = sorted(memories, key=lambda m: m.timestamp)

        if len(sorted_memories) < 2:
            return {'trend': 'insufficient_data'}

        # Simple trend analysis
        recent_importance = sum(mem.importance for mem in sorted_memories[-10:]) / min(10, len(sorted_memories))
        older_importance = sum(mem.importance for mem in sorted_memories[:10]) / min(10, len(sorted_memories))

        trend = 'increasing' if recent_importance > older_importance else 'decreasing'

        return {
            'trend': trend,
            'recent_avg_importance': recent_importance,
            'older_avg_importance': older_importance,
            'overall_avg_importance': sum(mem.importance for mem in memories) / len(memories)
        }
