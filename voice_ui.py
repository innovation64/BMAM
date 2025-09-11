"""
类脑智能体记忆系统 - 语音交互界面
持续语音交互，类似GPT的voice模式
"""

import asyncio
import sys
import threading
import queue
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import numpy as np
import sounddevice as sd
import webrtcvad
from openai import AsyncOpenAI
import pyttsx3
import tkinter as tk
from tkinter import ttk, scrolledtext
import io
import wave

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


class VoiceActivityDetector:
    """语音激活检测器 (VAD)"""
    
    def __init__(self, sample_rate=16000, frame_duration=30):
        self.sample_rate = sample_rate
        self.frame_duration = frame_duration  # ms
        self.frame_size = int(sample_rate * frame_duration / 1000)
        self.vad = webrtcvad.Vad(2)  # 中等灵敏度
        
    def is_speech(self, audio_frame: bytes) -> bool:
        """检测音频帧是否包含语音"""
        try:
            return self.vad.is_speech(audio_frame, self.sample_rate)
        except:
            return False


class ContinuousVoiceUI:
    """持续语音交互UI"""
    
    def __init__(self):
        # 核心组件
        self.coordinator = BrainInspiredCoordinator()
        self.openai_client = AsyncOpenAI()
        
        # 语音处理
        self.vad = VoiceActivityDetector()
        self.tts_engine = pyttsx3.init()
        self._setup_tts()
        
        # 音频参数
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = np.int16
        
        # 状态控制
        self.is_listening = False
        self.is_speaking = False
        self.is_processing = False
        self.should_stop = False
        
        # 音频缓冲区
        self.audio_queue = queue.Queue()
        self.speech_buffer = []
        self.silence_counter = 0
        self.silence_threshold = 20  # 连续静音帧数阈值
        
        # 回调函数
        self.on_listening_start: Optional[Callable] = None
        self.on_listening_stop: Optional[Callable] = None
        self.on_processing_start: Optional[Callable] = None
        self.on_processing_stop: Optional[Callable] = None
        self.on_speaking_start: Optional[Callable] = None
        self.on_speaking_stop: Optional[Callable] = None
        self.on_transcript_ready: Optional[Callable] = None
        self.on_response_ready: Optional[Callable] = None
        
    def _setup_tts(self):
        """设置文本转语音引擎"""
        voices = self.tts_engine.getProperty('voices')
        # 尝试使用中文语音
        for voice in voices:
            if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        
        self.tts_engine.setProperty('rate', 180)  # 语速
        self.tts_engine.setProperty('volume', 0.8)  # 音量
    
    async def start(self):
        """启动语音交互系统"""
        print("启动类脑智能体语音交互系统...")
        
        # 启动协调器
        await self.coordinator.start_system()
        
        # 启动音频处理线程
        self.audio_thread = threading.Thread(target=self._audio_processing_loop, daemon=True)
        self.audio_thread.start()
        
        # 启动语音识别线程
        self.recognition_thread = threading.Thread(target=self._recognition_loop, daemon=True)
        self.recognition_thread.start()
        
        # 开始持续监听
        await self._start_continuous_listening()
    
    async def stop(self):
        """停止语音交互系统"""
        self.should_stop = True
        self.is_listening = False
        
        # 停止音频流
        if hasattr(self, 'audio_stream'):
            self.audio_stream.stop()
            self.audio_stream.close()
        
        # 停止协调器
        await self.coordinator.stop_system()
        
        print("语音交互系统已停止")
    
    def _audio_callback(self, indata, frames, time, status):
        """音频输入回调"""
        if status:
            print(f"音频状态警告: {status}")
        
        if self.is_listening and not self.is_speaking:
            # 转换为16位整数
            audio_data = (indata[:, 0] * 32767).astype(np.int16)
            self.audio_queue.put(audio_data.tobytes())
    
    def _audio_processing_loop(self):
        """音频处理循环"""
        while not self.should_stop:
            try:
                if not self.audio_queue.empty():
                    audio_frame = self.audio_queue.get(timeout=0.1)
                    
                    # VAD检测
                    if len(audio_frame) == self.vad.frame_size * 2:  # 16位音频
                        is_speech = self.vad.is_speech(audio_frame)
                        
                        if is_speech:
                            self.speech_buffer.append(audio_frame)
                            self.silence_counter = 0
                            
                            # 开始录音状态
                            if len(self.speech_buffer) == 1 and self.on_listening_start:
                                self.on_listening_start()
                        else:
                            if self.speech_buffer:
                                self.silence_counter += 1
                                
                                # 静音阈值检测 - 语音结束
                                if self.silence_counter >= self.silence_threshold:
                                    if len(self.speech_buffer) > 10:  # 至少有一定长度的语音
                                        # 合并音频数据并发送识别
                                        audio_data = b''.join(self.speech_buffer)
                                        self._queue_for_recognition(audio_data)
                                    
                                    self.speech_buffer.clear()
                                    self.silence_counter = 0
                                    
                                    if self.on_listening_stop:
                                        self.on_listening_stop()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"音频处理错误: {e}")
    
    def _queue_for_recognition(self, audio_data: bytes):
        """将音频数据排队等待识别"""
        self.recognition_queue.put(audio_data)
    
    def _recognition_loop(self):
        """语音识别循环"""
        self.recognition_queue = queue.Queue()
        
        while not self.should_stop:
            try:
                audio_data = self.recognition_queue.get(timeout=1.0)
                
                # 异步执行语音识别和处理
                asyncio.run_coroutine_threadsafe(
                    self._process_audio_data(audio_data),
                    asyncio.get_event_loop()
                )
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"识别线程错误: {e}")
    
    async def _process_audio_data(self, audio_data: bytes):
        """处理音频数据"""
        try:
            if self.on_processing_start:
                self.on_processing_start()
            
            self.is_processing = True
            
            # 转换为WAV格式
            wav_data = self._convert_to_wav(audio_data)
            
            # OpenAI Whisper识别
            transcript = await self._transcribe_audio(wav_data)
            
            if transcript and transcript.strip():
                print(f"用户说: {transcript}")
                
                if self.on_transcript_ready:
                    self.on_transcript_ready(transcript)
                
                # 发送给类脑记忆系统处理
                response = await self._process_with_brain_system(transcript)
                
                if self.on_response_ready:
                    self.on_response_ready(response)
                
                # 语音合成并播放
                await self._speak_response(response)
            
        except Exception as e:
            print(f"音频处理错误: {e}")
        finally:
            self.is_processing = False
            if self.on_processing_stop:
                self.on_processing_stop()
    
    def _convert_to_wav(self, audio_data: bytes) -> io.BytesIO:
        """将原始音频转换为WAV格式"""
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        return wav_buffer
    
    async def _transcribe_audio(self, wav_data: io.BytesIO) -> str:
        """使用OpenAI Whisper进行语音识别"""
        try:
            wav_data.seek(0)
            transcript = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=wav_data,
                language="zh"  # 中文
            )
            return transcript.text
        except Exception as e:
            print(f"语音识别错误: {e}")
            return ""
    
    async def _process_with_brain_system(self, text: str) -> str:
        """使用类脑记忆系统处理文本"""
        try:
            result = await self.coordinator.process_user_input(text)
            return result.response if result.success else "抱歉，系统处理出现错误。"
        except Exception as e:
            print(f"类脑系统处理错误: {e}")
            return "抱歉，我现在无法处理您的请求。"
    
    async def _speak_response(self, response: str):
        """语音合成并播放响应"""
        if not response.strip():
            return
        
        try:
            if self.on_speaking_start:
                self.on_speaking_start()
            
            self.is_speaking = True
            
            # 使用线程避免阻塞
            def tts_worker():
                self.tts_engine.say(response)
                self.tts_engine.runAndWait()
            
            tts_thread = threading.Thread(target=tts_worker)
            tts_thread.start()
            tts_thread.join()
            
            print(f"系统回复: {response}")
            
        except Exception as e:
            print(f"语音合成错误: {e}")
        finally:
            self.is_speaking = False
            if self.on_speaking_stop:
                self.on_speaking_stop()
    
    async def _start_continuous_listening(self):
        """开始持续监听"""
        print("开始持续语音监听...")
        self.is_listening = True
        
        # 启动音频流
        self.audio_stream = sd.InputStream(
            callback=self._audio_callback,
            channels=self.channels,
            samplerate=self.sample_rate,
            dtype=self.dtype,
            blocksize=int(self.sample_rate * 0.03)  # 30ms块
        )
        
        self.audio_stream.start()
        print("语音监听已启动，可以开始对话...")


