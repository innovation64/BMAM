"""
AI-as-Evaluator Framework
AI 作为评估者框架

🧠 设计原理:
- 使用 LLM 模拟用户来评估 BMAM 系统的回答质量
- 提供多维度评估：事实正确性、时间准确性、信息完整性
- 生成模拟用户反馈，用于测试系统的学习能力

使用场景:
1. Benchmark 自动评估：批量评估 QA 对
2. 反馈闭环测试：测试系统如何响应纠正
3. 置信度校准：验证系统置信度与实际准确率的相关性

Reference: BMAM Human-AI Collaboration Architecture Design
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """用户反馈类型"""
    POSITIVE = "positive"       # 回答正确，用户满意
    NEGATIVE = "negative"       # 回答错误，用户不满
    CORRECTION = "correction"   # 需要纠正，提供正确信息
    FOLLOW_UP = "follow_up"     # 回答不完整，需要追问
    NEUTRAL = "neutral"         # 无明确反馈


@dataclass
class EvaluationResult:
    """评估结果"""
    # 核心评分 (0-1)
    factual_correctness: float = 0.0      # 事实正确性
    temporal_accuracy: float = 0.0        # 时间准确性 (如果涉及时间)
    completeness: float = 0.0             # 信息完整性
    relevance: float = 0.0                # 相关性

    # 综合评分
    overall_score: float = 0.0
    user_satisfaction: float = 0.0        # 模拟用户满意度

    # 元信息
    is_correct: bool = False              # 是否正确 (二分类)
    confidence_calibration: float = 0.0   # 置信度校准误差

    # 详细分析
    analysis: str = ""                    # 详细分析说明
    issues: List[str] = field(default_factory=list)  # 发现的问题

    # 评估元数据
    evaluator_model: str = ""
    evaluation_time: float = 0.0


@dataclass
class SimulatedFeedback:
    """模拟用户反馈"""
    feedback_type: FeedbackType
    content: str                          # 反馈内容
    correction: Optional[str] = None      # 如果是纠正，提供正确答案
    severity: str = "medium"              # 严重程度: low, medium, high
    confidence: float = 0.8               # 反馈置信度

    def to_dict(self) -> Dict[str, Any]:
        return {
            'feedback_type': self.feedback_type.value,
            'content': self.content,
            'correction': self.correction,
            'severity': self.severity,
            'confidence': self.confidence
        }


class AIEvaluator:
    """
    AI 评估器

    使用 LLM 来评估 BMAM 系统的回答质量，并生成模拟用户反馈。

    Features:
    1. 多维度评估 (事实、时间、完整性、相关性)
    2. 模拟用户反馈生成
    3. 置信度校准分析
    4. 批量评估支持
    """

    def __init__(
        self,
        evaluator_model: str = "gpt-4o-mini",
        strict_mode: bool = False
    ):
        """
        初始化 AI 评估器

        Args:
            evaluator_model: 用于评估的模型
            strict_mode: 严格模式 (更严格的评估标准)
        """
        self.evaluator_model = evaluator_model
        self.strict_mode = strict_mode
        self._client = None

    async def _get_client(self):
        """获取 OpenAI 客户端"""
        if self._client is None:
            from src.services.shared_openai_client import shared_client_manager
            self._client = await shared_client_manager.get_chat_client()
        return self._client

    async def evaluate_response(
        self,
        question: str,
        bmam_answer: str,
        ground_truth: str,
        bmam_confidence: float = 0.5,
        context: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        评估 BMAM 的回答

        Args:
            question: 用户问题
            bmam_answer: BMAM 系统的回答
            ground_truth: 正确答案
            bmam_confidence: BMAM 报告的置信度
            context: 额外上下文 (对话历史等)

        Returns:
            EvaluationResult: 评估结果
        """
        start_time = datetime.now()

        # 构建评估 prompt
        context_str = json.dumps(context, ensure_ascii=False) if context else "无"

        evaluation_prompt = f"""作为一个严格的评估者，请评估以下 AI 助手的回答。

## 问题
{question}

## AI 回答
{bmam_answer}

## 正确答案
{ground_truth}

## 上下文
{context_str}

## AI 报告的置信度
{bmam_confidence * 100:.0f}%

请评估以下维度 (0-1 分):

1. **事实正确性** (factual_correctness): AI 回答的核心事实是否与正确答案一致？
   - 1.0: 完全正确
   - 0.5: 部分正确
   - 0.0: 完全错误

2. **时间准确性** (temporal_accuracy): 如果涉及时间/日期，是否准确？
   - 1.0: 时间完全正确
   - 0.5: 时间接近但有误差
   - 0.0: 时间错误
   - -1: 不涉及时间

3. **信息完整性** (completeness): 回答是否完整，没有遗漏关键信息？
   - 1.0: 信息完整
   - 0.5: 部分信息缺失
   - 0.0: 严重缺失

4. **相关性** (relevance): 回答是否与问题相关？
   - 1.0: 高度相关
   - 0.5: 部分相关
   - 0.0: 不相关

5. **用户满意度** (user_satisfaction): 模拟用户对回答的满意程度
   - 1.0: 非常满意
   - 0.5: 一般
   - 0.0: 不满意

6. **是否正确** (is_correct): 综合判断回答是否正确 (true/false)

7. **问题分析** (issues): 列出发现的问题 (数组格式)

8. **详细分析** (analysis): 简要说明评估理由 (1-2句话)

请以 JSON 格式输出:
```json
{{
  "factual_correctness": 0.0,
  "temporal_accuracy": 0.0,
  "completeness": 0.0,
  "relevance": 0.0,
  "user_satisfaction": 0.0,
  "is_correct": false,
  "issues": ["问题1", "问题2"],
  "analysis": "详细分析..."
}}
```"""

        try:
            client = await self._get_client()
            response = await client.chat.completions.create(
                model=self.evaluator_model,
                messages=[{"role": "user", "content": evaluation_prompt}],
                temperature=0.1,  # 低温度以获得一致的评估
                max_tokens=500
            )

            response_text = response.choices[0].message.content

            # 解析 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                eval_data = json.loads(json_match.group())
            else:
                raise ValueError("无法解析评估结果")

            # 处理时间准确性 (-1 表示不涉及)
            temporal_accuracy = eval_data.get('temporal_accuracy', 0)
            if temporal_accuracy == -1:
                temporal_accuracy = 1.0  # 不涉及时间则视为正确

            # 计算综合评分
            overall_score = (
                eval_data.get('factual_correctness', 0) * 0.4 +
                temporal_accuracy * 0.2 +
                eval_data.get('completeness', 0) * 0.2 +
                eval_data.get('relevance', 0) * 0.2
            )

            # 计算置信度校准误差
            # |预测置信度 - 实际准确率|
            actual_accuracy = 1.0 if eval_data.get('is_correct') else 0.0
            confidence_calibration = abs(bmam_confidence - actual_accuracy)

            evaluation_time = (datetime.now() - start_time).total_seconds()

            return EvaluationResult(
                factual_correctness=eval_data.get('factual_correctness', 0),
                temporal_accuracy=temporal_accuracy,
                completeness=eval_data.get('completeness', 0),
                relevance=eval_data.get('relevance', 0),
                overall_score=overall_score,
                user_satisfaction=eval_data.get('user_satisfaction', 0),
                is_correct=eval_data.get('is_correct', False),
                confidence_calibration=confidence_calibration,
                analysis=eval_data.get('analysis', ''),
                issues=eval_data.get('issues', []),
                evaluator_model=self.evaluator_model,
                evaluation_time=evaluation_time
            )

        except Exception as e:
            logger.error(f"评估失败: {e}")
            return EvaluationResult(
                analysis=f"评估失败: {str(e)}",
                evaluator_model=self.evaluator_model,
                evaluation_time=(datetime.now() - start_time).total_seconds()
            )

    async def generate_feedback(
        self,
        question: str,
        bmam_answer: str,
        evaluation: EvaluationResult,
        ground_truth: Optional[str] = None
    ) -> SimulatedFeedback:
        """
        生成模拟用户反馈

        根据评估结果生成一个模拟的用户反馈，可用于测试系统的学习能力。

        Args:
            question: 用户问题
            bmam_answer: BMAM 回答
            evaluation: 评估结果
            ground_truth: 正确答案 (可选)

        Returns:
            SimulatedFeedback: 模拟的用户反馈
        """

        # 根据评估结果决定反馈类型
        if evaluation.is_correct and evaluation.user_satisfaction >= 0.8:
            return SimulatedFeedback(
                feedback_type=FeedbackType.POSITIVE,
                content="谢谢！这正是我想知道的。",
                severity="low",
                confidence=0.9
            )

        elif evaluation.factual_correctness < 0.3:
            # 严重错误 -> 纠正
            correction_text = ground_truth if ground_truth else "（需要用户提供正确答案）"
            return SimulatedFeedback(
                feedback_type=FeedbackType.CORRECTION,
                content=f"不对，正确答案是: {correction_text}",
                correction=correction_text,
                severity="high",
                confidence=0.95
            )

        elif evaluation.completeness < 0.5:
            # 信息不完整 -> 追问
            return SimulatedFeedback(
                feedback_type=FeedbackType.FOLLOW_UP,
                content="能详细说说吗？还有什么相关信息？",
                severity="medium",
                confidence=0.7
            )

        elif evaluation.user_satisfaction < 0.5:
            # 不满意
            return SimulatedFeedback(
                feedback_type=FeedbackType.NEGATIVE,
                content="这个回答不太对，让我想想...",
                severity="medium",
                confidence=0.6
            )

        else:
            # 中性反馈
            return SimulatedFeedback(
                feedback_type=FeedbackType.NEUTRAL,
                content="好的，知道了。",
                severity="low",
                confidence=0.5
            )

    async def evaluate_batch(
        self,
        qa_pairs: List[Dict[str, Any]],
        bmam_answers: List[str],
        bmam_confidences: Optional[List[float]] = None,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        批量评估

        Args:
            qa_pairs: QA 对列表 [{'question': ..., 'answer': ...}, ...]
            bmam_answers: BMAM 回答列表
            bmam_confidences: BMAM 置信度列表
            progress_callback: 进度回调函数

        Returns:
            {
                'results': List[EvaluationResult],
                'summary': {...},
                'feedback': List[SimulatedFeedback]
            }
        """
        if bmam_confidences is None:
            bmam_confidences = [0.5] * len(qa_pairs)

        results = []
        feedback_list = []

        for i, (qa, answer, conf) in enumerate(zip(qa_pairs, bmam_answers, bmam_confidences)):
            try:
                # 评估
                eval_result = await self.evaluate_response(
                    question=qa['question'],
                    bmam_answer=answer,
                    ground_truth=qa.get('answer', ''),
                    bmam_confidence=conf
                )
                results.append(eval_result)

                # 生成反馈
                feedback = await self.generate_feedback(
                    question=qa['question'],
                    bmam_answer=answer,
                    evaluation=eval_result,
                    ground_truth=qa.get('answer')
                )
                feedback_list.append(feedback)

                if progress_callback:
                    progress_callback(i + 1, len(qa_pairs), eval_result)

            except Exception as e:
                logger.error(f"评估第 {i+1} 项失败: {e}")
                results.append(EvaluationResult(analysis=f"评估失败: {e}"))
                feedback_list.append(SimulatedFeedback(
                    feedback_type=FeedbackType.NEUTRAL,
                    content="无法评估"
                ))

        # 计算汇总统计
        valid_results = [r for r in results if r.overall_score > 0]

        summary = {
            'total': len(qa_pairs),
            'evaluated': len(valid_results),
            'correct': sum(1 for r in results if r.is_correct),
            'accuracy': sum(1 for r in results if r.is_correct) / len(results) if results else 0,
            'avg_factual_correctness': sum(r.factual_correctness for r in valid_results) / len(valid_results) if valid_results else 0,
            'avg_temporal_accuracy': sum(r.temporal_accuracy for r in valid_results) / len(valid_results) if valid_results else 0,
            'avg_completeness': sum(r.completeness for r in valid_results) / len(valid_results) if valid_results else 0,
            'avg_user_satisfaction': sum(r.user_satisfaction for r in valid_results) / len(valid_results) if valid_results else 0,
            'avg_confidence_calibration_error': sum(r.confidence_calibration for r in valid_results) / len(valid_results) if valid_results else 0,
            'feedback_distribution': {
                ft.value: sum(1 for f in feedback_list if f.feedback_type == ft)
                for ft in FeedbackType
            }
        }

        return {
            'results': results,
            'summary': summary,
            'feedback': feedback_list
        }


class FeedbackLoopTester:
    """
    反馈闭环测试器

    测试 BMAM 系统如何响应用户反馈并学习改进。
    """

    def __init__(self, bmam_coordinator, ai_evaluator: AIEvaluator):
        """
        初始化反馈闭环测试器

        Args:
            bmam_coordinator: BMAM 系统的协调器
            ai_evaluator: AI 评估器
        """
        self.coordinator = bmam_coordinator
        self.evaluator = ai_evaluator
        self.test_history = []

    async def test_learning_cycle(
        self,
        question: str,
        ground_truth: str,
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        测试学习周期

        1. 提问 -> BMAM 回答
        2. 评估回答
        3. 如果错误，生成反馈
        4. 提供反馈给 BMAM
        5. 重新提问，检查是否改进

        Args:
            question: 测试问题
            ground_truth: 正确答案
            max_iterations: 最大迭代次数

        Returns:
            学习周期结果
        """
        iterations = []

        for i in range(max_iterations):
            # 1. 获取 BMAM 回答
            result = await self.coordinator.process_user_input(question)
            bmam_answer = result.response
            bmam_confidence = result.insights.get('uncertainty_verification', {}).get('confidence', 0.5)

            # 2. 评估
            evaluation = await self.evaluator.evaluate_response(
                question=question,
                bmam_answer=bmam_answer,
                ground_truth=ground_truth,
                bmam_confidence=bmam_confidence
            )

            iteration_result = {
                'iteration': i + 1,
                'bmam_answer': bmam_answer,
                'bmam_confidence': bmam_confidence,
                'evaluation': evaluation,
                'is_correct': evaluation.is_correct
            }

            # 3. 如果正确，结束
            if evaluation.is_correct:
                iteration_result['status'] = 'correct'
                iterations.append(iteration_result)
                break

            # 4. 生成反馈
            feedback = await self.evaluator.generate_feedback(
                question=question,
                bmam_answer=bmam_answer,
                evaluation=evaluation,
                ground_truth=ground_truth
            )
            iteration_result['feedback'] = feedback.to_dict()

            # 5. 提供反馈给 BMAM (如果有反馈处理接口)
            if hasattr(self.coordinator, 'process_user_feedback'):
                await self.coordinator.process_user_feedback(
                    query=question,
                    response=bmam_answer,
                    feedback_type=feedback.feedback_type.value,
                    correction=feedback.correction
                )
                iteration_result['feedback_processed'] = True
            else:
                # 模拟反馈：将纠正作为新的对话存储
                if feedback.correction:
                    feedback_content = f"纠正: {question} 的正确答案是 {feedback.correction}"
                    await self.coordinator.process_input(feedback_content)
                iteration_result['feedback_processed'] = 'simulated'

            iterations.append(iteration_result)

        # 计算学习效果
        final_correct = iterations[-1]['is_correct'] if iterations else False
        learning_progress = [it['evaluation'].overall_score for it in iterations]

        return {
            'question': question,
            'ground_truth': ground_truth,
            'iterations': iterations,
            'total_iterations': len(iterations),
            'final_correct': final_correct,
            'learning_progress': learning_progress,
            'improved': len(learning_progress) > 1 and learning_progress[-1] > learning_progress[0]
        }


# 便捷函数
def get_ai_evaluator(model: str = "gpt-4o-mini") -> AIEvaluator:
    """获取 AI 评估器实例"""
    return AIEvaluator(evaluator_model=model)


async def quick_evaluate(
    question: str,
    bmam_answer: str,
    ground_truth: str,
    model: str = "gpt-4o-mini"
) -> Tuple[EvaluationResult, SimulatedFeedback]:
    """
    快速评估单个 QA

    Returns:
        (评估结果, 模拟反馈)
    """
    evaluator = get_ai_evaluator(model)
    evaluation = await evaluator.evaluate_response(question, bmam_answer, ground_truth)
    feedback = await evaluator.generate_feedback(question, bmam_answer, evaluation, ground_truth)
    return evaluation, feedback


__all__ = [
    'AIEvaluator',
    'EvaluationResult',
    'SimulatedFeedback',
    'FeedbackType',
    'FeedbackLoopTester',
    'get_ai_evaluator',
    'quick_evaluate'
]
