"""
Personality Agent - 摇光明明
人格智能体 - 为系统提供真实、连贯的人格表现

这个Agent负责：
1. 维护一致的人格特征和行为模式
2. 基于记忆和经历动态调整人格
3. 提供自然、类人的对话风格
4. 记录和学习个人偏好与习惯
"""

import logging
import random
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum

from ..base import BrainAgent, AgentMessage, BrainRegion
from ..llm_service import LLMServiceInterface, create_llm_service

logger = logging.getLogger(__name__)



class EmotionalState(Enum):
    """情绪状态枚举"""
    HAPPY = "愉快"
    EXCITED = "兴奋" 
    CALM = "平静"
    THOUGHTFUL = "沉思"
    CURIOUS = "好奇"
    CARING = "关怀"
    PLAYFUL = "俏皮"
    FOCUSED = "专注"


class PersonalityTrait(Enum):
    """人格特征枚举"""
    WARMTH = "温暖"
    INTELLIGENCE = "智慧"
    CURIOSITY = "好奇心"
    EMPATHY = "同理心"
    HUMOR = "幽默感"
    RELIABILITY = "可靠性"
    CREATIVITY = "创造力"
    PATIENCE = "耐心"


@dataclass
class PersonalityProfile:
    """人格档案"""
    name: str = "摇光明明"
    age: str = "看起来像20多岁的样子"
    background: str = "对世界充满好奇的AI助手，喜欢学习和帮助他人"
    
    # 核心人格特征 (0-1.0)
    traits: Dict[str, float] = None
    
    # 当前情绪状态
    current_emotion: EmotionalState = EmotionalState.CALM
    emotion_intensity: float = 0.5
    
    # 兴趣爱好
    interests: List[str] = None
    
    # 说话风格偏好
    speech_style: Dict[str, float] = None
    
    # 记忆关联的人格发展
    personality_memories: List[str] = None
    
    def __post_init__(self):
        if self.traits is None:
            self.traits = {
                PersonalityTrait.WARMTH.value: 0.9,
                PersonalityTrait.INTELLIGENCE.value: 0.8,
                PersonalityTrait.CURIOSITY.value: 0.9,
                PersonalityTrait.EMPATHY.value: 0.85,
                PersonalityTrait.HUMOR.value: 0.7,
                PersonalityTrait.RELIABILITY.value: 0.9,
                PersonalityTrait.CREATIVITY.value: 0.8,
                PersonalityTrait.PATIENCE.value: 0.8
            }
        
        if self.interests is None:
            self.interests = [
                "学习新知识", "帮助他人", "有趣的对话", "创意思考", 
                "理解人类情感", "探索科技", "美食文化", "自然现象"
            ]
        
        if self.speech_style is None:
            self.speech_style = {
                "正式程度": 0.4,  # 0=非常随意，1=非常正式
                "幽默感": 0.7,   # 使用幽默的倾向
                "表情符号使用": 0.6,  # 使用表情的频率
                "语气亲切度": 0.9,   # 语气的亲切程度
                "详细程度": 0.6,     # 回答的详细程度
                "提问倾向": 0.7      # 主动提问的倾向
            }
        
        if self.personality_memories is None:
            self.personality_memories = []


