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
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from ..base import BrainAgent, AgentMessage, BrainRegion
from ...brain.habit_learner import HabitLearner

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

        # 🔥 策略缓存 (strategy_cache) - 用于存储行为模式和策略
        # References self.skills for procedural patterns
        self.strategy_cache = self.skills  # Alias for functional brain regions test
        
        # 🧠 Habit Learner
        self.habit_learner = HabitLearner()

        # 统计信息
        self.total_stored = 0

        # 🔥 Auto-persistence setup
        self.state_file = Path("data/basal_ganglia_state.json")
        self._load_state_from_file()

        logger.info(f"✅ BasalGangliaAgent initialized (capacity={capacity})")


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
            
        # 🧠 Habit Learner Actions
        elif action == 'update_policy':
            return self.update_policy(
                context=message.content['context'],
                strategy_id=message.content['strategy_id'],
                reward=message.content['reward']
            )
            
        elif action == 'recommend_strategy':
            return self.recommend_strategy(
                context=message.content['context'],
                available_strategies=message.content['available_strategies']
            )

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

            # Persist update
            self._save_state_to_file()

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

        # Persist new skill
        self._save_state_to_file()

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

        # 🔥 Persist practice update
        self._save_state_to_file()

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

        if not query:
            return {
                'skills': [],
                'count': 0,
                'error': 'Query is required for skill search'
            }

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

    def update_policy(self, context: str, strategy_id: str, reward: float) -> Dict[str, Any]:
        """更新策略"""
        self.habit_learner.update_policy(context, strategy_id, reward)
        return {'status': 'updated', 'context': context, 'strategy_id': strategy_id, 'reward': reward}

    def recommend_strategy(self, context: str, available_strategies: List[str]) -> Dict[str, Any]:
        """推荐策略"""
        recommended = self.habit_learner.recommend_strategy(context, available_strategies)
        return {'recommended_strategy': recommended, 'context': context}

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

    # =========================
    # Auto-persistence helpers
    # =========================

    def _load_state_from_file(self):
        """从JSON文件加载技能记忆"""
        if not self.state_file.exists():
            return

        try:
            with self.state_file.open('r', encoding='utf-8') as fp:
                data = json.load(fp)

            loaded = 0
            for entry in data:
                try:
                    memory = ProceduralMemory(
                        id=entry['id'],
                        skill_name=entry['skill_name'],
                        content=entry.get('content', ''),
                        steps=entry.get('steps', []),
                        timestamp=datetime.fromisoformat(entry['timestamp']),
                        proficiency_level=entry.get('proficiency_level', 0.0),
                        practice_count=entry.get('practice_count', 0),
                        last_practiced=datetime.fromisoformat(entry['last_practiced']) if entry.get('last_practiced') else None,
                        metadata=entry.get('metadata', {})
                    )
                    self.skills[memory.skill_name] = memory
                    loaded += 1
                except Exception as exc:
                    logger.warning(f"⚠️ Failed to load BasalGanglia memory entry: {exc}")

            self.total_stored = max(self.total_stored, len(self.skills))
            logger.info(f"🧠 Loaded {loaded} procedural memories from {self.state_file}")
        except FileNotFoundError:
            logger.info("BasalGanglia state file not found, starting fresh")
        except Exception as exc:
            logger.error(f"❌ Failed to load BasalGanglia state: {exc}")

    def _save_state_to_file(self):
        """保存技能记忆到JSON文件"""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = [self._memory_to_dict(mem) for mem in self.skills.values()]
            with self.state_file.open('w', encoding='utf-8') as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.error(f"❌ Failed to save BasalGanglia state: {exc}")

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

    def export_state(self) -> Dict[str, Any]:
        """
        Export basal ganglia state to JSON-serializable format for BMA archive.

        Returns:
            Dict containing all procedural memories (skills)
        """
        # Serialize procedural memories
        skills_data = []
        for skill_name, skill in self.skills.items():
            skills_data.append({
                'id': skill.id,
                'skill_name': skill.skill_name,
                'content': skill.content,
                'steps': skill.steps,
                'timestamp': skill.timestamp.isoformat() if skill.timestamp else None,
                'proficiency_level': skill.proficiency_level,
                'practice_count': skill.practice_count,
                'last_practiced': skill.last_practiced.isoformat() if skill.last_practiced else None,
                'metadata': skill.metadata
            })

        # Export state
        state = {
            'format_version': '1.0.0',
            'agent_id': self.agent_id,
            'brain_region': 'basal_ganglia',
            'capacity': self.capacity,
            'skills': skills_data,
            'statistics': {
                'total_stored': self.total_stored,
                'current_count': len(self.skills)
            }
        }

        logger.info(f"✅ Exported BasalGangliaAgent state: {len(skills_data)} skills")
        return state

    def load_state(self, state: Dict[str, Any]) -> bool:
        """
        Load basal ganglia state from exported data.

        Args:
            state: State dictionary from export_state()

        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate format
            if state.get('brain_region') != 'basal_ganglia':
                logger.error(f"❌ Invalid brain region: {state.get('brain_region')}")
                return False

            # Clear current state
            self.skills.clear()

            # Restore configuration
            self.capacity = state.get('capacity', self.capacity)

            # Restore procedural memories (skills)
            for skill_data in state.get('skills', []):
                skill = ProceduralMemory(
                    id=skill_data['id'],
                    skill_name=skill_data['skill_name'],
                    content=skill_data['content'],
                    steps=skill_data.get('steps', []),
                    timestamp=datetime.fromisoformat(skill_data['timestamp']) if skill_data.get('timestamp') else datetime.now(),
                    proficiency_level=skill_data.get('proficiency_level', 0.0),
                    practice_count=skill_data.get('practice_count', 0),
                    last_practiced=datetime.fromisoformat(skill_data['last_practiced']) if skill_data.get('last_practiced') else None,
                    metadata=skill_data.get('metadata', {})
                )

                self.skills[skill.skill_name] = skill

            # Restore statistics
            stats = state.get('statistics', {})
            self.total_stored = stats.get('total_stored', 0)

            logger.info(f"✅ Loaded BasalGangliaAgent state: {len(self.skills)} skills")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load BasalGangliaAgent state: {e}")
            return False
