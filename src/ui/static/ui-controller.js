'use strict';

(function () {
    const RECONNECT_DELAY_MS = 3000;
    const WAVE_BAR_COUNT = 32;
    const MAX_AMPLITUDE = 1;
    const AMPLITUDE_DECAY = 0.9;

    let ws = null;
    let isListening = false;
    let currentAmplitude = 0;
    let liveWaveform = new Array(WAVE_BAR_COUNT).fill(0);
    window.currentlySpeaking = false;

    function initWebSocket() {
        try {
            ws = new WebSocket('ws://localhost:8080/ws');
        } catch (error) {
            console.error('WebSocket creation failed:', error);
            scheduleReconnect();
            return;
        }

        ws.onopen = () => {
            console.log('Connected to server');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleMessage(data);
            } catch (error) {
                console.error('Failed to parse server message:', error);
            }
        };

        ws.onerror = (event) => {
            console.error('WebSocket error:', event);
        };

        ws.onclose = () => {
            console.log('Disconnected from server');
            scheduleReconnect();
        };
    }

    function scheduleReconnect() {
        setTimeout(initWebSocket, RECONNECT_DELAY_MS);
    }

    function handleMessage(data) {
        switch (data.type) {
            case 'animation_update':
                if (data.character) {
                    updateCharacter(data.character);
                }
                if (Array.isArray(data.waveform)) {
                    updateWaveform(data.waveform);
                }
                if (data.chat_bubble) {
                    updateChatBubble(data.chat_bubble);
                }
                break;
            case 'memory_update':
                updateMemoryPanel(data.memories);
                break;
            case 'response':
                if (typeof data.text === 'string') {
                    showChatBubble(data.text);
                }
                break;
            case 'amplitude':
                if (typeof data.value === 'number') {
                    updateWaveformAmplitude(data.value);
                }
                break;
            default:
                console.debug('Unhandled message type:', data.type, data);
        }
    }

    function updateCharacter(character) {
        const characterEl = document.getElementById('character');

        if (window.live2dViewer && window.live2dViewer.isLoaded) {
            if (typeof window.live2dViewer.setState === 'function') {
                window.live2dViewer.setState(character.state);
            }

            if (character.state === 'speaking' && !window.currentlySpeaking) {
                if (typeof window.live2dViewer.startSpeaking === 'function') {
                    window.live2dViewer.startSpeaking();
                }
                window.currentlySpeaking = true;
            } else if (character.state !== 'speaking' && window.currentlySpeaking) {
                if (typeof window.live2dViewer.stopSpeaking === 'function') {
                    window.live2dViewer.stopSpeaking();
                }
                window.currentlySpeaking = false;
            }
        } else if (characterEl) {
            const state = character.state || 'idle';
            const emotion = character.emotion || 'neutral';

            const stateClasses = ['idle', 'listening', 'thinking', 'speaking', 'happy', 'excited', 'concerned', 'confused'];
            stateClasses.forEach((cls) => {
                characterEl.classList.remove(cls);
                characterEl.classList.remove(`state-${cls}`);
            });
            characterEl.classList.add(state);
            characterEl.classList.add(`state-${state}`);
            characterEl.dataset.state = state;

            const emotionClasses = ['neutral', 'joy', 'surprise', 'thinking', 'sad', 'concerned', 'confused'];
            emotionClasses.forEach((cls) => characterEl.classList.remove(`emotion-${cls}`));
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
            eyes.forEach((eye) => {
                eye.classList.toggle('eye-happy', emotion === 'joy');
                eye.classList.toggle('eye-surprise', emotion === 'surprise');
                eye.classList.toggle('eye-thinking', emotion === 'thinking');
            });
        }

        if (character.emotion === 'joy') {
            addEmotionParticles('heart');
        } else if (character.emotion === 'surprise') {
            addEmotionParticles('star');
        } else if (character.emotion === 'thinking') {
            addEmotionParticles('question');
        }
    }

    function addEmotionParticles(type) {
        const particlesEl = document.querySelector('.emotion-particles');
        if (!particlesEl) {
            return;
        }

        particlesEl.innerHTML = '';

        for (let i = 0; i < 3; i += 1) {
            const particle = document.createElement('div');
            particle.className = `particle ${type}`;
            particle.style.left = `${20 + i * 30}px`;
            particle.style.animationDelay = `${i * 0.5}s`;
            particlesEl.appendChild(particle);
        }

        setTimeout(() => {
            particlesEl.innerHTML = '';
        }, 3000);
    }

    function ensureWaveformBars() {
        const waveformEl = document.getElementById('waveform');
        if (!waveformEl) {
            return null;
        }

        if (waveformEl.children.length === 0) {
            for (let i = 0; i < WAVE_BAR_COUNT; i += 1) {
                const bar = document.createElement('div');
                bar.className = 'wave-bar';
                waveformEl.appendChild(bar);
            }
        }

        return waveformEl.children;
    }

    function updateWaveform(waveformData) {
        const bars = ensureWaveformBars();
        if (!bars) {
            return;
        }

        const len = Math.min(bars.length, waveformData.length);
        for (let i = 0; i < len; i += 1) {
            liveWaveform[i] = waveformData[i];
            bars[i].style.height = `${waveformData[i] * 60 + 5}px`;
        }
    }

    function updateWaveformAmplitude(value) {
        const clamped = Math.max(0, Math.min(MAX_AMPLITUDE, value));
        currentAmplitude = Math.max(currentAmplitude * AMPLITUDE_DECAY, clamped);
        const bars = ensureWaveformBars();
        if (!bars) {
            return;
        }

        for (let i = 0; i < bars.length; i += 1) {
            const base = liveWaveform[i] || 0;
            const amplitudeBoost = currentAmplitude * (1 - i / bars.length);
            const height = (base + amplitudeBoost) * 60 + 5;
            bars[i].style.height = `${height}`;
        }

        if (window.live2dViewer && typeof window.live2dViewer.setMouthOpen === 'function') {
            window.live2dViewer.setMouthOpen(currentAmplitude);
        }
    }

    function updateChatBubble(chatBubble) {
        const bubbleEl = document.getElementById('chat-bubble');
        const textEl = document.getElementById('chat-text');

        if (!bubbleEl || !textEl) {
            return;
        }

        if (chatBubble.visible) {
            bubbleEl.style.display = 'block';
            bubbleEl.style.opacity = typeof chatBubble.alpha === 'number' ? chatBubble.alpha : 1;
            textEl.textContent = chatBubble.text || '';
        } else {
            bubbleEl.style.display = 'none';
        }
    }

    function showChatBubble(text) {
        const bubbleEl = document.getElementById('chat-bubble');
        const textEl = document.getElementById('chat-text');

        if (!bubbleEl || !textEl) {
            return;
        }

        textEl.textContent = text;
        bubbleEl.style.display = 'block';

        setTimeout(() => {
            bubbleEl.style.display = 'none';
        }, 5000);
    }

    function updateMemoryPanel(memories) {
        const listEl = document.getElementById('memory-list');
        if (!listEl) {
            return;
        }

        listEl.innerHTML = '';

        if (!Array.isArray(memories) || memories.length === 0) {
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

        memories.forEach((memory) => {
            const item = document.createElement('div');
            item.className = 'memory-item';

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
                        ${content.length > 200 ? `${content.substring(0, 200)}...` : content}
                    </div>
                    <div style="font-size: 11px; color: #888; margin-top: 5px;">
                        <div>🏷️ Context: ${contextTags.join(', ') || 'None'}</div>
                        ${emotionTags.length > 0 ? `<div>💭 Emotions: ${emotionTags.join(', ')}</div>` : ''}
                        <div>⏰ ${timestamp}</div>
                    </div>
                `;

            item.addEventListener('click', () => {
                console.log('BMAM Memory Details:', memory);
                showMemoryDetails(memory);
            });

            listEl.appendChild(item);
        });
    }

    function showMemoryDetails(memory) {
        const details = `BMAM Memory Details:\n───────────────────\n\n` +
            `Content: ${memory.content || 'N/A'}\n` +
            `ID: ${memory.id || 'N/A'}\n` +
            `Importance: ${((memory.importance || 0) * 100).toFixed(1)}%\n` +
            `Similarity: ${((memory.similarity_score || 0) * 100).toFixed(1)}%\n` +
            `Timestamp: ${memory.timestamp || 'N/A'}\n\n` +
            `Context Tags: ${(memory.context_tags || []).join(', ') || 'None'}\n` +
            `Emotion Tags: ${(memory.emotion_tags || []).join(', ') || 'None'}\n\n` +
            `Metadata: ${JSON.stringify(memory.metadata || {}, null, 2)}`;

        alert(details);
    }

    function handleListenButton() {
        const listenBtn = document.getElementById('listen-btn');
        if (!listenBtn) {
            return;
        }

        listenBtn.addEventListener('click', () => {
            if (!ws || ws.readyState !== WebSocket.OPEN) {
                console.warn('WebSocket not ready; attempting reconnection.');
                initWebSocket();
                return;
            }

            if (!isListening) {
                ws.send(JSON.stringify({ type: 'start_listening' }));
                listenBtn.textContent = '⏹️ Stop';
                const characterEl = document.getElementById('character');
                if (characterEl) {
                    characterEl.classList.add('manual-listening');
                    characterEl.classList.add('listening');
                }
                isListening = true;
            } else {
                ws.send(JSON.stringify({ type: 'stop_listening' }));
                listenBtn.textContent = '🎤 Start Listening';
                const characterEl = document.getElementById('character');
                if (characterEl) {
                    characterEl.classList.remove('manual-listening');
                    characterEl.classList.remove('listening');
                }
                isListening = false;
            }
        });
    }

    function attachControls() {
        handleListenButton();

        const clearBtn = document.getElementById('clear-btn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                const listEl = document.getElementById('memory-list');
                if (listEl) {
                    listEl.innerHTML = '';
                }
            });
        }
    }

    async function initCharacter() {
        try {
            console.log('Initializing Live2D character...');
            window.live2dViewer = await window.initLive2DViewer();
            console.log('Live2D character initialized:', window.live2dViewer ? 'success' : 'failed');
        } catch (error) {
            console.error('Live2D initialization error:', error);
        }
    }

    async function init() {
        initWebSocket();
        attachControls();
        await initCharacter();
        updateWaveform(new Array(WAVE_BAR_COUNT).fill(0));
        console.log('BMAM Voice UI fully initialized');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
