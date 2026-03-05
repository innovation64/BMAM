#!/usr/bin/env python3
"""
快速验证 KV→FAISS 同步修复
"""
import sys
sys.path.insert(0, '.')
import asyncio
from tests.test_locomo_10samples_full import (
    load_locomo_data,
    test_single_sample,
    clear_all_memory_files,
    LLM_JUDGE_AVAILABLE
)
from datetime import datetime
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

async def main():
    load_dotenv()
    llm_client = AsyncOpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        base_url=os.getenv('OPENAI_BASE_URL')
    )

    # 清空所有记忆和备份
    print("[1] 清空记忆...", flush=True)
    clear_all_memory_files()

    # 加载数据
    print("[2] 加载数据...", flush=True)
    data = load_locomo_data()
    sample = data[0]  # conv-26

    # 运行测试 (use_backup=False 强制重新塑造)
    print("[3] 开始测试...", flush=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result = await test_single_sample(0, sample, llm_client, timestamp, use_backup=False)

    print('='*60)
    print(f"结果: {result['qa']['correct']}/{result['qa']['total']} = {result['qa']['accuracy']*100:.1f}%")

if __name__ == '__main__':
    asyncio.run(main())
