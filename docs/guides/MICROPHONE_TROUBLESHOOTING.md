# 麦克风权限问题排查指南

## 🎯 现在的工作流程

### 1. 启动服务器
```bash
cd .
python3 run_voice_ui.py
```

### 2. 打开浏览器
访问: `http://localhost:8080`

### 3. 页面加载后
你会看到一个**粉色提示框**，显示：
```
🎤
麦克风权限需要

BMAM Voice UI 需要访问您的麦克风来进行语音交互。
点击下方按钮后，浏览器会请求麦克风权限，请点击"允许"。

[🎤 启用麦克风]
```

### 4. 点击"启用麦克风"按钮
- 浏览器**应该**弹出权限请求对话框
- 对话框可能在以下位置出现：
  - **Chrome/Edge**: 地址栏下方的横幅
  - **Firefox**: 地址栏左侧的弹窗
  - **Safari**: 地址栏内的提示

### 5. 点击"允许"
如果成功，会显示：
```
✅ 麦克风已成功连接！

现在可以点击 "🎤 Start Listening" 开始录音。
```

---

## ❌ 问题1: 点击按钮后没有弹出权限请求

### 原因 A: 权限之前被拒绝过

**检查方法 (Chrome/Edge):**
1. 打开 `http://localhost:8080`
2. 点击地址栏左侧的 🔒 或 ⓘ 图标
3. 查看权限列表中的"麦克风"
4. 如果显示"已阻止"或"询问(默认)"

**解决方法:**
1. 点击麦克风设置
2. 选择"允许"
3. 刷新页面 (F5)
4. 重新点击"启用麦克风"

**检查方法 (Safari):**
1. Safari 菜单 → 偏好设置
2. 网站 → 麦克风
3. 找到 localhost:8080
4. 设置为"允许"

### 原因 B: macOS 系统权限未授予浏览器

**检查系统设置:**
1. 打开"系统偏好设置" (或"系统设置" on macOS 13+)
2. 安全性与隐私 → 隐私 → 麦克风 (或搜索"麦克风")
3. 查看左侧列表中是否有你使用的浏览器（Chrome、Safari、Firefox 等）
4. 确保浏览器旁边的复选框**已勾选**

**如果浏览器不在列表中:**
- 可能需要先在浏览器中尝试访问麦克风，系统才会显示权限请求
- 尝试重启浏览器

### 原因 C: 浏览器不支持 getUserMedia

**检查浏览器版本:**
```
打开浏览器控制台 (F12 → Console)
输入: navigator.mediaDevices
```

- 如果显示 `undefined` → 浏览器太旧或不支持
- 如果显示 `MediaDevices {...}` → 支持

**解决:** 更新浏览器到最新版本

### 原因 D: 麦克风硬件问题

**测试麦克风是否工作:**

macOS 系统测试:
1. 打开"系统偏好设置" → 声音 → 输入
2. 选择麦克风设备
3. 对着麦克风说话
4. 观察"输入电平"是否有波动

**命令行测试 (需要安装 sox):**
```bash
# 安装 sox
brew install sox

# 录制 5 秒音频
rec test.wav trim 0 5

# 播放刚才录制的音频
play test.wav
```

---

## ❌ 问题2: 权限已允许，但检测不到声音

### 打开调试面板
1. 点击页面底部的 "⚙️ Settings" 按钮
2. 左上角会出现"🎤 Audio Debug"面板
3. 点击 "🎤 Start Listening"
4. 对着麦克风说话

### 观察调试信息

**正常情况:**
```
🎤 Audio Debug
Status: 🎙️ Listening
Amplitude: 35.7%      ← 说话时应该大于 10%
Microphone: ✅ Connected
[━━━━━━━░░░░░░░░░░░░]  ← 有动画波动
```

**异常情况 1: Amplitude 始终是 0%**
```
可能原因:
1. 选择了错误的麦克风设备
2. 麦克风被系统静音
3. 麦克风音量太低
```

**解决方法:**
```bash
# 1. 检查 macOS 输入设备
打开系统设置 → 声音 → 输入
- 确保选择了正确的麦克风
- 输入音量拉到中间或以上
- 对着麦克风说话，看输入电平是否波动

# 2. 检查浏览器是否使用了正确的设备
Chrome: chrome://settings/content/microphone
查看"默认"设置
```

**异常情况 2: Microphone 显示 ❌ 错误**
```
可能的错误:
- NotAllowedError: 权限被拒绝
- NotFoundError: 未找到麦克风设备
- NotReadableError: 麦克风被其他应用占用
```

---

## 🔧 深度排查

### 1. 查看浏览器控制台
按 F12 打开开发者工具，查看 Console 标签

