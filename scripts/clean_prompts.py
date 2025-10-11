#!/usr/bin/env python3
"""
清理所有硬编码规则,让prompt纯粹简洁
"""

# capability_orchestrator.py - identity_inference简化
identity_prompt = '''Infer the person's identity from memories.

Question: {query}

Memories:
{memories_text}

Task: Based on the behavioral clues in memories, what is the person's identity?

Output JSON:
{{
    "identity": "inferred identity",
    "confidence": 0.0-1.0,
    "evidence": ["key clues"],
    "reasoning": "inference logic"
}}
'''

# capability_orchestrator.py - multi_hop简化
multihop_prompt = '''Answer the question by synthesizing information from memories.

Question: {query}

Memories:
{memories_text}

Task: Analyze the memories and provide an answer.

Output JSON:
{{
    "answer": "synthesized answer",
    "confidence": 0.0-1.0,
    "evidence": ["supporting memories"],
    "reasoning": "synthesis logic"
}}
'''

print("✅ 简化后的Prompts:")
print("\n=== Identity Inference ===")
print(identity_prompt)
print("\n=== Multi-Hop Inference ===")
print(multihop_prompt)
