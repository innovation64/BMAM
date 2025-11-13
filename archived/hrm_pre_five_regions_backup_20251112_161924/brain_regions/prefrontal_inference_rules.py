"""
Prefrontal Inference Rules - 前额叶推理规则

⚠️ DEPRECATED IN PHASE 2 ⚠️

该文件已在Phase 2层间协作优化中被弃用。

原因:
1. 硬编码5条if-then规则,完全针对LoCoMo数据集
2. 无学习能力,无法泛化到新场景
3. 违反系统设计原则 ("不能有硬编码，只能有算法")

替代方案:
- PrefrontalAgent中的LLM-based推理 (prefrontal_agent.py)
- ReasoningValidator中的动态推理 (reasoning_validator.py)
- 无需手写规则,LLM自适应推理

参考:
- BMAM分布式存储层问题分析_其他脑区.md (问题4, 优化6)
- BMAM层间协作优化方案_Phase2.md

---

原功能 (已废弃):
功能: 存储抽象推理模式和规则
结构: 规则库 (Rule-based system)
用途: 从事实推断结论

灵感来源:
- 前额叶负责高级推理和决策
- 存储"if X then Y"推理规则
"""

import logging
from typing import Dict, List, Any, Callable, Tuple, Optional

logger = logging.getLogger(__name__)


class PrefrontalInferenceRules:
    """
    前额叶推理规则 - 存储推理模式

    核心特点:
    1. 规则库结构
    2. 支持条件函数
    3. 支持置信度
    """

    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        # 规则格式: {'condition': Callable, 'conclusion': str, 'confidence': float, 'name': str}


    def add_rule(
        self,
        name: str,
        condition: Callable[[Dict], bool],
        conclusion: str,
        confidence: float
    ) -> None:
        """
        添加推理规则

        Args:
            name: 规则名称
            condition: 条件函数 (接收facts字典，返回bool)
            conclusion: 结论模板字符串
            confidence: 置信度 0.0-1.0
        """
        self.rules.append({
            'name': name,
            'condition': condition,
            'conclusion': conclusion,
            'confidence': confidence
        })


    def apply_rules(self, facts: Dict[str, Any]) -> List[Tuple[str, float, str]]:
        """
        应用推理规则

        Args:
            facts: 已知事实字典

        Returns:
            [(conclusion, confidence, rule_name), ...]
        """
        conclusions = []

        for rule in self.rules:
            try:
                # 检查条件是否满足
                if rule['condition'](facts):
                    # 格式化结论
                    try:
                        conclusion_text = rule['conclusion'].format(**facts)
                    except (KeyError, ValueError):
                        conclusion_text = rule['conclusion']

                    conclusions.append((
                        conclusion_text,
                        rule['confidence'],
                        rule['name']
                    ))


            except (Exception) as e:
                logger.warning(f"Rule '{rule['name']}' failed: {e}")

        return conclusions

    def get_rules_by_confidence(self, min_confidence: float = 0.5) -> List[Dict]:
        """
        获取高置信度的规则

        Args:
            min_confidence: 最小置信度

        Returns:
            规则列表
        """
        return [r for r in self.rules if r['confidence'] >= min_confidence]

    def remove_rule(self, name: str) -> bool:
        """
        删除规则

        Args:
            name: 规则名称

        Returns:
            是否成功删除
        """
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r['name'] != name]

        success = len(self.rules) < initial_count

        if success:
            logger.info(f"Rule removed: {name}")

        return success

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.rules:
            return {
                'total_rules': 0,
                'avg_confidence': 0.0
            }

        return {
            'total_rules': len(self.rules),
            'avg_confidence': sum(r['confidence'] for r in self.rules) / len(self.rules),
            'high_confidence_rules': len([r for r in self.rules if r['confidence'] >= 0.8])
        }


def init_default_rules() -> PrefrontalInferenceRules:
    """
    初始化默认推理规则

    这些规则模拟人类的常识推理
    """
    rules = PrefrontalInferenceRules()

    # 规则1: LGBTQ group参与 → 身份线索
    rules.add_rule(
        name="lgbtq_participation_inference",
        condition=lambda f: any('LGBTQ' in str(e) for e in f.get('events', [])),
        conclusion="Identity clue: LGBTQ+ related (participation in LGBTQ activities)",
        confidence=0.6
    )

    # 规则2: transgender stories共鸣 + 高情绪 → 强线索
    rules.add_rule(
        name="transgender_resonance_inference",
        condition=lambda f: (
            any('transgender' in str(e).lower() for e in f.get('events', [])) and
            f.get('emotion_intensity', 0) > 0.7
        ),
        conclusion="Strong identity clue: transgender (high emotional resonance with transgender content)",
        confidence=0.85
    )

    # 规则3: 多次LGBTQ相关活动 → 确认身份
    rules.add_rule(
        name="repeated_lgbtq_activity_inference",
        condition=lambda f: len([e for e in f.get('events', []) if 'LGBTQ' in str(e)]) >= 3,
        conclusion="Confirmed: LGBTQ+ identity (repeated engagement with LGBTQ+ activities)",
        confidence=0.9
    )

    # 规则4: 时间推理 - 如果提到"昨天"且有日期信息
    rules.add_rule(
        name="temporal_yesterday_inference",
        condition=lambda f: 'yesterday' in f.get('query', '').lower() and f.get('current_date'),
        conclusion="Temporal inference: user is asking about {yesterday_date}",
        confidence=0.95
    )

    # 规则5: 身份隐私推理 - 高情绪+LGBTQ → 可能是隐私话题
    rules.add_rule(
        name="identity_privacy_inference",
        condition=lambda f: (
            f.get('emotion_intensity', 0) > 0.8 and
            any('LGBTQ' in str(e) or 'identity' in str(e).lower() for e in f.get('events', []))
        ),
        conclusion="Privacy consideration: identity topic with high emotional significance",
        confidence=0.75
    )


    return rules
