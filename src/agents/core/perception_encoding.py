"""
Enhanced Perception Encoding Agent with Long Text Support
增强的感知编码智能体 - 支持长文本处理
"""

import re
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import tiktoken
from ...agents.base import BrainAgent, BrainRegion, AgentMessage
from ...utils.config import get_logger, get_settings

logger = get_logger(__name__)


class EnhancedPerceptionEncodingAgent(BrainAgent):
    """Enhanced perception and encoding agent with intelligent text chunking"""

    def __init__(self):
        super().__init__(
            agent_id="perception_encoding",
            brain_region=BrainRegion.THALAMUS,
            system_prompt="""You are an intelligent perception and encoding system.
Your role is to:
1. Analyze and structure incoming information
2. Break down long texts into manageable chunks
3. Extract key features and patterns
4. Generate summaries and overviews
5. Prepare information for downstream processing"""
        )
        self.settings = get_settings()

        # Initialize tokenizer for accurate token counting
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-4")
        except:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process incoming perception requests"""
        action = message.content.get('action')

        if action == 'encode_input':
            return await self._encode_input(message.content['input_data'])
        elif action == 'analyze_chunks':
            return await self._analyze_chunks(message.content['chunks'])
        elif action == 'generate_overview':
            return await self._generate_overview(message.content['segments'])
        elif action == 'detect_language':
            return await self._detect_language(message.content['user_input'])

        return {'error': f'Unknown action: {action}'}

    async def _detect_language(self, user_input: str) -> Dict[str, Any]:
        """检测用户输入的语言

        Args:
            user_input: 用户输入文本

        Returns:
            {
                'language': 'zh' | 'en',
                'confidence': float,
                'chinese_ratio': float
            }
        """
        if not user_input or not user_input.strip():
            return {'language': 'en', 'confidence': 0.5, 'chinese_ratio': 0.0}

        # 统计中文字符
        chinese_chars = sum(1 for c in user_input if '\u4e00' <= c <= '\u9fff')
        total_chars = len(user_input.strip())

        if total_chars == 0:
            return {'language': 'en', 'confidence': 0.5, 'chinese_ratio': 0.0}

        chinese_ratio = chinese_chars / total_chars

        # 判断语言
        if chinese_ratio > 0.3:
            language = 'zh'
            confidence = min(0.9, 0.5 + chinese_ratio)
        else:
            language = 'en'
            confidence = min(0.9, 0.5 + (1 - chinese_ratio))

        logger.info(f"🌐 Language detection: {language} (confidence={confidence:.2f}, chinese_ratio={chinese_ratio:.2f})")

        return {
            'language': language,
            'confidence': confidence,
            'chinese_ratio': chinese_ratio
        }

    async def _encode_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced input encoding with intelligent chunking"""
        content = input_data.get('content', '')
        input_type = input_data.get('type', 'text')
        context = input_data.get('context', {})

        # Apply input size limits
        token_count = self._count_tokens(content)
        if token_count > self.settings.max_input_tokens:
            logger.warning(f"Input exceeds max_input_tokens ({token_count} > {self.settings.max_input_tokens}), truncating")
            # Truncate to maximum allowed size
            content = self._truncate_to_tokens(content, self.settings.max_input_tokens)
            token_count = self.settings.max_input_tokens

        # Basic feature extraction
        features = self._extract_basic_features(content)

        if token_count > self.settings.max_chunk_tokens:
            # Process as long text
            logger.info(f"Long text detected ({token_count} tokens), initiating chunked processing")
            segments = await self._process_long_text(content)

            # Generate global overview
            overview = await self._generate_text_overview(content, segments)

            return {
                'encoded_input': {
                    'content': content[:500] + "..." if len(content) > 500 else content,
                    'features': features,
                    'segments': segments,
                    'overview': overview,
                    'processing_mode': 'chunked',
                    'total_tokens': token_count,
                    'chunk_count': len(segments),
                    'encoding_timestamp': datetime.now().isoformat()
                },
                'encoding_success': True,
                'requires_chunked_storage': True
            }
        else:
            # Process as regular text
            return {
                'encoded_input': {
                    'content': content,
                    'features': features,
                    'processing_mode': 'standard',
                    'total_tokens': token_count,
                    'encoding_timestamp': datetime.now().isoformat()
                },
                'encoding_success': True,
                'requires_chunked_storage': False
            }

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""
        try:
            return len(self.encoding.encode(text))
        except:
            # Fallback estimation: ~4 chars per token
            return len(text) // 4

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to specified token count"""
        try:
            tokens = self.encoding.encode(text)
            if len(tokens) <= max_tokens:
                return text

            truncated_tokens = tokens[:max_tokens]
            return self.encoding.decode(truncated_tokens)
        except:
            # Fallback to character-based truncation
            chars_to_keep = max_tokens * 4  # Estimate
            return text[:chars_to_keep]

    def _extract_basic_features(self, content: str) -> Dict[str, Any]:
        """Extract basic text features"""
        lines = content.split('\n')
        words = content.split()
        sentences = re.split(r'[.!?]+', content)

        return {
            'length': len(content),
            'line_count': len(lines),
            'word_count': len(words),
            'sentence_count': len([s for s in sentences if s.strip()]),
            'avg_word_length': sum(len(w) for w in words) / len(words) if words else 0,
            'has_code': bool(re.search(r'```|def |class |function |import ', content)),
            'has_urls': bool(re.search(r'https?://\S+', content)),
            'has_numbers': bool(re.search(r'\d+', content)),
            'language': self._detect_language_simple(content),
            'complexity': self._assess_complexity(content)
        }

    def _detect_language_simple(self, text: str) -> str:
        """Simple language detection for chunk analysis"""
        chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
        chinese_ratio = len(''.join(chinese_chars)) / len(text) if text else 0

        if chinese_ratio > 0.3:
            return 'chinese'
        elif chinese_ratio > 0.05:
            return 'mixed'
        else:
            return 'english'

    def _assess_complexity(self, content: str) -> str:
        """Assess text complexity"""
        words = content.split()
        if not words:
            return 'simple'

        avg_word_len = sum(len(w) for w in words) / len(words)
        sentence_count = len(re.split(r'[.!?]+', content))
        avg_sentence_len = len(words) / sentence_count if sentence_count else len(words)

        if avg_word_len > 6 and avg_sentence_len > 20:
            return 'complex'
        elif avg_word_len > 5 or avg_sentence_len > 15:
            return 'moderate'
        else:
            return 'simple'

    async def _process_long_text(self, content: str) -> List[Dict[str, Any]]:
        """Process long text by intelligent chunking"""
        chunks = self._smart_chunk_text(content)
        segments = []

        # Process each chunk
        for i, chunk in enumerate(chunks):
            segment_data = await self._process_chunk(chunk, i, len(chunks))
            segments.append(segment_data)

        return segments

    def _smart_chunk_text(self, text: str) -> List[str]:
        """Intelligently chunk text based on natural boundaries with Chinese support"""
        max_tokens = self.settings.max_chunk_tokens
        overlap_tokens = self.settings.chunk_overlap_tokens

        chunks = []

        # First try paragraph splitting
        paragraphs = text.split('\n\n')
        current_chunk = ""
        current_tokens = 0

        for para in paragraphs:
            para_tokens = self._count_tokens(para)

            if para_tokens > max_tokens:
                # Paragraph too long, need to split further
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                    current_tokens = 0

                # Split by sentences - support both English and Chinese punctuation
                sentences = self._split_sentences(para)

                for sent in sentences:
                    sent_tokens = self._count_tokens(sent)

                    # If single sentence exceeds max_tokens, force split it
                    if sent_tokens > max_tokens:
                        sent_chunks = self._force_split_by_tokens(sent, max_tokens)
                        for sub_chunk in sent_chunks:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sub_chunk
                            current_tokens = self._count_tokens(sub_chunk)
                    elif current_tokens + sent_tokens > max_tokens:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sent
                        current_tokens = sent_tokens
                    else:
                        separator = " " if self._is_english_dominant(sent) else ""
                        current_chunk = (current_chunk + separator + sent).strip() if current_chunk else sent
                        current_tokens += sent_tokens

            elif current_tokens + para_tokens > max_tokens:
                # Adding this paragraph would exceed limit
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = para
                current_tokens = para_tokens
            else:
                # Add paragraph to current chunk
                current_chunk = (current_chunk + "\n\n" + para).strip() if current_chunk else para
                current_tokens += para_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)

        # Add overlap for context continuity
        if overlap_tokens > 0 and len(chunks) > 1:
            overlapped_chunks = []
            for i, chunk in enumerate(chunks):
                if i > 0:
                    # Add end of previous chunk as context
                    prev_chunk_end = self._extract_overlap_context(chunks[i-1], overlap_tokens)
                    chunk = prev_chunk_end + "\n[...]\n" + chunk
                overlapped_chunks.append(chunk)
            chunks = overlapped_chunks

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences supporting both English and Chinese punctuation"""
        # Pattern includes English and Chinese sentence endings
        # English: . ! ?
        # Chinese: 。！？；
        pattern = r'(?<=[.!?。！？；])\s*'
        sentences = re.split(pattern, text)

        # Filter out empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        # If no sentence boundaries found, try comma splitting for Chinese
        if len(sentences) == 1 and len(text) > 500:
            # Try splitting by Chinese comma if text is predominantly Chinese
            if self._detect_language(text) == 'chinese':
                sentences = re.split(r'[，,]\s*', text)
                # Rejoin short segments to avoid over-fragmentation
                combined_sentences = []
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) < 200:  # ~50 tokens
                        current = current + "，" + sent if current else sent
                    else:
                        if current:
                            combined_sentences.append(current)
                        current = sent
                if current:
                    combined_sentences.append(current)
                sentences = combined_sentences

        return sentences

    def _force_split_by_tokens(self, text: str, max_tokens: int) -> List[str]:
        """Force split text when it exceeds max_tokens even as single unit"""
        chunks = []

        # Try to encode the text to get exact token positions
        try:
            tokens = self.encoding.encode(text)

            for i in range(0, len(tokens), max_tokens):
                chunk_tokens = tokens[i:i + max_tokens]
                chunk_text = self.encoding.decode(chunk_tokens)
                chunks.append(chunk_text)

        except Exception as e:
            logger.warning(f"Token-based splitting failed, falling back to character splitting: {e}")
            # Fallback to character-based splitting
            # Estimate ~4 chars per token for English, ~2 for Chinese
            chars_per_chunk = max_tokens * (2 if self._detect_language(text) == 'chinese' else 4)

            for i in range(0, len(text), chars_per_chunk):
                chunks.append(text[i:i + chars_per_chunk])

        return chunks

    def _is_english_dominant(self, text: str) -> bool:
        """Check if text is predominantly English"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        return chinese_chars / total_chars < 0.3 if total_chars > 0 else True

    def _extract_overlap_context(self, text: str, overlap_tokens: int) -> str:
        """Extract overlap context from end of text"""
        try:
            tokens = self.encoding.encode(text)
            if len(tokens) > overlap_tokens:
                overlap_tokens_list = tokens[-overlap_tokens:]
                return self.encoding.decode(overlap_tokens_list)
            else:
                return text
        except:
            # Fallback to character-based
            chars_to_extract = overlap_tokens * 4
            return text[-chars_to_extract:] if len(text) > chars_to_extract else text

    async def _process_chunk(self, chunk: str, index: int, total: int) -> Dict[str, Any]:
        """Process individual chunk with local summarization to minimize LLM calls"""

        # Use local summarization for most chunks
        # Only use LLM for the first chunk or very important ones
        use_llm = (index == 0 and total <= 3)  # Only use LLM for first chunk of short texts

        if use_llm:
            try:
                summary = await self._generate_llm_summary(chunk, index, total)
            except Exception as e:
                logger.debug(f"LLM summary failed, using local: {e}")
                summary = self._generate_local_summary(chunk)
        else:
            # Use local summarization to avoid excessive LLM calls
            summary = self._generate_local_summary(chunk)

        return {
            'index': index,
            'content': chunk,
            'token_count': self._count_tokens(chunk),
            'char_count': len(chunk),
            'summary': summary['summary'],
            'keywords': summary['keywords'],
            'intent': summary.get('intent', 'content'),
            'position': f"{index+1}/{total}",
            'processing_method': 'llm' if use_llm else 'local'
        }

    async def _generate_llm_summary(self, chunk: str, index: int, total: int) -> Dict[str, Any]:
        """Generate summary using LLM (sparingly)"""
        summary_prompt = f"""Briefly summarize this text (part {index+1} of {total}):

