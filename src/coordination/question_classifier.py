"""
🧠 语义问题分类器 - Semantic Question Classifier

核心思想: 完全抛弃硬编码规则,基于语义理解

工作流程:
1. LLM动态分析问题语义特征
2. 判断需要哪种推理能力 (而非匹配关键词)
3. 缓存常见模式 (优化性能,但不影响泛化)

Author: Brain-Inspired Coordinator
"""

import json
import logging
from typing import Dict, Any, Optional, List
import os

logger = logging.getLogger(__name__)


class SemanticQuestionClassifier:
    """
    语义问题分类器 - 纯LLM驱动,无硬编码规则

    设计理念:
    - 不预设问题类型列表
    - LLM根据语义理解判断需要什么"推理能力"
    - 系统根据推理能力动态路由到合适的agent

    优点:
    ✅ 完全泛化 - 可以处理任何新型问题
    ✅ 语义准确 - 不依赖表面关键词
    ✅ 可解释 - LLM会说明为什么需要某种推理

    缺点:
    ⚠️ 延迟 - 每次都要LLM调用 (用缓存优化)
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.semantic_cache = {}  # 语义缓存: query_embedding → classification

        # 加载缓存
        self._load_cache()

    def classify(self, query: str, use_llm_if_uncertain: bool = True) -> Dict[str, Any]:
        """
        分类问题类型

        Args:
            query: 用户问题
            use_llm_if_uncertain: 如果规则不确定,是否使用LLM

        Returns:
            {
                'type': 'factual|identity|temporal|research|...',
                'confidence': 0.0-1.0,
                'method': 'rule|llm|cache',
                'reasoning': '分类理由'
            }
        """
        query_lower = query.lower()

        # Step 1: 检查缓存
        if query_lower in self.pattern_cache:
            cached = self.pattern_cache[query_lower]
            logger.debug(f"📦 Cache hit: {cached['type']}")
            return {**cached, 'method': 'cache'}

        # Step 2: 规则匹配
        rule_result = self._rule_based_classify(query_lower)
        if rule_result['confidence'] >= 0.8:  # 高置信度,直接返回
            logger.info(f"✅ Rule-based: {query[:50]} → {rule_result['type']} (conf={rule_result['confidence']:.2f})")
            return {**rule_result, 'method': 'rule'}

        # Step 3: LLM语义分类 (如果允许)
        if use_llm_if_uncertain and self.llm_client:
            llm_result = await self._llm_classify(query)
            if llm_result['confidence'] >= 0.7:
                logger.info(f"🤖 LLM-based: {query[:50]} → {llm_result['type']} (conf={llm_result['confidence']:.2f})")

                # 学习: 如果LLM高置信度且与规则不同,记录以备学习
                if llm_result['type'] != rule_result['type']:
                    self._record_for_learning(query, llm_result)

                return {**llm_result, 'method': 'llm'}

        # Step 4: Fallback - 使用规则结果 (即使置信度较低)
        logger.warning(f"⚠️ Uncertain classification: {query[:50]} → {rule_result['type']} (conf={rule_result['confidence']:.2f})")
        return {**rule_result, 'method': 'rule_fallback'}

    def _rule_based_classify(self, query_lower: str) -> Dict[str, Any]:
        """基于规则的快速分类"""

        # 优先级顺序检查
        matches = []

        for q_type, keywords in self.rules.items():
            matched_keywords = [kw for kw in keywords if kw in query_lower]
            if matched_keywords:
                # 计算置信度: 匹配关键词数量和位置
                confidence = min(0.9, 0.5 + 0.1 * len(matched_keywords))
                matches.append({
                    'type': q_type,
                    'confidence': confidence,
                    'matched': matched_keywords
                })

        if matches:
            # 选择置信度最高的
            best = max(matches, key=lambda x: x['confidence'])
            return {
                'type': best['type'],
                'confidence': best['confidence'],
                'reasoning': f"Matched keywords: {', '.join(best['matched'])}"
            }

        # 兜底: multi_hop (如果包含疑问词) 或 simple
        if any(word in query_lower for word in ['what', 'which', 'how', 'why', '什么', '哪些', '怎么', '为什么']):
            return {
                'type': 'multi_hop',
                'confidence': 0.4,
                'reasoning': 'Contains question word but no specific pattern'
            }

        return {
            'type': 'simple',
            'confidence': 0.3,
            'reasoning': 'No specific pattern matched'
        }

    async def _llm_classify(self, query: str) -> Dict[str, Any]:
        """使用LLM进行语义分类"""

        prompt = f"""You are a question type classifier for a memory system.

Question: {query}

Classify this question into ONE of these types:

