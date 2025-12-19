// WebSocket connection
let ws = null;
let isListening = false;

// Audio capture variables
let audioContext = null;
let mediaStream = null;
let audioWorkletNode = null;
let mediaRecorder = null;
let audioChunks = [];

// Initialize WebSocket
function initWebSocket() {
    ws = new WebSocket('ws://localhost:8080/ws');

    ws.onopen = () => {
        console.log('✅ Connected to server');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onclose = () => {
        console.log('❌ Disconnected from server');
        setTimeout(initWebSocket, 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// Handle server messages
function handleMessage(data) {
    switch (data.type) {
        case 'animation_update':
            updateCharacter(data.character);
            updateWaveform(data.waveform);
            updateChatBubble(data.chat_bubble);
            break;

        case 'memory_update':
            updateMemoryPanel(data.memories);
            break;

        case 'response':
            showChatBubble(data.text);
            break;

        case 'amplitude':
            updateWaveformAmplitude(data.value);
            break;

        case 'listening_started':
            console.log('✅', data.message);
            break;

        case 'listening_stopped':
            console.log('🛑', data.message);
            break;

        case 'processing':
            console.log('⚙️', data.message);
            showChatBubble(data.message);
            break;

        case 'transcription':
            console.log('📝 Transcription:', data.text);
            showChatBubble(`You: ${data.text}`);
            break;

        case 'error':
            console.error('❌ Error:', data.message);
            alert(data.message);
            break;
    }
}

// Update character animation
function updateCharacter(character) {
    const characterEl = document.getElementById('character');

    if (window.live2dViewer && window.live2dViewer.isLoaded) {
        window.live2dViewer.setState(character.state);

        if (character.state === 'speaking' && !window.currentlySpeaking) {
            window.live2dViewer.startSpeaking();
            window.currentlySpeaking = true;
        } else if (character.state !== 'speaking' && window.currentlySpeaking) {
            window.live2dViewer.stopSpeaking();
            window.currentlySpeaking = false;
        }
    } else if (characterEl) {
        const state = character.state || 'idle';
        const emotion = character.emotion || 'neutral';

        const stateClasses = ['idle', 'listening', 'thinking', 'speaking', 'happy', 'excited', 'concerned', 'confused'];
        stateClasses.forEach(cls => {
            characterEl.classList.remove(cls);
            characterEl.classList.remove(`state-${cls}`);
        });
        characterEl.classList.add(state);
        characterEl.classList.add(`state-${state}`);
        characterEl.dataset.state = state;

        const emotionClasses = ['neutral', 'joy', 'surprise', 'thinking', 'sad', 'concerned', 'confused'];
        emotionClasses.forEach(cls => characterEl.classList.remove(`emotion-${cls}`));
        characterEl.classList.add(`emotion-${emotion}`);
        characterEl.dataset.emotion = emotion;

        const mouth = characterEl.querySelector('.mascot-mouth');
        if (mouth) {
            if (state === 'speaking') {
                mouth.dataset.state = 'open';
            } else if (state === 'happy') {
                mouth.dataset.state = 'smile';
            } else if (state === 'confused' || emotion === 'thinking') {
                mouth.dataset.state = 'small';
            } else {
                delete mouth.dataset.state;
            }
        }

        const eyes = characterEl.querySelectorAll('.mascot-eye');
        eyes.forEach(eye => {
            eye.classList.toggle('eye-happy', emotion === 'joy');
            eye.classList.toggle('eye-surprise', emotion === 'surprise');
            eye.classList.toggle('eye-thinking', emotion === 'thinking');
        });
    }

    // Add emotion particles (works with all character types)
    if (character.emotion === 'joy') {
        addEmotionParticles('heart');
    } else if (character.emotion === 'surprise') {
        addEmotionParticles('star');
    } else if (character.emotion === 'thinking') {
        addEmotionParticles('question');
    }
}

// Add emotion particles
function addEmotionParticles(type) {
    const particlesEl = document.querySelector('.emotion-particles');
    if (!particlesEl) return;

    // Remove old particles
    particlesEl.innerHTML = '';

    // Add new particles
    for (let i = 0; i < 3; i++) {
        const particle = document.createElement('div');
        particle.className = `particle ${type}`;
        particle.style.left = `${20 + i * 30}px`;
        particle.style.animationDelay = `${i * 0.5}s`;
        particlesEl.appendChild(particle);
    }

    // Remove particles after animation
    setTimeout(() => {
        particlesEl.innerHTML = '';
    }, 3000);
}

// Update waveform visualization
function updateWaveform(waveformData) {
    const waveformEl = document.getElementById('waveform');

    if (waveformEl.children.length === 0) {
        // Create wave bars
        for (let i = 0; i < 32; i++) {
            const bar = document.createElement('div');
            bar.className = 'wave-bar';
            waveformEl.appendChild(bar);
        }
    }

    // Update bar heights
    const bars = waveformEl.children;
    for (let i = 0; i < bars.length && i < waveformData.length; i++) {
        bars[i].style.height = `${waveformData[i] * 60 + 5}px`;
    }
}

// Update chat bubble
function updateChatBubble(chatBubble) {
    const bubbleEl = document.getElementById('chat-bubble');
    const textEl = document.getElementById('chat-text');

    if (chatBubble.visible) {
        bubbleEl.style.display = 'block';
        bubbleEl.style.opacity = chatBubble.alpha;
        textEl.textContent = chatBubble.text;
    } else {
        bubbleEl.style.display = 'none';
    }
}

// Show chat bubble with text
function showChatBubble(text) {
    const bubbleEl = document.getElementById('chat-bubble');
    const textEl = document.getElementById('chat-text');

    textEl.textContent = text;
    bubbleEl.style.display = 'block';

    setTimeout(() => {
        bubbleEl.style.display = 'none';
    }, 5000);
}

// Update memory panel with BMAM data
function updateMemoryPanel(memories) {
    const listEl = document.getElementById('memory-list');
    listEl.innerHTML = '';

    if (!memories || memories.length === 0) {
        const emptyItem = document.createElement('div');
        emptyItem.className = 'memory-item';
        emptyItem.innerHTML = `
            <div style="color: #888; font-style: italic;">
                No memories retrieved yet.<br>
                Start a conversation to see BMAM memory retrieval.
            </div>
        `;
        listEl.appendChild(emptyItem);
        return;
    }

    memories.forEach((memory, index) => {
        const item = document.createElement('div');
        item.className = 'memory-item';

        // Extract BMAM memory data
        const content = memory.content || 'Memory content unavailable';
        const importance = memory.importance || 0;
        const similarity = memory.similarity_score || 0;
        const timestamp = memory.timestamp ? new Date(memory.timestamp).toLocaleString() : 'Unknown time';
        const contextTags = memory.context_tags || [];
        const emotionTags = memory.emotion_tags || [];

        item.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-size: 12px; color: #00D9FF;">
                    Similarity: ${(similarity * 100).toFixed(0)}%
                </span>
                <span style="font-size: 12px; color: #FF6B9D;">
                    Importance: ${(importance * 100).toFixed(0)}%
                </span>
            </div>
            <div style="margin-bottom: 5px; line-height: 1.4;">
                ${content.length > 200 ? content.substring(0, 200) + '...' : content}
            </div>
            <div style="font-size: 11px; color: #888; margin-top: 5px;">
                <div>🏷️ Context: ${contextTags.join(', ') || 'None'}</div>
                ${emotionTags.length > 0 ? `<div>💭 Emotions: ${emotionTags.join(', ')}</div>` : ''}
                <div>⏰ ${timestamp}</div>
            </div>
        `;

        // Add click handler for memory inspection
        item.addEventListener('click', () => {
            console.log('BMAM Memory Details:', memory);
            showMemoryDetails(memory);
        });

        listEl.appendChild(item);
    });
}

// Show memory details in console/alert
function showMemoryDetails(memory) {
    const details = `
BMAM Memory Details:
───────────────────

Content: ${memory.content || 'N/A'}
ID: ${memory.id || 'N/A'}
Importance: ${((memory.importance || 0) * 100).toFixed(1)}%
Similarity: ${((memory.similarity_score || 0) * 100).toFixed(1)}%
Timestamp: ${memory.timestamp || 'N/A'}

Context Tags: ${(memory.context_tags || []).join(', ') || 'None'}
Emotion Tags: ${(memory.emotion_tags || []).join(', ') || 'None'}

Metadata: ${JSON.stringify(memory.metadata || {}, null, 2)}
    `.trim();

    alert(details);
}

// Start audio initialization (called from button)
async function startAudioInit() {
    const notice = document.getElementById('permission-notice');
    const initBtn = document.getElementById('init-audio-btn');
    const listenBtn = document.getElementById('listen-btn');

    try {
        // Hide notice
        if (notice) notice.style.display = 'none';

        console.log('🎤 User clicked to initialize microphone...');
        const success = await initAudioCapture();

        if (success) {
            // Show listen button, hide init button
            if (initBtn) initBtn.style.display = 'none';
            if (listenBtn) listenBtn.style.display = 'inline-block';

            alert('✅ 麦克风已成功连接！\n\n现在可以点击 "🎤 Start Listening" 开始录音。');
        } else {
            // Show notice again
            if (notice) notice.style.display = 'block';
        }
    } catch (error) {
        console.error('❌ Initialization error:', error);
        if (notice) notice.style.display = 'block';
    }
}

// Initialize audio capture
async function initAudioCapture() {
    try {
        console.log('🎤 Requesting microphone access from browser...');
        console.log('📢 Please click "Allow" when browser asks for permission!');

        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            }
        });

        console.log('✅ Microphone access granted');

        // Update debug panel
        const debugMic = document.getElementById('debug-mic');
        if (debugMic) {
            debugMic.textContent = '✅ Connected';
            debugMic.style.color = '#00FF00';
        }

        // Create audio context
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(mediaStream);

        // Create analyzer for visualization
        const analyzer = audioContext.createAnalyser();
        analyzer.fftSize = 256;
        source.connect(analyzer);

        // Create MediaRecorder for audio capture
        mediaRecorder = new MediaRecorder(mediaStream, {
            mimeType: 'audio/webm'
        });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            console.log('🎤 Recording stopped, processing audio...');
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioChunks = [];

            // Convert to base64 and send to server
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64Audio = reader.result.split(',')[1];
                ws.send(JSON.stringify({
                    type: 'audio_data',
                    audio: base64Audio,
                    format: 'webm'
                }));
            };
            reader.readAsDataURL(audioBlob);
        };

        // Start real-time amplitude monitoring
        startAmplitudeMonitoring(analyzer);

        return true;
    } catch (error) {
        console.error('❌ Failed to access microphone:', error);

        let errorMsg = '无法访问麦克风。\n\n';

        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            errorMsg += '❌ 权限被拒绝\n\n解决方法：\n';
            errorMsg += '1. 点击地址栏左侧的 🔒 或 ⓘ 图标\n';
            errorMsg += '2. 找到"麦克风"设置\n';
            errorMsg += '3. 选择"允许"\n';
            errorMsg += '4. 刷新页面重试';
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            errorMsg += '❌ 未检测到麦克风\n\n请检查：\n';
            errorMsg += '1. 麦克风是否已连接\n';
            errorMsg += '2. 系统设置中麦克风是否可用';
        } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
            errorMsg += '❌ 麦克风被占用\n\n请检查：\n';
            errorMsg += '1. 关闭其他使用麦克风的应用\n';
            errorMsg += '2. 重启浏览器';
        } else {
            errorMsg += `错误: ${error.name}\n${error.message}`;
        }

        alert(errorMsg);

        // Update debug panel
        const debugMic = document.getElementById('debug-mic');
        if (debugMic) {
            debugMic.textContent = `❌ ${error.name}`;
            debugMic.style.color = '#FF0000';
        }

        return false;
    }
}

// Monitor audio amplitude for visualization
function startAmplitudeMonitoring(analyzer) {
    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function update() {
        if (!isListening && !audioContext) {
            return;
        }

        analyzer.getByteFrequencyData(dataArray);

        // Calculate average amplitude
        const average = dataArray.reduce((a, b) => a + b) / bufferLength;
        const normalizedAmplitude = average / 255.0;

        // Update waveform visualization
        updateWaveformAmplitude(normalizedAmplitude);

        // Update debug panel
        updateDebugPanel(normalizedAmplitude);

        // Visual feedback
        if (normalizedAmplitude > 0.1) {
            console.log(`🔊 Audio detected: ${(normalizedAmplitude * 100).toFixed(1)}%`);
        }

        requestAnimationFrame(update);
    }

    update();
}

// Update debug panel
function updateDebugPanel(amplitude) {
    const debugStatus = document.getElementById('debug-status');
    const debugAmplitude = document.getElementById('debug-amplitude');
    const debugMeter = document.getElementById('debug-meter');

    if (debugStatus) {
        debugStatus.textContent = isListening ? '🎙️ Listening' : '⏸️ Ready';
        debugStatus.style.color = isListening ? '#00FF00' : '#FFA500';
    }

    if (debugAmplitude) {
        debugAmplitude.textContent = `${(amplitude * 100).toFixed(1)}%`;
        debugAmplitude.style.color = amplitude > 0.1 ? '#00FF00' : '#888';
    }

    if (debugMeter) {
        debugMeter.style.width = `${amplitude * 100}%`;
    }
}

// Update waveform with amplitude
function updateWaveformAmplitude(amplitude) {
    const waveformEl = document.getElementById('waveform');
    const bars = waveformEl.children;

    if (bars.length === 0) return;

    // Create wave pattern based on amplitude
    for (let i = 0; i < bars.length; i++) {
        const wave = Math.sin((i / bars.length) * Math.PI * 2 + Date.now() / 200);
        const height = Math.abs(wave) * amplitude * 60 + 5;
        bars[i].style.height = `${height}px`;
    }
}

// Initialize Live2D character
async function initCharacter() {
    try {
        console.log('Initializing Live2D character...');
        window.live2dViewer = new Live2DViewerV3('live2d-canvas', 'ANIYA');
        await window.live2dViewer.init();
        console.log('Live2D character initialized:', window.live2dViewer.isLoaded ? 'success' : 'pending');
    } catch (error) {
        console.error('Live2D initialization error:', error);
        // Don't show fallback - just log the error and let canvas remain
    }
}

// Check browser compatibility and permissions
async function checkBrowserSupport() {
    console.log('🔍 Checking browser support...');

    // Check if running on HTTPS or localhost
    const isSecure = window.location.protocol === 'https:' ||
        window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1';

    if (!isSecure) {
        console.warn('⚠️ Not running on HTTPS or localhost. Microphone access may be restricted.');
    }

    // Check getUserMedia support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('❌ 您的浏览器不支持麦克风访问\n\n请使用现代浏览器：\n- Chrome 53+\n- Firefox 36+\n- Safari 11+\n- Edge 79+');
        return false;
    }

    // Check MediaRecorder support
    if (typeof MediaRecorder === 'undefined') {
        console.warn('⚠️ MediaRecorder not supported, audio recording may not work');
    }

    // Try to query permission state
    try {
        if (navigator.permissions && navigator.permissions.query) {
            const result = await navigator.permissions.query({ name: 'microphone' });
            console.log(`🎤 Microphone permission state: ${result.state}`);

            if (result.state === 'denied') {
                alert('❌ 麦克风权限已被拒绝\n\n请在浏览器设置中重新允许麦克风访问：\n1. 点击地址栏的锁图标\n2. 找到麦克风权限\n3. 选择"允许"\n4. 刷新页面');
                return false;
            } else if (result.state === 'granted') {
                console.log('✅ Microphone permission already granted');
                // Auto-hide permission notice if already granted
                const notice = document.getElementById('permission-notice');
                if (notice) notice.style.display = 'none';
            }
        }
    } catch (e) {
        // Permission API not supported, that's ok
        console.log('ℹ️ Permission API not available');
    }

    console.log('✅ Browser support check passed');
    return true;
}

// Initialize everything
async function init() {
    // Check browser support first
    const supported = await checkBrowserSupport();
    if (!supported) {
        return;
    }

    // Initialize WebSocket
    initWebSocket();

    // Initialize character
    await initCharacter();

    // Generate initial waveform
    updateWaveform(new Array(32).fill(0));

    console.log('BMAM Voice UI fully initialized');
    console.log('💡 Tip: Click "⚙️ Settings" to show audio debug panel');
    console.log('📢 Click "🎤 启用麦克风" to start using voice features');
}

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    // Init audio button handler
    document.getElementById('init-audio-btn').addEventListener('click', startAudioInit);

    // Listen button handler
    document.getElementById('listen-btn').addEventListener('click', async () => {
        if (!isListening) {
            // Check if audio is initialized
            if (!audioContext) {
                alert('⚠️ 请先点击 "🎤 Initialize Microphone" 按钮初始化麦克风');
                return;
            }

            // Start recording
            console.log('🎙️ Starting to listen...');
            audioChunks = [];
            mediaRecorder.start();

            ws.send(JSON.stringify({ type: 'start_listening' }));
            document.getElementById('listen-btn').textContent = '⏹️ Stop';
            document.getElementById('listen-btn').classList.add('listening');

            const characterEl = document.getElementById('character');
            if (characterEl) {
                characterEl.classList.add('manual-listening');
                characterEl.classList.add('listening');
            }

            isListening = true;

            // Auto-stop after 10 seconds (safety)
            setTimeout(() => {
                if (isListening) {
                    console.log('⏱️ Auto-stopping after 10 seconds');
                    document.getElementById('listen-btn').click();
                }
            }, 10000);

        } else {
            // Stop recording
            console.log('🛑 Stopping listening...');
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
            }

            ws.send(JSON.stringify({ type: 'stop_listening' }));
            document.getElementById('listen-btn').textContent = '🎤 Start Listening';
            document.getElementById('listen-btn').classList.remove('listening');

            const characterEl = document.getElementById('character');
            if (characterEl) {
                characterEl.classList.remove('manual-listening');
                characterEl.classList.remove('listening');
            }

            isListening = false;
        }
    });

    // Settings button handler (optional element)
    const settingsBtn = document.getElementById('settings-btn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            const debugPanel = document.getElementById('audio-debug');
            if (debugPanel) {
                debugPanel.style.display = debugPanel.style.display === 'none' ? 'block' : 'none';
            }
        });
    }

    // Clear button handler (optional element)
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            const memoryList = document.getElementById('memory-list');
            if (memoryList) {
                memoryList.innerHTML = '';
            }
            const chatBubble = document.getElementById('chat-bubble');
            if (chatBubble) {
                chatBubble.style.display = 'none';
            }
        });
    }
});

// Start initialization when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
