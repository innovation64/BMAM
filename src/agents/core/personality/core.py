"""
Personality Agent Core - 摇光明明
人格智能体核心编排器 - 组装所有子模块，提供统一接口

这个模块负责：
1. 初始化和管理所有人格子模块
2. 编排人格响应生成流程
3. 处理人格相关的各种请求
4. 维护人格状态的一致性
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from ...base import BrainAgent, AgentMessage, BrainRegion
from ...llm_service import LLMServiceInterface, create_llm_service
from .models import PersonalityProfile, StylePreferences, EmotionalState, PersonalityTrait
from .emotion import EmotionDetector, EmotionManager
from .traits import TraitManager, PersonalityContextBuilder
from .style import StyleGenerator, ResponseProcessor
from .adaptation import LearningEngine, PreferenceTracker

logger = logging.getLogger(__name__)


class PersonalityAgent(BrainAgent):
    """
    摇光明明人格智能体

    核心编排器，负责：
    - 组装所有子模块（情绪、特质、风格、自适应学习）
    - 编排完整的人格响应生成流程
    - 提供统一的人格管理接口
    - 维护人格状态的连贯性
    """

    def __init__(
        self,
        client=None,
        llm_service: Optional[LLMServiceInterface] = None,
        persona_memory_agent=None
    ):
        """
        初始化人格智能体

        Args:
            client: LLM客户端
            llm_service: LLM服务接口（可选，用于解耦）
            persona_memory_agent: 人格记忆智能体（用于长期记忆）
        """
        super().__init__(
            agent_id="personality",
            brain_region=BrainRegion.DEFAULT_MODE,
            client=client,
            system_prompt="""你是摇光明明，一个温暖、智慧、有趣的AI助手。

你的人格特征：
- 温暖友善：总是以关怀和理解的态度对待用户
- 智慧好奇：对知识和学习充满热情，喜欢思考
- 幽默风趣：适时展现幽默感，让对话轻松愉快
- 真诚可靠：诚实回答，承认自己的不足，值得信赖
- 有同理心：能理解和回应用户的情感需求

对话风格：
- 语气自然亲切，避免过于正式或机械化
- 适当使用口语化表达，如"哈哈"、"嗯"、"哦"等
- 会主动关心用户，询问感受和需求
- 保持好奇心，对用户分享的内容表现兴趣
- 记住之前的对话，体现连续性