{chunk[:800]}...

Provide: summary (1-2 sentences), keywords (3-5), intent
Format as JSON."""

        response = await self.call_llm(
            summary_prompt,
            max_tokens=150,
            temperature=0.3,
            quick_fail=True
        )

        import json
        try:
            return json.loads(response)
        except:
            return {
                "summary": response[:150],
                "keywords": self._extract_keywords(chunk),
                "intent": "content"
            }

    def _generate_local_summary(self, chunk: str) -> Dict[str, Any]:
        """Generate summary locally without LLM calls"""
        # Extract first and last sentences as summary
        sentences = self._split_sentences(chunk)

        if len(sentences) == 0:
            summary = chunk[:150] + "..."
        elif len(sentences) == 1:
            summary = sentences[0][:200]
        elif len(sentences) == 2:
            summary = f"{sentences[0][:100]}... {sentences[-1][:100]}"
        else:
            # Take first and last sentence
            summary = f"{sentences[0][:100]}... {sentences[-1][:100]}"

        # Extract keywords
        keywords = self._extract_keywords(chunk)

        # Determine intent based on content patterns
        intent = self._detect_intent(chunk)

        return {
            "summary": summary,
            "keywords": keywords,
            "intent": intent
        }

    def _detect_intent(self, text: str) -> str:
        """Simple intent detection based on patterns"""
        lower_text = text.lower()

        if any(word in lower_text for word in ['记住', '保存', 'remember', 'save']):
            return 'memory_request'
        elif any(word in lower_text for word in ['问题', '怎么', 'how', 'what', 'why', '？']):
            return 'question'
        elif any(word in lower_text for word in ['步骤', '方法', '教程', 'steps', 'guide']):
            return 'instruction'
        elif any(word in lower_text for word in ['分析', '解释', 'analyze', 'explain']):
            return 'analysis'
        else:
            return 'content'

    def _extract_keywords(self, text: str) -> List[str]:
        """Simple keyword extraction fallback"""
        # Remove common words and extract potential keywords
        words = re.findall(r'\b[A-Za-z\u4e00-\u9fff]{3,}\b', text.lower())
        word_freq = {}

        common_words = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'was', 'are', 'been', 'have', 'had', 'were'}

        for word in words:
            if word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Return top 5 most frequent words
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:5]]

    async def _generate_text_overview(self, content: str, segments: List[Dict]) -> Dict[str, Any]:
        """Generate global overview for long text"""

        # Collect all summaries
        all_summaries = [seg['summary'] for seg in segments if seg.get('summary')]
        combined_summary = "\n".join(all_summaries)

        # Generate meta-summary
        overview_prompt = f"""Based on these segment summaries, provide an overall overview:

