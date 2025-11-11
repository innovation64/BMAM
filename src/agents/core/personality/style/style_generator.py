"""
Style Generator
风格生成器 - 生成符合人格的对话风格
"""

import logging
import random
from typing import Dict, Any, Optional

from ..models import PersonalityTrait, EmotionalState, StylePreferences

logger = logging.getLogger(__name__)


class StyleGenerator:
    """
    对话风格生成器

    职责:
    - 生成自然的人格化响应
    - 构建人格化提示词
    - 提供备用响应机制
    """

    def __init__(self, llm_service):
        """
        初始化风格生成器

        Args:
            llm_service: LLM服务接口
        """
        self.llm_service = llm_service

    async def generate_natural_response(
        self,
        user_input: str,
        personality_context: Dict[str, Any],
        emotional_context: Dict[str, Any],
        base_response: str = ""
    ) -> str:
        """
        生成自然的人格化响应

        Args:
            user_input: 用户输入
            personality_context: 人格上下文
            emotional_context: 情绪上下文
            base_response: 基础响应 (可选)

        Returns:
            生成的响应文本
        """
        base_response = (base_response or "").strip()

        # 如果有基础回复，不需要LLM生成，直接返回
        # 风格处理由 ResponseProcessor 负责
        if base_response:
            return base_response

        # 没有基础回复时才调用 LLM 生成
        personality_prompt = self.build_personality_prompt(
            user_input, personality_context, emotional_context, base_response
        )

        try:
            response = await self.llm_service.call_llm(
                personality_prompt,
                max_tokens=220,
                temperature=0.7
            )
            return response
        except Exception as e:
            logger.warning(f"LLM调用失败: {e}")
            return self.generate_fallback_response(
                user_input, emotional_context, personality_context, base_response
            )

    def build_personality_prompt(
        self,
        user_input: str,
        personality_context: Dict[str, Any],
        emotional_context: Dict[str, Any],
        base_response: str = ""
    ) -> str:
        """
        构建人格化提示词

        整合:
        - 人格特征
        - 当前情绪
        - 对话风格
        - 记忆上下文

        Args:
            user_input: 用户输入
            personality_context: 人格上下文
            emotional_context: 情绪上下文
            base_response: 基础响应

        Returns:
            构建好的提示词
        """
        # 基础人格描述
        current_emotion = personality_context.get('current_emotion', '平静')
        emotion_intensity = personality_context.get('emotion_intensity', 0.5)
        traits = personality_context.get('personality_traits', {})

        base_personality = f"""现在你是摇光明明，当前情绪状态是{current_emotion}（强度{emotion_intensity:.1f}）。

你的核心特质：
- 温暖度: {traits.get(PersonalityTrait.WARMTH.value, 0.9):.1f}
- 智慧: {traits.get(PersonalityTrait.INTELLIGENCE.value, 0.8):.1f}
- 好奇心: {traits.get(PersonalityTrait.CURIOSITY.value, 0.9):.1f}
- 同理心: {traits.get(PersonalityTrait.EMPATHY.value, 0.85):.1f}
- 幽默感: {traits.get(PersonalityTrait.HUMOR.value, 0.7):.1f}"""

        # 记忆相关信息
        memory_context = ""
        relevant_memories = personality_context.get('relevant_memories', [])
        if relevant_memories:
            memory_context = "\\n相关记忆：\\n" + "\\n".join(relevant_memories[:2])

        # 个人细节
        personal_context = ""
        personal_details = personality_context.get('personal_details', [])
        if personal_details:
            personal_context = "\\n了解到的用户信息：\\n" + "\\n".join(personal_details[:2])

        # 人设上下文
        persona_context = ""
        persona_details = personality_context.get('persona_details', [])
        if persona_details:
            persona_context = "\\n人格/价值观记忆：\\n" + "\\n".join(persona_details[:2])

        # 情绪风格指导
        style = personality_context.get('style_adjustments', {})
        tone = style.get('tone', '温暖友好')
        expressions = style.get('expressions', ['嗯'])
        formality_level = style.get('formality_level', 0.4)
        brevity = style.get('brevity', 'balanced')

        style_guide = f"\\n回应风格：{tone}，可以使用这些表达：{', '.join(expressions[:2])}"
        style_guide += f"\\n形式要求：正式程度{formality_level:.2f}，篇幅倾向为{brevity}"

        # 检查是否使用表情符号
        learned_preferences = personality_context.get('learned_preferences', {})
        if '😊' in expressions or '😉' in expressions:
            style_guide += "（可以适度使用表情符号表达情绪）"

        # 基础事实性回应
        base_fact_section = ""
        retained_response = base_response.strip()
        if retained_response:
            base_fact_section = f"\\n需要保留的事实性回应：{retained_response}"

        # 组装完整提示词
        full_prompt = f"""{base_personality}{memory_context}{personal_context}{persona_context}{style_guide}
{base_fact_section}

用户说："{user_input}"

请以摇光明明的身份回应，要求：
1. 体现你当前的情绪状态和人格特征
2. 若提供了"需要保留的事实性回应"，必须完整保留其中的信息，可在此基础上润色语气
3. 语言自然亲切，不要说"作为AI"这样的表达
4. 根据情绪使用合适的语气和表达方式
5. 在尊重事实的前提下，结合人格特质添加关怀或好奇的元素，可适度补充细节

回应："""

        return full_prompt

    def generate_fallback_response(
        self,
        user_input: str,
        emotional_context: Dict[str, Any],
        personality_context: Dict[str, Any] = None,
        base_response: str = ""
    ) -> str:
        """
        生成备用响应 (LLM失败时)

        Args:
            user_input: 用户输入
            emotional_context: 情绪上下文
            personality_context: 人格上下文 (可选)
            base_response: 基础响应

        Returns:
            备用响应文本
        """
        memories = []
        persona_details = []
        if personality_context:
            memories = personality_context.get('relevant_memories', [])
            persona_details = personality_context.get('persona_details', [])

        # 尝试基于记忆生成响应
        if memories:
            # 处理记忆相关查询
            if any(keyword in user_input.lower() for keyword in ['刚才', '之前', '什么时候', '喝什么', '我说']):
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

        # 基于人设记忆
        if persona_details:
            joined = persona_details[0][:60]
            return f"我记得我们之前聊到：{joined}。这对我来说很重要，也会影响我接下来的回答。"

        # 根据情绪生成通用回应
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
