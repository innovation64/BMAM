"""
Metacognition Module - 元认知模块
P5: Reflection and Continuous Learning

核心功能:
1. 用户偏好抽取 (User Preference Extraction)
2. 置信度评估 (Confidence Evaluation)
3. 冲突检测 (Conflict Detection)
4. 持续学习循环 (Continuous Learning Loop)
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict, Counter
import re

logger = logging.getLogger(__name__)


class UserPreferenceExtractor:
    """
    用户偏好抽取器 (Enhanced for PersonaMem)

    从对话历史和记忆中提取用户偏好:
    - 喜好 (likes/dislikes) - 显式和隐式
    - 习惯 (habits)
    - 兴趣 (interests) - 活动、爱好、热情
    - 事实 (facts) - 用户分享的个人信息
    - 技能 (skills) - 用户擅长的事情
    - 价值观 (values)

    2025-12-22: 增强版，支持隐式偏好提取，提升 PersonaMem 性能
    """

    def __init__(self):
        self.preferences = defaultdict(list)  # {category: [preferences]}
        self.preference_confidence = {}  # {preference: confidence}
        self.preference_counts = Counter()  # {preference: count}

        # ====== 显式偏好模式 (Explicit Preferences) ======
        self.like_patterns = [
            r"(?:I\s+)?(?:really\s+)?(?:love|like|enjoy|prefer)\s+([^.,!?]+)",
            r"(?:I'm|I\s+am)\s+(?:a\s+fan\s+of|into)\s+([^.,!?]+)",
            r"([^.,!?]+)\s+is\s+(?:my\s+favorite|amazing|great)",
        ]

        self.dislike_patterns = [
            r"(?:I\s+)?(?:don't|do not|never)\s+(?:like|enjoy)\s+([^.,!?]+)",
            r"(?:I\s+)?(?:hate|dislike)\s+([^.,!?]+)",
            r"([^.,!?]+)\s+is\s+(?:terrible|awful|boring)",
        ]

        self.habit_patterns = [
            r"(?:I\s+)?(?:usually|always|often|regularly)\s+([^.,!?]+)",
            r"(?:every\s+(?:day|morning|evening))\s+(?:I\s+)?([^.,!?]+)",
        ]

        # ====== 隐式偏好模式 (Implicit Preferences) - NEW ======
        # 热情/兴趣表达 - 捕捉 "my passion for X", "fascinated by X"
        self.passion_patterns = [
            r"(?:my|a)\s+passion\s+(?:for|about)\s+([^.,!?]+)",
            r"(?:I'm|I\s+am)\s+(?:passionate|fascinated|excited)\s+(?:about|by)\s+([^.,!?]+)",
            r"(?:deeply\s+)?(?:interested|invested)\s+in\s+([^.,!?]+)",
            r"diving\s+(?:deeper\s+)?into\s+(?:my\s+)?(?:passion\s+for\s+)?([^.,!?]+)",
            r"(?:I\s+)?(?:find|found)\s+([^.,!?]+)\s+(?:fascinating|amazing|incredible)",
        ]

        # 活动/创作表达 - 捕捉 "I started creating X", "working on X"
        self.activity_patterns = [
            r"(?:I\s+)?(?:started|began|been)\s+(?:creating|making|producing|developing)\s+([^.,!?]+)",
            r"(?:I'm|I\s+am)\s+(?:working|experimenting)\s+(?:on|with)\s+([^.,!?]+)",
            r"(?:I\s+)?(?:spend|spent)\s+(?:my\s+)?(?:time|weekends?)\s+([^.,!?]+)",
            r"(?:I've|I\s+have)\s+been\s+([^.,!?]+ing[^.,!?]*)",
        ]

        # 个人事实模式 - 捕捉 "I am a X", "I work as X"
        self.fact_patterns = [
            r"(?:I'm|I\s+am)\s+(?:a|an)\s+([^.,!?]+)",
            r"(?:I\s+)?work\s+(?:as|in)\s+(?:a|an)?\s*([^.,!?]+)",
            r"(?:I\s+)?(?:was\s+)?born\s+(?:in|to)\s+([^.,!?]+)",
            r"(?:my\s+)?(?:family|heritage|background)\s+(?:is|are|comes?\s+from)\s+([^.,!?]+)",
            r"(?:I\s+)?(?:have|had)\s+(?:a\s+)?(?:background|experience)\s+in\s+([^.,!?]+)",
        ]

        # 技能模式 - 捕捉 "I'm good at X", "skilled in X"
        self.skill_patterns = [
            r"(?:I'm|I\s+am)\s+(?:good|skilled|proficient|experienced)\s+(?:at|in|with)\s+([^.,!?]+)",
            r"(?:I\s+)?(?:know\s+how\s+to|can)\s+([^.,!?]+)",
            r"(?:my\s+)?(?:expertise|skill)\s+(?:is|lies)\s+in\s+([^.,!?]+)",
        ]

        # 目标/意图模式 - 捕捉 "My goal is X", "I want to X"
        self.goal_patterns = [
            r"(?:my\s+)?(?:goal|dream|aim)\s+is\s+(?:to\s+)?([^.,!?]+)",
            r"(?:I\s+)?(?:want|hope|plan)\s+to\s+([^.,!?]+)",
            r"(?:I'm|I\s+am)\s+(?:trying|hoping|planning)\s+to\s+([^.,!?]+)",
        ]


    def extract_from_text(self, text: str) -> Dict[str, List[str]]:
        """
        从文本中提取偏好 (增强版)

        Args:
            text: 用户输入文本

        Returns:
            {
                'likes': [...],
                'dislikes': [...],
                'habits': [...],
                'interests': [...],  # NEW: 热情/兴趣
                'activities': [...], # NEW: 活动/创作
                'facts': [...],      # NEW: 个人事实
                'skills': [...],     # NEW: 技能
                'goals': [...]       # NEW: 目标/意图
            }
        """
        extracted = {
            'likes': [],
            'dislikes': [],
            'habits': [],
            'interests': [],
            'activities': [],
            'facts': [],
            'skills': [],
            'goals': []
        }

        # 提取喜好 (显式)
        for pattern in self.like_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                preference = self._clean_match(match)
                if preference:
                    extracted['likes'].append(preference)
                    self.preference_counts[f"like:{preference}"] += 1

        # 提取不喜欢
        for pattern in self.dislike_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                preference = self._clean_match(match)
                if preference:
                    extracted['dislikes'].append(preference)
                    self.preference_counts[f"dislike:{preference}"] += 1

        # 提取习惯
        for pattern in self.habit_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                habit = self._clean_match(match)
                if habit:
                    extracted['habits'].append(habit)
                    self.preference_counts[f"habit:{habit}"] += 1

        # ====== NEW: 隐式偏好提取 ======

        # 提取兴趣/热情 (隐式喜好)
        for pattern in self.passion_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                interest = self._clean_match(match)
                if interest:
                    extracted['interests'].append(interest)
                    # 同时记入 likes (兴趣即喜好)
                    extracted['likes'].append(interest)
                    self.preference_counts[f"interest:{interest}"] += 1
                    self.preference_counts[f"like:{interest}"] += 1

        # 提取活动
        for pattern in self.activity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                activity = self._clean_match(match)
                if activity:
                    extracted['activities'].append(activity)
                    self.preference_counts[f"activity:{activity}"] += 1

        # 提取个人事实
        for pattern in self.fact_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                fact = self._clean_match(match)
                if fact:
                    extracted['facts'].append(fact)
                    self.preference_counts[f"fact:{fact}"] += 1

        # 提取技能
        for pattern in self.skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = self._clean_match(match)
                if skill:
                    extracted['skills'].append(skill)
                    self.preference_counts[f"skill:{skill}"] += 1

        # 提取目标
        for pattern in self.goal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                goal = self._clean_match(match)
                if goal:
                    extracted['goals'].append(goal)
                    self.preference_counts[f"goal:{goal}"] += 1

        return extracted

    def _clean_match(self, match: str) -> Optional[str]:
        """清理匹配结果，过滤无效内容"""
        if not match:
            return None
        cleaned = match.strip()
        # 过滤太短或太长的
        if len(cleaned) < 3 or len(cleaned) > 100:
            return None
        # 过滤纯代词/冠词开头的无意义匹配
        stop_starts = ('it', 'this', 'that', 'the', 'a ', 'an ', 'to ', 'and ')
        if cleaned.lower().startswith(stop_starts):
            return None
        return cleaned

    def extract_from_memories(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从记忆集合中聚合偏好 (增强版)

        Args:
            memories: 记忆列表

        Returns:
            聚合的偏好统计，包含所有类别
        """
        # 所有类别
        all_preferences = {
            'likes': Counter(),
            'dislikes': Counter(),
            'habits': Counter(),
            'interests': Counter(),
            'activities': Counter(),
            'facts': Counter(),
            'skills': Counter(),
            'goals': Counter()
        }

        for memory in memories:
            content = memory.get('content', '')
            extracted = self.extract_from_text(content)

            # 聚合所有类别
            for category in all_preferences.keys():
                for item in extracted.get(category, []):
                    all_preferences[category][item] += 1

        # 计算置信度 (基于出现频率)
        total_memories = len(memories)
        for category in all_preferences:
            for item, count in all_preferences[category].items():
                confidence = min(count / total_memories, 1.0) if total_memories > 0 else 0
                self.preference_confidence[f"{category}:{item}"] = confidence

        # 返回所有类别的 top items
        result = {
            category: dict(counter.most_common(10))
            for category, counter in all_preferences.items()
        }
        result['confidence'] = self.preference_confidence

        return result

    def get_structured_preferences(self) -> Dict[str, Any]:
        """
        获取结构化的偏好数据 (用于 PersonaMemory 存储)

        Returns:
            结构化偏好字典，适合存储到 metadata
        """
        structured = {
            'preference_categories': {},
            'total_count': 0,
            'by_type': {}
        }

        # 按类别分组
        for pref_key, count in self.preference_counts.items():
            parts = pref_key.split(':', 1)
            if len(parts) == 2:
                category, value = parts
                if category not in structured['by_type']:
                    structured['by_type'][category] = []
                structured['by_type'][category].append({
                    'value': value,
                    'count': count,
                    'confidence': self.preference_confidence.get(pref_key, 0.5)
                })
                structured['total_count'] += count

        # 排序每个类别
        for category in structured['by_type']:
            structured['by_type'][category].sort(key=lambda x: x['count'], reverse=True)

        return structured

    def get_preference_summary(self) -> Dict[str, Any]:
        """获取偏好摘要 (增强版)"""
        categories = {}
        for prefix in ['like', 'dislike', 'habit', 'interest', 'activity', 'fact', 'skill', 'goal']:
            categories[prefix] = sum(1 for k in self.preference_counts if k.startswith(f'{prefix}:'))

        return {
            'total_preferences': sum(self.preference_counts.values()),
            'categories': categories,
            'top_preferences': self.preference_counts.most_common(10)
        }