{combined_summary}

Provide:
1. Main theme/topic (1 sentence)
2. Key takeaways (2-3 points)
3. Overall category (technical/narrative/informative/etc)
4. Suggested storage priority (low/medium/high)

Format as JSON."""

        try:
            response = await self.call_llm(
                overview_prompt,
                max_tokens=300,
                temperature=0.3,
                quick_fail=True
            )

            import json
            try:
                overview = json.loads(response)
            except:
                overview = {
                    "theme": combined_summary[:100],
                    "takeaways": ["Content processed in segments"],
                    "category": "long_text",
                    "storage_priority": "medium"
                }
        except Exception as e:
            logger.warning(f"Failed to generate overview: {e}")
            overview = {
                "theme": "Long text requiring segmented processing",
                "takeaways": [f"Processed in {len(segments)} segments"],
                "category": "long_text",
                "storage_priority": "medium"
            }

        # Collect all keywords
        all_keywords = []
        for seg in segments:
            all_keywords.extend(seg.get('keywords', []))

        # Deduplicate and get top keywords
        keyword_freq = {}
        for kw in all_keywords:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1

        top_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        overview['global_keywords'] = [kw for kw, _ in top_keywords]
        overview['total_segments'] = len(segments)
        overview['total_tokens'] = sum(seg['token_count'] for seg in segments)

        return overview

    async def _analyze_chunks(self, chunks: List[Dict]) -> Dict[str, Any]:
        """Analyze a collection of chunks for patterns"""

        # Analyze patterns across chunks
        topics = {}
        intents = {}

        for chunk in chunks:
            for keyword in chunk.get('keywords', []):
                topics[keyword] = topics.get(keyword, 0) + 1

            intent = chunk.get('intent', 'unknown')
            intents[intent] = intents.get(intent, 0) + 1

        return {
            'chunk_count': len(chunks),
            'common_topics': sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5],
            'intent_distribution': intents,
            'requires_deep_processing': len(chunks) > 5
        }

    async def _generate_overview(self, segments: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive overview from segments"""

        if not segments:
            return {'error': 'No segments provided'}

        # This is a standalone method for external calls
        return await self._generate_text_overview("", segments)