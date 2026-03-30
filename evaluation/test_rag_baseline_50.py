#!/usr/bin/env python3
"""
RAG Baseline Test - 在50个BMAM失败案例上测试纯RAG方法

纯RAG = embedding检索 + 直接拼接上下文 + LLM生成，不做任何记忆管理
"""
import asyncio
import json
import os
import sys
import time
import numpy as np
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / '.env')

from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL")
)

EMBED_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o-mini"


async def get_embedding(text: str) -> list:
    """获取文本嵌入"""
    r = await client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return r.data[0].embedding


async def get_embeddings_batch(texts: list) -> list:
    """批量获取嵌入"""
    results = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = [t[:8000] for t in texts[i:i+batch_size]]
        r = await client.embeddings.create(model=EMBED_MODEL, input=batch)
        results.extend([d.embedding for d in r.data])
    return results


def cosine_sim(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)


async def rag_query(question: str, chunks: list, chunk_embeddings: list, top_k: int = 10) -> str:
    """纯RAG: embedding检索 + LLM生成"""
    # 1. 检索
    q_emb = await get_embedding(question)
    sims = [cosine_sim(q_emb, ce) for ce in chunk_embeddings]
    top_indices = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)[:top_k]

    context = "\n\n".join([chunks[i] for i in top_indices])

    # 2. 生成
    prompt = f"""Based on the following conversation history, answer the question concisely.

Conversation context:
{context}

Question: {question}

Answer concisely and directly. If the information is not available, say "No information available"."""

    r = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=500
    )
    return r.choices[0].message.content.strip()


async def llm_judge(q, gold, gen) -> bool:
    """LLM评判"""
    prompt = f"""Label the generated answer as CORRECT or WRONG.

Question: {q}
Gold answer: {gold}
Generated answer: {gen}

Be generous: same meaning = CORRECT. Same date different format = CORRECT.
Partial match with key info = CORRECT.
Return JSON: {{"label": "CORRECT" or "WRONG"}}"""

    try:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "You are an expert grader"},
                      {"role": "user", "content": prompt}],
            temperature=0)
        return json.loads(r.choices[0].message.content).get("label", "").upper() == "CORRECT"
    except:
        return str(gold).lower() in str(gen).lower()


def build_chunks_from_locomo(conv_data: dict, group_idx: int) -> list:
    """从LoCoMo对话数据构建chunks"""
    chunks = []
    conv = conv_data['conversation']
    speaker_a = conv.get('speaker_a', 'A')
    speaker_b = conv.get('speaker_b', 'B')

    # 遍历所有session
    for i in range(1, 36):
        session_key = f'session_{i}'
        date_key = f'session_{i}_date_time'
        session = conv.get(session_key)
        date_str = conv.get(date_key, '')

        if not session:
            continue

        # 按对话轮次分chunk (每2-3轮一个chunk)
        current_chunk = []
        if date_str:
            current_chunk.append(f"[Date: {date_str}]")

        for j, msg in enumerate(session):
            speaker = msg.get('speaker', 'Unknown')
            text = msg.get('text', '')
            current_chunk.append(f"{speaker}: {text}")

            if len(current_chunk) >= 4:  # 每4条消息一个chunk
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                if date_str:
                    current_chunk.append(f"[Date: {date_str}]")

        if current_chunk and len(current_chunk) > 1:
            chunks.append("\n".join(current_chunk))

    return chunks


def build_chunks_from_longmemeval(sample: dict) -> list:
    """从LongMemEval数据构建chunks"""
    chunks = []
    sessions = sample.get('haystack_sessions', [])
    dates = sample.get('haystack_dates', [])

    for sess_idx, session in enumerate(sessions):
        date_str = dates[sess_idx] if sess_idx < len(dates) else ''
        current_chunk = []
        if date_str:
            current_chunk.append(f"[Session date: {date_str}]")

        for msg in session:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            current_chunk.append(f"{role.capitalize()}: {content[:500]}")

            if len(current_chunk) >= 4:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                if date_str:
                    current_chunk.append(f"[Session date: {date_str}]")

        if current_chunk and len(current_chunk) > 1:
            chunks.append("\n".join(current_chunk))

    return chunks


