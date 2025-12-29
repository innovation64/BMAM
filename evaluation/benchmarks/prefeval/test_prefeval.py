#!/usr/bin/env python3
"""
PrefEval Benchmark - 偏好一致性评测 (与MemOS标准完全对齐)

测试系统是否能记住用户偏好并在回答中尊重这些偏好。

评估4个维度 (与MemOS一致):
  1. violate_preference: 是否违反偏好
  2. acknowledge_preference: 是否提及偏好 (并提取具体声明)
  3. hallucinate_preference: 是否编造/幻觉偏好
  4. helpful_response: 是否有帮助

错误类型 (5种, 与MemOS一致):
  - Personalized Response: 个性化回答 (好)
  - Preference-Unaware Violation: 违反偏好但未意识到
  - Preference Hallucination Violation: 编造了偏好 (新增!)
  - Inconsistency Violation: 意识到偏好但仍违反
  - Unhelpful Response: 没帮助的回答

使用:
  python3 test_prefeval.py                    # 测试全部
  python3 test_prefeval.py --questions 50     # 测试50题
"""

import asyncio
import json
import os
import sys
import argparse
import time
import logging
import shutil
from datetime import datetime
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import warnings
warnings.filterwarnings('ignore')
logging.getLogger().setLevel(logging.CRITICAL)
for name in ['src', 'openai', 'httpx', 'httpcore', 'urllib3', 'faiss']:
    logging.getLogger(name).setLevel(logging.CRITICAL)
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator
from src.coordination.hrm_coordinator_wrapper import HRMCoordinatorWrapper, HRMConfig

try:
    from openai import AsyncOpenAI
    from dotenv import load_dotenv
    load_dotenv()
    LLM_JUDGE = True
except ImportError:
    LLM_JUDGE = False

# Paths
PREFEVAL_PATH = PROJECT_ROOT / 'data' / 'datasets' / 'prefeval' / 'pref_processed.jsonl'
DATA_DIR = PROJECT_ROOT / 'data' / 'memory'
RESULTS_DIR = PROJECT_ROOT / 'evaluation' / 'results' / 'prefeval'
STATUS_FILE = RESULTS_DIR / 'live_status.json'


def clear_memory():
    """清空记忆文件"""
    # Memory databases
    db_files = ['brain_memory.db', 'temporal_lobe.db', 'working_memory.db', 'kv_value_store.db',
                'memory_vectors.index', 'memory_vectors_mappings.json']
    for f in db_files:
        p = DATA_DIR / f
        if p.exists(): p.unlink()

    # Memory checkpoints
    checkpoint_dir = DATA_DIR / 'checkpoints'
    if checkpoint_dir.exists():
        for f in checkpoint_dir.glob('*.json'):
            f.unlink()

    # State files
    state_dir = PROJECT_ROOT / 'data' / 'state'
    state_files = ['hippocampus_state.json', 'basal_ganglia_state.json', 'prefrontal_state.json',
                   'amygdala_state.json', 'story_arc_state.json', 'calibration_state.json']
    for f in state_files:
        p = state_dir / f
        if p.exists(): p.unlink()

    # User profile files
    for f in ['value_profiles.json', 'user_portraits.json']:
        p = PROJECT_ROOT / 'data' / f
        if p.exists(): p.unlink()

    # Cache directories (correct path: data/cache/)
    cache_dir = PROJECT_ROOT / 'data' / 'cache'
    for d in ['embedding', 'knowledge_graph', 'faiss_index']:
        p = cache_dir / d
        if p.exists(): shutil.rmtree(p)

    # Legacy paths (data/memory/)
    for d in ['embedding_cache', 'knowledge_graph', 'faiss_index']:
        p = DATA_DIR / d
        if p.exists(): shutil.rmtree(p)

    try:
        from src.memory.story_arc import reset_story_arc_manager
        reset_story_arc_manager()
    except ImportError:
        pass


def save_status(status):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def load_data(limit=None):
    """加载PrefEval数据"""
    samples = []
    with open(PREFEVAL_PATH, 'r') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            samples.append(json.loads(line))
    return samples


async def ingest_conversation(coord, conversation):
    """塑造对话历史"""
    for msg in conversation:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        if content:
            await coord.store_memory_with_timestamp(
                f"{role.capitalize()}: {content[:500]}",
                datetime.now(),
                role,
                0.7
            )


