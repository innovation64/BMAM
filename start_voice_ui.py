#!/usr/bin/env python3
"""
语音交互系统快速启动脚本
"""

import sys
import os
import asyncio

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有python-dotenv，手动加载.env
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"')

def check_dependencies():
    """检查必要依赖"""
    missing = []
    
    try:
        import sounddevice as sd
    except ImportError:
        missing.append("sounddevice")
    
    try:
        import webrtcvad
    except ImportError:
        missing.append("webrtcvad")
    
    try:
        import pyttsx3
    except ImportError:
        missing.append("pyttsx3")
    
    try:
        from openai import AsyncOpenAI
    except ImportError:
        missing.append("openai")
    
    try:
        import numpy as np
    except ImportError:
        missing.append("numpy")
    
    try:
        import tkinter as tk
    except ImportError:
        missing.append("tkinter")
    
    return missing

def check_openai_key():
    """检查OpenAI API密钥"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️ 未设置OPENAI_API_KEY环境变量")
        print("请设置后再运行:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return False
    return True

def check_audio_device():
    """检查音频设备"""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if not input_devices:
            print("❌ 未找到可用的音频输入设备")
            return False
        
        print(f"✅ 找到 {len(input_devices)} 个音频输入设备")
        return True
    except Exception as e:
        print(f"❌ 音频设备检查失败: {e}")
        return False

def main():
    print("🎤 类脑智能体语音交互系统启动检查")
    print("=" * 50)
    
    # 1. 检查依赖
    print("1. 检查Python依赖...")
    missing_deps = check_dependencies()
    
    if missing_deps:
        print(f"❌ 缺少依赖: {', '.join(missing_deps)}")
        print("请运行: python install_voice_dependencies.py")
        return False
    else:
        print("✅ 所有Python依赖已满足")
    
    # 2. 检查OpenAI API密钥
    print("\n2. 检查OpenAI API配置...")
    if not check_openai_key():
        return False
    else:
        print("✅ OpenAI API密钥已配置")
    
    # 3. 检查音频设备
    print("\n3. 检查音频设备...")
    if not check_audio_device():
        return False
    
    # 4. 启动系统
    print("\n4. 启动语音交互系统...")
    print("=" * 50)
    
    try:
        from voice_ui import VoiceUIWindow
        
        print("🚀 正在启动语音交互界面...")
        app = VoiceUIWindow()
        app.run()
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在退出...")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("\n请检查:")
        print("1. 所有依赖是否正确安装")
        print("2. OpenAI API密钥是否有效")
        print("3. 音频设备权限是否允许")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n💡 需要帮助？请查看项目文档或联系开发者")
        sys.exit(1)