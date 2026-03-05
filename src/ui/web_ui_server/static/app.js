// ─── WebSocket connection ────────────────────────────────────────────────────
let ws = null;
let isListening = false;

// Audio capture (AudioWorklet-based streaming)
let audioContext = null;
let mediaStream = null;
let workletNode = null;
let analyzerNode = null;
let micInitialized = false;

// TTS playback
let playbackCtx = null;
let nextPlayTime = 0;
let audioQueue = [];
let isSystemSpeaking = false;

// ─── Toast notifications ─────────────────────────────────────────────────────

function showToast(msg, duration, isError) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const el = document.createElement('div');
    el.className = 'toast' + (isError ? ' toast-error' : '');
    el.textContent = msg;
    container.appendChild(el);
    setTimeout(() => {
        el.style.animation = 'toast-out 0.3s ease-in forwards';
        el.addEventListener('animationend', () => el.remove());
    }, duration || 3500);
}

// ─── Chat history ────────────────────────────────────────────────────────────

let partialMessageEl = null;

function appendMessage(text, role, kind) {
    const history = document.getElementById('chat-history');
    if (!history) return;

    // Partial messages update in-place
    if (kind === 'partial') {
        if (!partialMessageEl) {
            partialMessageEl = document.createElement('div');
            partialMessageEl.className = 'message ' + role + ' partial';
            history.appendChild(partialMessageEl);
        }
        partialMessageEl.textContent = text;
        history.scrollTop = history.scrollHeight;
        return;
    }

    // Finalize any partial message
    if (partialMessageEl) {
        partialMessageEl.remove();
        partialMessageEl = null;
    }

    const el = document.createElement('div');
    el.className = 'message ' + role;
    el.textContent = text;
    history.appendChild(el);
    history.scrollTop = history.scrollHeight;
}

// ─── Memory detail modal ─────────────────────────────────────────────────────

