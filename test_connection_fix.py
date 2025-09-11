#!/usr/bin/env python3
"""
测试跨事件循环连接修复
模拟UI的实际使用模式
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.services.shared_openai_client import shared_client_manager

async def simulate_ui_conversation_round(round_num: int, message: str):
    """模拟UI的单轮对话处理"""
    print(f"\n=== 第{round_num}轮对话 ===")
    print(f"输入: {message}")
    
    # 模拟UI重置客户端
    print("UI重置客户端...")
    shared_client_manager.reset_clients()
    
    # 初始化协调器
    coordinator = BrainInspiredCoordinator()
    
    try:
        # 处理用户输入
        result = await coordinator.process_user_input(message)
        print(f"✅ 第{round_num}轮成功: {result.success}")
        if result.response:
            print(f"响应: {result.response[:100]}...")
        if result.error:
            print(f"错误: {result.error}")
        return True
    except Exception as e:
        print(f"❌ 第{round_num}轮失败: {e}")
        return False

def main():
    print("=== 跨事件循环连接修复测试 ===")
    
    # 第一轮对话
    loop1 = asyncio.new_event_loop()
    asyncio.set_event_loop(loop1)
    try:
        success1 = loop1.run_until_complete(
            simulate_ui_conversation_round(1, "请记住我喜欢喝绿茶")
        )
    finally:
        loop1.close()
    
    print("\n" + "="*50)
    
    # 第二轮对话（新事件循环）
    loop2 = asyncio.new_event_loop()
    asyncio.set_event_loop(loop2)
    try:
        success2 = loop2.run_until_complete(
            simulate_ui_conversation_round(2, "我刚才说我喜欢喝什么？")
        )
    finally:
        loop2.close()
    
    print("\n" + "="*50)
    print("=== 测试结果 ===")
    if success1 and success2:
        print("🎉 跨事件循环问题已修复！两轮对话都成功！")
    elif success1 and not success2:
        print("❌ 第二轮对话失败 - 跨事件循环问题仍存在")
    else:
        print("❌ 基础功能有问题")

if __name__ == "__main__":
    main()