class ConfidenceEvaluator:
    """
    置信度评估器

    评估系统对回答/记忆的置信度:
    - 记忆一致性
    - 信息完整性
    - 时间可靠性
    """

    def __init__(self):
        self.evaluation_history = []

    def evaluate_memory_confidence(self, memory: Dict[str, Any], context: Dict[str, Any] = None) -> float:
        """
        评估单个记忆的置信度

        Args:
            memory: 记忆对象
            context: 上下文信息

        Returns:
            置信度分数 (0.0-1.0)
        """
        confidence_factors = []

        # 1. 访问次数 (经常访问的记忆更可靠)
        access_count = memory.get('access_count', 0)
        access_confidence = min(access_count / 10.0, 1.0)
        confidence_factors.append(('access_frequency', access_confidence, 0.2))

        # 2. 重要性 (用户标记的重要性)
        importance = memory.get('importance', 0.5)
        confidence_factors.append(('importance', importance, 0.3))

        # 3. 时间新近性 (最近的记忆更可靠)
        timestamp = memory.get('timestamp')
        if timestamp:
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except (ValueError, TypeError) as e:
                    logger.debug(f"Failed to parse timestamp: {e}")
                    timestamp = None

            if timestamp:
                age_days = (datetime.now() - timestamp).days
                recency_confidence = max(1.0 - age_days / 365.0, 0.1)  # 1年后降到0.1
                confidence_factors.append(('recency', recency_confidence, 0.2))

        # 4. 内容完整性 (有实体、情绪等信息的记忆更可靠)
        has_entities = len(memory.get('entities', [])) > 0
        has_emotion = len(memory.get('emotion_tags', [])) > 0
        has_metadata = len(memory.get('metadata', {})) > 0

        completeness = (
            (0.4 if has_entities else 0) +
            (0.3 if has_emotion else 0) +
            (0.3 if has_metadata else 0)
        )
        confidence_factors.append(('completeness', completeness, 0.15))

        # 5. KG关系 (有知识图谱关系的记忆更结构化)
        has_kg_relations = memory.get('metadata', {}).get('kg_relations') is not None
        kg_confidence = 1.0 if has_kg_relations else 0.5
        confidence_factors.append(('knowledge_graph', kg_confidence, 0.15))

        # 加权平均
        total_confidence = sum(score * weight for _, score, weight in confidence_factors)

        return round(total_confidence, 3)

    def evaluate_response_confidence(
        self,
        response: str,
        supporting_memories: List[Dict[str, Any]],
        query: str = ""
    ) -> Dict[str, Any]:
        """
        评估回答的置信度

        Args:
            response: 系统回答
            supporting_memories: 支持此回答的记忆
            query: 用户查询

        Returns:
            置信度评估结果
        """
        if not supporting_memories:
            return {
                'confidence': 0.1,
                'reason': 'No supporting memories',
                'level': 'very_low'
            }

        # 1. 记忆置信度平均值
        memory_confidences = [
            self.evaluate_memory_confidence(mem)
            for mem in supporting_memories
        ]
        avg_memory_confidence = sum(memory_confidences) / len(memory_confidences)

        # 2. 记忆数量 (多个记忆支持提高置信度)
        memory_count_factor = min(len(supporting_memories) / 5.0, 1.0)

        # 3. 记忆一致性 (如果多个记忆内容相似，置信度更高)
        consistency_score = self._evaluate_memory_consistency(supporting_memories)

        # 4. 响应完整性 (更长更详细的回答通常更可靠)
        response_length_factor = min(len(response) / 200.0, 1.0)

        # 综合置信度
        confidence = (
            0.4 * avg_memory_confidence +
            0.2 * memory_count_factor +
            0.3 * consistency_score +
            0.1 * response_length_factor
        )

        # 置信度等级
        if confidence >= 0.8:
            level = 'very_high'
        elif confidence >= 0.6:
            level = 'high'
        elif confidence >= 0.4:
            level = 'medium'
        elif confidence >= 0.2:
            level = 'low'
        else:
            level = 'very_low'

        # 记录评估
        evaluation = {
            'confidence': round(confidence, 3),
            'level': level,
            'factors': {
                'memory_confidence': round(avg_memory_confidence, 3),
                'memory_count': len(supporting_memories),
                'consistency': round(consistency_score, 3),
                'response_completeness': round(response_length_factor, 3)
            },
            'supporting_memories': len(supporting_memories)
        }

        self.evaluation_history.append({
            'timestamp': datetime.now().isoformat(),
            'evaluation': evaluation
        })

        return evaluation

    def _evaluate_memory_consistency(self, memories: List[Dict[str, Any]]) -> float:
        """评估记忆之间的一致性"""
        if len(memories) < 2:
            return 1.0  # 单个记忆默认一致

        # 简化版: 检查实体重叠
        all_entities = []
        for mem in memories:
            all_entities.extend(mem.get('entities', []))

        if not all_entities:
            return 0.5  # 没有实体信息，中等一致性

        # 计算实体重复率
        entity_counts = Counter(all_entities)
        repeated_entities = sum(1 for count in entity_counts.values() if count > 1)
        consistency = repeated_entities / len(entity_counts) if entity_counts else 0.5

        return min(consistency, 1.0)