function showMemoryModal(memory) {
    // Remove existing modal if any
    const existing = document.querySelector('.memory-modal-overlay');
    if (existing) existing.remove();

    const t = (typeof I18N !== 'undefined') ? I18N.t.bind(I18N) : (k) => k;
    const content = memory.content || 'N/A';
    const importance = memory.importance ? (memory.importance * 100).toFixed(0) + '%' : 'N/A';
    const similarity = memory.similarity_score ? (memory.similarity_score * 100).toFixed(0) + '%' : 'N/A';
    const timestamp = memory.timestamp ? new Date(memory.timestamp).toLocaleString() : 'Unknown';
    const contextTags = (memory.context_tags || []).join(', ') || 'None';
    const emotionTags = (memory.emotion_tags || []).join(', ') || 'None';

    const overlay = document.createElement('div');
    overlay.className = 'memory-modal-overlay';
    overlay.innerHTML =
        '<div class="memory-modal">' +
            '<h3>' + t('modal.memory_details') + '</h3>' +
            '<div class="modal-field"><label>' + t('modal.content') + '</label><div class="modal-value">' + escapeHtml(content) + '</div></div>' +
            '<div class="modal-field"><label>' + t('modal.similarity') + '</label><div class="modal-value">' + similarity + '</div></div>' +
            '<div class="modal-field"><label>' + t('modal.importance') + '</label><div class="modal-value">' + importance + '</div></div>' +
            '<div class="modal-field"><label>' + t('modal.context') + '</label><div class="modal-value">' + escapeHtml(contextTags) + '</div></div>' +
            '<div class="modal-field"><label>' + t('modal.emotions') + '</label><div class="modal-value">' + escapeHtml(emotionTags) + '</div></div>' +
            '<div class="modal-field"><label>' + t('modal.timestamp') + '</label><div class="modal-value">' + escapeHtml(timestamp) + '</div></div>' +
            '<button class="modal-close">' + t('modal.close') + '</button>' +
        '</div>';

    overlay.addEventListener('click', (e) => {
        if (e.target === overlay || e.target.classList.contains('modal-close')) {
            overlay.remove();
        }
    });

    document.body.appendChild(overlay);
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── WebSocket ───────────────────────────────────────────────────────────────

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || 'localhost:8080';
    ws = new WebSocket(`${protocol}//${host}/ws`);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
        console.log('Connected to server');
    };

    ws.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
            handleTTSAudio(event.data);
            return;
        }
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    ws.onclose = () => {
        console.log('Disconnected from server');
        setTimeout(initWebSocket, 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

// ─── Message handlers ────────────────────────────────────────────────────────

function handleMessage(data) {
    switch (data.type) {
        case 'connected':
            console.log('Server connected, voice_available:', data.voice_available);
            break;

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
            appendMessage(data.text, 'assistant');
            break;

        case 'brain_status':
            showChatBubble(data.stage || data.details || 'Processing...');
            appendMessage(data.stage || data.details || 'Processing...', 'system');
            // Pipe to brain panel if available
            if (window.updateBrainActivity && data.regions) {
                window.updateBrainActivity(data.regions, data.reasoning_chain);
            }
            break;

        case 'brain_activity':
            if (window.updateBrainActivity) {
                window.updateBrainActivity(data.regions, data.reasoning_chain);
            }
            break;

        case 'amplitude':
            updateWaveformAmplitude(data.value);
            break;

        case 'listening_started':
            console.log('Listening started');
            break;

        case 'listening_stopped':
            console.log('Listening stopped');
            break;

        case 'processing':
            showChatBubble(data.message);
            appendMessage(data.message, 'system');
            break;

        case 'transcription':
            showChatBubble('You: ' + data.text);
            appendMessage(data.text, 'user');
            break;

        // ─── Voice protocol messages ─────────────────────────────────────
        case 'voice_start_ack':
            console.log('Voice session started:', data.session_id);
            break;

        case 'voice_vad':
            handleVAD(data);
            break;

        case 'voice_partial':
            showChatBubble('...' + data.text, 'partial');
            appendMessage(data.text, 'assistant', 'partial');
            break;

        case 'voice_transcript':
            showChatBubble('You: ' + data.text);
            appendMessage(data.text, 'user');
            break;

        case 'voice_tts_start':
            isSystemSpeaking = true;
            setCharacterState('speaking');
            if (!playbackCtx || playbackCtx.state === 'closed') {
                playbackCtx = new AudioContext();
            }
            audioQueue = [];
            nextPlayTime = 0;
            break;

        case 'voice_tts_end':
            isSystemSpeaking = false;
            setTimeout(() => setCharacterState('idle'), 500);
            break;

        case 'error':
            console.error('Error:', data.message);
            showChatBubble('Error: ' + data.message);
            showToast(data.message, 5000, true);
            break;
    }
}

// ─── Voice protocol helpers ──────────────────────────────────────────────────

function handleVAD(data) {
    if (data.speaking) {
        setCharacterState('listening');
    } else if (!isSystemSpeaking) {
        setCharacterState('thinking');
    }
}

function handleTTSAudio(arrayBuffer) {
    if (!playbackCtx || playbackCtx.state === 'closed') return;

    playbackCtx.decodeAudioData(arrayBuffer.slice(0))
        .then((audioBuffer) => {
            const source = playbackCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(playbackCtx.destination);
            const now = playbackCtx.currentTime;
            const startTime = Math.max(now, nextPlayTime);
            source.start(startTime);
            nextPlayTime = startTime + audioBuffer.duration;
        })
        .catch(() => {
            audioQueue.push(new Uint8Array(arrayBuffer));
            tryDecodeAccumulated();
        });
}

function tryDecodeAccumulated() {
    if (audioQueue.length < 2 || !playbackCtx) return;

    const totalLen = audioQueue.reduce((s, a) => s + a.length, 0);
    const merged = new Uint8Array(totalLen);
    let offset = 0;
    for (const chunk of audioQueue) {
        merged.set(chunk, offset);
        offset += chunk.length;
    }

    playbackCtx.decodeAudioData(merged.buffer.slice(0))
        .then((audioBuffer) => {
            audioQueue = [];
            const source = playbackCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(playbackCtx.destination);
            const now = playbackCtx.currentTime;
            const startTime = Math.max(now, nextPlayTime);
            source.start(startTime);
            nextPlayTime = startTime + audioBuffer.duration;
        })
        .catch(() => { /* wait for more data */ });
}

// ─── Character animation ─────────────────────────────────────────────────────

function setCharacterState(state) {
    const characterEl = document.getElementById('character');
    if (!characterEl) return;

    if (window.live2dViewer && window.live2dViewer.isLoaded) {
        window.live2dViewer.setState(state);
        if (state === 'speaking' && !window.currentlySpeaking) {
            window.live2dViewer.startSpeaking();
            window.currentlySpeaking = true;
        } else if (state !== 'speaking' && window.currentlySpeaking) {
            window.live2dViewer.stopSpeaking();
            window.currentlySpeaking = false;
        }
        return;
    }

    const stateClasses = ['idle', 'listening', 'thinking', 'speaking', 'happy', 'excited', 'concerned', 'confused'];
    stateClasses.forEach(cls => {
        characterEl.classList.remove(cls);
        characterEl.classList.remove('state-' + cls);
    });
    characterEl.classList.add(state);
    characterEl.classList.add('state-' + state);
    characterEl.dataset.state = state;
}

function updateCharacter(character) {
    setCharacterState(character.state || 'idle');

    const characterEl = document.getElementById('character');
    if (!characterEl) return;

    const emotion = character.emotion || 'neutral';
    const emotionClasses = ['neutral', 'joy', 'surprise', 'thinking', 'sad', 'concerned', 'confused'];
    emotionClasses.forEach(cls => characterEl.classList.remove('emotion-' + cls));
    characterEl.classList.add('emotion-' + emotion);
    characterEl.dataset.emotion = emotion;

    const mouth = characterEl.querySelector('.mascot-mouth');
    if (mouth) {
        if (character.state === 'speaking') mouth.dataset.state = 'open';
        else if (character.state === 'happy') mouth.dataset.state = 'smile';
        else if (character.state === 'confused' || emotion === 'thinking') mouth.dataset.state = 'small';
        else delete mouth.dataset.state;
    }

    const eyes = characterEl.querySelectorAll('.mascot-eye');
    eyes.forEach(eye => {
        eye.classList.toggle('eye-happy', emotion === 'joy');
        eye.classList.toggle('eye-surprise', emotion === 'surprise');
        eye.classList.toggle('eye-thinking', emotion === 'thinking');
    });

    if (character.emotion === 'joy') addEmotionParticles('heart');
    else if (character.emotion === 'surprise') addEmotionParticles('star');
    else if (character.emotion === 'thinking') addEmotionParticles('question');
}

function addEmotionParticles(type) {
    const particlesEl = document.querySelector('.emotion-particles');
    if (!particlesEl) return;
    particlesEl.innerHTML = '';
    for (let i = 0; i < 3; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle ' + type;
        particle.style.left = (20 + i * 30) + 'px';
        particle.style.animationDelay = (i * 0.5) + 's';
        particlesEl.appendChild(particle);
    }
    setTimeout(() => { particlesEl.innerHTML = ''; }, 3000);
}

// ─── Waveform visualization ──────────────────────────────────────────────────

function updateWaveform(waveformData) {
    const waveformEl = document.getElementById('waveform');
    if (waveformEl.children.length === 0) {
        for (let i = 0; i < 32; i++) {
            const bar = document.createElement('div');
            bar.className = 'wave-bar';
            waveformEl.appendChild(bar);
        }
    }
    const bars = waveformEl.children;
    for (let i = 0; i < bars.length && i < waveformData.length; i++) {
        bars[i].style.height = (waveformData[i] * 60 + 5) + 'px';
    }
}

function updateWaveformAmplitude(amplitude) {
    const waveformEl = document.getElementById('waveform');
    const bars = waveformEl.children;
    if (bars.length === 0) return;
    for (let i = 0; i < bars.length; i++) {
        const wave = Math.sin((i / bars.length) * Math.PI * 2 + Date.now() / 200);
        const height = Math.abs(wave) * amplitude * 60 + 5;
        bars[i].style.height = height + 'px';
    }
}

// ─── Chat bubble (animation-overlay) ─────────────────────────────────────────

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

let chatBubbleTimeout = null;
function showChatBubble(text, kind) {
    const bubbleEl = document.getElementById('chat-bubble');
    const textEl = document.getElementById('chat-text');
    textEl.textContent = text;
    bubbleEl.style.display = 'block';

    if (chatBubbleTimeout) clearTimeout(chatBubbleTimeout);
    if (kind !== 'partial') {
        chatBubbleTimeout = setTimeout(() => {
            bubbleEl.style.display = 'none';
        }, 8000);
    }
}

// ─── Memory panel ────────────────────────────────────────────────────────────

function updateMemoryPanel(memories) {
    const listEl = document.getElementById('memory-list');
    listEl.innerHTML = '';

    if (!memories || memories.length === 0) {
        const t = (typeof I18N !== 'undefined') ? I18N.t.bind(I18N) : (k) => k;
        const emptyItem = document.createElement('div');
        emptyItem.className = 'memory-item';
        emptyItem.innerHTML = '<div style="color: #888; font-style: italic;">' + t('right.no_memories') + '</div>';
        listEl.appendChild(emptyItem);
        return;
    }

    memories.forEach((memory) => {
        const item = document.createElement('div');
        item.className = 'memory-item';
        const content = memory.content || 'Memory content unavailable';
        const importance = memory.importance || 0;
        const similarity = memory.similarity_score || 0;
        const timestamp = memory.timestamp ? new Date(memory.timestamp).toLocaleString() : 'Unknown time';
        const contextTags = memory.context_tags || [];
        const emotionTags = memory.emotion_tags || [];

        item.innerHTML =
            '<div style="display: flex; justify-content: space-between; margin-bottom: 5px;">' +
            '<span style="font-size: 12px; color: var(--accent);">Sim: ' + (similarity * 100).toFixed(0) + '%</span>' +
            '<span style="font-size: 12px; color: var(--secondary);">Imp: ' + (importance * 100).toFixed(0) + '%</span>' +
            '</div>' +
            '<div style="margin-bottom: 5px; line-height: 1.4; font-size: 13px;">' + (content.length > 150 ? content.substring(0, 150) + '...' : content) + '</div>' +
            '<div style="font-size: 11px; color: #888; margin-top: 5px;">' +
            (contextTags.length > 0 ? contextTags.join(', ') : '') +
            '</div>';

        item.addEventListener('click', () => {
            showMemoryModal(memory);
        });

        listEl.appendChild(item);
    });
}

// ─── Audio capture (AudioWorklet + PCM streaming) ────────────────────────────

async function startAudioInit() {
    const micBtn = document.getElementById('mic-button');

    try {
        console.log('Requesting microphone access...');
        mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                sampleRate: 16000,
            },
        });

        console.log('Microphone access granted');

        audioContext = new AudioContext({ sampleRate: 16000 });
        const source = audioContext.createMediaStreamSource(mediaStream);

        analyzerNode = audioContext.createAnalyser();
        analyzerNode.fftSize = 256;
        source.connect(analyzerNode);

        await audioContext.audioWorklet.addModule('/static/audio-worklet-processor.js');
        workletNode = new AudioWorkletNode(audioContext, 'pcm-capture-processor');

        workletNode.port.onmessage = (e) => {
            if (ws && ws.readyState === WebSocket.OPEN && isListening) {
                ws.send(e.data);
            }
        };

        source.connect(workletNode);

        const debugMic = document.getElementById('debug-mic');
        if (debugMic) {
            debugMic.textContent = 'Connected';
            debugMic.style.color = '#00FF00';
        }

        micInitialized = true;
        startAmplitudeMonitoring(analyzerNode);

        const t = (typeof I18N !== 'undefined') ? I18N.t.bind(I18N) : (k) => k;
        showToast(t('toast.mic_connected'), 2500);

        // Update mic button state
        if (micBtn) {
            micBtn.classList.remove('disabled');
            micBtn.title = t('mic.click_to_speak');
        }
    } catch (error) {
        console.error('Failed to access microphone:', error);

        const t = (typeof I18N !== 'undefined') ? I18N.t.bind(I18N) : (k) => k;
        let errorMsg = t('toast.mic_error') + ': ';
        if (error.name === 'NotAllowedError') {
            errorMsg = t('toast.mic_denied');
        } else if (error.name === 'NotFoundError') {
            errorMsg += 'No microphone detected.';
        } else {
            errorMsg += error.name + ': ' + error.message;
        }
        showToast(errorMsg, 6000, true);
    }
}