**期望的输出:**
```
✅ Connected to server
🔍 Checking browser support...
✅ Browser support check passed
BMAM Voice UI fully initialized
💡 Tip: Click "⚙️ Settings" to show audio debug panel
📢 Click "🎤 启用麦克风" to start using voice features
```

**点击"启用麦克风"后:**
```
🎤 User clicked to initialize microphone...
🎤 Requesting microphone access from browser...
📢 Please click "Allow" when browser asks for permission!
✅ Microphone access granted
```

**如果看到错误:**
```javascript
❌ Failed to access microphone: NotAllowedError
// 权限问题

❌ Failed to access microphone: NotFoundError
// 没有麦克风设备

❌ Failed to access microphone: NotReadableError
// 麦克风被占用
```

### 2. 检查 WebSocket 连接
在控制台应该看到:
```
✅ Connected to server
```

如果看到:
```
❌ Disconnected from server
```

**解决:**
1. 确保服务器正在运行
2. 检查防火墙设置
3. 尝试重启服务器

### 3. 测试麦克风权限状态
在浏览器控制台输入:
```javascript
navigator.permissions.query({ name: 'microphone' })
  .then(result => console.log('Microphone permission:', result.state))
```

**可能的结果:**
- `granted` - 已授权 ✅
- `prompt` - 需要询问用户 ⚠️
- `denied` - 已拒绝 ❌

### 4. 手动测试 getUserMedia
在浏览器控制台输入:
```javascript
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    console.log('✅ Microphone access successful!');
    console.log('Audio tracks:', stream.getAudioTracks());
    stream.getTracks().forEach(track => track.stop());
  })
  .catch(error => {
    console.error('❌ Error:', error.name, error.message);
  })
```

---

## 📝 完整检查清单

按顺序逐项检查:

- [ ] **步骤 1**: 浏览器是最新版本
  - Chrome 53+ / Firefox 36+ / Safari 11+ / Edge 79+

- [ ] **步骤 2**: 使用正确的 URL
  - `http://localhost:8080` ✅
  - `http://127.0.0.1:8080` ✅
  - `http://YOUR_IP:8080` ⚠️ (需要 HTTPS)

- [ ] **步骤 3**: macOS 系统已授权浏览器访问麦克风
  - 系统偏好设置 → 安全性与隐私 → 麦克风 → 勾选浏览器

- [ ] **步骤 4**: 浏览器已授权网站访问麦克风
  - 地址栏 🔒 → 麦克风 → 允许

- [ ] **步骤 5**: 麦克风硬件正常工作
  - 系统偏好设置 → 声音 → 输入 → 输入电平有波动

- [ ] **步骤 6**: 没有其他应用占用麦克风
  - 关闭 Zoom、Teams、录屏软件等

- [ ] **步骤 7**: 网页控制台没有错误
  - F12 → Console → 没有红色错误信息

- [ ] **步骤 8**: 调试面板显示正常
  - Settings → Audio Debug → Amplitude 有变化

---

## 🆘 仍然无法解决？

### 收集诊断信息

1. **浏览器信息:**
```javascript
// 在控制台运行
console.log('User Agent:', navigator.userAgent);
console.log('Platform:', navigator.platform);
```

2. **麦克风设备信息:**
```javascript
// 在控制台运行
navigator.mediaDevices.enumerateDevices()
  .then(devices => {
    devices.filter(d => d.kind === 'audioinput')
      .forEach(d => console.log('Microphone:', d.label || d.deviceId));
  })
```

3. **权限状态:**
```javascript
// 在控制台运行
navigator.permissions.query({ name: 'microphone' })
  .then(r => console.log('Permission:', r.state))
```

4. **截图保存:**
   - 浏览器控制台的错误信息
   - 调试面板的显示
   - 系统麦克风设置页面

### 尝试其他浏览器
如果 Chrome 不行，试试:
- Firefox
- Safari (macOS 自带)
- Edge

### 简化测试

创建一个最小测试页面:
```html
<!DOCTYPE html>
<html>
<body>
<button onclick="test()">Test Microphone</button>
<script>
async function test() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    alert('✅ Success! Microphone is working.');
    stream.getTracks().forEach(t => t.stop());
  } catch (error) {
    alert('❌ Error: ' + error.name + '\n' + error.message);
  }
}
</script>
</body>
</html>
```

保存为 `test.html`，用浏览器打开测试。

---

## 📚 参考资料

- [MDN: getUserMedia](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- [Chrome 麦克风权限](https://support.google.com/chrome/answer/2693767)
- [macOS 麦克风权限](https://support.apple.com/guide/mac-help/control-access-to-your-microphone-mchla1b1e1fe/mac)

---

**更新时间:** 2025-09-30
**适用版本:** BMAM Voice UI v1.0