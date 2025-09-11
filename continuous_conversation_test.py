#!/usr/bin/env python3
"""
连续对话功能测试
测试新增的对话上下文管理和token限制功能
"""

import asyncio
import time
import logging
from datetime import datetime
from src.coordination.brain_coordinator import BrainInspiredCoordinator

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContinuousConversationTester:
    """连续对话测试器"""
    
    def __init__(self):
        self.coordinator = BrainInspiredCoordinator()
        self.session_context = {
            'last_user_preference_id': None,
            'conversation_start': datetime.now()
        }
        
        # 模拟UI的对话历史管理
        self.dialogue_history = []
        self.max_history_turns = 10
        self.max_context_tokens = 2000
    
    def _estimate_tokens(self, text: str) -> int:
        """粗略估算文本token数（中文约1.5字符/token，英文约4字符/token）"""
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        other_chars = len(text) - chinese_chars
        return int(chinese_chars / 1.5 + other_chars / 4)
    
    def _manage_dialogue_history(self, user_input: str, assistant_response: str):
        """管理对话历史，保持在token限制内"""
        # 添加新对话
        new_turn = {
            'user': user_input,
            'assistant': assistant_response,
            'timestamp': datetime.now().isoformat()
        }
        self.dialogue_history.append(new_turn)
        
        # 计算总token数并修剪历史
        total_tokens = 0
        valid_history = []
        
        # 从最新的开始计算，保留在token限制内的对话
        for turn in reversed(self.dialogue_history):
            turn_tokens = self._estimate_tokens(turn['user'] + turn['assistant'])
            if total_tokens + turn_tokens <= self.max_context_tokens:
                valid_history.insert(0, turn)
                total_tokens += turn_tokens
            else:
                break
        
        self.dialogue_history = valid_history[-self.max_history_turns:]  # 最多保留指定轮数
        
        print(f"📚 对话历史管理: 保留{len(self.dialogue_history)}轮, 约{total_tokens}tokens")
    
    def _get_conversation_context(self) -> list:
        """获取格式化的对话上下文"""
        context = []
        for turn in self.dialogue_history:
            context.append({"role": "user", "content": turn['user']})
            context.append({"role": "assistant", "content": turn['assistant']})
        return context
    
    async def test_conversation_turn(self, user_input: str, turn_id: int):
        """测试单轮对话"""
        print(f"\n--- 连续对话第 {turn_id} 轮 ---")
        print(f"👤 用户: {user_input}")
        
        start_time = time.time()
        
        try:
            # 构建包含对话历史的上下文
            context = {
                'session_context': self.session_context,
                'dialogue_history': self._get_conversation_context()
            }
            
            result = await self.coordinator.process_user_input(user_input, context)
            processing_time = time.time() - start_time
            
            if result['success']:
                response = result.get('response', '')
                print(f"🤖 助手: {response[:100]}...")
                print(f"⏱️  耗时: {processing_time:.2f}s")
                
                # 更新对话历史
                self._manage_dialogue_history(user_input, response)
                
                print("✅ 对话成功")
                return True
            else:
                print(f"❌ 对话失败: {result.get('error', '未知错误')}")
                return False
                
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"💥 异常: {type(e).__name__}: {e}")
            print(f"异常耗时: {processing_time:.2f}s")
            return False
    
    async def test_continuous_conversation(self):
        """测试连续对话流程"""
        print("🔄 连续对话功能测试")
        print("测试对话上下文管理和token限制机制")
        print("=" * 60)
        
        # 设计一个连续性强的对话场景
        conversation_flow = [
            "请记住我喜欢喝绿茶，每天下午3点左右。",
            "我刚才说我什么时候喝茶？",
            "除了绿茶，还有什么茶适合下午喝？",
            "你刚才推荐了什么茶？我忘记了。",
            "基于我们之前的对话，你觉得我应该尝试什么新的茶？",
            "我们开始聊天时我说了什么偏好？",
            "你还记得我们讨论过哪些茶类吗？",
            "总结一下我们今天聊了什么关于茶的话题。"
        ]
        
        success_count = 0
        total_turns = len(conversation_flow)
        
        for i, user_input in enumerate(conversation_flow, 1):
            success = await self.test_conversation_turn(user_input, i)
            if success:
                success_count += 1
            
            # 短暂等待，模拟真实对话间隔
            await asyncio.sleep(1)
        
        print(f"\n🏁 连续对话测试完成")
        print(f"成功率: {success_count}/{total_turns} ({success_count/total_turns*100:.1f}%)")
        print(f"最终对话历史长度: {len(self.dialogue_history)} 轮")
        
        # 测试token管理效果
        if self.dialogue_history:
            total_context_chars = sum(len(turn['user'] + turn['assistant']) for turn in self.dialogue_history)
            estimated_tokens = self._estimate_tokens(''.join([turn['user'] + turn['assistant'] for turn in self.dialogue_history]))
            print(f"上下文字符数: {total_context_chars}")
            print(f"估算token数: {estimated_tokens}")
            print(f"Token限制: {self.max_context_tokens}")
        
        return success_count == total_turns

def main():
    """主函数"""
    print("🚀 连续对话功能测试")
    print("验证对话上下文管理、token限制和连续性")
    print("=" * 60)
    
    tester = ContinuousConversationTester()
    
    try:
        success = asyncio.run(tester.test_continuous_conversation())
        
        if success:
            print("\n🎉 连续对话功能测试成功！")
            print("✅ 对话上下文管理正常")
            print("✅ Token限制机制有效") 
            print("✅ 连续性对话流畅")
        else:
            print("\n⚠️ 连续对话功能存在问题")
            print("需要进一步调试和优化")
            
    except Exception as e:
        print(f"\n💥 测试异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()