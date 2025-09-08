#!/usr/bin/env python3
"""
🧠 Brain-Inspired Design 主程序入口
"""

import sys
import subprocess
from pathlib import Path

def show_help():
    print("""
🧠 Brain-Inspired Design - 类脑多智能体记忆系统

使用方法:
  python main.py [选项]

选项:
  --chat          启动交互界面
  --help          显示帮助信息

示例:
  python main.py             # 直接启动界面
  python main.py --chat      # 启动交互界面
  python ui.py               # 直接启动UI界面
    """)

def main():
    if len(sys.argv) == 1:
        # 默认启动UI界面
        ui_path = Path(__file__).parent / 'ui.py'
        subprocess.run([sys.executable, str(ui_path)], check=False)
        return
    
    if '--help' in sys.argv:
        show_help()
        return
    
    if '--chat' in sys.argv:
        ui_path = Path(__file__).parent / 'ui.py'
        subprocess.run([sys.executable, str(ui_path)], check=False)
    else:
        print("❌ 未知选项，使用 --help 查看帮助")
        print("💡 提示: 直接运行 python main.py 启动界面")
        print("💡 提示: 或者运行 python ui.py 直接启动界面")

if __name__ == '__main__':
    main()