#!/usr/bin/env python3
"""
🧠 Brain-Inspired Design 主程序入口
"""

import sys
import os

def show_help():
    print("""
🧠 Brain-Inspired Design - 类脑多智能体记忆系统

使用方法:
  python main.py [选项]

选项:
  --chat          启动主对话界面 (推荐)
  --monitor       启动记忆系统监控
  --agent-monitor 启动智能体监控  
  --test          运行测试套件
  --health        系统健康检查
  --help          显示帮助信息

示例:
  python main.py --chat          # 启动主界面
  python main.py --monitor       # 启动监控
  python main.py --test          # 运行测试
    """)

def main():
    if len(sys.argv) == 1 or '--help' in sys.argv:
        show_help()
        return
    
    if '--chat' in sys.argv:
        os.system('python fixed_brain_interface.py')
    elif '--monitor' in sys.argv:
        os.system('python memory_system_monitor.py') 
    elif '--agent-monitor' in sys.argv:
        os.system('python brain_agent_monitor.py')
    elif '--test' in sys.argv:
        os.system('python tests/test_buffer_integration.py')
    elif '--health' in sys.argv:
        os.system('python tools/project_health_check.py')
    else:
        print("❌ 未知选项，使用 --help 查看帮助")

if __name__ == '__main__':
    main()