class VoiceUIWindow:
    """语音交互UI窗口"""
    
    def __init__(self):
        self.voice_ui = ContinuousVoiceUI()
        self.setup_ui()
        self.setup_callbacks()
        
    def setup_ui(self):
        """设置UI界面"""
        self.root = tk.Tk()
        self.root.title("类脑智能体语音交互系统")
        self.root.geometry("800x600")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 状态显示
        self.status_var = tk.StringVar(value="准备中...")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Arial", 14))
        status_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # 状态指示器
        indicator_frame = ttk.Frame(main_frame)
        indicator_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.listening_indicator = tk.Canvas(indicator_frame, width=20, height=20)
        self.listening_indicator.grid(row=0, column=0, padx=5)
        self.listening_label = ttk.Label(indicator_frame, text="监听中")
        self.listening_label.grid(row=0, column=1, padx=5)
        
        self.processing_indicator = tk.Canvas(indicator_frame, width=20, height=20)
        self.processing_indicator.grid(row=0, column=2, padx=5)
        self.processing_label = ttk.Label(indicator_frame, text="处理中")
        self.processing_label.grid(row=0, column=3, padx=5)
        
        self.speaking_indicator = tk.Canvas(indicator_frame, width=20, height=20)
        self.speaking_indicator.grid(row=0, column=4, padx=5)
        self.speaking_label = ttk.Label(indicator_frame, text="回复中")
        self.speaking_label.grid(row=0, column=5, padx=5)
        
        # 对话历史
        history_frame = ttk.LabelFrame(main_frame, text="对话历史", padding="10")
        history_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        self.conversation_text = scrolledtext.ScrolledText(
            history_frame, 
            width=70, 
            height=20,
            font=("Arial", 11)
        )
        self.conversation_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 控制按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="启动", command=self.start_voice_ui)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self.stop_voice_ui, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        # 系统状态
        status_frame = ttk.LabelFrame(main_frame, text="系统状态", padding="10")
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.system_status = scrolledtext.ScrolledText(
            status_frame,
            width=70,
            height=8,
            font=("Consolas", 9)
        )
        self.system_status.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # 配置权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)
        
        # 初始化指示器
        self.update_indicator(self.listening_indicator, False)
        self.update_indicator(self.processing_indicator, False)
        self.update_indicator(self.speaking_indicator, False)
    
    def setup_callbacks(self):
        """设置回调函数"""
        self.voice_ui.on_listening_start = lambda: self.root.after(0, self.on_listening_start)
        self.voice_ui.on_listening_stop = lambda: self.root.after(0, self.on_listening_stop)
        self.voice_ui.on_processing_start = lambda: self.root.after(0, self.on_processing_start)
        self.voice_ui.on_processing_stop = lambda: self.root.after(0, self.on_processing_stop)
        self.voice_ui.on_speaking_start = lambda: self.root.after(0, self.on_speaking_start)
        self.voice_ui.on_speaking_stop = lambda: self.root.after(0, self.on_speaking_stop)
        self.voice_ui.on_transcript_ready = lambda text: self.root.after(0, lambda: self.on_transcript_ready(text))
        self.voice_ui.on_response_ready = lambda text: self.root.after(0, lambda: self.on_response_ready(text))
    
    def update_indicator(self, canvas, active):
        """更新状态指示器"""
        canvas.delete("all")
        color = "green" if active else "gray"
        canvas.create_oval(2, 2, 18, 18, fill=color, outline="black")
    
    def on_listening_start(self):
        """开始监听回调"""
        self.update_indicator(self.listening_indicator, True)
        self.status_var.set("正在监听...")
    
    def on_listening_stop(self):
        """停止监听回调"""
        self.update_indicator(self.listening_indicator, False)
    
    def on_processing_start(self):
        """开始处理回调"""
        self.update_indicator(self.processing_indicator, True)
        self.status_var.set("正在处理...")
    
    def on_processing_stop(self):
        """停止处理回调"""
        self.update_indicator(self.processing_indicator, False)
    
    def on_speaking_start(self):
        """开始回复回调"""
        self.update_indicator(self.speaking_indicator, True)
        self.status_var.set("正在回复...")
    
    def on_speaking_stop(self):
        """停止回复回调"""
        self.update_indicator(self.speaking_indicator, False)
        self.status_var.set("等待中...")
    
    def on_transcript_ready(self, transcript):
        """转录完成回调"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.conversation_text.insert(tk.END, f"[{timestamp}] 用户: {transcript}\n")
        self.conversation_text.see(tk.END)
    
    def on_response_ready(self, response):
        """响应准备回调"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.conversation_text.insert(tk.END, f"[{timestamp}] 系统: {response}\n\n")
        self.conversation_text.see(tk.END)
    
    def start_voice_ui(self):
        """启动语音UI"""
        async def start_async():
            try:
                await self.voice_ui.start()
                self.root.after(0, lambda: self.start_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self.stop_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.status_var.set("等待中..."))
                
                # 更新系统状态
                status = self.voice_ui.coordinator.get_system_status()
                status_text = json.dumps(status, ensure_ascii=False, indent=2)
                self.root.after(0, lambda: self.system_status.delete(1.0, tk.END))
                self.root.after(0, lambda: self.system_status.insert(1.0, status_text))
                
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"启动失败: {e}"))
        
        # 在新线程中启动异步操作
        threading.Thread(target=lambda: asyncio.run(start_async()), daemon=True).start()
    
    def stop_voice_ui(self):
        """停止语音UI"""
        async def stop_async():
            try:
                await self.voice_ui.stop()
                self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self.status_var.set("已停止"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"停止失败: {e}"))
        
        threading.Thread(target=lambda: asyncio.run(stop_async()), daemon=True).start()
    
    def run(self):
        """运行UI"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n正在退出...")
        finally:
            # 清理资源
            if hasattr(self.voice_ui, 'should_stop'):
                self.voice_ui.should_stop = True


if __name__ == "__main__":
    # 检查依赖
    try:
        import sounddevice as sd
        import webrtcvad
        import pyttsx3
        from openai import AsyncOpenAI
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请安装: pip install sounddevice webrtcvad pyttsx3 openai numpy")
        sys.exit(1)
    
    # 启动语音UI
    app = VoiceUIWindow()
    app.run()