#!/usr/bin/env python3
"""
答案长度判断智能体
动态分析问题类型、evidence和golden answer模式来判断最佳答案长度
"""

import asyncio
import re
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI

class AnswerLengthAgent:
    """答案长度判断智能体"""
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self.length_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, Dict]:
        """初始化不同问题类型的长度模式"""
        return {
            "yes_no": {
                "target_words": 1,
                "max_tokens": 5,
                "strategy": "single_word",
                "examples": ["Yes", "No", "True", "False"]
            },
            "temporal": {
                "target_words": 3,
                "max_tokens": 15,
                "strategy": "date_format",
                "examples": ["May 21, 2023", "June 2023", "Yesterday"]
            },
            "factual_short": {
                "target_words": 2,
                "max_tokens": 10,
                "strategy": "key_entity",
                "examples": ["John Smith", "New York", "Basketball"]
            },
            "list_based": {
                "target_words": 4,
                "max_tokens": 20,
                "strategy": "comma_separated",
                "examples": ["Psychology, counseling", "Red, blue, green"]
            },
            "open_domain": {
                "target_words": 50,
                "max_tokens": 250,
                "strategy": "comprehensive_detailed",
                "examples": ["Software engineering and data science", "Helping people with mental health"]
            },
            "code_related": {
                "target_words": 80,
                "max_tokens": 400,
                "strategy": "code_with_explanation",
                "examples": ["Here's how to implement a binary search in Python:", "To debug this issue, try the following approach:"]
            },
            "programming_tutorial": {
                "target_words": 120,
                "max_tokens": 600,
                "strategy": "step_by_step_with_code",
                "examples": ["Step 1: Install the required packages...", "First, let's create the main function..."]
            }
        }
    
    async def analyze_optimal_length(self, 
                                   question: str,
                                   evidence_segments: List[Dict[str, Any]],
                                   question_type: str) -> Dict[str, Any]:
        """智能分析最佳答案长度"""
        
        # 基础长度判断
        base_config = self.length_patterns.get(question_type, self.length_patterns["open_domain"])
        
        # 动态调整逻辑
        dynamic_config = await self._dynamic_length_analysis(
            question, evidence_segments, question_type, base_config
        )
        
        return dynamic_config
    
    async def _dynamic_length_analysis(self, 
                                     question: str,
                                     evidence_segments: List[Dict[str, Any]],
                                     question_type: str,
                                     base_config: Dict) -> Dict[str, Any]:
        """动态分析最佳长度"""
        
        # 构建分析prompt
        evidence_text = "\n".join([f"- {seg['text']}" for seg in evidence_segments])
        
        analysis_prompt = f"""
You are an expert in determining optimal answer length for different question types.

Question: {question}
Question Type: {question_type}
Evidence:
{evidence_text}

Base Configuration:
- Target words: {base_config['target_words']}
- Max tokens: {base_config['max_tokens']}
- Strategy: {base_config['strategy']}

ANALYSIS TASK:
1. Analyze the question complexity and expected answer format
2. Consider the evidence richness and required detail level
3. Determine if the base configuration needs adjustment
4. Provide specific length recommendation

Consider these factors:
- Yes/No questions: Always 1 word
- Time questions: Prefer concise date format (3-4 words)
- List questions: Number of items should match evidence richness
- Complex questions: Provide detailed explanations (20-100 words)
- Technical questions: Include necessary details and examples (50-150 words)
- Code-related questions: Include complete examples with explanations (100-200 words)
- Programming tutorials: Provide step-by-step instructions with code (150-300 words)
- Conversational questions: Match the depth of previous context

OUTPUT FORMAT:
Recommended length: [X] words
Max tokens: [Y]
Strategy: [brief description]
Reasoning: [why this length is optimal]
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.1,
                max_tokens=150
            )
            
            analysis = response.choices[0].message.content.strip()
            
            # 解析分析结果
            parsed_config = self._parse_analysis_result(analysis, base_config)
            
            return parsed_config
            
        except Exception as e:
            # 如果分析失败，使用基础配置
            return {
                "target_words": base_config["target_words"],
                "max_tokens": base_config["max_tokens"],
                "strategy": base_config["strategy"],
                "reasoning": f"Using base config due to analysis error: {str(e)}"
            }
    
    def _parse_analysis_result(self, analysis: str, base_config: Dict) -> Dict[str, Any]:
        """解析智能体分析结果"""
        
        # 提取推荐长度
        words_match = re.search(r'Recommended length:\s*(\d+)\s*words?', analysis)
        target_words = int(words_match.group(1)) if words_match else base_config["target_words"]
        
        # 提取最大tokens
        tokens_match = re.search(r'Max tokens:\s*(\d+)', analysis)
        max_tokens = int(tokens_match.group(1)) if tokens_match else base_config["max_tokens"]
        
        # 提取策略
        strategy_match = re.search(r'Strategy:\s*([^\n]+)', analysis)
        strategy = strategy_match.group(1).strip() if strategy_match else base_config["strategy"]
        
        # 提取推理
        reasoning_match = re.search(r'Reasoning:\s*([^\n]+)', analysis)
        reasoning = reasoning_match.group(1).strip() if reasoning_match else "Dynamic analysis"
        
        # 智能安全检查 - 根据问题类型设置合理上限
        if question_type in ["yes_no"]:
            # 是非问题严格限制
            target_words = max(1, min(target_words, 3))
            max_tokens = max(5, min(max_tokens, 10))
        elif question_type in ["temporal", "factual_short"]:
            # 简短事实问题适中限制
            target_words = max(1, min(target_words, 10))
            max_tokens = max(5, min(max_tokens, 50))
        else:
            # 开放域、技术、代码类问题允许更长回答
            target_words = max(1, min(target_words, 200))  # 最多200词
            max_tokens = max(5, min(max_tokens, 1000))     # 最多1000 tokens
        
        return {
            "target_words": target_words,
            "max_tokens": max_tokens,
            "strategy": strategy,
            "reasoning": reasoning,
            "analysis": analysis
        }
    
    async def validate_answer_length(self, 
                                   question: str,
                                   answer: str,
                                   target_config: Dict[str, Any]) -> Dict[str, Any]:
        """验证答案长度是否符合期望"""
        
        actual_words = len(answer.split())
        target_words = target_config["target_words"]
        
        # 长度评估
        if actual_words <= target_words:
            length_score = 1.0
            length_status = "optimal"
        elif actual_words <= target_words * 1.5:
            length_score = 0.7
            length_status = "acceptable"
        else:
            length_score = 0.3
            length_status = "too_long"
        
        return {
            "actual_words": actual_words,
            "target_words": target_words,
            "length_score": length_score,
            "length_status": length_status,
            "needs_compression": length_status == "too_long"
        }
    
    async def compress_answer(self, 
                            question: str,
                            original_answer: str,
                            target_config: Dict[str, Any]) -> Dict[str, Any]:
        """压缩冗长的答案"""
        
        target_words = target_config["target_words"]
        max_tokens = target_config["max_tokens"]
        
        compression_prompt = f"""