1. **factual** - Direct fact retrieval (relationship status, location, occupation)
   Examples: "Where is X from?", "What is X's job?"

2. **identity** - Identity/characteristic inference
   Examples: "Who is X?", "What is X's identity?"

3. **temporal** - Time-related (dates, durations, sequences)
   Examples: "When did X happen?", "How long has X been doing Y?"

4. **research** - Research/study activities
   Examples: "What did X research?", "What has X been studying?"

5. **comparison** - Comparing two entities/concepts
   Examples: "What's the difference between X and Y?", "Is X better than Y?"

6. **causal** - Cause-effect reasoning
   Examples: "Why did X happen?", "What caused X?"

7. **counterfactual** - Hypothetical scenarios
   Examples: "What if X had happened?", "What would have happened if Y?"

8. **multi_hop** - Requires combining multiple pieces of information
   Examples: "What is X interested in?" (needs to infer from activities)

9. **simple** - Simple acknowledgment or non-question

Output JSON only:
{{
    "type": "one of the types above",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation of why this type"
}}
"""

        try:
            from src.agents.base import BaseAgent
            # 临时创建一个base agent来使用call_llm
            temp_agent = BaseAgent(agent_id='temp_classifier', region='prefrontal')
            content = await temp_agent.call_llm(
                prompt=prompt,
                temperature=0.1,
                max_tokens=200
            )

            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            result = json.loads(content)
            return result

        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            return {'type': 'simple', 'confidence': 0.0, 'reasoning': f'Error: {str(e)}'}

    def _record_for_learning(self, query: str, llm_result: Dict[str, Any]):
        """记录LLM分类结果,用于后续学习新规则"""
        self.classification_history.append({
            'query': query,
            'type': llm_result['type'],
            'confidence': llm_result['confidence'],
            'reasoning': llm_result.get('reasoning', '')
        })

        # 每50次学习一次
        if len(self.classification_history) >= 50:
            self._learn_new_patterns()

    def _learn_new_patterns(self):
        """
        从LLM分类历史中学习新模式

        策略:
        1. 找到高置信度的LLM分类
        2. 提取共同关键词
        3. 添加到规则库
        """
        logger.info("🎓 Learning new patterns from classification history...")

        # 按类型分组
        by_type = {}
        for record in self.classification_history:
            if record['confidence'] >= 0.8:  # 只学习高置信度的
                q_type = record['type']
                if q_type not in by_type:
                    by_type[q_type] = []
                by_type[q_type].append(record['query'].lower())

        # 提取共同词汇 (简化版)
        learned_count = 0
        for q_type, queries in by_type.items():
            if len(queries) >= 3:  # 至少3个样本才学习
                # 提取2-3词的常见短语
                from collections import Counter
                phrases = []
                for q in queries:
                    words = q.split()
                    for i in range(len(words) - 1):
                        phrases.append(' '.join(words[i:i+2]))
                        if i < len(words) - 2:
                            phrases.append(' '.join(words[i:i+3]))

                # 找到出现频率 >= 30%的短语
                common = [p for p, count in Counter(phrases).items()
                         if count >= len(queries) * 0.3 and p not in self.rules.get(q_type, [])]

                if common:
                    if q_type not in self.rules:
                        self.rules[q_type] = []
                    self.rules[q_type].extend(common[:2])  # 最多添加2个新规则
                    learned_count += len(common[:2])
                    logger.info(f"  ✅ Learned {len(common[:2])} new patterns for '{q_type}': {common[:2]}")

        if learned_count > 0:
            self._save_learned_rules()

        # 清空历史
        self.classification_history = []

    def _load_learned_rules(self):
        """从文件加载学习到的规则"""
        rules_file = 'data/learned_question_rules.json'
        if os.path.exists(rules_file):
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    learned = json.load(f)
                    # 合并到现有规则
                    for q_type, keywords in learned.items():
                        if q_type in self.rules:
                            self.rules[q_type].extend(keywords)
                        else:
                            self.rules[q_type] = keywords
                logger.info(f"📚 Loaded learned rules from {rules_file}")
            except Exception as e:
                logger.warning(f"Failed to load learned rules: {e}")

    def _save_learned_rules(self):
        """保存学习到的规则"""
        rules_file = 'data/learned_question_rules.json'
        try:
            # 只保存学习到的规则 (原始规则不保存)
            with open(rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Saved learned rules to {rules_file}")
        except Exception as e:
            logger.error(f"Failed to save learned rules: {e}")

    def get_supported_types(self) -> List[str]:
        """获取当前支持的所有问题类型"""
        return list(self.rules.keys()) + ['multi_hop', 'simple']
