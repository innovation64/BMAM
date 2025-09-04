"""
Conversation Agent
对话智能体 - 对应语言区（Broca + Wernicke）
"""

from collections import deque
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

from ..base import BrainAgent, AgentMessage

logger = logging.getLogger(__name__)


class ConversationAgent(BrainAgent):
    """
    Conversation Agent (Language Areas - Broca + Wernicke)
    
    对应脑区：语言区（Broca + Wernicke）
    主要功能：自然语言理解与生成，对话管理
    """
    
    def __init__(self):
        super().__init__(
            agent_id="conversation",
            brain_region="language_cortex",
            system_prompt="""You are the language processing system of a brain-inspired AI.
            Your role is to:
            1. Process and understand natural language input from users
            2. Generate appropriate and contextual responses
            3. Maintain conversation context and coherence
            4. Extract meaning and intent from user communications
            5. Adapt communication style based on context and user needs"""
        )
        
        # Conversation management
        self.conversation_history = deque(maxlen=50)  # Extended conversation memory
        self.context_window = deque(maxlen=10)        # Recent context
        self.active_topics = []                       # Currently active topics
        
        # Language processing components
        self.intent_recognition = {
            'question': ['what', 'how', 'why', 'when', 'where', 'who', '?'],
            'request': ['please', 'can you', 'could you', 'would you'],
            'command': ['do', 'create', 'make', 'generate', 'build'],
            'information': ['tell me', 'explain', 'describe', 'information about'],
            'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon'],
            'farewell': ['goodbye', 'bye', 'see you', 'talk later']
        }
        
        # Conversation states
        self.conversation_state = {
            'mode': 'normal',  # normal, focused, casual, formal
            'topic_depth': 'surface',  # surface, intermediate, deep
            'user_engagement': 'moderate',  # low, moderate, high
            'formality_level': 'moderate'  # casual, moderate, formal
        }
        
        # Response generation settings
        self.response_styles = {
            'casual': {'temperature': 0.8, 'formality': 'low', 'length': 'short'},
            'moderate': {'temperature': 0.7, 'formality': 'medium', 'length': 'medium'},
            'formal': {'temperature': 0.6, 'formality': 'high', 'length': 'detailed'},
            'technical': {'temperature': 0.5, 'formality': 'high', 'length': 'comprehensive'}
        }
        
        # Statistics
        self.conversations_processed = 0
        self.responses_generated = 0
        self.intents_detected = 0
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process conversation and language requests"""
        action = message.content.get('action')
        
        if action == 'process_input':
            return await self._process_user_input(message.content['input'])
        elif action == 'generate_response':
            return await self._generate_response(message.content['context'])
        elif action == 'maintain_context':
            return await self._maintain_conversation_context(message.content['utterance'])
        elif action == 'analyze_intent':
            return await self._analyze_user_intent(message.content['text'])
        elif action == 'extract_entities':
            return await self._extract_entities(message.content['text'])
        elif action == 'conversation_summary':
            return await self._generate_conversation_summary()
        elif action == 'adapt_style':
            return await self._adapt_communication_style(message.content['style_cues'])
        
        return {'error': f'Unknown conversation action: {action}'}
    
    async def _process_user_input(self, user_input: str) -> Dict[str, Any]:
        """Comprehensive processing of user input"""
        
        # Multi-faceted analysis of input
        analysis = {
            'input_text': user_input,
            'intent': await self._detect_intent(user_input),
            'entities': await self._extract_entities(user_input),
            'sentiment': await self._analyze_sentiment(user_input),
            'topics': await self._extract_topics(user_input),
            'complexity': self._assess_input_complexity(user_input),
            'formality': self._assess_formality_level(user_input),
            'emotional_tone': await self._detect_emotional_tone(user_input)
        }
        
        # Update conversation state
        self._update_conversation_state(analysis)
        
        # Add to conversation history
        conversation_turn = {
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now(),
            'analysis': analysis,
            'turn_id': len(self.conversation_history)
        }
        
        self.conversation_history.append(conversation_turn)
        self.conversations_processed += 1
        
        # Update active topics
        self._update_active_topics(analysis['topics'])
        
        return {
            'input_processed': True,
            'analysis': analysis,
            'conversation_state': self.conversation_state.copy(),
            'active_topics': self.active_topics.copy()
        }
    
    async def _generate_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate contextually appropriate response"""
        
        # 提取用户输入和记忆
        user_input = context.get('user_input', '')
        memories = context.get('memories', [])
        
        # 检测是否有引用之前的对话
        reference_detected = self._detect_reference_intent(user_input)
        
        # Prepare response generation context
        response_context = self._prepare_response_context(context)
        response_context['memories'] = memories
        response_context['user_input'] = user_input
        response_context['reference_detected'] = reference_detected
        
        # Select appropriate response style
        response_style = self._select_response_style(context)
        
        # Generate base response using LLM with memories
        base_response = await self._generate_base_response_with_memory(response_context, response_style)
        
        # Post-process response
        final_response = await self._post_process_response(base_response, response_context)
        
        # Add to conversation history
        conversation_turn = {
            'role': 'assistant',
            'content': final_response,
            'timestamp': datetime.now(),
            'context_used': response_context,
            'style': response_style,
            'turn_id': len(self.conversation_history)
        }
        
        self.conversation_history.append(conversation_turn)
        self.responses_generated += 1
        
        return {
            'response': final_response,
            'response_style': response_style,
            'context_used': response_context,
            'conversation_length': len(self.conversation_history),
            'reference_detected': reference_detected,
            'memories_used': len(memories)
        }
    
    async def _maintain_conversation_context(self, utterance: Dict[str, Any]) -> Dict[str, Any]:
        """Maintain and update conversation context"""
        
        # Extract contextual elements from utterance
        context_elements = {
            'topic': utterance.get('topic'),
            'entities': utterance.get('entities', []),
            'intent': utterance.get('intent'),
            'emotional_state': utterance.get('emotional_state'),
            'temporal_references': self._extract_temporal_references(utterance),
            'spatial_references': self._extract_spatial_references(utterance)
        }
        
        # Add to context window
        self.context_window.append({
            'utterance': utterance,
            'context_elements': context_elements,
            'timestamp': datetime.now()
        })
        
        # Update conversation coherence
        coherence_score = self._calculate_conversation_coherence()
        
        # Detect context shifts
        context_shift = self._detect_context_shift(context_elements)
        
        return {
            'context_updated': True,
            'context_elements': context_elements,
            'context_window_size': len(self.context_window),
            'coherence_score': coherence_score,
            'context_shift_detected': context_shift['detected'],
            'shift_type': context_shift.get('type', None)
        }
    
    async def _analyze_user_intent(self, text: str) -> Dict[str, Any]:
        """Analyze user intent with confidence scores"""
        
        # Rule-based intent detection
        rule_based_intents = self._detect_intent_rules(text)
        
        # LLM-based intent analysis for complex cases
        llm_intent_analysis = await self._detect_intent_llm(text)
        
        # Combine and score intents
        combined_intents = self._combine_intent_analyses(rule_based_intents, llm_intent_analysis)
        
        # Select primary intent
        primary_intent = max(combined_intents, key=combined_intents.get) if combined_intents else 'unknown'
        
        self.intents_detected += 1
        
        return {
            'primary_intent': primary_intent,
            'intent_confidence': combined_intents.get(primary_intent, 0.0),
            'all_intents': combined_intents,
            'analysis_method': 'hybrid',
            'rule_based': rule_based_intents,
            'llm_based': llm_intent_analysis
        }
    
    async def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract named entities and key concepts"""
        
        # Simple entity extraction using LLM
        entity_prompt = f"""Extract entities from this text and categorize them:
        Text: {text}
        
        Categories: PERSON, PLACE, ORGANIZATION, DATE, TIME, CONCEPT, OBJECT
        Format: entity_name (CATEGORY)
        """
        
        entities_text = await self.call_llm(entity_prompt)
        
        # Parse extracted entities
        entities = self._parse_entities_response(entities_text)
        
        # Additional keyword extraction
        keywords = self._extract_keywords(text)
        
        return {
            'named_entities': entities,
            'keywords': keywords,
            'entity_count': len(entities),
            'keyword_count': len(keywords)
        }
    
    async def _generate_conversation_summary(self) -> Dict[str, Any]:
        """Generate summary of current conversation"""
        
        if not self.conversation_history:
            return {
                'summary': 'No conversation to summarize',
                'key_topics': [],
                'conversation_length': 0
            }
        
        # Extract conversation content
        conversation_content = []
        for turn in self.conversation_history[-10:]:  # Last 10 turns
            conversation_content.append(f"{turn['role']}: {turn['content']}")
        
        conversation_text = "\n".join(conversation_content)
        
        # Generate summary using LLM
        summary_prompt = f"""Summarize this conversation in 2-3 sentences:
        {conversation_text}
        
        Focus on main topics and key points discussed.
        """
        
        summary = await self.call_llm(summary_prompt)
        
        # Extract key topics from conversation
        key_topics = self._extract_conversation_topics()
        
        # Calculate conversation metrics
        metrics = self._calculate_conversation_metrics()
        
        return {
            'summary': summary,
            'key_topics': key_topics,
            'conversation_length': len(self.conversation_history),
            'metrics': metrics,
            'active_topics': self.active_topics.copy()
        }
    
    async def _adapt_communication_style(self, style_cues: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt communication style based on cues"""
        
        # Analyze style cues
        style_analysis = {
            'formality_cues': style_cues.get('formality_indicators', []),
            'emotional_cues': style_cues.get('emotional_indicators', []),
            'complexity_cues': style_cues.get('complexity_indicators', []),
            'relationship_cues': style_cues.get('relationship_indicators', [])
        }
        
        # Determine target style
        target_style = self._determine_target_style(style_analysis)
        
        # Update conversation state
        old_state = self.conversation_state.copy()
        self.conversation_state.update({
            'formality_level': target_style['formality'],
            'complexity_level': target_style['complexity'],
            'emotional_tone': target_style['emotional_tone']
        })
        
        return {
            'style_adapted': True,
            'target_style': target_style,
            'old_state': old_state,
            'new_state': self.conversation_state.copy(),
            'adaptation_confidence': target_style.get('confidence', 0.5)
        }
    
    # Helper methods for conversation processing
    
    async def _detect_intent(self, text: str) -> str:
        """Simple intent detection"""
        text_lower = text.lower()
        
        # Check for question patterns
        if '?' in text or any(word in text_lower for word in ['what', 'how', 'why', 'when', 'where', 'who']):
            return 'question'
        
        # Check for request patterns
        if any(phrase in text_lower for phrase in ['please', 'can you', 'could you', 'would you']):
            return 'request'
        
        # Check for command patterns
        if any(word in text_lower for word in ['do', 'create', 'make', 'generate', 'build']):
            return 'command'
        
        # Check for greeting patterns
        if any(word in text_lower for word in ['hello', 'hi', 'hey']):
            return 'greeting'
        
        return 'statement'
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text"""
        prompt = f"Analyze the sentiment of this text (positive/negative/neutral with confidence 0-1): {text}"
        
        try:
            sentiment_response = await self.call_llm(prompt)
            
            # Parse sentiment response
            if 'positive' in sentiment_response.lower():
                sentiment = 'positive'
            elif 'negative' in sentiment_response.lower():
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            # Extract confidence if possible
            import re
            confidence_match = re.search(r'(\d*\.?\d+)', sentiment_response)
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'raw_response': sentiment_response
            }
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {'sentiment': 'neutral', 'confidence': 0.5}
    
    async def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics from text"""
        prompt = f"Extract the main topics (max 3) from this text: {text}"
        
        try:
            topics_response = await self.call_llm(prompt)
            topics = [topic.strip() for topic in topics_response.split(',')]
            return topics[:3]  # Max 3 topics
        except Exception as e:
            logger.error(f"Topic extraction error: {e}")
            return []
    
    def _assess_input_complexity(self, text: str) -> str:
        """Assess complexity of input text"""
        word_count = len(text.split())
        avg_word_length = sum(len(word) for word in text.split()) / word_count if word_count > 0 else 0
        
        if word_count < 10 and avg_word_length < 5:
            return 'simple'
        elif word_count < 30 and avg_word_length < 7:
            return 'moderate'
        else:
            return 'complex'
    
    def _assess_formality_level(self, text: str) -> str:
        """Assess formality level of text"""
        formal_indicators = ['please', 'would', 'could', 'kindly', 'appreciate']
        casual_indicators = ['hey', 'gonna', 'wanna', 'yeah', 'ok']
        
        formal_count = sum(1 for indicator in formal_indicators if indicator in text.lower())
        casual_count = sum(1 for indicator in casual_indicators if indicator in text.lower())
        
        if formal_count > casual_count:
            return 'formal'
        elif casual_count > formal_count:
            return 'casual'
        else:
            return 'moderate'
    
    async def _detect_emotional_tone(self, text: str) -> Dict[str, float]:
        """Detect emotional tone in text"""
        emotions = {
            'joy': ['happy', 'glad', 'excited', 'thrilled', 'delighted'],
            'sadness': ['sad', 'unhappy', 'disappointed', 'upset', 'down'],
            'anger': ['angry', 'mad', 'frustrated', 'annoyed', 'irritated'],
            'fear': ['scared', 'afraid', 'worried', 'anxious', 'nervous'],
            'neutral': []
        }
        
        emotion_scores = {}
        text_lower = text.lower()
        
        for emotion, keywords in emotions.items():
            if emotion == 'neutral':
                continue
            
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score / len(keywords)
        
        # If no emotions detected, default to neutral
        if not emotion_scores:
            emotion_scores['neutral'] = 1.0
        
        return emotion_scores
    
    def _update_conversation_state(self, analysis: Dict[str, Any]):
        """Update conversation state based on analysis"""
        
        # Update formality level
        if analysis['formality'] != self.conversation_state['formality_level']:
            self.conversation_state['formality_level'] = analysis['formality']
        
        # Update complexity handling
        if analysis['complexity'] == 'complex':
            self.conversation_state['topic_depth'] = 'deep'
        elif analysis['complexity'] == 'simple':
            self.conversation_state['topic_depth'] = 'surface'
        
        # Update engagement based on intent
        if analysis['intent'] in ['question', 'request']:
            self.conversation_state['user_engagement'] = 'high'
        elif analysis['intent'] in ['greeting', 'farewell']:
            self.conversation_state['user_engagement'] = 'low'
    
    def _update_active_topics(self, new_topics: List[str]):
        """Update list of active topics"""
        for topic in new_topics:
            if topic not in self.active_topics:
                self.active_topics.append(topic)
        
        # Keep only recent topics (max 5)
        self.active_topics = self.active_topics[-5:]
    
    def _prepare_response_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comprehensive context for response generation"""
        
        # Get recent conversation history
        recent_history = list(self.conversation_history)[-5:] if self.conversation_history else []
        
        # Combine with provided context
        response_context = {
            'recent_conversation': [
                {'role': turn['role'], 'content': turn['content']} 
                for turn in recent_history
            ],
            'active_topics': self.active_topics,
            'conversation_state': self.conversation_state.copy(),
            'user_context': context.get('user_context', {}),
            'memory_retrieval': context.get('retrieved_memories', []),
            'current_task': context.get('current_task'),
            'emotional_context': context.get('emotional_state', {})
        }
        
        return response_context
    
    def _select_response_style(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate response style"""
        
        # Default to current conversation state
        base_style = self.conversation_state['formality_level']
        
        # Adjust based on context
        if context.get('requires_technical_response'):
            return self.response_styles['technical']
        elif self.conversation_state['formality_level'] == 'formal':
            return self.response_styles['formal']
        elif self.conversation_state['formality_level'] == 'casual':
            return self.response_styles['casual']
        else:
            return self.response_styles['moderate']
    
    async def _generate_base_response(self, context: Dict[str, Any], style: Dict[str, Any]) -> str:
        """Generate base response using LLM"""
        
        # Construct prompt with context
        context_str = f"""
        Conversation Context:
        Recent conversation: {context['recent_conversation']}
        Active topics: {context['active_topics']}
        User emotional state: {context.get('emotional_context', {})}
        Retrieved memories: {context.get('memory_retrieval', [])}
        
        Response Style:
        Formality: {style['formality']}
        Length: {style['length']}
        Temperature: {style['temperature']}
        
        Generate an appropriate response that:
        1. Addresses the user's needs
        2. Maintains conversation flow
        3. Uses the specified style
        4. Incorporates relevant context
        """
        
        response = await self.call_llm(context_str)
        return response
    
    async def _post_process_response(self, response: str, context: Dict[str, Any]) -> str:
        """Post-process generated response"""
        
        # Basic post-processing
        processed = response.strip()
        
        # Ensure appropriate length
        max_length = context.get('max_response_length', 500)
        if len(processed) > max_length:
            processed = processed[:max_length] + "..."
        
        # Add contextual elements if needed
        if context.get('add_empathy') and not any(word in processed.lower() for word in ['understand', 'feel', 'sorry']):
            processed = "I understand. " + processed
        
        return processed
    
    # Additional helper methods
    
    def _detect_intent_rules(self, text: str) -> Dict[str, float]:
        """Rule-based intent detection"""
        intents = {}
        text_lower = text.lower()
        
        for intent_type, keywords in self.intent_recognition.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                intents[intent_type] = score / len(keywords)
        
        return intents
    
    async def _detect_intent_llm(self, text: str) -> Dict[str, float]:
        """LLM-based intent detection"""
        prompt = f"""Analyze the intent of this text and provide confidence scores (0-1):
        Text: {text}
        
        Possible intents: question, request, command, information, greeting, farewell, complaint, compliment
        Format: intent_name: confidence_score
        """
        
        try:
            llm_response = await self.call_llm(prompt)
            return self._parse_intent_response(llm_response)
        except Exception as e:
            logger.error(f"LLM intent detection error: {e}")
            return {}
    
    def _combine_intent_analyses(self, rule_based: Dict[str, float], llm_based: Dict[str, float]) -> Dict[str, float]:
        """Combine rule-based and LLM-based intent analyses"""
        combined = {}
        
        # Combine scores with weights
        all_intents = set(rule_based.keys()) | set(llm_based.keys())
        
        for intent in all_intents:
            rule_score = rule_based.get(intent, 0.0) * 0.6  # Rule-based weight
            llm_score = llm_based.get(intent, 0.0) * 0.4   # LLM-based weight
            combined[intent] = rule_score + llm_score
        
        return combined
    
    def _parse_entities_response(self, response: str) -> List[Dict[str, str]]:
        """Parse entity extraction response"""
        entities = []
        
        lines = response.strip().split('\n')
        for line in lines:
            if '(' in line and ')' in line:
                try:
                    entity_part = line.split('(')[0].strip()
                    category_part = line.split('(')[1].split(')')[0].strip()
                    
                    entities.append({
                        'entity': entity_part,
                        'category': category_part
                    })
                except:
                    continue
        
        return entities
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction
        words = text.lower().split()
        
        # Filter out common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        return list(set(keywords))  # Remove duplicates
    
    def _extract_conversation_topics(self) -> List[str]:
        """Extract key topics from conversation history"""
        topics = set()
        
        for turn in self.conversation_history:
            if 'analysis' in turn and 'topics' in turn['analysis']:
                topics.update(turn['analysis']['topics'])
        
        return list(topics)
    
    def _calculate_conversation_metrics(self) -> Dict[str, Any]:
        """Calculate conversation metrics"""
        if not self.conversation_history:
            return {}
        
        total_turns = len(self.conversation_history)
        user_turns = len([t for t in self.conversation_history if t['role'] == 'user'])
        assistant_turns = len([t for t in self.conversation_history if t['role'] == 'assistant'])
        
        avg_user_length = sum(len(t['content']) for t in self.conversation_history if t['role'] == 'user') / user_turns if user_turns > 0 else 0
        avg_assistant_length = sum(len(t['content']) for t in self.conversation_history if t['role'] == 'assistant') / assistant_turns if assistant_turns > 0 else 0
        
        return {
            'total_turns': total_turns,
            'user_turns': user_turns,
            'assistant_turns': assistant_turns,
            'avg_user_message_length': avg_user_length,
            'avg_assistant_message_length': avg_assistant_length,
            'conversation_duration_minutes': (datetime.now() - self.conversation_history[0]['timestamp']).seconds / 60 if self.conversation_history else 0
        }
    
    def _extract_temporal_references(self, utterance: Dict[str, Any]) -> List[str]:
        """Extract temporal references from utterance"""
        temporal_words = ['today', 'tomorrow', 'yesterday', 'now', 'later', 'before', 'after', 'when', 'time']
        content = utterance.get('content', '').lower()
        
        return [word for word in temporal_words if word in content]
    
    def _extract_spatial_references(self, utterance: Dict[str, Any]) -> List[str]:
        """Extract spatial references from utterance"""
        spatial_words = ['here', 'there', 'where', 'place', 'location', 'near', 'far', 'above', 'below']
        content = utterance.get('content', '').lower()
        
        return [word for word in spatial_words if word in content]
    
    def _calculate_conversation_coherence(self) -> float:
        """Calculate conversation coherence score"""
        if len(self.context_window) < 2:
            return 1.0
        
        # Simple coherence based on topic overlap
        recent_topics = []
        for context_item in self.context_window:
            if 'context_elements' in context_item and 'topic' in context_item['context_elements']:
                topic = context_item['context_elements']['topic']
                if topic:
                    recent_topics.append(topic)
        
        if len(recent_topics) < 2:
            return 1.0
        
        # Calculate topic overlap
        unique_topics = len(set(recent_topics))
        total_topics = len(recent_topics)
        
        coherence = 1.0 - (unique_topics / total_topics) if total_topics > 0 else 1.0
        return max(0.0, coherence)
    
    def _detect_context_shift(self, context_elements: Dict[str, Any]) -> Dict[str, Any]:
        """Detect if there's been a significant context shift"""
        
        if len(self.context_window) < 2:
            return {'detected': False}
        
        current_topic = context_elements.get('topic')
        previous_context = self.context_window[-1] if self.context_window else None
        
        if not previous_context or not current_topic:
            return {'detected': False}
        
        previous_topic = previous_context['context_elements'].get('topic')
        
        if current_topic != previous_topic:
            return {
                'detected': True,
                'type': 'topic_shift',
                'previous_topic': previous_topic,
                'current_topic': current_topic
            }
        
        return {'detected': False}
    
    def _determine_target_style(self, style_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Determine target communication style"""
        
        # Default style
        target_style = {
            'formality': 'moderate',
            'complexity': 'moderate',
            'emotional_tone': 'neutral',
            'confidence': 0.5
        }
        
        # Adjust based on cues
        formality_cues = style_analysis.get('formality_cues', [])
        if len(formality_cues) > 0:
            if any('formal' in cue for cue in formality_cues):
                target_style['formality'] = 'formal'
            elif any('casual' in cue for cue in formality_cues):
                target_style['formality'] = 'casual'
        
        # Adjust complexity
        complexity_cues = style_analysis.get('complexity_cues', [])
        if len(complexity_cues) > 0:
            if any('technical' in cue for cue in complexity_cues):
                target_style['complexity'] = 'high'
            elif any('simple' in cue for cue in complexity_cues):
                target_style['complexity'] = 'low'
        
        return target_style
    
    def _detect_reference_intent(self, text: str) -> bool:
        """检测用户是否在引用之前的对话内容"""
        reference_keywords = [
            '刚才', '之前', '前面', '刚刚', '刚说', 
            '我说', '我提到', '我问', '记得', '还记得',
            'earlier', 'before', 'mentioned', 'said', 'asked',
            '什么', '为什么', '怎么'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in reference_keywords)
    
    async def _generate_base_response_with_memory(self, context: Dict[str, Any], style: Dict[str, Any]) -> str:
        """使用记忆生成响应 - 简化版本"""
        user_input = context.get('user_input', '')
        memories = context.get('memories', [])
        
        # 构建简单的记忆上下文
        memory_context = ""
        if memories:
            memory_context = "\n相关记忆：\n"
            for mem in memories[:3]:  # 只使用前3条最相关的记忆
                content = mem.get('content', '')
                memory_context += f"- {content[:80]}...\n"
        
        # 使用简单统一的prompt
        prompt = f"""基于记忆回复用户：

用户：{user_input}
{memory_context}

请自然地回复用户。"""
        
        try:
            # 调用LLM生成响应
            response = await self.call_llm(prompt)
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # 简单的降级响应
            if memories:
                return f"根据记录：{memories[0].get('content', '')[:100]}"
            else:
                return "抱歉，我暂时无法处理这个请求。"
    
    def _build_response_from_memory(self, user_input: str, memories: List[Dict]) -> str:
        """从记忆中构建响应（不依赖LLM）"""
        if not memories:
            return "抱歉，我暂时无法访问之前的对话记录。"
        
        # 分析用户询问的内容
        user_input_lower = user_input.lower()
        
        # 获取最相关的记忆
        most_relevant = memories[0] if memories else None
        if most_relevant:
            content = most_relevant.get('content', '')
            
            # 尝试提取关键信息
            if '喜欢' in user_input_lower and '什么' in user_input_lower:
                # 寻找包含"喜欢"的记忆
                for memory in memories[:3]:
                    mem_content = memory.get('content', '')
                    if '喜欢' in mem_content:
                        # 提取喜欢的对象
                        return f"根据记录，{mem_content[:100]}"
            
            # 默认返回最相关的记忆内容
            return f"根据之前的对话：{content[:150]}"
        
        return "抱歉，我暂时无法找到相关的对话记录。"
    
    def _parse_intent_response(self, response: str) -> Dict[str, float]:
        """Parse LLM intent detection response"""
        intents = {}
        
        lines = response.strip().split('\n')
        for line in lines:
            if ':' in line:
                try:
                    intent, score_str = line.split(':')
                    intent = intent.strip().lower()
                    score = float(score_str.strip())
                    intents[intent] = min(1.0, max(0.0, score))
                except:
                    continue
        
        return intents