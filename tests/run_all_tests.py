#!/usr/bin/env python3
"""
Test Runner - 运行所有单元测试
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 确保tests目录在路径中
sys.path.append(str(Path(__file__).parent))

async def run_test_module(module_name):
    """运行单个测试模块"""
    print(f"\n{'='*60}")
    print(f"🧪 运行测试模块: {module_name}")
    print(f"{'='*60}")
    
    try:
        if module_name == "test_agent_buffer_system":
            from test_agent_buffer_system import run_all_tests
        elif module_name == "test_embedding_service":
            from test_embedding_service import run_all_tests
        else:
            print(f"❌ 未知测试模块: {module_name}")
            return False
            
        result = await run_all_tests()
        return result
        
    except Exception as e:
        print(f"❌ 运行测试模块 {module_name} 时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试入口"""
    print("🚀 开始运行BMAM系统单元测试套件")
    print(f"项目根目录: {project_root}")
    
    # 所有测试模块
    test_modules = [
        "test_agent_buffer_system",
        "test_embedding_service"
    ]
    
    total_modules = len(test_modules)
    passed_modules = 0
    failed_modules = 0
    
    # 运行每个测试模块
    for module in test_modules:
        try:
            success = await run_test_module(module)
            if success:
                passed_modules += 1
                print(f"✅ {module} - 所有测试通过")
            else:
                failed_modules += 1
                print(f"❌ {module} - 有测试失败")
        except KeyboardInterrupt:
            print("\n⚠️ 用户中断测试")
            break
        except Exception as e:
            failed_modules += 1
            print(f"❌ {module} - 运行出错: {e}")
    
    # 输出最终结果
    print(f"\n{'='*60}")
    print(f"📊 测试套件执行完成")
    print(f"{'='*60}")
    print(f"总模块数: {total_modules}")
    print(f"✅ 通过模块: {passed_modules}")
    print(f"❌ 失败模块: {failed_modules}")
    
    if failed_modules == 0:
        print("\n🎉 所有测试模块都通过了！系统功能验证成功。")
        return True
    else:
        print(f"\n⚠️ {failed_modules} 个测试模块存在问题，需要修复。")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ 测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n💥 测试运行器出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)