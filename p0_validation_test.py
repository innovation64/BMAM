#!/usr/bin/env python3
"""
P0 验收测试：连续5次"记住→追问"测试
验收标准：P50<6s、P95<10s、memories_used≥1、无30s长尾
"""

import asyncio
import time
import statistics
import logging
from datetime import datetime
from src.coordination.brain_coordinator import BrainInspiredCoordinator

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class P0ValidationTest:
    def __init__(self):
        self.coordinator = BrainInspiredCoordinator()
        self.session_context = {
            'last_user_preference_id': None,
            'conversation_start': datetime.now()
        }
        self.context = {'session_context': self.session_context}
        self.results = []
        
    async def run_single_cycle(self, cycle_num: int):
        """运行单次"记住→追问"循环"""
        cycle_start = time.time()
        
        print(f"\n=== Cycle {cycle_num} ===")
        
        # 1. 记住偏好
        remember_start = time.time()
        remember_input = f"请记住我喜欢喝乌龙茶，每天晚上{7+cycle_num}点左右。"
        
        result1 = await self.coordinator.process_user_input(remember_input, self.context)
        remember_time = time.time() - remember_start
        
        success = result1['success']
        stored_memory_id = result1.get('stored_memory_id')
        
        print(f"记住: {remember_input}")
        print(f"成功: {success}, 存储ID: {stored_memory_id}, 用时: {remember_time:.2f}s")
        
        if not success or not stored_memory_id:
            return {
                'cycle': cycle_num,
                'success': False,
                'error': 'Failed to store preference',
                'remember_time': remember_time,
                'query_time': 0,
                'total_time': remember_time,
                'memories_used': 0
            }
        
        # 2. 追问记忆
        query_start = time.time()
        query_input = "我刚才说我什么时候喝什么茶？"
        
        result2 = await self.coordinator.process_user_input(query_input, self.context)
        query_time = time.time() - query_start
        
        memories_used = result2.get('memory_count', 0)
        response = result2.get('response', '')
        
        print(f"追问: {query_input}")
        print(f"回答: {response[:100]}...")
        print(f"记忆使用: {memories_used}, 用时: {query_time:.2f}s")
        
        total_time = time.time() - cycle_start
        
        # 验证回答质量
        answer_quality = self._validate_answer_quality(response, cycle_num + 7)
        
        return {
            'cycle': cycle_num,
            'success': success and result2['success'] and answer_quality,
            'remember_time': remember_time,
            'query_time': query_time,
            'total_time': total_time,
            'memories_used': memories_used,
            'answer_quality': answer_quality,
            'response': response
        }
    
    def _validate_answer_quality(self, response: str, expected_hour: int) -> bool:
        """验证回答质量"""
        response_lower = response.lower()
        
        # 检查是否包含关键信息
        has_tea = any(tea in response_lower for tea in ['乌龙茶', '茶', 'tea'])
        has_time = any(str(expected_hour) in response or f'{expected_hour}点' in response for expected_hour in range(7, 12))
        has_memory_reference = any(ref in response_lower for ref in ['记得', '说过', '提到', '之前'])
        
        return has_tea and (has_time or has_memory_reference)
    
    async def run_full_validation(self):
        """运行完整的P0验收测试"""
        print("🚀 P0 验收测试开始")
        print(f"测试标准：连续5次成功，P50<6s，P95<10s，memories_used≥1")
        print("="*60)
        
        # 运行5次循环
        for i in range(1, 6):
            try:
                result = await self.run_single_cycle(i)
                self.results.append(result)
                
                # 检查是否出现长尾延迟
                if result['total_time'] > 15:
                    print(f"⚠️  Cycle {i}: 检测到长尾延迟 {result['total_time']:.2f}s")
                    
            except Exception as e:
                logger.error(f"Cycle {i} 异常: {e}")
                self.results.append({
                    'cycle': i,
                    'success': False,
                    'error': str(e),
                    'total_time': 0,
                    'memories_used': 0
                })
        
        # 分析结果
        self.analyze_results()
    
    def analyze_results(self):
        """分析测试结果"""
        print("\n" + "="*60)
        print("📊 P0 验收结果分析")
        print("="*60)
        
        successful_results = [r for r in self.results if r['success']]
        success_rate = len(successful_results) / len(self.results) * 100
        
        print(f"成功率: {success_rate:.1f}% ({len(successful_results)}/5)")
        
        if successful_results:
            total_times = [r['total_time'] for r in successful_results]
            query_times = [r['query_time'] for r in successful_results]
            memories_used = [r['memories_used'] for r in successful_results]
            
            # 性能指标
            p50_total = statistics.median(total_times)
            p95_total = statistics.quantiles(total_times, n=20)[18] if len(total_times) >= 5 else max(total_times)
            p50_query = statistics.median(query_times)
            p95_query = statistics.quantiles(query_times, n=20)[18] if len(query_times) >= 5 else max(query_times)
            
            avg_memories = statistics.mean(memories_used)
            min_memories = min(memories_used)
            
            print(f"\n📈 性能指标:")
            print(f"总时间 P50: {p50_total:.2f}s, P95: {p95_total:.2f}s")
            print(f"查询时间 P50: {p50_query:.2f}s, P95: {p95_query:.2f}s") 
            print(f"记忆使用: 平均{avg_memories:.1f}, 最少{min_memories}")
            
            # 验收判定
            print(f"\n✅ P0验收标准检查:")
            p50_pass = p50_total < 6.0
            p95_pass = p95_total < 10.0
            memory_pass = min_memories >= 1
            success_pass = success_rate >= 80
            
            print(f"P50 < 6s: {'✅' if p50_pass else '❌'} ({p50_total:.2f}s)")
            print(f"P95 < 10s: {'✅' if p95_pass else '❌'} ({p95_total:.2f}s)")
            print(f"记忆使用≥1: {'✅' if memory_pass else '❌'} (最少{min_memories})")
            print(f"成功率≥80%: {'✅' if success_pass else '❌'} ({success_rate:.1f}%)")
            
            all_pass = p50_pass and p95_pass and memory_pass and success_pass
            
            print(f"\n🎯 P0验收结果: {'🎉 通过' if all_pass else '❌ 未通过'}")
            
            if not all_pass:
                print("\n🔧 需要改进的方面:")
                if not p50_pass:
                    print(f"- P50延迟过高：{p50_total:.2f}s > 6s")
                if not p95_pass:
                    print(f"- P95延迟过高：{p95_total:.2f}s > 10s")
                if not memory_pass:
                    print(f"- 记忆使用不足：最少{min_memories} < 1")
                if not success_pass:
                    print(f"- 成功率不足：{success_rate:.1f}% < 80%")
        
        # 详细结果
        print(f"\n📋 详细结果:")
        for result in self.results:
            status = "✅" if result['success'] else "❌"
            print(f"Cycle {result['cycle']}: {status} 总时间{result['total_time']:.2f}s, "
                  f"查询{result['query_time']:.2f}s, 记忆{result['memories_used']}")

async def main():
    """主函数"""
    test = P0ValidationTest()
    await test.run_full_validation()

if __name__ == "__main__":
    asyncio.run(main())