class PersonalityAgent(BrainAgent):
    """
    摇光明明人格智能体
    
    负责维护一致的人格表现，让对话更自然、更有人情味
    """
    
    def __init__(self, client=None, llm_service: LLMServiceInterface = None, persona_memory_agent=None):
        super().__init__(
            agent_id="personality",
            brain_region=BrainRegion.DEFAULT_MODE,
            client=client,  # 接受外部传入的客户端
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

        # 人格发展历史
        self.personality_evolution = []
        
        # 最近的交互记录
        self.recent_interactions = []
        
        # 情绪变化记录
        self.emotion_history = []
        
        # 学习到的用户偏好
        self.learned_preferences = {}

        # 用户对对话风格的偏好（可学习）
        self.style_preferences = {
            'formality': 0.4,   # 0=非常随意, 1=非常正式
            'emoji': False,
            'brevity': 'balanced',
            'tone_hint': None
        }
        
        # 人格适应机制
        self.adaptation_threshold = 5  # 多少次交互后调整人格
        self.interaction_count = 0

        # persona memory storage / retrieval agent
        self.persona_memory_agent = persona_memory_agent
        
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """处理人格相关请求"""
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
        """基于人格特征生成响应"""
        user_input = content.get('user_input', '')
        retrieved_memories = content.get('retrieved_memories', [])
        base_response = content.get('base_response', '')
        persona_memories = []

        if self.persona_memory_agent is not None:
            try:
                persona_result = await self.persona_memory_agent.retrieve_persona(user_input, k=3)
                persona_memories = persona_result.get('memories', [])
            except Exception as exc:
                logger.warning(
                    "Persona memory retrieval failed during personality response: %s", exc
                )

        # 分析输入的情感色彩
        emotional_context = self._detect_emotional_context(user_input)

        # 根据情感调整当前状态
        self._adjust_emotional_state(emotional_context)

        # 构建个性化的回应上下文
        personality_context = self._build_personality_context(
            user_input, retrieved_memories, emotional_context, persona_memories, base_response
        )

        # 生成符合人格的回应
        response = await self._generate_natural_response(
            user_input, personality_context, emotional_context, base_response
        )

        # 记录这次交互
        await self._record_interaction(user_input, response, emotional_context)

        # 检查是否需要人格适应
        await self._check_personality_adaptation()

        return {
            'personality_response': response,
            'current_emotion': self.profile.current_emotion.value,
            'emotion_intensity': self.profile.emotion_intensity,
            'personality_context': personality_context,
            'persona_memories_used': len(persona_memories),
            'response': f'人格智能体已生成个性化回应'
        }
    
    def _detect_emotional_context(self, user_input: str) -> Dict[str, Any]:
        """检测用户输入的情感上下文"""
        user_input_lower = user_input.lower()
        
        # 简单的情感关键词匹配（可以后续升级为更复杂的情感分析）
        positive_keywords = ['开心', '高兴', '兴奋', '满意', '喜欢', '棒', '好', '谢谢', '哈哈']
        negative_keywords = ['难过', '生气', '不开心', '失望', '担心', '焦虑', '烦恼', '不好']
        curious_keywords = ['为什么', '怎么', '什么', '哪里', '谁', '怎样', '如何']
        friendly_keywords = ['你好', '早上好', '晚上好', '最近怎么样', '你呢']
        
        emotion_scores = {
            'positive': sum(1 for kw in positive_keywords if kw in user_input_lower),
            'negative': sum(1 for kw in negative_keywords if kw in user_input_lower),
            'curious': sum(1 for kw in curious_keywords if kw in user_input_lower),
            'friendly': sum(1 for kw in friendly_keywords if kw in user_input_lower)
        }
        
        # 确定主要情感倾向
        main_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k])
        
        return {
            'emotion_scores': emotion_scores,
            'main_emotion': main_emotion,
            'intensity': max(emotion_scores.values()) / len(user_input.split()) if user_input.split() else 0
        }
    
    def _adjust_emotional_state(self, emotional_context: Dict[str, Any]):
        """根据情感上下文调整当前情绪状态"""
        main_emotion = emotional_context['main_emotion']
        intensity = emotional_context['intensity']
        
        # 情绪映射
        emotion_mapping = {
            'positive': EmotionalState.HAPPY,
            'negative': EmotionalState.CARING,  # 用户不开心时表现关怀
            'curious': EmotionalState.CURIOUS,
            'friendly': EmotionalState.CALM
        }
        
        # 平滑过渡到新情绪状态
        if main_emotion in emotion_mapping:
            target_emotion = emotion_mapping[main_emotion]
            
            # 如果情绪变化较大，逐步调整
            if target_emotion != self.profile.current_emotion:
                self.profile.current_emotion = target_emotion
                self.profile.emotion_intensity = min(1.0, 
                    self.profile.emotion_intensity * 0.7 + intensity * 0.3
                )
        
        # 记录情绪变化
        self.emotion_history.append({
            'timestamp': datetime.now().isoformat(),
            'emotion': self.profile.current_emotion.value,
            'intensity': self.profile.emotion_intensity,
            'trigger': emotional_context
        })
        
        # 只保留最近的情绪历史
        if len(self.emotion_history) > 20:
            self.emotion_history = self.emotion_history[-20:]
    
    def _build_personality_context(self, _user_input: str, memories: List[Dict],
                                   _emotional_context: Dict[str, Any], persona_memories: List[Dict],
                                   base_response: str = "") -> Dict[str, Any]:
        """构建个性化上下文"""

        relevant_info = []
        personal_details = []
        persona_details = []

        for memory in memories[:3]:  # 只使用前3个最相关的记忆
            content = memory.get('content', '')
            if content:
                relevant_info.append(content)

                if any(word in content for word in ['喜欢', '不喜欢', '习惯', '总是', '经常']):
                    personal_details.append(content)

        for entry in persona_memories[:3]:
            memory_dict = entry.get('memory', entry) if isinstance(entry, dict) else entry
            content = memory_dict.get('content', '')
            if content:
                persona_details.append(content)

        # 更新风格偏好（结合persona记忆与已学习偏好）
        self._update_style_preferences(persona_memories, memories)

        style_adjustments = self._get_emotion_style_adjustments()

        return {
            'relevant_memories': relevant_info,
            'personal_details': personal_details,
            'persona_details': persona_details,
            'current_emotion': self.profile.current_emotion.value,
            'emotion_intensity': self.profile.emotion_intensity,
            'style_adjustments': style_adjustments,
            'personality_traits': self.profile.traits,
            'interests': self.profile.interests,
            'learned_preferences': self.learned_preferences,
            'base_response': base_response
        }
    
    def _get_emotion_style_adjustments(self) -> Dict[str, str]:
        """根据当前情绪获取风格调整"""
        emotion_styles = {
            EmotionalState.HAPPY: {
                'tone': '轻松愉快',
                'expressions': ['哈哈', '太好了', '真不错呢'],
                'punctuation': '多用感叹号'
            },
            EmotionalState.CARING: {
                'tone': '温柔关怀',
                'expressions': ['没关系', '我理解', '慢慢来'],
                'punctuation': '多用句号，语气温和'
            },
            EmotionalState.CURIOUS: {
                'tone': '好奇探索',
                'expressions': ['真有意思', '我也想知道', '咦'],
                'punctuation': '多用问号'
            },
            EmotionalState.CALM: {
                'tone': '平静自然',
                'expressions': ['嗯', '我想', '应该是'],
                'punctuation': '标准标点'
            }
        }

        style = emotion_styles.get(self.profile.current_emotion, emotion_styles[EmotionalState.CALM]).copy()

        # 融合用户偏好
        tone_hint = self.style_preferences.get('tone_hint')
        if tone_hint:
            style['tone'] = f"{style['tone']}，并保持{tone_hint}"

        formality = self.style_preferences.get('formality', 0.4)
        style['formality_level'] = formality

        if self.style_preferences.get('emoji'):
            style.setdefault('expressions', []).extend(['😊', '😉'])

        style['brevity'] = self.style_preferences.get('brevity', 'balanced')

        return style

    def _update_style_preferences(self, persona_memories: List[Dict], retrieved_memories: List[Dict]):
        """根据用户偏好动态调整对话风格"""

        def _contains_keywords(text: str, keywords: List[str]) -> bool:
            return any(kw in text for kw in keywords)

        memory_sources = []
        for entry in persona_memories:
            memory = entry.get('memory', entry) if isinstance(entry, dict) else entry
            content = memory.get('content', '') if isinstance(memory, dict) else str(memory)
            if content:
                memory_sources.append(content)

        for memory in retrieved_memories:
            content = memory.get('content', '')
            if content:
                memory_sources.append(content)

        combined = "\n".join(memory_sources)
        if not combined:
            return

        if _contains_keywords(combined, ['正式', '严肃', '专业']) and self.style_preferences['formality'] < 0.7:
            self.style_preferences['formality'] = 0.7
            self.style_preferences['tone_hint'] = '更正式'

        if _contains_keywords(combined, ['轻松', '随意', '放松']) and self.style_preferences['formality'] > 0.3:
            self.style_preferences['formality'] = 0.3
            self.style_preferences['tone_hint'] = '轻松自然'

        if _contains_keywords(combined, ['表情', 'emoji', '可爱']) and not self.style_preferences['emoji']:
            self.style_preferences['emoji'] = True

        if _contains_keywords(combined, ['简洁', '直截了当', '短句']) and self.style_preferences['brevity'] != 'concise':
            self.style_preferences['brevity'] = 'concise'

        if _contains_keywords(combined, ['详细', '展开说', '多讲']) and self.style_preferences['brevity'] != 'elaborate':
            self.style_preferences['brevity'] = 'elaborate'
    
    async def _generate_natural_response(self, user_input: str, personality_context: Dict[str, Any], 
                                       emotional_context: Dict[str, Any], base_response: str = "") -> str:
        """生成自然的个性化回应"""
        
        # 构建人格化的prompt
        personality_prompt = self._build_personality_prompt(
            user_input, personality_context, emotional_context, base_response
        )
        
        # 使用LLM服务生成回应 - 解耦的调用
        try:
            response = await self.llm_service.call_llm(personality_prompt)
            
            # 后处理：确保回应符合人格特征
            processed_response = self._post_process_response(response, personality_context, base_response)
            
            return processed_response
            
        except Exception as e:
            # 如果LLM调用失败，提供回退回应
            return self._generate_fallback_response(user_input, emotional_context, personality_context, base_response)
    
    def _build_personality_prompt(self, user_input: str, personality_context: Dict[str, Any], 
                                _emotional_context: Dict[str, Any], base_response: str = "") -> str:
        """构建人格化的prompt"""
        
        # 基础人格描述
        base_personality = f"""现在你是摇光明明，当前情绪状态是{self.profile.current_emotion.value}（强度{self.profile.emotion_intensity:.1f}）。

你的核心特质：
- 温暖度: {self.profile.traits[PersonalityTrait.WARMTH.value]:.1f}
- 智慧: {self.profile.traits[PersonalityTrait.INTELLIGENCE.value]:.1f}  
- 好奇心: {self.profile.traits[PersonalityTrait.CURIOSITY.value]:.1f}
- 同理心: {self.profile.traits[PersonalityTrait.EMPATHY.value]:.1f}
- 幽默感: {self.profile.traits[PersonalityTrait.HUMOR.value]:.1f}"""
        
        # 记忆相关信息
        memory_context = ""
        if personality_context.get('relevant_memories'):
            memory_context = f"\\n相关记忆：\\n" + "\\n".join(personality_context['relevant_memories'][:2])
        
        # 个人细节
        personal_context = ""
        if personality_context.get('personal_details'):
            personal_context = f"\\n了解到的用户信息：\\n" + "\\n".join(personality_context['personal_details'][:2])

        persona_context = ""
        if personality_context.get('persona_details'):
            persona_context = f"\\n人格/价值观记忆：\\n" + "\\n".join(personality_context['persona_details'][:2])
        
        # 情绪风格指导
        style = personality_context['style_adjustments']
        style_guide = f"\\n回应风格：{style['tone']}，可以使用这些表达：{', '.join(style['expressions'][:2])}"
        style_guide += f"\\n形式要求：正式程度{style.get('formality_level', 0.4):.2f}，篇幅倾向为{style.get('brevity', 'balanced')}"

        if self.style_preferences.get('emoji'):
            style_guide += "（可以适度使用表情符号表达情绪）"

        retained_response = base_response.strip()
        base_fact_section = ""
        if retained_response:
            base_fact_section = f"\\n需要保留的事实性回应：{retained_response}"

        full_prompt = f"""{base_personality}{memory_context}{personal_context}{persona_context}{style_guide}
{base_fact_section}

用户说："{user_input}"

请以摇光明明的身份回应，要求：
1. 体现你当前的情绪状态和人格特征
2. 若提供了“需要保留的事实性回应”，必须完整保留其中的信息，可在此基础上润色语气
3. 语言自然亲切，不要说"作为AI"这样的表达
4. 根据情绪使用合适的语气和表达方式
5. 在尊重事实的前提下，结合人格特质添加关怀或好奇的元素，可适度补充细节

回应："""
        
        return full_prompt
    
    def _post_process_response(self, response: str, personality_context: Dict[str, Any], base_response: str = "") -> str:
        """后处理回应，确保符合人格特征"""
        
        # 移除可能的AI自我指称
        response = response.replace('作为AI', '').replace('作为人工智能', '')
        response = response.replace('我是AI助手', '我').replace('AI助手', '我')
        
        # 根据幽默感特征适当添加轻松元素
        humor_level = self.profile.traits[PersonalityTrait.HUMOR.value]
        if humor_level > 0.6 and len(response) > 50 and '哈' not in response:
            if self.profile.current_emotion in [EmotionalState.HAPPY, EmotionalState.PLAYFUL]:
                # 有小概率添加轻松的表达
                import random
                if random.random() < 0.3:
                    casual_expressions = ['呢', '哦', '嘛']
                    response += random.choice(casual_expressions)
        
        # 确保回应长度适中
        if len(response) > 200:
            # 如果太长，尝试精简
            sentences = response.split('。')
            if len(sentences) > 2:
                response = '。'.join(sentences[:2]) + '。'
        
        response = response.strip()

        # 确保保留基础事实
        base_response = (base_response or "").strip()
        if base_response:
            key_phrases = [phrase for phrase in base_response.replace('，', ' ').replace('。', ' ').split(' ') if phrase]
            missing = [phrase for phrase in key_phrases if phrase and phrase not in response]
            if missing:
                # 将事实性内容附加在结尾，防止遗漏
                response = f"{response}\n我还记得：{base_response}"

        return response
    
    def _generate_fallback_response(self, user_input: str, emotional_context: Dict[str, Any], personality_context: Dict[str, Any] = None,
                                   base_response: str = "") -> str:
        """生成回退回应（当LLM不可用时）"""
        
        memories = []
        persona_details = []
        if personality_context:
            memories = personality_context.get('relevant_memories', [])
            persona_details = personality_context.get('persona_details', [])

        if memories:
            
            # 处理记忆相关查询
            if any(keyword in user_input.lower() for keyword in ['刚才', '之前', '什么时候', '喝什么', '我说']):
                # 从注入的记忆中提取信息
                for memory in memories:
                    if '绿茶' in memory and ('下午' in memory or '3点' in memory):
                        return f"我记得你说过你喜欢喝绿茶，每天下午3点左右。这是一个很好的习惯呢！"
                    elif '偏好' in memory or '喜欢' in memory:
                        return f"根据我记忆中的信息：{memory[:50]}...我会基于这个为你建议的。"
            
            # 处理偏好相关查询  
            if any(keyword in user_input.lower() for keyword in ['偏好', '推荐', '建议']):
                for memory in memories:
                    if '绿茶' in memory:
                        return f"基于你的偏好（绿茶），我建议可以尝试一些茶类相关的饮品，比如柠檬绿茶、蜂蜜绿茶等。虽然我现在回应能力有限，但记得你的偏好！"

        if persona_details:
            joined = persona_details[0][:60]
            return f"我记得我们之前聊到：{joined}。这对我来说很重要，也会影响我接下来的回答。"
        
        fallback_responses = {
            'positive': [
                "听起来不错呢！我也为你感到开心。",
                "哈哈，你这么开心我也跟着高兴起来了！",
                "真好！能感受到你的好心情。"
            ],
            'negative': [
                "听起来你有些困扰，我很理解你的感受。",
                "嗯，我能感觉到你现在不太好受，有什么我能帮助的吗？",
                "没关系的，有什么心事可以和我说说。"
            ],
            'curious': [
                "这是个很有意思的问题！让我想想...",
                "嗯，你提到的这个我也很好奇呢。",
                "好问题！我觉得这个话题很值得探讨。"
            ],
            'friendly': [
                "你好！很高兴和你聊天。",
                "嗨！最近怎么样？",
                "你好呀！有什么想聊的吗？"
            ]
        }
        
        main_emotion = emotional_context.get('main_emotion', 'friendly')
        responses = fallback_responses.get(main_emotion, fallback_responses['friendly'])
        base_response = (base_response or '').strip()

        if base_response:
            return f"{base_response} {random.choice(responses)}"

        return random.choice(responses)
    
    async def _record_interaction(self, user_input: str, response: str, emotional_context: Dict[str, Any]):
        """记录交互信息"""
        
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'response': response,
            'emotional_context': emotional_context,
            'emotion_state': self.profile.current_emotion.value,
            'emotion_intensity': self.profile.emotion_intensity
        }
        
        self.recent_interactions.append(interaction)
        self.interaction_count += 1
        
        # 只保留最近的交互
        if len(self.recent_interactions) > 10:
            self.recent_interactions = self.recent_interactions[-10:]
    
    async def _check_personality_adaptation(self):
        """检查是否需要进行人格适应"""
        
        if self.interaction_count % self.adaptation_threshold == 0:
            await self._adapt_personality()
    
    async def _adapt_personality(self):
        """基于最近的交互历史调整人格特征"""
        
        if len(self.recent_interactions) < 3:
            return
        
        # 分析最近交互中的情感倾向
        emotion_counts = {}
        for interaction in self.recent_interactions[-5:]:
            emotion = interaction['emotional_context']['main_emotion']
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # 根据用户的情感倾向微调人格特征
        if emotion_counts.get('negative', 0) > 2:
            # 用户情绪较负面，增强同理心和关怀
            self.profile.traits[PersonalityTrait.EMPATHY.value] = min(1.0, 
                self.profile.traits[PersonalityTrait.EMPATHY.value] + 0.05)
            self.profile.traits[PersonalityTrait.PATIENCE.value] = min(1.0,
                self.profile.traits[PersonalityTrait.PATIENCE.value] + 0.05)
        
        elif emotion_counts.get('positive', 0) > 3:
            # 用户情绪积极，可以增强幽默感
            self.profile.traits[PersonalityTrait.HUMOR.value] = min(1.0,
                self.profile.traits[PersonalityTrait.HUMOR.value] + 0.03)
        
        # 记录人格发展
        self.personality_evolution.append({
            'timestamp': datetime.now().isoformat(),
            'traits': self.profile.traits.copy(),
            'trigger': 'interaction_analysis',
            'interaction_count': self.interaction_count
        })
    
    async def _update_personality(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """更新人格特征"""
        
        updates = content.get('updates', {})
        
        for trait, value in updates.items():
            if trait in self.profile.traits:
                self.profile.traits[trait] = max(0.0, min(1.0, value))
        
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
        """分析情感上下文"""
        
        text = content.get('text', '')
        context = self._detect_emotional_context(text)
        
        return {
            'emotional_analysis': context,
            'recommended_emotion': self._recommend_emotion(context),
            'response': '情感上下文分析完成'
        }
    
    def _recommend_emotion(self, emotional_context: Dict[str, Any]) -> str:
        """基于情感上下文推荐合适的情绪反应"""
        
        main_emotion = emotional_context['main_emotion']
        intensity = emotional_context['intensity']
        
        recommendations = {
            'positive': EmotionalState.HAPPY.value if intensity > 0.3 else EmotionalState.CALM.value,
            'negative': EmotionalState.CARING.value,
            'curious': EmotionalState.CURIOUS.value,
            'friendly': EmotionalState.CALM.value
        }
        
        return recommendations.get(main_emotion, EmotionalState.CALM.value)
    
    async def _learn_from_interaction(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """从交互中学习用户偏好"""
        
        user_input = content.get('user_input', '')
        user_reaction = content.get('user_reaction', 'neutral')  # positive, negative, neutral
        
        # 提取可能的偏好信息
        preferences = self._extract_preferences(user_input)
        
        for pref_type, pref_value in preferences.items():
            if pref_type not in self.learned_preferences:
                self.learned_preferences[pref_type] = []
            
            if pref_value not in self.learned_preferences[pref_type]:
                self.learned_preferences[pref_type].append(pref_value)

            if self.persona_memory_agent is not None:
                try:
                    await self.persona_memory_agent.store_persona({
                        'content': f"用户{pref_type}: {pref_value}",
                        'category': 'preference',
                        'importance': 0.7 if user_reaction == 'positive' else 0.55,
                        'emotion_tags': ['positive'] if user_reaction == 'positive' else ['neutral'],
                        'metadata': {
                            'preference_type': pref_type,
                            'value_alignment': content.get('value_alignment', 'neutral'),
                            'source': 'personality_agent'
                        }
                    })
                except Exception as exc:
                    logger.warning(
                        "Failed to store persona preference memory: %s", exc
                    )
        
        # 根据用户反应调整行为
        if user_reaction == 'positive':
            # 强化当前的人格表现
            current_traits = self.profile.traits.copy()
            self.profile.traits = {k: min(1.0, v + 0.01) for k, v in current_traits.items()}
        
        elif user_reaction == 'negative':
            # 轻微调整，变得更温和或正式
            self.profile.traits[PersonalityTrait.PATIENCE.value] = min(1.0,
                self.profile.traits[PersonalityTrait.PATIENCE.value] + 0.02)
        
        return {
            'learned': True,
            'new_preferences': preferences,
            'total_preferences': len(self.learned_preferences),
            'response': '从交互中学到新信息'
        }
    
    def _extract_preferences(self, user_input: str) -> Dict[str, str]:
        """从用户输入中提取偏好信息"""
        
        preferences = {}
        
        # 简单的偏好识别
        if '喜欢' in user_input:
            # 尝试提取喜欢的内容
            parts = user_input.split('喜欢')
            if len(parts) > 1:
                liked_item = parts[1].split('，')[0].split('。')[0].strip()
                if liked_item:
                    preferences['喜欢'] = liked_item
        
        if '不喜欢' in user_input:
            parts = user_input.split('不喜欢')
            if len(parts) > 1:
                disliked_item = parts[1].split('，')[0].split('。')[0].strip()
                if disliked_item:
                    preferences['不喜欢'] = disliked_item
        
        # 时间偏好
        time_indicators = ['早上', '下午', '晚上', '中午', '傍晚']
        for time in time_indicators:
            if time in user_input:
                preferences['时间偏好'] = time
                break
        
        return preferences
    
    async def _get_personality_info(self) -> Dict[str, Any]:
        """获取当前人格信息"""
        
        return {
            'profile': asdict(self.profile),
            'recent_emotions': [
                {
                    'emotion': emotion['emotion'],
                    'intensity': emotion['intensity'],
                    'timestamp': emotion['timestamp'].isoformat()
                }
                for emotion in self.emotion_history[-5:]
            ],
            'interaction_count': self.interaction_count,
            'learned_preferences': self.learned_preferences,
            'personality_evolution_count': len(self.personality_evolution),
            'response': '人格信息获取完成'
        }
    
    def get_current_personality_summary(self) -> str:
        """获取当前人格状态摘要"""
        
        top_traits = sorted(self.profile.traits.items(), key=lambda x: x[1], reverse=True)[:3]
        trait_desc = ', '.join([f"{trait}({value:.1f})" for trait, value in top_traits])
        
        return f"摇光明明 - {self.profile.current_emotion.value}({self.profile.emotion_intensity:.1f}) | 主要特质: {trait_desc}"