class ConflictDetector:
    """
    冲突检测器

    检测矛盾信息:
    - 时间冲突 (同一时间不同事件)
    - 事实冲突 (互相矛盾的陈述)
    - 偏好冲突 (先说喜欢后说不喜欢)
    """

    def __init__(self):
        self.detected_conflicts = []

    def detect_conflicts(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测记忆中的冲突

        Args:
            memories: 记忆列表

        Returns:
            冲突列表
        """
        conflicts = []

        # 1. 时间冲突检测
        temporal_conflicts = self._detect_temporal_conflicts(memories)
        conflicts.extend(temporal_conflicts)

        # 2. 实体关系冲突检测
        relation_conflicts = self._detect_relation_conflicts(memories)
        conflicts.extend(relation_conflicts)

        # 3. 偏好冲突检测
        preference_conflicts = self._detect_preference_conflicts(memories)
        conflicts.extend(preference_conflicts)

        # 记录检测到的冲突
        self.detected_conflicts.extend(conflicts)

        return conflicts

    def _detect_temporal_conflicts(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测时间冲突"""
        conflicts = []

        # 按时间分组
        time_groups = defaultdict(list)
        for mem in memories:
            timestamp = mem.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Failed to parse timestamp for temporal conflict detection: {e}")
                        continue

                # 按小时分组
                time_key = timestamp.strftime('%Y-%m-%d %H')
                time_groups[time_key].append(mem)

        # 检查同一时间段内的不同事件
        for time_key, mems in time_groups.items():
            if len(mems) > 1:
                # 简化检测: 如果内容完全不同，可能是冲突
                unique_contents = set(mem.get('content', '') for mem in mems)
                if len(unique_contents) > 1:
                    conflicts.append({
                        'type': 'temporal',
                        'time': time_key,
                        'conflicting_memories': [m.get('id') for m in mems],
                        'severity': 'low',  # 可能只是同时发生的多个事件
                        'description': f"Multiple events at {time_key}"
                    })

        return conflicts

    def _detect_relation_conflicts(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测关系冲突 (KG)"""
        conflicts = []

        # 收集所有KG关系
        relations = defaultdict(set)  # {(source, relation): set(targets)}

        for mem in memories:
            kg_relations = mem.get('metadata', {}).get('kg_relations', [])
            for rel in kg_relations:
                source = rel.get('source', '').lower()
                relation_type = rel.get('relation', '').lower()
                target = rel.get('target', '').lower()

                if source and relation_type and target:
                    key = (source, relation_type)
                    relations[key].add(target)

        # 检测冲突: 同一个 (source, relation) 有多个不同的 target
        for (source, relation_type), targets in relations.items():
            if len(targets) > 1:
                # 某些关系允许多个target (如 "likes")
                if relation_type not in ['likes', 'enjoys', 'knows', 'visited']:
                    conflicts.append({
                        'type': 'relation',
                        'source': source,
                        'relation': relation_type,
                        'conflicting_targets': list(targets),
                        'severity': 'medium',
                        'description': f"{source} has conflicting {relation_type}: {', '.join(targets)}"
                    })

        return conflicts

    def _detect_preference_conflicts(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测偏好冲突"""
        conflicts = []

        # 提取偏好
        extractor = UserPreferenceExtractor()
        likes = set()
        dislikes = set()

        for mem in memories:
            content = mem.get('content', '')
            prefs = extractor.extract_from_text(content)
            likes.update(prefs['likes'])
            dislikes.update(prefs['dislikes'])

        # 检测冲突: 同时喜欢和不喜欢同一事物
        overlap = likes & dislikes
        if overlap:
            for item in overlap:
                conflicts.append({
                    'type': 'preference',
                    'item': item,
                    'severity': 'high',
                    'description': f"Conflicting preference: both likes and dislikes '{item}'"
                })

        return conflicts


class ContinuousLearner:
    """
    持续学习器

    实现反思→调整→优化循环:
    1. Reflect: 分析当前状态和历史表现
    2. Adjust: 根据反思结果调整策略
    3. Optimize: 持续优化系统参数
    """

    def __init__(self, preference_extractor, confidence_evaluator, conflict_detector):
        self.preference_extractor = preference_extractor
        self.confidence_evaluator = confidence_evaluator
        self.conflict_detector = conflict_detector

        self.learning_history = []
        self.adjustments_made = []


    async def reflect(self, memories: List[Dict[str, Any]], interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        反思阶段: 分析当前状态

        Args:
            memories: 记忆列表
            interactions: 交互历史

        Returns:
            反思结果
        """
        reflection = {
            'timestamp': datetime.now().isoformat(),
            'memories_analyzed': len(memories),
            'interactions_analyzed': len(interactions)
        }

        # 1. 用户偏好分析
        preferences = self.preference_extractor.extract_from_memories(memories)
        reflection['user_preferences'] = preferences

        # 2. 置信度分析
        if self.confidence_evaluator.evaluation_history:
            avg_confidence = sum(
                e['evaluation']['confidence']
                for e in self.confidence_evaluator.evaluation_history
            ) / len(self.confidence_evaluator.evaluation_history)
            reflection['average_confidence'] = round(avg_confidence, 3)
        else:
            reflection['average_confidence'] = 0.5

        # 3. 冲突检测
        conflicts = self.conflict_detector.detect_conflicts(memories)
        reflection['conflicts_detected'] = len(conflicts)
        reflection['conflicts'] = conflicts

        # 4. 学习趋势
        reflection['learning_trends'] = self._analyze_learning_trends()

        self.learning_history.append(reflection)

        return reflection

    def adjust(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        调整阶段: 根据反思结果调整策略

        Args:
            reflection: 反思结果

        Returns:
            调整建议
        """
        adjustments = {
            'timestamp': datetime.now().isoformat(),
            'based_on_reflection': reflection.get('timestamp'),
            'recommendations': []
        }

        # 1. 基于置信度的调整
        avg_confidence = reflection.get('average_confidence', 0.5)
        if avg_confidence < 0.5:
            adjustments['recommendations'].append({
                'type': 'confidence_improvement',
                'priority': 'high',
                'action': 'Increase memory consolidation frequency',
                'reason': f'Low average confidence: {avg_confidence:.2f}'
            })

        # 2. 基于冲突的调整
        conflicts_count = reflection.get('conflicts_detected', 0)
        if conflicts_count > 0:
            adjustments['recommendations'].append({
                'type': 'conflict_resolution',
                'priority': 'medium',
                'action': 'Review and resolve detected conflicts',
                'reason': f'{conflicts_count} conflicts detected',
                'conflicts': reflection.get('conflicts', [])
            })

        # 3. 基于偏好的调整
        preferences = reflection.get('user_preferences', {})
        if preferences.get('likes'):
            adjustments['recommendations'].append({
                'type': 'personalization',
                'priority': 'low',
                'action': 'Adjust response style based on user preferences',
                'preferences': preferences
            })

        self.adjustments_made.append(adjustments)

        return adjustments

    def optimize(self, adjustments: Dict[str, Any]) -> Dict[str, Any]:
        """
        优化阶段: 应用调整建议

        Args:
            adjustments: 调整建议

        Returns:
            优化结果
        """
        optimization = {
            'timestamp': datetime.now().isoformat(),
            'based_on_adjustments': adjustments.get('timestamp'),
            'optimizations_applied': []
        }

        for rec in adjustments.get('recommendations', []):
            # 🔥 2025-12-15: 优化建议由 LearningManager.apply_learning_to_weights() 实际应用
            # ContinuousLearner 只负责生成建议，不直接执行
            optimization['optimizations_applied'].append({
                'type': rec['type'],
                'action': rec['action'],
                'priority': rec.get('priority', 'medium'),
                'status': 'pending_application',  # 等待 LearningManager 应用
                'conflicts': rec.get('conflicts', [])  # 传递冲突信息供实际解决
            })


        return optimization

    def _analyze_learning_trends(self) -> Dict[str, Any]:
        """分析学习趋势"""
        if len(self.learning_history) < 2:
            return {'trend': 'insufficient_data'}

        # 比较最近两次反思
        recent = self.learning_history[-1]
        previous = self.learning_history[-2]

        confidence_trend = (
            recent.get('average_confidence', 0) -
            previous.get('average_confidence', 0)
        )

        conflicts_trend = (
            recent.get('conflicts_detected', 0) -
            previous.get('conflicts_detected', 0)
        )

        return {
            'confidence_change': round(confidence_trend, 3),
            'conflicts_change': conflicts_trend,
            'trend': 'improving' if confidence_trend > 0 and conflicts_trend <= 0 else 'needs_attention'
        }


# ============================================================
# Singleton Pattern with Thread Safety
# ============================================================
import threading

class MetacognitionSingletons:
    """
    Thread-safe singletons for metacognition components

    Pattern: Singleton with lazy initialization and thread safety
    Why: These are stateful services that track global learning state
    """
    _preference_extractor: Optional[UserPreferenceExtractor] = None
    _confidence_evaluator: Optional[ConfidenceEvaluator] = None
    _conflict_detector: Optional[ConflictDetector] = None
    _continuous_learner: Optional[ContinuousLearner] = None
    _lock = threading.RLock()  # Fixed: Use RLock for reentrant locking (get_continuous_learner calls other getters)

    @classmethod
    def get_preference_extractor(cls) -> UserPreferenceExtractor:
        """获取用户偏好提取器单例 (thread-safe)"""
        if cls._preference_extractor is None:
            with cls._lock:
                if cls._preference_extractor is None:
                    cls._preference_extractor = UserPreferenceExtractor()
        return cls._preference_extractor

    @classmethod
    def get_confidence_evaluator(cls) -> ConfidenceEvaluator:
        """获取置信度评估器单例 (thread-safe)"""
        if cls._confidence_evaluator is None:
            with cls._lock:
                if cls._confidence_evaluator is None:
                    cls._confidence_evaluator = ConfidenceEvaluator()
        return cls._confidence_evaluator

    @classmethod
    def get_conflict_detector(cls) -> ConflictDetector:
        """获取冲突检测器单例 (thread-safe)"""
        if cls._conflict_detector is None:
            with cls._lock:
                if cls._conflict_detector is None:
                    cls._conflict_detector = ConflictDetector()
        return cls._conflict_detector

    @classmethod
    def get_continuous_learner(cls) -> ContinuousLearner:
        """获取持续学习器单例 (thread-safe)"""
        if cls._continuous_learner is None:
            with cls._lock:
                if cls._continuous_learner is None:
                    cls._continuous_learner = ContinuousLearner(
                        cls.get_preference_extractor(),
                        cls.get_confidence_evaluator(),
                        cls.get_conflict_detector()
                    )
        return cls._continuous_learner

    @classmethod
    def reset_all(cls):
        """Reset all singletons (mainly for testing)"""
        with cls._lock:
            cls._preference_extractor = None
            cls._confidence_evaluator = None
            cls._conflict_detector = None
            cls._continuous_learner = None


# Backward-compatible factory functions
def get_preference_extractor() -> UserPreferenceExtractor:
    """获取用户偏好提取器单例 (backward compatible)"""
    return MetacognitionSingletons.get_preference_extractor()


def get_confidence_evaluator() -> ConfidenceEvaluator:
    """获取置信度评估器单例 (backward compatible)"""
    return MetacognitionSingletons.get_confidence_evaluator()


def get_conflict_detector() -> ConflictDetector:
    """获取冲突检测器单例 (backward compatible)"""
    return MetacognitionSingletons.get_conflict_detector()


def get_continuous_learner() -> ContinuousLearner:
    """获取持续学习器单例 (backward compatible)"""
    return MetacognitionSingletons.get_continuous_learner()