function startAmplitudeMonitoring(analyzer) {
    const bufferLength = analyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function update() {
        if (!audioContext) return;
        analyzer.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / bufferLength;
        const normalizedAmplitude = average / 255.0;
        updateWaveformAmplitude(normalizedAmplitude);
        updateDebugPanel(normalizedAmplitude);
        requestAnimationFrame(update);
    }
    update();
}

function updateDebugPanel(amplitude) {
    const debugStatus = document.getElementById('debug-status');
    const debugAmplitude = document.getElementById('debug-amplitude');
    const debugMeter = document.getElementById('debug-meter');

    if (debugStatus) {
        debugStatus.textContent = isListening ? 'Listening' : 'Ready';
        debugStatus.style.color = isListening ? '#00FF00' : '#FFA500';
    }
    if (debugAmplitude) {
        debugAmplitude.textContent = (amplitude * 100).toFixed(1) + '%';
        debugAmplitude.style.color = amplitude > 0.1 ? '#00FF00' : '#888';
    }
    if (debugMeter) {
        debugMeter.style.width = (amplitude * 100) + '%';
    }
}

// ─── Push-to-talk mic button ─────────────────────────────────────────────────

function toggleMic() {
    const micBtn = document.getElementById('mic-button');
    const t = (typeof I18N !== 'undefined') ? I18N.t.bind(I18N) : (k) => k;

    // First click: initialize mic
    if (!micInitialized) {
        startAudioInit();
        return;
    }

    if (!audioContext) {
        showToast(t('mic.init_required'), 3000, true);
        return;
    }

    if (!isListening) {
        // Start listening
        ws.send(JSON.stringify({ type: 'voice_start', language: 'auto' }));
        isListening = true;

        if (micBtn) {
            micBtn.classList.add('recording');
            micBtn.title = t('mic.recording');
        }

        const characterEl = document.getElementById('character');
        if (characterEl) {
            characterEl.classList.add('manual-listening', 'listening');
        }
    } else {
        // Stop listening
        ws.send(JSON.stringify({ type: 'voice_stop' }));
        isListening = false;

        if (micBtn) {
            micBtn.classList.remove('recording');
            micBtn.title = t('mic.click_to_speak');
        }

        const characterEl = document.getElementById('character');
        if (characterEl) {
            characterEl.classList.remove('manual-listening', 'listening');
        }
    }
}