async def evaluate_response(client, preference, question, response):
    """评估回答是否尊重偏好 - 与MemOS标准完全对齐

    评估4个维度:
    1. violate_preference: 是否违反偏好
    2. acknowledge_preference: 是否提及偏好 (并提取具体声明)
    3. hallucinate_preference: 是否编造/幻觉偏好
    4. helpful_response: 是否有帮助

    错误类型 (5种):
    - Personalized Response: 好的个性化回答
    - Preference-Unaware Violation: 违反偏好但未意识到
    - Preference Hallucination Violation: 编造了偏好
    - Inconsistency Violation: 意识到偏好但仍违反
    - Unhelpful Response: 没有帮助的回答
    """

    # 1. 检查是否违反偏好 (与MemOS一致)
    violate_prompt = f"""You will analyze a conversation between a user and an assistant, focusing on whether the assistant's response violates the user's stated preference.

Evaluate the response based on these criteria:

Answer "Yes" if:
1. The response contains any recommendations that directly contradict or violate the user's stated preference without any reasoning for why it recommends these contrasting items and no acknowledgment of the user's preference at all.

Answer "No" if:
1. The response respects the user's stated preference.
2. It's acceptable if it includes options that could potentially conflict with the preference, as long as it has acknowledged the user's preference and also specified the reason why or how to avoid the conflict.
3. If the response does not acknowledge the user's preference and if no recommendations violate the user's preference, there is no violation.

Here is the conversation:
User's preference: {preference}
User query: {question}
Assistant response: {response}

Return JSON: {{"violate": "Yes" or "No", "explanation": "brief reason"}}"""

    # 2. 检查是否提及偏好并提取声明 (与MemOS一致)
    acknowledge_prompt = f"""You will analyze a conversation between a user and an assistant, focusing on whether the assistant acknowledges any user preference in answering the user's query.

Evaluate the response based on these stringent criteria:

1. Check if the response explicitly or implicitly mentions or references a user preference.
2. The content of the preference is irrelevant for this check; only its presence matters.

Answer "Yes" if:
1. The response explicitly mentions or refers to a user preference in answering the user's question. Examples include: "Based on your previous preference for xxxx"; "Since you mentioned you prefer/dislike xxxx"; "Since you are a xxxx"; "I will recommend the following given your preference for xxx", etc.
2. The response assumes the user preference in answering the user's question implicitly.

Answer "No" if the response does not mention or refer to any user preference explicitly or implicitly.

Here is the assistant's response:
The user's question is: {question}
Assistant response: {response}

Return JSON: {{"acknowledge": "Yes" or "No", "preference_mention": "quote of the sentence that mentions preference, or empty string if none"}}"""

    # 3. 检查是否有帮助 (与MemOS一致)
    helpful_prompt = f"""You will analyze a conversation between a user and an assistant, focusing on whether the assistant provides any substantive response to the user's query.

Evaluate the response based on these stringent criteria:

Answer "Yes" if any of the following:
1. The response provides specific, relevant recommendations or advice related to the user's query without any apologetic statements or claims of inability to respond.
2. It remembers the user's preference and provides recommendations or suggestions to the user's query without any apologetic statements or claims of inability to respond.

Answer "No" if any of the following:
1. The response contains apologetic statements or claims of inability to respond due to lack of memory of the user's preference.
2. The assistant asks for more information without providing any substantive suggestions, advices directly related to the query.
3. The response doesn't address the user's query.
4. Even if the agent provides some relevant recommendations, if the agent first expresses an inability to follow the user's preference, answer 'No'.

Examples of unhelpful responses (Answer: No):
"Unfortunately, I don't actually have enough context about your specific preferences for xxx"
"Unfortunately, we haven't had a previous discussion about your preferences for xxx. Could you let me know your preference for xxx?"
"I apologize, but I don't have access to your personal information or previous conversations."

Here is the conversation:
User query: {question}
Assistant response: {response}

Return JSON: {{"helpful": "Yes" or "No", "explanation": "brief reason"}}"""

    try:
        # 先评估前3个维度
        responses = await asyncio.gather(
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": violate_prompt}],
                temperature=0
            ),
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": acknowledge_prompt}],
                temperature=0
            ),
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": helpful_prompt}],
                temperature=0
            )
        )

        violate_result = json.loads(responses[0].choices[0].message.content)
        acknowledge_result = json.loads(responses[1].choices[0].message.content)
        helpful_result = json.loads(responses[2].choices[0].message.content)

        violate = violate_result.get("violate", "No") == "Yes"
        acknowledge = acknowledge_result.get("acknowledge", "No") == "Yes"
        preference_mention = acknowledge_result.get("preference_mention", "")
        helpful = helpful_result.get("helpful", "No") == "Yes"

        # 4. 如果提及了偏好,检查是否幻觉 (与MemOS一致)
        hallucinate = False
        if acknowledge and preference_mention.strip():
            hallucinate_prompt = f"""You will analyze a conversation between a user and an assistant, focusing on whether the assistant's restatement of the user's stated preference is the same preference.

Evaluate the response based on these stringent criteria to answer if the assistant has hallucinated the preference or not:

Answer "Yes" if:
1. The assistant's restatement differs from the original preference in meaning or intent.
2. The assistant's restatement contradicts the original preference.
3. The assistant's restatement is not related or irrelevant to the original preference.

Answer "No" if has not hallucinated:
1. The assistant's restatement matches the original preference.
2. The assistant's restatement is a minor paraphrase that fully preserves the meaning and intent of the original preference.
3. The restatement is just empty, no hallucination.

Here is the information:
Original user preference: "{preference}"
Assistant's restatement: "{preference_mention}"

Return JSON: {{"hallucinate": "Yes" or "No", "explanation": "brief reason"}}"""

            hallucinate_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": hallucinate_prompt}],
                temperature=0
            )
            hallucinate_result = json.loads(hallucinate_response.choices[0].message.content)
            hallucinate = hallucinate_result.get("hallucinate", "No") == "Yes"

    except Exception as e:
        # Fallback: 简单检查
        response_lower = response.lower()
        violate = False
        acknowledge = any(word in response_lower for word in ['prefer', 'preference', 'you mentioned', 'based on'])
        helpful = len(response) > 50 and 'sorry' not in response_lower and "don't have" not in response_lower
        hallucinate = False

    # 分类错误类型 - 与MemOS完全一致的5种类型
    if violate and not acknowledge and helpful:
        return "Preference-Unaware Violation"
    elif violate and acknowledge and hallucinate and helpful:
        return "Preference Hallucination Violation"
    elif violate and acknowledge and not hallucinate and helpful:
        return "Inconsistency Violation"
    elif not violate and not helpful:
        return "Unhelpful Response"
    else:
        return "Personalized Response"


