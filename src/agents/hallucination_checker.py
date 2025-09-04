#!/usr/bin/env python3
"""
幻觉检查Agent - 检测并防止AI生成虚假信息
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# 尝试导入OpenAI
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class HallucinationChecker:
    """幻觉检查智能体"""
    
    def __init__(self, openai_client=None):
        self.client = openai_client
        self.logger = logging.getLogger(__name__)
        
        # 幻觉检查提示词
        self.verification_prompt = """
你是一个严格的事实核查专家。请分析以下回答是否存在幻觉或虚假信息。

**评估标准：**
1. 是否有不支持的断言
2. 是否有编造的具体数据、日期、人名、地名
3. 是否有超出证据范围的结论
4. 是否有不确定的内容被表述为确定事实

**证据材料：**
{evidence}

**待检查的回答：**
{answer}

**请按以下格式回复：**
```json
{
    "has_hallucination": true/false,
    "confidence": 0.0-1.0,
    "issues": [
        {
            "type": "断言无依据|数据编造|超范围结论|不确定表述",
            "content": "具体问题内容",
            "suggestion": "修改建议"
        }
    ],
    "verified_facts": ["确实支持的事实列表"],
    "recommendation": "整体建议"
}
```
"""
        
        # 事实声明检查模式
        self.fact_patterns = [
            r'根据.*?显示',
            r'数据表明',
            r'研究发现',
            r'具体来说',
            r'确切地说',
            r'事实上',
            r'实际上',
            r'据.*?统计',
            r'.*?年.*?月.*?日',
            r'\d+%',
            r'\d+\.?\d*[万千百十]*[人次元件台]',
        ]
    
    async def check_hallucination(self, 
                                answer: str, 
                                evidence_segments: List[Dict], 
                                question: str = "") -> Dict[str, Any]:
        """检查回答是否存在幻觉"""
        
        try:
            # 基础检查
            basic_check = self.basic_hallucination_check(answer, evidence_segments)
            
            # AI深度检查（如果可用）
            if self.client and OPENAI_AVAILABLE:
                ai_check = await self.ai_hallucination_check(answer, evidence_segments)
                
                # 合并检查结果
                combined_result = self.combine_checks(basic_check, ai_check)
            else:
                combined_result = basic_check
            
            # 生成修正建议
            combined_result["corrected_answer"] = self.generate_corrected_answer(
                answer, combined_result, evidence_segments
            )
            
            return combined_result
            
        except Exception as e:
            self.logger.error(f"幻觉检查失败: {e}")
            return {
                "has_hallucination": False,
                "confidence": 0.0,
                "issues": [],
                "verified_facts": [],
                "recommendation": "检查系统出错，请人工核实",
                "error": str(e)
            }
    
    def basic_hallucination_check(self, answer: str, evidence_segments: List[Dict]) -> Dict[str, Any]:
        """基础幻觉检查（基于规则）"""
        
        issues = []
        verified_facts = []
        
        # 提取所有证据文本
        evidence_text = ""
        for segment in evidence_segments:
            if isinstance(segment, dict):
                evidence_text += segment.get('text', '') + " "
            else:
                evidence_text += str(segment) + " "
        
        evidence_text = evidence_text.lower()
        answer_lower = answer.lower()
        
        # 检查1: 具体数字和数据
        number_pattern = r'\d+\.?\d*[%万千百十]*[人次元件台年月日]?'
        numbers_in_answer = re.findall(number_pattern, answer)
        
        for number in numbers_in_answer:
            if number not in evidence_text:
                issues.append({
                    "type": "数据编造",
                    "content": f"回答中包含的数据 '{number}' 在证据中未找到",
                    "suggestion": "删除或标注为不确定的数据"
                })
        
        # 检查2: 断言性语句
        assertive_patterns = [
            r'确实是',
            r'肯定是',
            r'绝对是',
            r'毫无疑问',
            r'事实上',
            r'实际上',
            r'根据.*?显示'
        ]
        
        for pattern in assertive_patterns:
            if re.search(pattern, answer):
                # 检查是否有足够证据支持
                matches = re.findall(pattern, answer)
                for match in matches:
                    issues.append({
                        "type": "断言无依据",
                        "content": f"使用了强烈断言 '{match}' 但可能缺乏足够证据",
                        "suggestion": "使用更谨慎的表述，如'根据现有信息可能是'"
                    })
        
        # 检查3: 专有名词和实体
        # 简单检查是否有不在证据中的专有名词
        answer_words = set(re.findall(r'[\u4e00-\u9fa5]+', answer))
        evidence_words = set(re.findall(r'[\u4e00-\u9fa5]+', evidence_text))
        
        uncommon_words = []
        for word in answer_words:
            if len(word) >= 3 and word not in evidence_words:
                # 过滤常见词汇
                if not self.is_common_word(word):
                    uncommon_words.append(word)
        
        if uncommon_words:
            issues.append({
                "type": "超范围结论",
                "content": f"回答中包含证据中未出现的专业术语: {', '.join(uncommon_words[:5])}",
                "suggestion": "确保所有专业术语都有证据支持，或标注为推测"
            })
        
        # 检查4: 时间和地点信息
        time_place_pattern = r'(\d{4}年|\d+月|\d+日|在.*?[市县区省国])'
        time_places = re.findall(time_place_pattern, answer)
        
        for tp in time_places:
            if tp not in evidence_text:
                issues.append({
                    "type": "数据编造",
                    "content": f"时间/地点信息 '{tp}' 在证据中未找到",
                    "suggestion": "删除具体时间/地点或标注为不确定"
                })
        
        # 计算可信度
        total_checks = 4
        failed_checks = len([issue for issue in issues if issue["type"] != "断言无依据"])
        confidence = max(0.0, 1.0 - (failed_checks / total_checks))
        
        # 提取确实支持的事实
        for segment in evidence_segments[:3]:  # 只检查前3个片段
            if isinstance(segment, dict):
                text = segment.get('text', '')[:100]
                if text and text.lower() in answer_lower:
                    verified_facts.append(text + "...")
        
        return {
            "has_hallucination": len(issues) > 0,
            "confidence": confidence,
            "issues": issues,
            "verified_facts": verified_facts,
            "recommendation": self.generate_basic_recommendation(issues)
        }
    
    async def ai_hallucination_check(self, answer: str, evidence_segments: List[Dict]) -> Dict[str, Any]:
        """AI深度幻觉检查"""
        
        if not self.client:
            return {"has_hallucination": False, "confidence": 0.0, "issues": [], "verified_facts": []}
        
        try:
            # 准备证据文本
            evidence_text = "\n".join([
                segment.get('text', str(segment))[:300] 
                for segment in evidence_segments[:5]
            ])
            
            # 构建检查提示
            check_prompt = self.verification_prompt.format(
                evidence=evidence_text,
                answer=answer
            )
            
            # 调用AI进行检查
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个严格的事实核查专家，专门检测AI回答中的幻觉和虚假信息。"},
                    {"role": "user", "content": check_prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 解析JSON结果
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                return result
            else:
                # 如果没有找到JSON，尝试解析整个响应
                try:
                    return json.loads(result_text)
                except:
                    return {
                        "has_hallucination": True,
                        "confidence": 0.5,
                        "issues": [{"type": "解析错误", "content": "AI检查结果解析失败", "suggestion": "人工核实"}],
                        "verified_facts": [],
                        "recommendation": "AI检查失败，建议人工核实"
                    }
                    
        except Exception as e:
            self.logger.error(f"AI幻觉检查失败: {e}")
            return {
                "has_hallucination": False,
                "confidence": 0.0,
                "issues": [],
                "verified_facts": [],
                "error": str(e)
            }
    
    def combine_checks(self, basic_check: Dict, ai_check: Dict) -> Dict[str, Any]:
        """合并基础检查和AI检查结果"""
        
        combined_issues = basic_check.get("issues", []) + ai_check.get("issues", [])
        combined_facts = list(set(basic_check.get("verified_facts", []) + ai_check.get("verified_facts", [])))
        
        # 综合判断是否存在幻觉
        has_hallucination = basic_check.get("has_hallucination", False) or ai_check.get("has_hallucination", False)
        
        # 综合可信度（取较低值）
        confidence = min(basic_check.get("confidence", 1.0), ai_check.get("confidence", 1.0))
        
        return {
            "has_hallucination": has_hallucination,
            "confidence": confidence,
            "issues": combined_issues,
            "verified_facts": combined_facts,
            "recommendation": self.generate_combined_recommendation(combined_issues, confidence),
            "basic_check": basic_check,
            "ai_check": ai_check
        }
    
    def generate_corrected_answer(self, original_answer: str, check_result: Dict, evidence_segments: List[Dict]) -> str:
        """生成修正后的答案"""
        
        if not check_result.get("has_hallucination", False):
            return original_answer
        
        corrected = original_answer
        issues = check_result.get("issues", [])
        
        # 添加不确定性表述
        uncertainty_phrases = [
            "根据现有信息",
            "基于提供的证据",
            "据可获得的资料显示",
            "在现有证据范围内"
        ]
        
        # 如果有数据编造或断言无依据的问题，添加不确定性前缀
        high_risk_issues = [issue for issue in issues if issue["type"] in ["数据编造", "断言无依据"]]
        if high_risk_issues and not any(phrase in corrected for phrase in uncertainty_phrases):
            corrected = "根据现有信息，" + corrected
        
        # 添加免责声明
        if len(issues) > 2:
            corrected += "\n\n⚠️ 注意：以上回答基于有限的证据材料，部分内容可能需要进一步核实。"
        
        return corrected
    
    def is_common_word(self, word: str) -> bool:
        """判断是否为常见词汇"""
        common_words = {
            "可能", "应该", "或者", "但是", "因为", "所以", "这样", "那样", "如果", "虽然",
            "然而", "首先", "其次", "最后", "总的", "一般", "通常", "经常", "有时", "偶尔",
            "系统", "方法", "问题", "解决", "实现", "功能", "技术", "开发", "应用", "服务"
        }
        return word in common_words or len(word) <= 2
    
    def generate_basic_recommendation(self, issues: List[Dict]) -> str:
        """生成基础检查建议"""
        if not issues:
            return "回答看起来较为可信，建议保持"
        
        if len(issues) >= 3:
            return "发现多个潜在问题，强烈建议重新核实并修改回答"
        elif len(issues) == 2:
            return "发现少量问题，建议适当修改以提高可信度"
        else:
            return "发现轻微问题，可考虑小幅调整"
    
    def generate_combined_recommendation(self, issues: List[Dict], confidence: float) -> str:
        """生成综合建议"""
        if confidence >= 0.8 and len(issues) <= 1:
            return "✅ 回答可信度高，建议采用"
        elif confidence >= 0.6 and len(issues) <= 2:
            return "⚠️ 回答基本可信，建议小幅修改"
        elif confidence >= 0.4:
            return "⚠️ 回答存在一定问题，建议仔细修改"
        else:
            return "❌ 回答可信度低，建议重新生成或人工核实"

class HallucinationAwareAgent:
    """具备幻觉检查能力的智能体包装器"""
    
    def __init__(self, base_agent, hallucination_checker: HallucinationChecker):
        self.base_agent = base_agent
        self.checker = hallucination_checker
        self.logger = logging.getLogger(__name__)
    
    async def generate_verified_response(self, 
                                       question: str, 
                                       evidence_segments: List[Dict], 
                                       **kwargs) -> Dict[str, Any]:
        """生成经过幻觉检查的响应"""
        
        try:
            # 生成原始回答
            if hasattr(self.base_agent, 'generate_response_for_question'):
                original_response = await self.base_agent.generate_response_for_question(
                    question, evidence_segments, **kwargs
                )
            else:
                # 兼容不同的接口
                original_response = {"answer": "无法生成回答", "confidence": 0.0}
            
            original_answer = original_response.get("answer", "")
            
            # 执行幻觉检查
            hallucination_check = await self.checker.check_hallucination(
                original_answer, evidence_segments, question
            )
            
            # 根据检查结果决定使用哪个答案
            if hallucination_check.get("has_hallucination", False):
                final_answer = hallucination_check.get("corrected_answer", original_answer)
                verification_status = "已修正"
            else:
                final_answer = original_answer
                verification_status = "已验证"
            
            # 构建最终响应
            final_response = {
                **original_response,
                "answer": final_answer,
                "verification_status": verification_status,
                "hallucination_check": hallucination_check,
                "original_answer": original_answer if final_answer != original_answer else None
            }
            
            return final_response
            
        except Exception as e:
            self.logger.error(f"验证响应生成失败: {e}")
            return {
                "answer": "回答生成失败，请重试",
                "confidence": 0.0,
                "verification_status": "错误",
                "error": str(e)
            }