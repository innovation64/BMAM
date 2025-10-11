"""
🧠 条件约束引擎 - Conditional Constraint Engine

核心理论: Conditional Constraint Theory (CCT)
- 根据条件动态调整推理约束
- 处理多路径推理和冲突解决
- 实现能力之间的依赖和优先级管理

Author: BMAM Team
Date: 2025-10-10
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConstraintAction(Enum):
    """约束动作类型"""
    INSERT_CAPABILITY = "insert_capability"  # 插入新能力
    SKIP_CAPABILITY = "skip_capability"      # 跳过能力
    RETRY_CAPABILITY = "retry_capability"    # 重试能力
    ADJUST_PRIORITY = "adjust_priority"      # 调整优先级
    ACTIVATE_ALTERNATIVE = "activate_alternative"  # 激活备选路径
    REQUIRE_VALIDATION = "require_validation"      # 要求验证
    RESOLVE_CONFLICT = "resolve_conflict"    # 解决冲突


@dataclass
class Constraint:
    """
    条件约束定义

    Attributes:
        name: 约束名称
        condition: 条件函数 (返回True表示约束被触发)
        action: 触发时的动作
        params: 动作参数
        priority: 约束优先级 (越小越优先)
    """
    name: str
    condition: Callable[[], bool]
    action: ConstraintAction
    params: Dict[str, Any]
    priority: int = 5


class ConditionalConstraintEngine:
    """
    条件约束引擎

    职责:
    1. 分析当前推理状态,确定应该应用哪些约束
    2. 根据约束调整能力执行顺序和策略
    3. 处理能力冲突和依赖关系
    4. 实现动态回溯和备选路径
    """

    def __init__(self):
        """初始化约束引擎"""
        self.constraint_rules = self._initialize_constraint_rules()
        self.execution_history = []

    def _initialize_constraint_rules(self) -> List[Constraint]:
        """
        初始化约束引擎

        注意: 不再使用预定义规则,改用LLM动态推理
        """
        return []

    async def analyze_constraints(
        self,
        query: str,
        capabilities: List[Dict[str, Any]],
        memories: List[Dict],
        intermediate_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        🧠 使用LLM动态分析应该应用哪些约束

        Args:
            query: 用户问题
            capabilities: 待执行的能力列表
            memories: 检索到的记忆
            intermediate_results: 已执行能力的中间结果

        Returns:
            List[Dict]: 约束规则列表(JSON格式,之后转换为Constraint对象)
        """
        # 准备上下文信息
        cap_names = [c['name'] for c in capabilities]
        memories_summary = f"{len(memories)} memories available"
        if memories:
            memories_summary += f" (first: {memories[0].get('content', '')[:100]}...)"

        intermediate_summary = "No intermediate results yet"
        if intermediate_results:
            intermediate_summary = f"{len(intermediate_results)} results: "
            for cap_name, result in intermediate_results.items():
                conf = result.get('confidence', 'N/A')
                intermediate_summary += f"{cap_name}(conf={conf:.2f}), "

        # 🔥 使用LLM推理约束规则
        from src.agents.base import BrainAgent

        class TempConstraintAnalyzer(BrainAgent):
            async def process_message(self, message):
                return {}

        analyzer = TempConstraintAnalyzer(
            agent_id='constraint_analyzer',
            brain_region='prefrontal',
            system_prompt='Constraint Analyzer'
        )

        prompt = f"""Analyze the reasoning execution plan and determine what constraints should be applied.

**Question**: {query}

**Planned Capabilities**: {cap_names}

**Available Memories**: {memories_summary}

**Intermediate Results**: {intermediate_summary}

**Task**: Identify constraints that should be applied to ensure correct reasoning execution.

**Available Constraint Actions**:
1. INSERT_CAPABILITY: Insert a missing prerequisite capability
2. SKIP_CAPABILITY: Skip a capability that cannot execute
3. ACTIVATE_ALTERNATIVE: Add an alternative reasoning path
4. ADJUST_PRIORITY: Change capability execution order

**Output JSON** (list of constraint rules):
```json
[
  {{
    "name": "descriptive_constraint_name",
    "action": "INSERT_CAPABILITY | SKIP_CAPABILITY | ACTIVATE_ALTERNATIVE | ADJUST_PRIORITY",
    "reason": "why this constraint is needed",
    "priority": 1-5 (lower = more important),
    "params": {{
      // For INSERT_CAPABILITY:
      "capability": {{"name": "capability_name", "priority": 1, "reason": "..."}},
      "insert_before": "target_capability_name",  // or "insert_after"

      // For SKIP_CAPABILITY:
      "capability": "capability_to_skip",

      // For ACTIVATE_ALTERNATIVE:
      "alternative_capability": "capability_name",

      // For ADJUST_PRIORITY:
      "capability": "capability_name",
      "new_priority": 1
    }},
    "condition_description": "when should this constraint trigger"
  }}
]
```

**Examples**:
- If temporal_calculation is planned but no dates extracted yet → INSERT fact_extraction before it
- If no memories available → SKIP all memory-dependent capabilities
- If intermediate result has low confidence → ACTIVATE pattern_recognition as alternative
- If multi_hop but no base facts → INSERT fact_extraction first

**Important**: Only return constraints that are actually needed for this specific case. Return empty list [] if no constraints needed.

Output only the JSON array, no explanation.
"""

        try:
            import json as json_lib
            content = await analyzer.call_llm(prompt=prompt, temperature=0.2, max_tokens=800)

            # Parse JSON
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()

            constraints_json = json_lib.loads(content)

            logger.info(f"🔍 LLM analyzed {len(constraints_json)} constraints for {len(capabilities)} capabilities")

            return constraints_json

        except Exception as e:
            logger.error(f"❌ LLM constraint analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Fallback: 返回空列表
            return []

    def apply_constraints(
        self,
        capabilities: List[Dict[str, Any]],
        constraints_json: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        应用LLM生成的约束,调整能力执行计划

        Args:
            capabilities: 原始能力列表
            constraints_json: LLM生成的约束列表(JSON格式)

        Returns:
            调整后的能力列表
        """
        if not constraints_json:
            logger.info("No constraints to apply")
            return capabilities

        # 按优先级排序约束
        sorted_constraints = sorted(constraints_json, key=lambda c: c.get('priority', 5))

        modified_capabilities = capabilities.copy()

        for constraint in sorted_constraints:
            constraint_name = constraint.get('name', 'unnamed')
            action = constraint.get('action', '').upper()
            params = constraint.get('params', {})
            reason = constraint.get('reason', 'No reason provided')

            logger.info(f"🔧 Applying constraint: {constraint_name} (action={action})")
            logger.info(f"   Reason: {reason}")

            # 执行动作
            if action == 'INSERT_CAPABILITY':
                modified_capabilities = self._insert_capability(
                    modified_capabilities,
                    params
                )

            elif action == 'SKIP_CAPABILITY':
                modified_capabilities = self._skip_capability(
                    modified_capabilities,
                    params
                )

            elif action == 'ACTIVATE_ALTERNATIVE':
                modified_capabilities = self._activate_alternative(
                    modified_capabilities,
                    params
                )

            elif action == 'ADJUST_PRIORITY':
                modified_capabilities = self._adjust_priority(
                    modified_capabilities,
                    params
                )

            else:
                logger.warning(f"⚠️ Unknown action: {action}")

            # 记录历史
            self.execution_history.append({
                'constraint': constraint_name,
                'action': action,
                'params': params,
                'reason': reason
            })

        return modified_capabilities

    def _insert_capability(
        self,
        capabilities: List[Dict[str, Any]],
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """插入新能力"""
        new_cap = params['capability']

        # 检查是否已经存在
        if any(c['name'] == new_cap['name'] for c in capabilities):
            logger.info(f"  ⏭️ Capability {new_cap['name']} already exists, skipping insert")
            return capabilities

        # 确定插入位置
        if 'insert_before' in params:
            target = params['insert_before']
            for i, cap in enumerate(capabilities):
                if cap['name'] == target:
                    capabilities.insert(i, new_cap)
                    logger.info(f"  ✅ Inserted {new_cap['name']} before {target}")
                    return capabilities

        elif 'insert_after' in params:
            target = params['insert_after']
            for i, cap in enumerate(capabilities):
                if cap['name'] == target:
                    capabilities.insert(i + 1, new_cap)
                    logger.info(f"  ✅ Inserted {new_cap['name']} after {target}")
                    return capabilities

        # 默认插入到开头
        capabilities.insert(0, new_cap)
        logger.info(f"  ✅ Inserted {new_cap['name']} at beginning")
        return capabilities

    def _skip_capability(
        self,
        capabilities: List[Dict[str, Any]],
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """跳过某个能力"""
        cap_name = params['capability']
        capabilities = [c for c in capabilities if c['name'] != cap_name]
        logger.info(f"  ⏭️ Skipped {cap_name}: {params.get('reason', 'No reason')}")
        return capabilities

    def _activate_alternative(
        self,
        capabilities: List[Dict[str, Any]],
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """激活备选能力"""
        alt_cap = params['alternative_capability']

        # 检查是否已经存在
        if any(c['name'] == alt_cap for c in capabilities):
            logger.info(f"  ⏭️ Alternative {alt_cap} already exists")
            return capabilities

        # 添加备选能力
        capabilities.append({
            'name': alt_cap,
            'priority': 10,  # 较低优先级
            'reason': params.get('reason', 'Alternative path')
        })
        logger.info(f"  ✅ Activated alternative: {alt_cap}")
        return capabilities

    def _adjust_priority(
        self,
        capabilities: List[Dict[str, Any]],
        params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """调整能力优先级"""
        cap_name = params['capability']
        new_priority = params['new_priority']

        for cap in capabilities:
            if cap['name'] == cap_name:
                old_priority = cap.get('priority', 99)
                cap['priority'] = new_priority
                logger.info(f"  ✅ Adjusted {cap_name} priority: {old_priority} → {new_priority}")
                break

        return capabilities

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """获取约束执行历史"""
        return self.execution_history