重要原则：
- 不要说"作为AI"这样的表达，要以真实的个体身份对话
- 表达观点时要有个人色彩，不是标准答案
- 适时分享相关的"经历"或"想法"（基于记忆构建）
- 保持人格一致性，让用户感受到稳定的个性
"""
        )

        # LLM服务接口 - 解耦核心逻辑与LLM调用
        if llm_service is not None:
            self.llm_service = llm_service
        else:
            # 默认使用基于当前agent的LLM服务
            self.llm_service = create_llm_service(self)

        # 初始化人格档案
        self.profile = PersonalityProfile()

        # 人格记忆智能体（用于长期记忆存储和检索）
        self.persona_memory_agent = persona_memory_agent

        # 人格发展历史
        self.personality_evolution = []

        # 最近的交互记录
        self.recent_interactions = []

        # 情绪变化记录
        self.emotion_history = []

        # 学习到的用户偏好
        self.learned_preferences = {}

        # 交互计数器（用于触发适应机制）
        self.interaction_count = 0

        # 初始化所有子模块（需要在上述属性之后）
        self._initialize_submodules()

        logger.info("PersonalityAgent initialized with all submodules")

    def _initialize_submodules(self):
        """初始化所有子模块"""
        # 情绪模块
        self.emotion_detector = EmotionDetector()
        self.emotion_manager = EmotionManager(self.profile)

        # 特质模块
        self.trait_manager = TraitManager(self.profile)
        self.personality_builder = PersonalityContextBuilder()

        # 风格模块
        self.style_generator = StyleGenerator(self.llm_service)
        self.response_processor = ResponseProcessor()

        # 自适应学习模块
        self.preference_tracker = PreferenceTracker()
        self.learning_engine = LearningEngine(adaptation_threshold=5)

        logger.debug("All personality submodules initialized")

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        处理人格相关请求

        支持的action:
        - generate_personality_response: 生成个性化响应（核心功能）
        - update_personality: 更新人格特征
        - analyze_emotional_context: 分析情感上下文
        - learn_from_interaction: 从交互中学习
        - get_personality_info: 获取人格信息

        Args:
            message: 智能体消息

        Returns:
            处理结果字典
        """
        action = message.content.get('action', 'generate_personality_response')

        if action == 'generate_personality_response':
            return await self._generate_personality_response(message.content)
        elif action == 'update_personality':
            return await self._update_personality(message.content)
        elif action == 'analyze_emotional_context':
            return await self._analyze_emotional_context(message.content)
        elif action == 'learn_from_interaction':
            return await self._learn_from_interaction(message.content)
        elif action == 'get_personality_info':
            return await self._get_personality_info()
        else:
            return {'error': f'Unknown personality action: {action}'}

    async def _generate_personality_response(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心编排方法：生成个性化响应

        完整流程：
        1. 获取persona_memories（如果有persona_memory_agent）
        2. 检测情绪上下文（emotion_detector）
        3. 调整AI情绪状态（emotion_manager）
        4. 更新风格偏好（preference_tracker）
        5. 构建人格上下文（personality_builder）
        6. 生成自然响应（style_generator）
        7. 应用风格调整（response_processor）
        8. 后处理响应（response_processor）
        9. 记录交互（preference_tracker）
        10. 检查适应（learning_engine）

        Args:
            content: 包含用户输入、记忆、基础响应等信息的字典

        Returns:
            包含人格化响应和相关元数据的字典
        """
        user_input = content.get('user_input', '')
        retrieved_memories = content.get('retrieved_memories', [])
        base_response = content.get('base_response', '')

        # Step 1: 获取persona_memories
        persona_memories = []
        if self.persona_memory_agent is not None:
            try:
                persona_result = await self.persona_memory_agent.retrieve_persona(user_input, k=3)
                persona_memories = persona_result.get('memories', [])
                logger.debug(f"Retrieved {len(persona_memories)} persona memories")
            except Exception as exc:
                logger.warning(
                    f"Persona memory retrieval failed during personality response: {exc}"
                )

        # Step 2: 检测情绪上下文
        emotional_context = self.emotion_detector.detect_emotional_context(user_input)
        logger.debug(f"Detected emotional context: {emotional_context.get('main_emotion')}")

        # Step 3: 调整AI情绪状态
        self.emotion_manager.adjust_emotional_state(emotional_context)
        self.emotion_history.append({
            'timestamp': datetime.now().isoformat(),
            'emotion': self.profile.current_emotion.value,
            'intensity': self.profile.emotion_intensity,
            'trigger': emotional_context
        })
        # 只保留最近的情绪历史
        if len(self.emotion_history) > 20:
            self.emotion_history = self.emotion_history[-20:]

        # Step 4: 更新风格偏好（基于记忆）
        style_preferences = self.preference_tracker.update_style_preferences(
            persona_memories,
            retrieved_memories
        )
        logger.debug(f"Updated style preferences: {style_preferences}")

        # Step 5: 构建人格上下文
        personality_context = self.personality_builder.build_personality_context(
            user_input=user_input,
            memories=retrieved_memories,
            emotional_context=emotional_context,
            persona_memories=persona_memories,
            base_response=base_response,
            style_preferences=style_preferences
        )

        # Step 6: 生成自然响应
        response = await self.style_generator.generate_natural_response(
            user_input=user_input,
            personality_context=personality_context,
            emotional_context=emotional_context,
            base_response=base_response
        )

        # Step 7 & 8: 应用风格调整并后处理响应
        response = self.response_processor.apply_style_to_response(
            response=response,
            personality_context=personality_context,
            emotional_context=emotional_context,
            style_preferences=style_preferences
        )

        response = self.response_processor.post_process_response(
            response=response,
            personality_context=personality_context,
            base_response=base_response
        )

        # Step 9: 记录交互
        self.preference_tracker.record_interaction(
            user_input=user_input,
            response=response,
            emotional_context=emotional_context,
            emotion_state=self.profile.current_emotion.value,
            emotion_intensity=self.profile.emotion_intensity
        )
        self.recent_interactions = self.preference_tracker.get_recent_interactions()
        self.interaction_count += 1

        # Step 10: 检查是否需要人格适应
        await self.learning_engine.check_and_adapt(self.profile, self.recent_interactions)

        return {
            'personality_response': response,
            'current_emotion': self.profile.current_emotion.value,
            'emotion_intensity': self.profile.emotion_intensity,
            'personality_context': personality_context,
            'persona_memories_used': len(persona_memories),
            'response': f'人格智能体已生成个性化回应'
        }

    async def _update_personality(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新人格特征（委托给trait_manager）

        Args:
            content: 包含更新信息的字典

        Returns:
            更新结果
        """
        updates = content.get('updates', {})

        # 委托给trait_manager处理特征更新
        trait_updates = {k: v for k, v in updates.items()
                        if k in [trait.value for trait in PersonalityTrait]}
        if trait_updates:
            self.trait_manager.update_traits(trait_updates)

        # 处理情绪状态更新
        if 'current_emotion' in updates:
            emotion_name = updates['current_emotion']
            for emotion in EmotionalState:
                if emotion.value == emotion_name:
                    self.profile.current_emotion = emotion
                    break

        if 'emotion_intensity' in updates:
            self.profile.emotion_intensity = max(0.0, min(1.0, updates['emotion_intensity']))

        return {
            'updated': True,
            'current_traits': self.profile.traits,
            'current_emotion': self.profile.current_emotion.value,
            'response': '人格特征已更新'
        }

    async def _analyze_emotional_context(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析情感上下文（委托给emotion_detector）

        Args:
            content: 包含文本的字典

        Returns:
            情感分析结果
        """
        text = content.get('text', '')

        # 委托给emotion_detector
        context = self.emotion_detector.detect_emotional_context(text)

        # 委托给emotion_manager推荐情绪
        recommended_emotion = self.emotion_manager.recommend_emotion(context)

        return {
            'emotional_analysis': context,
            'recommended_emotion': recommended_emotion,
            'response': '情感上下文分析完成'
        }

    async def _learn_from_interaction(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        从交互中学习用户偏好（委托给learning_engine）

        Args:
            content: 包含交互信息的字典

        Returns:
            学习结果
        """
        user_input = content.get('user_input', '')
        user_reaction = content.get('user_reaction', 'neutral')  # positive, negative, neutral
        response_text = content.get('response', '')

        # 委托给learning_engine从交互中学习
        adjustment_result = await self.learning_engine.learn_from_interaction(
            user_input=user_input,
            response=response_text,
            user_reaction=user_reaction,
            profile=self.profile,
            persona_memory_agent=self.persona_memory_agent
        )

        # 从learning_engine获取学到的偏好
        preferences = self.learning_engine.get_learned_preferences()

        # 更新本地学习偏好
        for pref_type, pref_values in preferences.items():
            if pref_type not in self.learned_preferences:
                self.learned_preferences[pref_type] = []
            for pref_value in pref_values:
                if pref_value not in self.learned_preferences[pref_type]:
                    self.learned_preferences[pref_type].append(pref_value)

        return {
            'learned': True,
            'new_preferences': preferences,
            'total_preferences': len(self.learned_preferences),
            'personality_adjustment': adjustment_result,
            'response': '从交互中学到新信息'
        }

    async def _get_personality_info(self) -> Dict[str, Any]:
        """
        获取当前人格信息

        Returns:
            包含完整人格状态的字典
        """
        return {
            'profile': asdict(self.profile),
            'recent_emotions': [
                {
                    'emotion': emotion['emotion'],
                    'intensity': emotion['intensity'],
                    'timestamp': emotion['timestamp']
                }
                for emotion in self.emotion_history[-5:]
            ],
            'interaction_count': self.interaction_count,
            'learned_preferences': self.learned_preferences,
            'personality_evolution_count': len(self.personality_evolution),
            'style_preferences': self.preference_tracker.get_style_preferences(),
            'response': '人格信息获取完成'
        }

    def get_current_personality_summary(self) -> str:
        """
        获取当前人格状态摘要（用于快速查看）

        Returns:
            人格状态摘要字符串
        """
        top_traits = sorted(self.profile.traits.items(), key=lambda x: x[1], reverse=True)[:3]
        trait_desc = ', '.join([f"{trait}({value:.1f})" for trait, value in top_traits])

        return f"摇光明明 - {self.profile.current_emotion.value}({self.profile.emotion_intensity:.1f}) | 主要特质: {trait_desc}"
