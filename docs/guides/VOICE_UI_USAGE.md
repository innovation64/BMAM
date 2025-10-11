# BMAM Voice UI 使用说明

## 修复内容

已修复语音UI检测不到声音输入的问题。主要改进：

### 1. 降低音频检测阈值
- 静音阈值从 500 降低到 100
- 位置: `src/ui/voice_interface.py:50`
- 使系统更容易检测到低音量输入

### 2. 添加浏览器麦克风捕获
- 使用 Web Audio API 捕获麦克风输入
- 实时音频分析和可视化
- 支持音频录制和传输到服务器

### 3. 音频调试工具
- 点击 "⚙️ Settings" 按钮显示调试面板
- 实时显示：
  - 麦克风连接状态
  - 当前音频幅度
  - 录音状态
  - 音量计量表

### 4. WebSocket 音频传输
- 浏览器录制音频并转换为 base64
- 通过 WebSocket 发送到服务器
- 服务器转换音频格式 (webm → wav)
- 使用语音识别处理音频

## 使用步骤

### 1. 启动服务
```bash
cd /Users/liyang/Desktop/testversion/BMAM
python3 run_voice_ui.py
```

### 2. 打开浏览器
访问: `http://localhost:8080`

### 3. 授予麦克风权限
- 浏览器会请求麦克风访问权限
- **必须点击"允许"才能使用语音功能**

### 4. 测试麦克风
1. 点击 "⚙️ Settings" 显示调试面板
2. 点击 "🎤 Start Listening" 开始录音
3. 对着麦克风说话
4. 观察调试面板中的：
   - **Amplitude 值应该变化** (说话时 > 10%)
   - **音量计量表应该有动画**
   - **控制台输出 "🔊 Audio detected"**

### 5. 录音和识别
- 点击 "🎤 Start Listening" 开始
- 说话（最多10秒）
- 点击 "⏹️ Stop" 结束
- 等待处理：
  - 转写文本会显示在聊天气泡
  - BMAM 处理后返回响应

## 故障排查

### 麦克风检测不到声音

#### 检查1: 浏览器权限
- Chrome: 地址栏左侧 🔒 → 网站设置 → 麦克风 → 允许
- Firefox: 地址栏左侧图标 → 权限 → 使用麦克风 → 允许
- Safari: Safari菜单 → 偏好设置 → 网站 → 麦克风

#### 检查2: 系统麦克风
**macOS:**
```bash
# 系统偏好设置 → 安全性与隐私 → 麦克风
# 确保浏览器有权限访问麦克风
```

**测试麦克风:**
```bash
# 录制5秒测试音频
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
stream = p.open(format=8, channels=1, rate=16000, input=True)
print('Recording 5 seconds...')
data = stream.read(16000*5)
print(f'Recorded {len(data)} bytes')
stream.close()
p.terminate()
"
```

#### 检查3: 依赖库
```bash
# 安装必要的音频库
pip install pyaudio speechrecognition gtts pydub

# macOS 可能需要先安装 portaudio
brew install portaudio

# 安装 ffmpeg (用于音频格式转换)
brew install ffmpeg
```

#### 检查4: 浏览器控制台
1. 按 F12 打开开发者工具
2. 查看 Console 标签
3. 检查错误消息：
   - ❌ `Failed to access microphone` → 权限问题
   - ✅ `Microphone access granted` → 正常
   - 🔊 `Audio detected: XX%` → 检测到声音

### 音频调试面板显示信息

```
🎤 Audio Debug
───────────────
Status: 🎙️ Listening          ← 当前状态
Amplitude: 45.3%              ← 实时音量 (说话时应该 > 10%)
Microphone: ✅ Connected      ← 麦克风状态
[━━━━━━━━━━░░░░░░░░░░]        ← 音量表
```

**Amplitude 含义:**
- 0-5%: 环境噪音（正常）
- 5-20%: 轻声说话
- 20-50%: 正常说话
- 50-100%: 大声说话

### 常见问题

#### Q: 点击按钮没反应
**A:** 检查 WebSocket 连接
- 控制台应显示: `✅ Connected to server`
- 如果显示 `❌ Disconnected`，重启服务器

#### Q: 麦克风已连接但 Amplitude 一直是 0%
**A:** 可能原因:
1. 选择了错误的麦克风设备
2. 麦克风被静音
3. 浏览器音频上下文未激活

**解决:**
- 系统设置中检查默认麦克风
- 关闭麦克风静音
- 刷新页面后重新点击按钮

#### Q: 录音成功但无法识别
**A:** 检查语音识别服务
- 代码使用 Google Speech Recognition (需要网络)
- 确保网络连接正常
- 控制台查看错误: `Speech recognition error: XXX`

#### Q: 浏览器不支持 MediaRecorder
**A:** 使用现代浏览器:
- ✅ Chrome/Edge 49+
- ✅ Firefox 25+
- ✅ Safari 14.1+
- ❌ IE 不支持

## 技术细节

### 音频流程

```
浏览器麦克风
    ↓
Web Audio API (实时分析)
    ↓
MediaRecorder (录制)
    ↓
WebM 音频 Blob
    ↓
Base64 编码
    ↓
WebSocket 传输
    ↓
服务器接收
    ↓
Pydub 转换 (WebM → WAV)
    ↓
SpeechRecognition 转写
    ↓
BMAM 处理
    ↓
返回响应
```

### 文件修改

1. **voice_interface.py** - 降低静音阈值
2. **web_ui_server.py** - 添加:
   - 浏览器音频捕获代码
   - 音频格式转换功能
   - WebSocket 音频处理
   - 调试面板 UI
   - 实时音量可视化

### 音频参数

```python
# 录音设置
sample_rate: 16000 Hz  # 语音识别最佳采样率
channels: 1            # 单声道
format: 16-bit PCM     # 标准音频格式

# 检测阈值
silence_threshold: 100  # RMS 幅度阈值
silence_duration: 1.5s  # 停止录音前的静音时长
```

## 性能优化建议

1. **降低延迟:**
   - 使用本地语音识别 (Whisper)
   - 减少音频编码/解码步骤

2. **提高准确性:**
   - 调整静音阈值适应环境
   - 使用降噪和回声消除
   - 选择合适的语音识别模型

3. **节省带宽:**
   - 压缩音频后传输
   - 使用流式传输而非完整录音
   - 实现 VAD (Voice Activity Detection)

## 下一步改进

- [ ] 添加语音识别语言选择
- [ ] 实现实时流式识别
- [ ] 支持多麦克风设备选择
- [ ] 添加音频增强和降噪
- [ ] 本地 Whisper 模型集成
- [ ] 支持连续对话模式
- [ ] 添加语音唤醒词检测

## 需要帮助？

如果问题仍未解决:

1. 查看服务器日志: 控制台输出的错误信息
2. 查看浏览器控制台: F12 → Console 标签
3. 检查网络标签: F12 → Network → WS (WebSocket)
4. 提供以下信息寻求帮助:
   - 操作系统版本
   - 浏览器版本
   - 错误消息截图
   - 调试面板截图

---

**修复完成时间:** 2025-09-30
**修复内容:** 麦克风音频捕获、实时可视化、WebSocket传输