async def main():
    print("=" * 70)
    print("RAG Baseline Test on 50 BMAM Failure Cases")
    print("=" * 70)

    # 加载选定的50个失败案例
    with open('/home/yanglee/Desktop/selected_50_failures.json') as f:
        failures = json.load(f)

    # 加载原始数据
    with open(PROJECT_ROOT / 'data/datasets/locomo/locomo10.json') as f:
        locomo_data = json.load(f)
    with open(PROJECT_ROOT / 'data/datasets/longmemeval/longmemeval_oracle.json') as f:
        lme_data = json.load(f)

    # 建立LongMemEval索引
    lme_index = {s['question_id']: s for s in lme_data}

    # 建立LoCoMo group索引 (group_id -> index in locomo_data)
    locomo_group_map = {}
    # conv-42 to conv-50 对应 locomo10 的 index 3-9 (根据result文件)
    # 需要从sample_id映射
    for idx, group in enumerate(locomo_data):
        sid = group.get('sample_id', f'group_{idx}')
        locomo_group_map[sid] = idx

    results = []
    total_start = time.time()

    # 对LoCoMo案例，需要找到对应的对话组
    # 按source分组处理
    locomo_cases = [f for f in failures if f['source'] == 'LoCoMo']
    lme_cases = [f for f in failures if f['source'] == 'LongMemEval']

    print(f"\nLoCoMo cases: {len(locomo_cases)}, LongMemEval cases: {len(lme_cases)}")

    # 处理LoCoMo案例 - 按group_id分组以复用embedding
    from collections import defaultdict
    locomo_by_group = defaultdict(list)
    for case in locomo_cases:
        locomo_by_group[case['group_id']].append(case)

    case_idx = 0

    # LoCoMo: 按group处理
    for group_id, cases in locomo_by_group.items():
        # 找到对应的conversation数据
        # group_id格式如 "conv-42", 对应到locomo10.json中需要映射
        # 从result文件看, conv-42对应idx=3, conv-43对应idx=4, ...
        # 尝试直接用所有groups的对话数据拼接
        # 因为7-group结果是sequential的，用所有10组的数据
        all_chunks = []
        for gdata in locomo_data:
            all_chunks.extend(build_chunks_from_locomo(gdata, 0))

        if not all_chunks:
            print(f"  WARNING: No chunks for {group_id}")
            continue

        print(f"\n[LoCoMo/{group_id}] Building embeddings for {len(all_chunks)} chunks...")
        chunk_embeddings = await get_embeddings_batch(all_chunks)

        for case in cases:
            case_idx += 1
            q = case['question']
            gold = case['gold']

            print(f"\n--- Case {case_idx}/50 ---")
            print(f"Q: {q}")
            print(f"Gold: {gold}")
            print(f"BMAM: {case['bmam_answer'][:100]}")

            rag_answer = await rag_query(q, all_chunks, chunk_embeddings)
            ok = await llm_judge(q, gold, rag_answer)

            print(f"RAG:  {rag_answer[:100]}")
            print(f"RAG correct: {ok}")

            results.append({
                'idx': case_idx,
                'source': 'LoCoMo',
                'category': case['category'],
                'question': q,
                'gold': gold,
                'bmam_answer': case['bmam_answer'],
                'rag_answer': rag_answer,
                'rag_correct': ok,
                'bmam_correct': False  # 这些都是BMAM失败的
            })

        # 只build一次LoCoMo embeddings就够了(全量)
        break  # 所有LoCoMo cases用同一个embedding池

    # 处理剩余LoCoMo cases (如果有)
    remaining_locomo = []
    first_group = True
    for group_id, cases in locomo_by_group.items():
        if first_group:
            first_group = False
            continue
        remaining_locomo.extend(cases)

    if remaining_locomo and 'all_chunks' in dir() and 'chunk_embeddings' in dir():
        for case in remaining_locomo:
            case_idx += 1
            q = case['question']
            gold = case['gold']

            print(f"\n--- Case {case_idx}/50 ---")
            print(f"Q: {q}")
            print(f"Gold: {gold}")

            rag_answer = await rag_query(q, all_chunks, chunk_embeddings)
            ok = await llm_judge(q, gold, rag_answer)

            print(f"RAG:  {rag_answer[:100]}")
            print(f"RAG correct: {ok}")

            results.append({
                'idx': case_idx,
                'source': 'LoCoMo',
                'category': case['category'],
                'question': q,
                'gold': gold,
                'bmam_answer': case['bmam_answer'],
                'rag_answer': rag_answer,
                'rag_correct': ok,
                'bmam_correct': False
            })

    # LongMemEval: 每个问题有自己的对话上下文
    for case in lme_cases:
        case_idx += 1
        sample = lme_index.get(case['id'])
        if not sample:
            print(f"  WARNING: Sample {case['id']} not found")
            continue

        chunks = build_chunks_from_longmemeval(sample)
        if not chunks:
            print(f"  WARNING: No chunks for {case['id']}")
            continue

        print(f"\n--- Case {case_idx}/50 [{case['type']}] ---")
        print(f"Q: {case['question']}")
        print(f"Gold: {case['gold']}")
        print(f"BMAM: {case['bmam_answer'][:100]}")

        chunk_embeddings_lme = await get_embeddings_batch(chunks)
        rag_answer = await rag_query(case['question'], chunks, chunk_embeddings_lme)
        ok = await llm_judge(case['question'], case['gold'], rag_answer)

        print(f"RAG:  {rag_answer[:100]}")
        print(f"RAG correct: {ok}")

        results.append({
            'idx': case_idx,
            'source': 'LongMemEval',
            'type': case['type'],
            'question': case['question'],
            'gold': case['gold'],
            'bmam_answer': case['bmam_answer'],
            'rag_answer': rag_answer,
            'rag_correct': ok,
            'bmam_correct': False
        })

    elapsed = time.time() - total_start

    # 统计
    total = len(results)
    rag_correct = sum(1 for r in results if r['rag_correct'])

    print("\n" + "=" * 70)
    print(f"RESULTS SUMMARY")
    print(f"=" * 70)
    print(f"Total cases: {total}")
    print(f"RAG correct: {rag_correct}/{total} = {rag_correct/total*100:.1f}%")
    print(f"BMAM correct: 0/{total} = 0% (all selected as BMAM failures)")
    print(f"Time: {elapsed:.1f}s")

    # 按类型统计
    print("\n--- By Source/Type ---")
    from collections import Counter

    # LoCoMo by category
    cat_names = {1: 'semantic', 2: 'temporal', 3: 'reasoning', 4: 'open-domain', 5: 'adversarial'}
    for cat in sorted(set(r.get('category', 0) for r in results if r['source'] == 'LoCoMo')):
        cat_results = [r for r in results if r['source'] == 'LoCoMo' and r.get('category') == cat]
        cat_correct = sum(1 for r in cat_results if r['rag_correct'])
        print(f"  LoCoMo/{cat_names.get(cat, cat)}: {cat_correct}/{len(cat_results)}")

    # LongMemEval by type
    for qtype in sorted(set(r.get('type', '') for r in results if r['source'] == 'LongMemEval')):
        if not qtype:
            continue
        type_results = [r for r in results if r['source'] == 'LongMemEval' and r.get('type') == qtype]
        type_correct = sum(1 for r in type_results if r['rag_correct'])
        print(f"  LongMemEval/{qtype}: {type_correct}/{len(type_results)}")

    # 保存结果
    output = {
        'config': {
            'method': 'RAG baseline (embedding retrieval + GPT-4o-mini)',
            'embed_model': EMBED_MODEL,
            'llm_model': LLM_MODEL,
            'top_k': 10,
            'total_cases': total
        },
        'summary': {
            'rag_correct': rag_correct,
            'rag_acc': rag_correct / total if total > 0 else 0,
            'bmam_correct': 0,
            'elapsed': elapsed
        },
        'results': results
    }

    output_path = '/home/yanglee/Desktop/rag_baseline_50_results.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {output_path}")


if __name__ == '__main__':
    asyncio.run(main())
