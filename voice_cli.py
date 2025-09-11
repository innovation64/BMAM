#!/usr/bin/env python3
"""
类脑智能体记忆系统 - 简化命令行语音交互
用于快速测试和调试
"""

import asyncio
import sys
import os
import signal
import threading
import queue
import numpy as np
import sounddevice as sd
import webrtcvad
from openai import AsyncOpenAI
import io
import wave

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

from src.coordination.brain_coordinator import BrainInspiredCoordinator


class SimpleVoiceCLI:
    """简化的命令行语音交互"""
    
    def __init__(self):
        self.coordinator = BrainInspiredCoordinator()
        self.openai_client = AsyncOpenAI()
        
        # 音频参数
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = np.int16
        
        # VAD
        self.vad = webrtcvad.Vad(2)
        self.frame_duration = 30  # ms
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
        
        # 状态
        self.is_recording = False
        self.should_stop = False
        self.audio_queue = queue.Queue()
        self.speech_buffer = []
        self.silence_counter = 0
        self.silence_threshold = 20
        
    def audio_callback(self, indata, frames, time, status):
        """音频输入回调"""
        if status:
            print(f"音频状态: {status}")
        
        if self.is_recording:
            audio_data = (indata[:, 0] * 32767).astype(np.int16)
            self.audio_queue.put(audio_data.tobytes())
    
    def process_audio_frames(self):
        """处理音频帧"""
        while not self.should_stop:
            try:
                if not self.audio_queue.empty():
                    audio_frame = self.audio_queue.get(timeout=0.1)
                    
                    if len(audio_frame) == self.frame_size * 2:
                        is_speech = self.vad.is_speech(audio_frame, self.sample_rate)
                        
                        if is_speech:
                            if not self.speech_buffer:
                                print("🎤 检测到语音，开始录音...")
                            
                            self.speech_buffer.append(audio_frame)
                            self.silence_counter = 0
                        else:
                            if self.speech_buffer:
                                self.silence_counter += 1
                                
                                if self.silence_counter >= self.silence_threshold:
                                    if len(self.speech_buffer) > 10:
                                        print("🔇 语音结束，开始处理...")
                                        audio_data = b''.join(self.speech_buffer)
                                        asyncio.run_coroutine_threadsafe(
                                            self.process_speech(audio_data),
                                            self.loop
                                        )
                                    
                                    self.speech_buffer.clear()
                                    self.silence_counter = 0
            except queue.Empty:
                continue
            except Exception as e:
                print(f"音频处理错误: {e}")
    
    def convert_to_wav(self, audio_data: bytes) -> io.BytesIO:
        """转换为WAV格式"""
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        return wav_buffer
    
    async def transcribe_audio(self, wav_data: io.BytesIO) -> str:
        """语音识别"""
        try:
            wav_data.seek(0)
            transcript = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=wav_data,
                language="zh"
            )
            return transcript.text
        except Exception as e:
            print(f"语音识别错误: {e}")
            return ""
    
    async def process_speech(self, audio_data: bytes):
        """处理语音数据"""
        try:
            print("🔄 正在识别语音...")
            wav_data = self.convert_to_wav(audio_data)
            transcript = await self.transcribe_audio(wav_data)
            
            if transcript and transcript.strip():
                print(f"👤 用户: {transcript}")
                
                print("🧠 类脑系统处理中...")
                result = await self.coordinator.process_user_input(transcript)
                
                response = result.response if result.success else "抱歉，处理失败。"
                print(f"🤖 系统: {response}")
                
                # 显示一些系统信息
                if result.success:
                    print(f"   📊 处理时间: {result.processing_time:.2f}s")
                    print(f"   🧠 激活智能体: {len(result.agents_involved)}")
                    print(f"   💭 检索记忆: {len(result.memories_retrieved)}")
                
                print("🎤 等待下一次语音输入...")
            else:
                print("❌ 未识别到有效语音")
                
        except Exception as e:
            print(f"处理错误: {e}")
    
    async def run(self):
        """运行语音交互"""
        print("🎤 类脑智能体语音交互系统 (命令行版)")
        print("=" * 50)
        
        # 启动协调器
        print("🧠 启动类脑记忆系统...")
        await self.coordinator.start_system()
        
        # 设置事件循环
        self.loop = asyncio.get_event_loop()
        
        # 启动音频处理线程
        audio_thread = threading.Thread(target=self.process_audio_frames, daemon=True)
        audio_thread.start()
        
        # 启动音频流
        print("🎤 启动语音监听...")
        self.is_recording = True
        
        with sd.InputStream(
            callback=self.audio_callback,
            channels=self.channels,
            samplerate=self.sample_rate,
            dtype=self.dtype,
            blocksize=int(self.sample_rate * 0.03)
        ):
            print("✅ 语音系统已启动！")
            print("\n使用说明:")
            print("• 直接对着麦克风说话")
            print("• 说完后等待1-2秒，系统会自动处理")
            print("• 按 Ctrl+C 退出")
            print("• 确保已设置 OPENAI_API_KEY 环境变量")
            print("\n🎤 等待语音输入...")
            
            try:
                while not self.should_stop:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                print("\n👋 正在退出...")
                self.should_stop = True
        
        # 停止协调器
        await self.coordinator.stop_system()
        print("✅ 系统已停止")


def signal_handler(signum, frame):
    """信号处理"""
    print("\n🛑 接收到退出信号...")
    sys.exit(0)


async def main():
    """主函数"""
    # 检查依赖
    try:
        import sounddevice as sd
        import webrtcvad
        from openai import AsyncOpenAI
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: python install_voice_dependencies.py")
        return
    
    # 检查API密钥
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ 未设置 OPENAI_API_KEY 环境变量")
        print("请设置: export OPENAI_API_KEY='your-api-key'")
        return
    
    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    # 启动语音CLI
    voice_cli = SimpleVoiceCLI()
    await voice_cli.run()


if __name__ == "__main__":
    asyncio.run(main())