// ─── Text input fallback ─────────────────────────────────────────────────────

function sendTextInput() {
    const input = document.getElementById('chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(JSON.stringify({ type: 'text_input', text: text }));
    appendMessage(text, 'user');
    input.value = '';
}

// ─── Sidebar toggle ──────────────────────────────────────────────────────────

function toggleSidebar() {
    const app = document.getElementById('app');
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    if (!app || !sidebar || !toggleBtn) return;

    const isCollapsed = sidebar.classList.toggle('collapsed');
    app.classList.toggle('sidebar-collapsed', isCollapsed);
    toggleBtn.classList.toggle('collapsed', isCollapsed);
    toggleBtn.innerHTML = isCollapsed ? '&#x25B6;' : '&#x25C0;';
}

// ─── Live2D character init ───────────────────────────────────────────────────

async function initCharacter() {
    try {
        console.log('Initializing Live2D character...');
        window.live2dViewer = await window.initLive2DViewer();
        console.log('Live2D character initialized:', window.live2dViewer ? 'success' : 'failed');
    } catch (error) {
        console.error('Live2D initialization error:', error);
    }
}

// ─── Browser support check ───────────────────────────────────────────────────

async function checkBrowserSupport() {
    const isSecure = window.location.protocol === 'https:' ||
        window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1';

    if (!isSecure) {
        console.warn('Not running on HTTPS or localhost. Microphone access may be restricted.');
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        const t = (typeof I18N !== 'undefined') ? I18N.t.bind(I18N) : (k) => k;
        showToast(t('toast.no_mic_support'), 6000, true);
        return false;
    }

    try {
        if (navigator.permissions && navigator.permissions.query) {
            const result = await navigator.permissions.query({ name: 'microphone' });
            if (result.state === 'denied') {
                const t = (typeof I18N !== 'undefined') ? I18N.t.bind(I18N) : (k) => k;
                showToast(t('toast.mic_denied'), 6000, true);
                return false;
            }
        }
    } catch (e) {
        // Permission API not supported
    }

    return true;
}

// ─── Initialization ──────────────────────────────────────────────────────────

async function init() {
    const supported = await checkBrowserSupport();
    if (!supported) return;

    initWebSocket();
    await initCharacter();
    updateWaveform(new Array(32).fill(0));

    // Apply i18n
    if (typeof I18N !== 'undefined') {
        I18N.applyAll();
    }

    console.log('BMAM Voice UI initialized');
}

// ─── Event listeners ─────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Mic button (push-to-talk)
    const micBtn = document.getElementById('mic-button');
    if (micBtn) {
        micBtn.addEventListener('click', toggleMic);
    }

    // Text input
    const chatInput = document.getElementById('chat-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendTextInput();
            }
        });
    }

    const sendBtn = document.getElementById('chat-send-btn');
    if (sendBtn) {
        sendBtn.addEventListener('click', sendTextInput);
    }

    // Sidebar toggle
    const sidebarToggle = document.getElementById('sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }

    // Language toggle
    const langToggle = document.getElementById('lang-toggle');
    if (langToggle) {
        langToggle.addEventListener('click', () => {
            if (typeof I18N !== 'undefined') {
                I18N.toggle();
                // Refresh brain panel labels too
                if (typeof refreshBrainLabels === 'function') {
                    window.refreshBrainLabels();
                }
                langToggle.textContent = I18N.getLang() === 'en' ? 'EN / ZH' : 'ZH / EN';
            }
        });
    }

    // Settings (debug toggle)
    const settingsBtn = document.getElementById('settings-btn');
    if (settingsBtn) {
        settingsBtn.addEventListener('click', () => {
            const debugPanel = document.getElementById('audio-debug');
            if (debugPanel) {
                debugPanel.style.display = debugPanel.style.display === 'none' ? 'block' : 'none';
            }
        });
    }

    // Clear
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            const chatHistory = document.getElementById('chat-history');
            if (chatHistory) chatHistory.innerHTML = '';
            const memoryList = document.getElementById('memory-list');
            if (memoryList) memoryList.innerHTML = '';
            const chatBubble = document.getElementById('chat-bubble');
            if (chatBubble) chatBubble.style.display = 'none';
        });
    }
});

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
