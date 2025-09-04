from typing import Dict, Any, List, Optional
from .base import BaseAgent
import json

class GeneratorAgent(BaseAgent):
    """修复版生成器 - 专注于简洁、准确的响应"""
    
    def __init__(self, api_client=None, config: Optional[Dict[str, Any]] = None):
        super().__init__("Generator", config)
        self.api_client = api_client
        
        # Ensure config is not None
        if config is None:
            config = {}
            
        self.max_context_length = config.get('max_context_length', 4000)
        self.temperature = config.get('temperature', 0.7)
        # 减少最大token数以避免过长响应
        self.max_tokens = config.get('max_tokens', 200)  # 从1000降到200
        
        # Response style control
        self.response_style = config.get('response_style', 'detailed')  # 'simple' or 'detailed'
        self.simple_max_tokens = config.get('simple_max_tokens', 50)   # For simple responses
        
        # Initialize OpenAI if no API client provided
        if self.api_client is None:
            self._initialize_openai()
    
    def set_response_style(self, style: str):
        """设置响应风格: 'simple' 或 'detailed'"""
        if style in ['simple', 'detailed']:
            self.response_style = style
            self.logger.info(f"Response style set to: {style}")
        else:
            self.logger.warning(f"Invalid response style: {style}. Using 'detailed'")
            self.response_style = 'detailed'
        
    def _initialize_openai(self):
        """Initialize OpenAI API client"""
        try:
            import os
            import sys
            from pathlib import Path
            
            # Add utils to path
            sys.path.append(str(Path(__file__).parent.parent))
            from utils.ensure_api import ensure_openai_api
            
            # Ensure API key is loaded
            if ensure_openai_api():
                from openai import AsyncOpenAI
                api_key = os.getenv('OPENAI_API_KEY')
                self.api_client = AsyncOpenAI(api_key=api_key)
                self.model_name = "gpt-4o-mini"
                self.logger.info("✅ Using OpenAI for response generation")
            else:
                self.logger.warning("❌ No valid OpenAI API key found, generator will use fallback")
                self.api_client = None
                
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI client: {e}")
            self.api_client = None
        
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成简洁、直接的响应"""
        query = input_data.get('query', '')
        documents = input_data.get('retrieved_documents', [])
        memory_state = input_data.get('memory_state', {})
        conversation_history = input_data.get('conversation_history', [])
        
        # Check for response style override in input
        response_style = input_data.get('response_style', self.response_style)
        
        # Check for feedback requests first
        feedback_requests = memory_state.get('feedback_requests', [])
        is_feedback_request = len(feedback_requests) > 0
        
        # 构建生成提示（根据风格调整）
        prompt = self._build_style_aware_prompt(query, documents, memory_state, conversation_history, response_style)
        
        # 根据风格调整token限制
        original_max_tokens = self.max_tokens
        if is_feedback_request:
            # Always use more tokens for feedback processing
            self.max_tokens = max(self.max_tokens, 300)  # At least 300 tokens for feedback
        elif response_style == 'simple':
            self.max_tokens = self.simple_max_tokens
        
        # 生成响应
        if self.api_client:
            response = await self._generate_with_api(prompt)
        else:
            # Use fallback generator
            try:
                from utils.api_fallback import FallbackGenerator
                fallback = FallbackGenerator()
                
                # Extract conditions from memory state
                conditions = {}
                if isinstance(memory_state, dict) and 'conditions' in memory_state:
                    # Convert flat list to categorized dict
                    conditions = {
                        'hard_constraints': [],
                        'soft_preferences': [],
                        'negations': [],
                        'temporal_conditions': []
                    }
                    for cond in memory_state.get('conditions', []):
                        category = cond.get('category', 'soft_preferences')
                        if category in conditions:
                            conditions[category].append(cond)
                
                response = fallback.generate_response(query, conditions, documents)
                self.logger.warning("Using fallback response generation")
            except Exception as e:
                self.logger.error(f"Fallback generation failed: {e}")
                response = "Unable to generate response."
        
        # 恢复原始token限制
        self.max_tokens = original_max_tokens
        
        # 后处理：移除系统内部标识符
        response = self._clean_response(response)
        
        return {
            "status": "success",
            "response": response,
            "response_style": response_style,
            "prompt_length": len(prompt),
            "documents_used": len(documents),
            "conditions_considered": len(memory_state.get('conditions', [])),
        }
    
    def _build_concise_prompt(self, query: str, documents: List[Dict[str, Any]], 
                             memory_state: Dict[str, Any], 
                             conversation_history: List[Dict[str, Any]]) -> str:
        """构建简洁、聚焦的生成提示"""
        prompt_parts = []
        
        # Enhanced system instructions for dialogue continuation
        if conversation_history:
            prompt_parts.append("You are continuing an ongoing conversation. Use the conversation history and retrieved memories to provide contextually appropriate responses. Build on the previous discussion and reference specific facts from your memory.")
        else:
            prompt_parts.append("You are a helpful AI assistant with access to memory about the user. Use the retrieved information and stored preferences to provide personalized, direct answers. Always use specific facts from memory when available.")
        
        # 添加对话历史上下文
        if conversation_history:
            prompt_parts.append("\nConversation history:")
            for turn in conversation_history[-5:]:  # 只显示最近5轮对话
                role = turn.get('role', 'unknown')
                content = turn.get('content', '')
                if content:
                    # 限制每个对话内容的长度
                    if len(content) > 300:
                        content = content[:300] + "..."
                    prompt_parts.append(f"{role.capitalize()}: {content}")
        
        # 添加关键条件（包括所有类型）
        all_conditions = []
        
        # Collect all condition types from memory_state
        for condition_type in ['hard_constraints', 'soft_preferences', 'temporal_conditions', 'negations']:
            conditions = memory_state.get(condition_type, [])
            if conditions:
                all_conditions.extend(conditions)
        
        # Also include flat conditions list for backward compatibility
        if 'conditions' in memory_state:
            all_conditions.extend(memory_state['conditions'])
        
        if all_conditions:
            prompt_parts.append("\nUser preferences and information to consider:")
            
            # Show the most important conditions
            important_conditions = sorted(all_conditions, 
                                        key=lambda c: c.get('importance_score', c.get('confidence', 'medium') == 'high' and 0.8 or 0.5), 
                                        reverse=True)[:5]  # Show more conditions
            
            for condition in important_conditions:
                condition_text = condition.get('text', '').strip()
                if condition_text:
                    # 去除技术性描述，使用用户友好的语言
                    clean_text = self._humanize_condition(condition_text)
                    if clean_text:
                        prompt_parts.append(f"- {clean_text}")
        
        # 添加相关文档信息（简化）
        if documents:
            prompt_parts.append("\nKnown facts about the user:")
            for doc_data in documents[:5]:  # Use more documents for better recall
                content = self._extract_document_content(doc_data.get('document', {}))
                # Keep more content for better memory utilization
                if len(content) > 200:
                    content = content[:200] + "..."
                prompt_parts.append(f"- {content}")
            
            prompt_parts.append("\nIMPORTANT: Use these facts to answer the user's question. Do not say you don't have access to information if it's listed above.")
        
        # 当前查询
        prompt_parts.append(f"\nCurrent user message: {query}")
        
        # Enhanced continuation instructions
        if conversation_history:
            prompt_parts.append("\nContinue the conversation naturally using the known facts above. Your response should build on the previous discussion and directly address the user's current message using specific information from memory.")
        else:
            prompt_parts.append("\nProvide a direct, helpful answer using the known facts above. Reference specific information when answering the user's question. Do NOT claim you don't have access to information that is clearly provided.")
        
        return "\n".join(prompt_parts)
    
    def _build_style_aware_prompt(self, query: str, documents: List[Dict[str, Any]], 
                                 memory_state: Dict[str, Any], 
                                 conversation_history: List[Dict[str, Any]],
                                 response_style: str) -> str:
        """构建风格感知的生成提示"""
        prompt_parts = []
        
        # Check for feedback requests first
        feedback_requests = memory_state.get('feedback_requests', [])
        is_feedback_request = len(feedback_requests) > 0
        
        # 根据风格设置系统指令
        if is_feedback_request:
            # Special handling for feedback requests - detect specific feedback type
            feedback_type = feedback_requests[0].get('feedback_type', 'general_improvement')
            if feedback_type == 'add_quantities':
                prompt_parts.append("The user is asking you to improve a previous grocery list by adding specific quantities to each item. Look at the conversation history to find the original grocery list, then enhance it by adding specific quantities like '2 lbs', '1 cup', '3 pieces', etc. for each item. Provide a complete detailed grocery list with quantities.")
            else:
                prompt_parts.append("You are processing a user's feedback to improve a previous response. The user wants you to refine or enhance something you previously provided. Look at the conversation history to identify what needs to be improved and apply the user's feedback to create a better, more detailed version.")
        elif response_style == 'simple':
            if conversation_history:
                prompt_parts.append("You are continuing an ongoing conversation. Provide a brief, direct answer using the retrieved memories. Keep your response concise and factual - typically 1-2 short sentences.")
            else:
                prompt_parts.append("You are a helpful AI assistant. Provide brief, direct answers using your memory about the user. Keep responses concise and factual - typically 1-2 short sentences. Answer directly without extra explanations.")
        else:  # detailed
            if conversation_history:
                prompt_parts.append("You are continuing an ongoing conversation. Use the conversation history and retrieved memories to provide contextually appropriate responses. Build on the previous discussion and reference specific facts from your memory.")
            else:
                prompt_parts.append("You are a helpful AI assistant with access to memory about the user. Use the retrieved information and stored preferences to provide personalized, direct answers. Always use specific facts from memory when available.")
        
        # 添加对话历史上下文
        if conversation_history:
            prompt_parts.append("\nConversation history:")
            for turn in conversation_history[-5:]:  # 只显示最近5轮对话
                role = turn.get('role', 'unknown')
                content = turn.get('content', '')
                if content:
                    # 限制每个对话内容的长度
                    if len(content) > 300:
                        content = content[:300] + "..."
                    prompt_parts.append(f"{role.capitalize()}: {content}")
        
        # 添加关键条件（根据风格调整数量）
        all_conditions = []
        
        # Check for feedback requests first
        feedback_requests = memory_state.get('feedback_requests', [])
        
        # Collect all condition types from memory_state
        for condition_type in ['hard_constraints', 'soft_preferences', 'biographical_facts', 'temporal_conditions', 'negations', 'feedback_requests']:
            conditions = memory_state.get(condition_type, [])
            if conditions:
                all_conditions.extend(conditions)
        
        # Also include flat conditions list for backward compatibility
        if 'conditions' in memory_state:
            all_conditions.extend(memory_state['conditions'])
        
        if all_conditions:
            prompt_parts.append("\nUser preferences and information to consider:")
            
            # 根据风格调整显示的条件数量
            max_conditions = 3 if response_style == 'simple' else 5
            important_conditions = sorted(all_conditions, 
                                        key=lambda c: c.get('importance_score', c.get('confidence', 'medium') == 'high' and 0.8 or 0.5), 
                                        reverse=True)[:max_conditions]
            
            for condition in important_conditions:
                condition_text = condition.get('text', '').strip()
                if condition_text:
                    # 去除技术性描述，使用用户友好的语言
                    clean_text = self._humanize_condition(condition_text)
                    if clean_text:
                        prompt_parts.append(f"- {clean_text}")
        
        # 添加相关文档信息（根据风格调整）
        if documents:
            prompt_parts.append("\nKnown facts about the user:")
            doc_limit = 3 if response_style == 'simple' else 5
            for doc_data in documents[:doc_limit]:
                content = self._extract_document_content(doc_data.get('document', {}))
                # 根据风格调整内容长度
                max_content_length = 100 if response_style == 'simple' else 200
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "..."
                prompt_parts.append(f"- {content}")
            
            if response_style == 'simple':
                prompt_parts.append("\nIMPORTANT: Use these facts to answer briefly and directly. Keep your response short and factual.")
            else:
                prompt_parts.append("\nIMPORTANT: Use these facts to answer the user's question. Do not say you don't have access to information if it's listed above.")
        
        # 当前查询
        prompt_parts.append(f"\nCurrent user message: {query}")
        
        # 根据风格设置结尾指令
        if is_feedback_request:
            # Special instructions for feedback processing
            if feedback_requests:
                feedback_details = feedback_requests[0]  # Use first feedback request
                feedback_type = feedback_details.get('feedback_type', 'general_feedback')
                
                if feedback_type == 'add_quantities':
                    prompt_parts.append("\nThe user wants you to add specific quantities to your previous response. Take your previous response from the conversation history and enhance it by adding specific measurements, amounts, or quantities where appropriate. For example, if you provided a grocery list, add specific quantities like '2 lbs chicken breast', '1 cup quinoa', etc.")
                elif feedback_type == 'add_information':
                    prompt_parts.append("\nThe user wants you to add more information to your previous response. Take your previous response and enhance it with additional relevant details, explanations, or examples.")
                else:
                    prompt_parts.append("\nThe user wants you to improve your previous response. Look at the conversation history, identify what needs to be enhanced based on their feedback, and provide an improved version.")
            else:
                prompt_parts.append("\nThe user is asking you to improve or refine something. Look at the conversation history and provide an enhanced version based on their request.")
        elif response_style == 'simple':
            if conversation_history:
                prompt_parts.append("\nProvide a brief, direct response (1-2 sentences) using the known facts above. Continue the conversation naturally but keep it concise.")
            else:
                prompt_parts.append("\nProvide a brief, direct answer (1-2 sentences) using the known facts above. Be factual and concise.")
        else:  # detailed
            if conversation_history:
                prompt_parts.append("\nContinue the conversation naturally using the known facts above. Your response should build on the previous discussion and directly address the user's current message using specific information from memory.")
            else:
                prompt_parts.append("\nProvide a direct, helpful answer using the known facts above. Reference specific information when answering the user's question. Do NOT claim you don't have access to information that is clearly provided.")
        
        return "\n".join(prompt_parts)
    
    def _humanize_condition(self, condition_text: str) -> str:
        """将技术性条件转换为用户友好的语言"""
        # 移除常见的技术性前缀
        prefixes_to_remove = [
            "user prefers", "user wants", "user needs", "user requires",
            "preference for", "requirement for", "constraint:"
        ]
        
        clean_text = condition_text.lower()
        for prefix in prefixes_to_remove:
            if clean_text.startswith(prefix):
                clean_text = clean_text[len(prefix):].strip()
                break
        
        # 移除常见的系统性词汇
        system_terms = ["MUST SATISFY", "SHOULD CONSIDER", "AVOID/EXCLUDE"]
        for term in system_terms:
            clean_text = clean_text.replace(term.lower(), "")
        
        # 确保首字母大写
        clean_text = clean_text.strip()
        if clean_text:
            clean_text = clean_text[0].upper() + clean_text[1:]
        
        return clean_text
    
    def _clean_response(self, response: str) -> str:
        """清理响应，移除系统内部标识符"""
        # 移除常见的系统标识符
        markers_to_remove = [
            "MUST SATISFY", "SHOULD CONSIDER", "AVOID/EXCLUDE", 
            "TIME-RELATED:", "[Turn ", "=== ", "SPECIAL NOTE",
            "INSTRUCTIONS:", "(MUST SATISFY)", "(SHOULD CONSIDER)"
        ]
        
        clean_response = response
        for marker in markers_to_remove:
            clean_response = clean_response.replace(marker, "")
        
        # 移除多余的空行和格式
        lines = [line.strip() for line in clean_response.split('\n') if line.strip()]
        clean_response = '\n'.join(lines)
        
        # 移除多余的项目符号和编号（如果太多的话）
        if clean_response.count('\n') > 10:  # 如果超过10行，简化格式
            # 保留主要内容，去除详细的列表项
            paragraphs = clean_response.split('\n\n')
            if len(paragraphs) > 1:
                clean_response = paragraphs[0]  # 只保留第一段
        
        return clean_response.strip()
    
    async def _generate_with_api(self, prompt: str) -> str:
        """使用API生成响应（带长度限制）"""
        try:
            # Check if we have OpenAI client
            if hasattr(self.api_client, 'chat'):
                # OpenAI API
                response = await self.api_client.chat.completions.create(
                    model=getattr(self, 'model_name', 'gpt-4o-mini'),
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.choices[0].message.content.strip()
            else:
                # Use unified API client
                response = await self.api_client.generate(
                    prompt=prompt,
                    model="gpt-4o-mini",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.strip()
        except Exception as e:
            self.logger.error(f"API generation failed: {e}")
            return "Unable to generate response due to API error."
    
    # Mock generation method removed - framework now requires real AI API
    
    def _extract_query_topic(self, query: str) -> str:
        """Extract main topic from query"""
        # Extract first significant word as topic
        words = query.split()
        for word in words:
            if len(word) > 3 and word.isalpha():
                return word.lower()
        
        return "your question"
    
    def _extract_document_content(self, document: Dict[str, Any]) -> str:
        """提取文档内容"""
        if isinstance(document, dict):
            # Try different possible content fields
            for field in ['content', 'text', 'description', 'summary']:
                if field in document and document[field]:
                    return str(document[field])
            # If no content fields, return string representation
            return str(document)
        elif isinstance(document, str):
            return document
        else:
            return str(document)