"""
Active Learning Manager
主动学习管理器 - 实现好奇心与提问机制

核心功能:
1. 监测低置信度回答 (Uncertainty Sampling)
2. 决定是否需要发起提问 (Curiosity Check)
3. 生成澄清性问题 (Question Generation)
4. 生成探索计划 (Exploration Planning)
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import random
import json

from ..utils.config import get_logger
from ..utils.model_selector import select_model_for_task
from ..services.shared_openai_client import shared_client_manager
from ..utils.parameters import LLMParams, MemoryParams, RetrievalParams, ProcessingParams, ThresholdParams
from ..coordination.soul_state import get_soul_state

logger = get_logger(__name__)

@dataclass
class GeneratedQuestion:
    """生成的提问对象"""
    content: str
    reason: str
    confidence_gap: float
    target_topic: str
    question_type: str = "clarification"  # clarification, exploration, confirmation

class ActiveLearningManager:
    """
    主动学习管理器
    
    负责在系统不确定时主动发起提问，获取新知识。
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.client_manager = shared_client_manager

        # 初始化 SoulState 连接
        self.soul_state = get_soul_state()

        # 默认配置
        self.enabled = self.config.get('active_learning_enabled', True)
        self.confidence_threshold = self.config.get('active_learning_threshold', 0.6) # Increased threshold
        self.curiosity_level = self.config.get('curiosity_level', 0.7)  # 0.0-1.0, 越高越爱问

        logger.info(f"✅ ActiveLearningManager initialized (enabled={self.enabled}, threshold={self.confidence_threshold})")

    async def check_and_generate_question(
        self, 
        query: str, 
        current_response: str, 
        confidence: float,
        context: Dict[str, Any]
    ) -> Optional[GeneratedQuestion]:
        """
        检查是否需要提问，如果需要则生成问题
        """
        if not self.enabled:
            return None
            
        # 1. Uncertainty Sampling Strategy
        # Probability of asking increases as confidence decreases
        uncertainty = 1.0 - confidence
        
        # If confidence is high, rarely ask (unless curiosity is very high)
        if confidence >= self.confidence_threshold:
            # Small chance to ask "confirmation" questions even if confident
            if random.random() > 0.95 and self.curiosity_level > 0.8:
                pass # Continue to ask
            else:
                return None
            
        # 2. Curiosity Check (Probabilistic)
        ask_probability = self.curiosity_level * uncertainty
        
        # Boost probability if query is a question (active dialogue)
        if "?" in query:
            ask_probability *= 1.2
            
        if random.random() > ask_probability:
            logger.debug(f"Active Learning: Skipped asking despite low confidence ({confidence:.2f}) due to curiosity check")
            return None
            
        # 3. Determine question topic
        topic = await self._extract_topic_llm(query)
        
        # 4. Generate question using LLM
        question_content = await self._generate_question_llm(query, current_response, topic)
        
        logger.info(f"🤔 Active Learning: Generated question about '{topic}' (confidence: {confidence:.2f})")
        await self.soul_state.async_add_thought(f"Generated clarification question: {question_content}")
        
        return GeneratedQuestion(
            content=question_content,
            reason="low_confidence",
            confidence_gap=uncertainty,
            target_topic=topic
        )

    async def generate_exploration_plan(self, recent_memories: List[Dict[str, Any]]) -> List[str]:
        """
        生成探索计划 (Dreaming/Daydreaming)
        当系统空闲时，基于最近的记忆生成需要进一步探索的主题
        """
        if not recent_memories:
            return []
            
        try:
            self.soul_state.set_dream_state(True) # Indicate dreaming state
            client = await self.client_manager.get_chat_client()
            model = select_model_for_task('planning')
            
            memory_texts = [m.get('content', '')[:100] for m in recent_memories[:5]]
            context_text = "\n".join(memory_texts)
            
            prompt = f"""Based on these recent memories, identify 3 topics that are ambiguous or worth exploring further to build a better world model.
            
            Memories:
            {context_text}
            
            Output JSON list of strings only:
            ["topic 1", "topic 2", "topic 3"]
            """
            
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLMParams.temperature_creative(),
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            topics = result.get('topics', [])
            if isinstance(result, list): 
                topics = result
                
            logger.info(f"🌌 Exploration Plan: Generated {len(topics)} topics to explore")
            self.soul_state.set_dream_state(False, topics) # Update soul state with generated topics
            return topics
            
        except Exception as e:
            logger.warning(f"Failed to generate exploration plan: {e}")
            self.soul_state.set_dream_state(False) # Reset dreaming state on failure
            return []

    async def _extract_topic_llm(self, query: str) -> str:
        """从查询中提取核心主题 (LLM版)"""
        try:
            client = await self.client_manager.get_chat_client()
            model = select_model_for_task('fast_classification')
            
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": f"Extract the main entity or concept from this text. Output ONLY the word/phrase.\nText: {query}"}],
                temperature=LLMParams.temperature_low(),
                max_tokens=LLMParams.max_tokens_short()
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return "this topic"

    async def _generate_question_llm(self, query: str, current_response: str, topic: str) -> str:
        """生成问题内容 (LLM版)"""
        try:
            client = await self.client_manager.get_chat_client()
            model = select_model_for_task('creative_writing')
            
            prompt = f"""You are a curious AI. You are unsure about '{topic}'.
            User asked: "{query}"
            You answered: "{current_response[:100]}..."
            
            Ask a short, natural follow-up question to clarify your understanding of '{topic}'.
            Be humble and curious.
            """
            
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=LLMParams.temperature_creative(),
                max_tokens=LLMParams.max_tokens_short()
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"Could you tell me more about {topic}?"
