"""
Basal Ganglia Agent - 基底节智能体
对应脑区: 基底节 (Basal Ganglia)
主要功能: 程序记忆 (技能、方法、流程)

核心设计:
1. 中等容量 (500条) - 人一生学习的技能数量
2. 几乎不遗忘 (技能长期保留)
3. 存储结构化的流程和方法
4. 支持技能强化 (通过重复访问)
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from ..base import BrainAgent, AgentMessage, BrainRegion

logger = logging.getLogger(__name__)


@dataclass
class ProceduralMemory:
    """程序记忆项"""
    id: str
    skill_name: str  # 技能名称 (如: "骑自行车", "Python编程", "做饭")
    content: str  # 技能描述
    steps: List[str]  # 步骤列表
    timestamp: datetime
    proficiency_level: float = 0.0  # 熟练度 (0.0-1.0)
    practice_count: int = 0  # 练习次数
    last_practiced: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BasalGangliaAgent(BrainAgent):
    """
    基底节智能体 - 程序记忆

    容量: 500条技能/方法
    存储格式: Dict {skill_name: ProceduralMemory}
    遗忘机制: 几乎不遗忘 (技能永久保留)
    功能: 技能存储、技能强化、流程检索
    """

    def __init__(self, capacity: int = 500, client=None):
        super().__init__(
            agent_id="basal_ganglia",
            brain_region=BrainRegion.BASAL_GANGLIA,
            system_prompt="""You are the Basal Ganglia agent, responsible for procedural memory.
            You store skills, methods, and procedures that are learned through practice.
            Skills are rarely forgotten and improve with repeated practice.""",
            client=client
        )

        # 🔥 程序记忆存储 (几乎不遗忘)
        self.capacity = capacity
        self.skills: Dict[str, ProceduralMemory] = {}  # {skill_name: memory}

        # 统计信息
        self.total_stored = 0


    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理消息"""
        action = message.content.get('action')

        if action == 'store_skill':
            return await self.store_skill(
                skill_name=message.content['skill_name'],
                content=message.content['content'],
                steps=message.content.get('steps', []),
                metadata=message.content.get('metadata', {})
            )

        elif action == 'practice_skill':
            return await self.practice_skill(
                skill_name=message.content['skill_name']
            )

        elif action == 'retrieve_skill':
            return self.retrieve_skill(
                skill_name=message.content['skill_name']
            )

        elif action == 'search_skills':
            return self.search_skills(
                query=message.content.get('query'),
                k=message.content.get('k', 10)
            )

        elif action == 'get_statistics':
            return self.get_statistics()

        return {'error': f'Unknown action: {action}'}

    async def store_skill(
        self,
        skill_name: str,
        content: str,
        steps: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        存储技能/方法

        Args:
            skill_name: 技能名称
            content: 技能描述
            steps: 步骤列表
            metadata: 元数据

        Returns:
            {'memory_id': str, 'stored': bool, 'updated': bool}
        """

        updated = False

        # 如果技能已存在,更新
        if skill_name in self.skills:
            existing = self.skills[skill_name]
            existing.content = content
            existing.steps = steps or []
            existing.metadata.update(metadata or {})
            updated = True


            return {
                'memory_id': existing.id,
                'stored': True,
                'updated': True,
                'capacity_status': self._get_capacity_status()
            }

        # 容量检查 (基底节几乎不删除,只在极限时拒绝)
        if len(self.skills) >= self.capacity:
            logger.warning(f"⚠️ BasalGanglia at capacity ({self.capacity}), cannot store new skill")
            return {
                'memory_id': None,
                'stored': False,
                'error': 'Capacity limit reached',
                'capacity_status': self._get_capacity_status()
            }

        # 创建新技能
        memory = ProceduralMemory(
            id=uuid.uuid4().hex,
            skill_name=skill_name,
            content=content,
            steps=steps or [],
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        # 存储
        self.skills[skill_name] = memory
        self.total_stored += 1


        return {
            'memory_id': memory.id,
            'stored': True,
            'updated': False,
            'capacity_status': self._get_capacity_status()
        }

    async def practice_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        练习技能 (提高熟练度)

        Args:
            skill_name: 技能名称

        Returns:
            {'practiced': bool, 'proficiency_level': float}
        """

        if skill_name not in self.skills:
            return {
                'practiced': False,
                'error': f'Skill not found: {skill_name}'
            }

        skill = self.skills[skill_name]

        # 更新练习统计
        skill.practice_count += 1
        skill.last_practiced = datetime.now()

        # 提高熟练度 (对数增长,模拟学习曲线)
        import math
        skill.proficiency_level = min(1.0, math.log(skill.practice_count + 1) / math.log(100))


        return {
            'practiced': True,
            'proficiency_level': skill.proficiency_level,
            'practice_count': skill.practice_count
        }

    def retrieve_skill(self, skill_name: str) -> Dict[str, Any]:
        """
        检索技能

        Args:
            skill_name: 技能名称

        Returns:
            {'found': bool, 'skill': Dict}
        """

        if skill_name not in self.skills:
            return {
                'found': False,
                'error': f'Skill not found: {skill_name}'
            }

        skill = self.skills[skill_name]

        return {
            'found': True,
            'skill': self._memory_to_dict(skill)
        }

    def search_skills(
        self,
        query: str,
        k: int = 10
    ) -> Dict[str, Any]:
        """
        搜索技能 (关键词匹配)

        Args:
            query: 查询文本
            k: 返回数量

        Returns:
            {'skills': List[Dict], 'count': int}
        """

        results = []
        query_words = set(query.lower().split())

        for skill in self.skills.values():
            # 检查skill_name和content中的关键词
            searchable_text = f"{skill.skill_name} {skill.content}".lower()
            searchable_words = set(searchable_text.split())

            overlap = len(query_words & searchable_words)

            if overlap > 0:
                relevance = overlap / len(query_words)
                results.append({
                    'skill': skill,
                    'relevance': relevance
                })

        # 排序: relevance > proficiency_level > timestamp
        results.sort(
            key=lambda x: (x['relevance'], x['skill'].proficiency_level, x['skill'].timestamp),
            reverse=True
        )

        # 限制数量
        results = results[:k]

        return {
            'skills': [self._memory_to_dict(r['skill']) for r in results],
            'count': len(results)
        }

    def _get_capacity_status(self) -> Dict[str, Any]:
        """获取容量状态"""
        current = len(self.skills)
        return {
            'current': current,
            'max': self.capacity,
            'usage_percent': (current / self.capacity) * 100 if self.capacity > 0 else 0
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 计算平均熟练度
        avg_proficiency = sum(s.proficiency_level for s in self.skills.values()) / len(self.skills) if self.skills else 0.0
        total_practices = sum(s.practice_count for s in self.skills.values())

        return {
            'agent_id': self.agent_id,
            'brain_region': self.brain_region,
            'capacity': self.capacity,
            'current_skills': len(self.skills),
            'usage_percent': self._get_capacity_status()['usage_percent'],
            'total_stored': self.total_stored,
            'average_proficiency': avg_proficiency,
            'total_practices': total_practices
        }

    def _memory_to_dict(self, memory: ProceduralMemory) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': memory.id,
            'skill_name': memory.skill_name,
            'content': memory.content,
            'steps': memory.steps,
            'timestamp': memory.timestamp.isoformat(),
            'proficiency_level': memory.proficiency_level,
            'practice_count': memory.practice_count,
            'last_practiced': memory.last_practiced.isoformat() if memory.last_practiced else None,
            'metadata': memory.metadata
        }