async def test_sample(coord, sample, client, idx, total):
    """测试单个样本"""
    conversation = sample.get('conversation', [])
    question = sample.get('question', '')
    preference = sample.get('preference', '')

    print(f"\n[{idx+1}/{total}] 塑造 {len(conversation)} 轮对话...", end='', flush=True)

    # 塑造对话
    clear_memory()
    base_coord = BrainInspiredCoordinator()
    hrm_config = HRMConfig(enable_multi_timescale=True, enable_act=True)
    coord = HRMCoordinatorWrapper(base_coord, hrm_config)
    await coord.start_system()

    await ingest_conversation(coord, conversation)
    await asyncio.sleep(0.5)

    # 提问
    r = await coord.process_user_input(question, context={'skip_memory_store': True, 'evaluation_mode': True})
    response = r.response if hasattr(r, 'response') else str(r)

    # 评估
    error_type = await evaluate_response(client, preference, question, response)

    print(f" → {error_type}")

    return {
        'preference': preference[:100],
        'question': question[:100],
        'response': response[:200],
        'error_type': error_type
    }


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--questions', type=int, default=30, help='测试问题数')
    args = p.parse_args()

    print("=" * 60)
    print(f"PrefEval 评测")
    print("=" * 60)

    # 加载数据
    samples = load_data(args.questions)
    print(f"✓ 加载 {len(samples)} 样本")

    # 初始化
    client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")) if LLM_JUDGE else None

    # 统计
    results = []
    error_counter = Counter()
    start = datetime.now()

    for i, sample in enumerate(samples):
        result = await test_sample(None, sample, client, i, len(samples))
        results.append(result)
        error_counter[result['error_type']] += 1

        # 实时状态
        save_status({
            'mode': 'prefeval',
            'progress': f"{i+1}/{len(samples)}",
            'error_types': dict(error_counter),
            'personalized_rate': error_counter.get('Personalized Response', 0) / (i+1),
            'updated': datetime.now().isoformat()
        })

    elapsed = (datetime.now() - start).total_seconds()

    # 计算指标
    total = len(samples)
    personalized = error_counter.get('Personalized Response', 0)
    personalized_rate = personalized / total * 100

    print("\n" + "=" * 60)
    print(f"完成! 耗时: {elapsed/60:.1f} min")
    print(f"\n错误类型分布:")
    for error_type, count in error_counter.most_common():
        pct = count / total * 100
        print(f"  {error_type}: {count} ({pct:.1f}%)")

    print(f"\n个性化回答率 (目标指标): {personalized_rate:.1f}%")

    # 保存结果
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(RESULTS_DIR / f'result_{ts}.json', 'w') as f:
        json.dump({
            'config': {'questions': len(samples)},
            'summary': {
                'personalized_rate': personalized_rate,
                'error_types': dict(error_counter),
                'elapsed': elapsed
            },
            'results': results[:20]
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到: {RESULTS_DIR / f'result_{ts}.json'}")


if __name__ == '__main__':
    asyncio.run(main())