You need to compress this answer to be more concise while preserving the key information.

Question: {question}
Original Answer: {original_answer}
Target Length: {target_words} words
Max Tokens: {max_tokens}

COMPRESSION RULES:
1. Keep only the most essential information
2. Remove unnecessary words and phrases
3. Use concise formatting
4. Maintain accuracy and completeness of key facts

Provide the compressed answer:
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": compression_prompt}],
                temperature=0,
                max_tokens=max_tokens
            )
            
            compressed_answer = response.choices[0].message.content.strip()
            
            # 移除可能的引号
            compressed_answer = compressed_answer.strip('"\'')
            
            return {
                "compressed_answer": compressed_answer,
                "original_words": len(original_answer.split()),
                "compressed_words": len(compressed_answer.split()),
                "compression_ratio": len(compressed_answer) / len(original_answer)
            }
            
        except Exception as e:
            # 压缩失败，返回原答案的截断版本
            words = original_answer.split()
            truncated = " ".join(words[:target_words])
            
            return {
                "compressed_answer": truncated,
                "original_words": len(words),
                "compressed_words": len(truncated.split()),
                "compression_ratio": len(truncated) / len(original_answer),
                "error": str(e)
            }
    
    def get_length_strategy_summary(self) -> str:
        """获取长度策略摘要"""
        
        summary = "=== 答案长度判断智能体策略 ===\n\n"
        
        for q_type, config in self.length_patterns.items():
            summary += f"{q_type.upper()}:\n"
            summary += f"  目标词数: {config['target_words']}\n"
            summary += f"  最大tokens: {config['max_tokens']}\n"
            summary += f"  策略: {config['strategy']}\n"
            summary += f"  示例: {', '.join(config['examples'])}\n\n"
        
        summary += "动态调整功能:\n"
        summary += "- 基于问题复杂度调整长度\n"
        summary += "- 根据evidence丰富度调整\n"
        summary += "- 实时验证答案长度\n"
        summary += "- 智能压缩过长答案\n"
        
        return summary


class LengthAwareAnswerExtractor:
    """集成长度智能体的答案提取器"""
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.client = openai_client
        self.length_agent = AnswerLengthAgent(openai_client)
    
    async def extract_length_optimized_answer(self, 
                                            question: str,
                                            evidence_segments: List[Dict[str, Any]],
                                            question_type: str) -> Dict[str, Any]:
        """提取长度优化的答案"""
        
        # 1. 分析最佳长度
        length_config = await self.length_agent.analyze_optimal_length(
            question, evidence_segments, question_type
        )
        
        # 2. 生成初始答案
        initial_answer = await self._generate_initial_answer(
            question, evidence_segments, question_type, length_config
        )
        
        # 3. 验证答案长度
        length_validation = await self.length_agent.validate_answer_length(
            question, initial_answer, length_config
        )
        
        # 4. 如果需要，压缩答案
        if length_validation["needs_compression"]:
            compression_result = await self.length_agent.compress_answer(
                question, initial_answer, length_config
            )
            final_answer = compression_result["compressed_answer"]
        else:
            final_answer = initial_answer
            compression_result = None
        
        return {
            "answer": final_answer,
            "length_config": length_config,
            "length_validation": length_validation,
            "compression_result": compression_result,
            "initial_answer": initial_answer,
            "extraction_method": "length_optimized"
        }
    
    async def _generate_initial_answer(self, 
                                     question: str,
                                     evidence_segments: List[Dict[str, Any]],
                                     question_type: str,
                                     length_config: Dict[str, Any]) -> str:
        """生成初始答案"""
        
        evidence_text = "\n".join([f"Evidence: {seg['text']}" for seg in evidence_segments])
        
        prompt = f"""
Question: {question}
Question Type: {question_type}
{evidence_text}

Target Length: {length_config['target_words']} words
Max Tokens: {length_config['max_tokens']}
Strategy: {length_config['strategy']}

Generate a concise, accurate answer following the length guidelines:
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=length_config["max_tokens"]
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating answer: {str(e)}"