#!/usr/bin/env python3
"""
语音交互系统依赖安装脚本
"""

import subprocess
import sys
import platform

def install_package(package):
    """安装Python包"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} 安装成功")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {package} 安装失败")
        return False

def check_system_dependencies():
    """检查系统依赖"""
    system = platform.system()
    print(f"检测到系统: {system}")
    
    if system == "Darwin":  # macOS
        print("macOS系统，请确保已安装:")
        print("1. Homebrew")
        print("2. PortAudio: brew install portaudio")
        print("3. 如遇到音频问题，可能需要安装: brew install ffmpeg")
    elif system == "Linux":
        print("Linux系统，请确保已安装:")
        print("1. PortAudio: sudo apt-get install portaudio19-dev")
        print("2. 如遇到音频问题，可能需要安装: sudo apt-get install ffmpeg")
    elif system == "Windows":
        print("Windows系统，通常不需要额外的系统依赖")

def main():
    print("🎤 语音交互系统依赖安装")
    print("=" * 40)
    
    # 检查系统依赖
    check_system_dependencies()
    print()
    
    # 需要安装的包
    packages = [
        "sounddevice",      # 音频录制
        "webrtcvad",        # 语音激活检测
        "pyttsx3",          # 文本转语音
        "openai>=1.0.0",    # OpenAI API
        "numpy",            # 数值计算
        "python-dotenv",    # 环境变量加载（推荐）
        "asyncio",          # 异步支持（Python 3.7+内置）
        "tkinter",          # GUI界面（通常预装）
    ]
    
    print("开始安装Python依赖...")
    success_count = 0
    
    for package in packages:
        if package == "asyncio":
            print(f"⏭️ {package} 是Python内置模块，跳过")
            success_count += 1
            continue
        elif package == "tkinter":
            try:
                import tkinter
                print(f"✅ {package} 已存在")
                success_count += 1
                continue
            except ImportError:
                print(f"❌ {package} 未找到，请手动安装")
                continue
        
        if install_package(package):
            success_count += 1
    
    print("\n" + "=" * 40)
    print(f"安装完成: {success_count}/{len(packages)} 成功")
    
    if success_count == len(packages):
        print("🎉 所有依赖安装成功！")
        print("\n使用方法:")
        print("python voice_ui.py")
    else:
        print("⚠️ 部分依赖安装失败，请手动解决")
        print("\n可能的解决方案:")
        print("1. 更新pip: python -m pip install --upgrade pip")
        print("2. 使用国内源: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple package_name")
        print("3. 检查系统依赖是否正确安装")

if __name__ == "__main__":
    main()