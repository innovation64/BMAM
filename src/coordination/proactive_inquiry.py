"""
Proactive Inquiry Manager - 主动询问机制
检测矛盾、知识缺口和模糊信息，主动向用户寻求澄清

设计理念:
- 基于脑科学中的前扣带皮层 (ACC) 冲突监控机制
- 当检测到矛盾信息时，主动暂停并寻求用户澄清
- 避免基于错误假设生成错误回答
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class InquiryType(Enum):
    """询问类型"""
    CONTRADICTION = "contradiction"        # 矛盾信息
    KNOWLEDGE_GAP = "knowledge_gap"        # 知识缺口
    AMBIGUITY = "ambiguity"               # 歧义/模糊
    TEMPORAL_CONFLICT = "temporal_conflict"  # 时间冲突
    CONFIDENCE_LOW = "confidence_low"      # 置信度低


@dataclass
class InquiryContext:
    """询问上下文"""
    inquiry_type: InquiryType
    severity: float  # 0-1, 越高越严重
    conflicting_sources: List[Dict[str, Any]] = field(default_factory=list)
    suggested_question: str = ""
    explanation: str = ""
    original_query: str = ""
    related_entities: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class InquiryResult:
    """询问结果"""
    should_inquire: bool
    inquiries: List[InquiryContext] = field(default_factory=list)
    formatted_prompt: str = ""
    bypass_response: bool = False  # 是否跳过正常响应，直接询问


class ProactiveInquiryManager:
    """
    主动询问管理器

    功能:
    1. 检测记忆中的矛盾信息
    2. 识别知识缺口和歧义
    3. 生成自然的澄清问题
    4. 决定何时中断响应流程进行主动询问

    触发条件:
    - 检测到高严重性矛盾 (severity > 0.7)
    - 关键信息缺失
    - 置信度过低 (< 0.4)
    """

    # 配置阈值
    CONTRADICTION_SEVERITY_THRESHOLD = 0.6  # 矛盾严重性阈值
    INQUIRY_TRIGGER_THRESHOLD = 0.7         # 触发主动询问的阈值
    LOW_CONFIDENCE_THRESHOLD = 0.4          # 低置信度阈值
    MAX_INQUIRIES_PER_TURN = 2              # 每轮最多询问数

    def __init__(self, prefrontal_agent=None, result_arbiter=None):
        self.prefrontal_agent = prefrontal_agent
        self.result_arbiter = result_arbiter

        # 追踪历史询问，避免重复
        self.recent_inquiries: List[InquiryContext] = []
        self.inquiry_cooldown: Dict[str, datetime] = {}  # entity -> last_inquiry_time

    async def analyze_for_inquiry(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        confidence: float,
        response_draft: Optional[str] = None
    ) -> InquiryResult:
        """
        分析是否需要主动询问

        Args:
            query: 用户查询
            memories: 检索到的记忆
            confidence: 当前置信度
            response_draft: 准备返回的回答草稿

        Returns:
            InquiryResult: 询问分析结果
        """
        inquiries = []

        # 1. 检测矛盾信息
        contradiction_inquiries = await self._detect_contradictions(query, memories)
        inquiries.extend(contradiction_inquiries)

        # 2. 检测时间冲突
        temporal_inquiries = self._detect_temporal_conflicts(query, memories)
        inquiries.extend(temporal_inquiries)

        # 3. 检测知识缺口
        gap_inquiries = self._detect_knowledge_gaps(query, memories, response_draft)
        inquiries.extend(gap_inquiries)

        # 4. 检测低置信度情况
        if confidence < self.LOW_CONFIDENCE_THRESHOLD:
            low_conf_inquiry = self._create_low_confidence_inquiry(query, confidence, memories)
            if low_conf_inquiry:
                inquiries.append(low_conf_inquiry)

        # 5. 过滤重复询问和冷却中的询问
        filtered_inquiries = self._filter_recent_inquiries(inquiries)

        # 6. 按严重性排序，取最重要的几个
        filtered_inquiries.sort(key=lambda x: x.severity, reverse=True)
        top_inquiries = filtered_inquiries[:self.MAX_INQUIRIES_PER_TURN]

        # 7. 决定是否触发询问
        should_inquire = any(inq.severity >= self.INQUIRY_TRIGGER_THRESHOLD for inq in top_inquiries)

        # 8. 生成格式化的询问提示
        formatted_prompt = ""
        if should_inquire and top_inquiries:
            formatted_prompt = self._format_inquiry_prompt(top_inquiries)

            # 记录这次询问
            self.recent_inquiries.extend(top_inquiries)
            for inq in top_inquiries:
                for entity in inq.related_entities:
                    self.inquiry_cooldown[entity] = datetime.now()

        return InquiryResult(
            should_inquire=should_inquire,
            inquiries=top_inquiries,
            formatted_prompt=formatted_prompt,
            bypass_response=should_inquire and any(inq.severity >= 0.9 for inq in top_inquiries)
        )

    async def _detect_contradictions(
        self,
        query: str,
        memories: List[Dict[str, Any]]
    ) -> List[InquiryContext]:
        """检测记忆中的矛盾"""
        inquiries = []

        if not self.prefrontal_agent:
            return inquiries

        try:
            # 使用 Prefrontal Agent 的冲突检测
            multi_source = {'episodic': memories}
            conflicts = await self.prefrontal_agent.detect_conflicts(multi_source)

            for conflict in conflicts:
                if conflict.get('severity', 0) >= self.CONTRADICTION_SEVERITY_THRESHOLD:
                    # 提取冲突实体
                    entities = self._extract_entities_from_conflict(conflict)

                    # 生成澄清问题
                    question = self._generate_contradiction_question(conflict, entities)

                    inquiries.append(InquiryContext(
                        inquiry_type=InquiryType.CONTRADICTION,
                        severity=conflict.get('severity', 0.7),
                        conflicting_sources=[
                            conflict.get('source1', {}),
                            conflict.get('source2', {})
                        ],
                        suggested_question=question,
                        explanation=conflict.get('explanation', ''),
                        original_query=query,
                        related_entities=entities
                    ))

        except Exception as e:
            logger.warning(f"Error detecting contradictions: {e}")

        return inquiries

    def _detect_temporal_conflicts(
        self,
        query: str,
        memories: List[Dict[str, Any]]
    ) -> List[InquiryContext]:
        """检测时间冲突"""
        inquiries = []

        # 按实体分组记忆
        entity_memories: Dict[str, List[Dict]] = {}
        for mem in memories:
            entities = mem.get('entities', [])
            for entity in entities:
                if entity not in entity_memories:
                    entity_memories[entity] = []
                entity_memories[entity].append(mem)

        # 检查每个实体的记忆是否有时间冲突
        for entity, mems in entity_memories.items():
            if len(mems) < 2:
                continue

            # 检查同一天的不同事件描述
            dated_mems = []
            for m in mems:
                event_time = m.get('metadata', {}).get('event_time')
                if event_time:
                    try:
                        if isinstance(event_time, str):
                            dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                        else:
                            dt = event_time
                        dated_mems.append((dt.date(), m))
                    except (ValueError, AttributeError):
                        pass

            # 按日期分组
            date_groups: Dict[str, List[Dict]] = {}
            for date, m in dated_mems:
                date_str = str(date)
                if date_str not in date_groups:
                    date_groups[date_str] = []
                date_groups[date_str].append(m)

            # 检查同一天有多个不同内容的记忆
            for date_str, day_mems in date_groups.items():
                if len(day_mems) >= 2:
                    contents = [m.get('content', '')[:100] for m in day_mems]
                    if self._are_contents_conflicting(contents):
                        question = f"关于 {entity} 在 {date_str} 的活动，我找到了不同的记录。您能帮我确认一下具体情况吗？"

                        inquiries.append(InquiryContext(
                            inquiry_type=InquiryType.TEMPORAL_CONFLICT,
                            severity=0.65,
                            conflicting_sources=day_mems,
                            suggested_question=question,
                            explanation=f"Same date ({date_str}) but different activities for {entity}",
                            original_query=query,
                            related_entities=[entity]
                        ))

        return inquiries

    def _detect_knowledge_gaps(
        self,
        query: str,
        memories: List[Dict[str, Any]],
        response_draft: Optional[str]
    ) -> List[InquiryContext]:
        """检测知识缺口"""
        inquiries = []

        # 提取查询中的关键实体
        query_entities = self._extract_query_entities(query)

        # 检查是否有实体完全没有记忆
        memory_entities = set()
        for mem in memories:
            memory_entities.update(mem.get('entities', []))

        missing_entities = [e for e in query_entities if e.lower() not in
                          {me.lower() for me in memory_entities}]

        if missing_entities:
            question = f"关于 {', '.join(missing_entities[:2])}，我没有找到相关记忆。您能提供一些背景信息吗？"

            inquiries.append(InquiryContext(
                inquiry_type=InquiryType.KNOWLEDGE_GAP,
                severity=0.5,  # 中等严重性
                suggested_question=question,
                explanation=f"No memories found for: {', '.join(missing_entities)}",
                original_query=query,
                related_entities=missing_entities
            ))

        return inquiries

    def _create_low_confidence_inquiry(
        self,
        query: str,
        confidence: float,
        memories: List[Dict[str, Any]]
    ) -> Optional[InquiryContext]:
        """创建低置信度询问"""

        # 分析置信度低的原因
        reasons = []
        if len(memories) == 0:
            reasons.append("没有找到相关记忆")
        elif len(memories) == 1:
            reasons.append("只找到一条相关记忆")

        # 检查记忆的质量
        low_quality_count = sum(1 for m in memories
                               if m.get('metadata', {}).get('confidence', 0) < 0.5)
        if low_quality_count > len(memories) / 2:
            reasons.append("记忆质量较低")

        if not reasons:
            reasons.append("信息可能不完整")

        reason_text = "、".join(reasons)
        question = f"我对这个问题的回答不太确定（{reason_text}）。您能确认一下我的理解是否正确吗？"

        return InquiryContext(
            inquiry_type=InquiryType.CONFIDENCE_LOW,
            severity=0.4 + (0.4 - confidence),  # 置信度越低，严重性越高
            suggested_question=question,
            explanation=f"Low confidence ({confidence:.2f}): {reason_text}",
            original_query=query,
            related_entities=[]
        )

    def _extract_entities_from_conflict(self, conflict: Dict) -> List[str]:
        """从冲突中提取实体"""
        entities = set()

        for source in [conflict.get('source1', {}), conflict.get('source2', {})]:
            entities.update(source.get('entities', []))

        return list(entities)

    def _generate_contradiction_question(
        self,
        conflict: Dict,
        entities: List[str]
    ) -> str:
        """生成矛盾澄清问题"""
        conflict_type = conflict.get('conflict_type', 'unknown')

        if conflict_type == 'temporal':
            return f"关于 {entities[0] if entities else '这件事'}，我发现了不同时间的记录。您能帮我确认正确的时间吗？"
        elif conflict_type == 'factual':
            return f"关于 {entities[0] if entities else '这个信息'}，我发现了矛盾的记录。哪个是正确的呢？"
        elif conflict_type == 'source':
            return f"我的记忆与外部资料关于 {entities[0] if entities else '这件事'} 有出入。您能帮我确认一下吗？"
        else:
            return f"我发现了一些矛盾的信息。您能帮我澄清一下吗？"

    def _extract_query_entities(self, query: str) -> List[str]:
        """从查询中提取实体（简化版）"""
        import re

        # 提取专有名词（首字母大写的词）
        words = re.findall(r'\b[A-Z][a-z]+\b', query)

        # 提取引号内的内容
        quoted = re.findall(r'"([^"]+)"', query)

        return list(set(words + quoted))

    def _are_contents_conflicting(self, contents: List[str]) -> bool:
        """检查内容是否冲突（简化版）"""
        if len(contents) < 2:
            return False

        # 简单的词重叠检测
        word_sets = [set(c.lower().split()) for c in contents]

        # 如果词重叠率很低，认为是不同的事件
        for i in range(len(word_sets)):
            for j in range(i + 1, len(word_sets)):
                intersection = word_sets[i] & word_sets[j]
                union = word_sets[i] | word_sets[j]
                overlap = len(intersection) / len(union) if union else 0

                if overlap < 0.3:  # 词重叠率低于30%
                    return True

        return False

    def _filter_recent_inquiries(
        self,
        inquiries: List[InquiryContext]
    ) -> List[InquiryContext]:
        """过滤最近已询问的内容"""
        from datetime import timedelta

        cooldown_period = timedelta(minutes=5)
        now = datetime.now()

        filtered = []
        for inq in inquiries:
            # 检查实体是否在冷却期内
            in_cooldown = False
            for entity in inq.related_entities:
                last_inquiry = self.inquiry_cooldown.get(entity)
                if last_inquiry and (now - last_inquiry) < cooldown_period:
                    in_cooldown = True
                    break

            if not in_cooldown:
                filtered.append(inq)

        return filtered

    def _format_inquiry_prompt(self, inquiries: List[InquiryContext]) -> str:
        """格式化询问提示"""
        if not inquiries:
            return ""

        lines = []
        lines.append("\n\n💬 **需要确认的信息**")

        for i, inq in enumerate(inquiries, 1):
            icon = {
                InquiryType.CONTRADICTION: "⚠️",
                InquiryType.TEMPORAL_CONFLICT: "📅",
                InquiryType.KNOWLEDGE_GAP: "❓",
                InquiryType.AMBIGUITY: "🤔",
                InquiryType.CONFIDENCE_LOW: "💭"
            }.get(inq.inquiry_type, "❓")

            lines.append(f"{icon} {inq.suggested_question}")

        return "\n".join(lines)

    def clear_history(self):
        """清除历史记录"""
        self.recent_inquiries = []
        self.inquiry_cooldown = {}


# 便捷函数
def create_proactive_inquiry_manager(
    prefrontal_agent=None,
    result_arbiter=None
) -> ProactiveInquiryManager:
    """创建主动询问管理器"""
    return ProactiveInquiryManager(
        prefrontal_agent=prefrontal_agent,
        result_arbiter=result_arbiter
    )
