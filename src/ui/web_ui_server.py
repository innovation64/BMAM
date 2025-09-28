"""
Web Server for Voice Anime UI
Provides WebSocket and REST API for the voice-driven anime interface
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path

# Web framework dependencies
try:
    from aiohttp import web
    from aiohttp import WSMsgType
    import aiohttp_cors
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False
    print("Web dependencies not installed. Install with: pip install aiohttp aiohttp-cors")

from .voice_anime_ui import VoiceAnimeUI, CharacterState, EmotionType
from .voice_interface import VoiceInterface, VoiceCommandProcessor


logger = logging.getLogger(__name__)


class WebUIServer:
    """Web server for the voice anime UI"""

    def __init__(self, bmam_coordinator, host: str = "0.0.0.0", port: int = 8080):
        self.coordinator = bmam_coordinator
        self.host = host
        self.port = port

        # UI components
        self.ui = VoiceAnimeUI(bmam_coordinator)
        self.voice = VoiceInterface()
        self.command_processor = VoiceCommandProcessor()

        # WebSocket connections
        self.websockets: Set[web.WebSocketResponse] = set()

        # Server state
        self.app = None
        self.runner = None
        self.site = None

    def setup_routes(self, app: web.Application):
        """Set up web routes"""
        # Static files
        app.router.add_get('/', self.index_handler)
        app.router.add_static('/static', Path(__file__).parent / 'static')

        # API endpoints
        app.router.add_get('/api/status', self.status_handler)
        app.router.add_post('/api/process', self.process_handler)
        app.router.add_post('/api/memory/edit', self.edit_memory_handler)
        app.router.add_get('/api/layout', self.layout_handler)

        # WebSocket
        app.router.add_get('/ws', self.websocket_handler)

        # CORS setup
        if WEB_AVAILABLE:
            cors = aiohttp_cors.setup(app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            for route in list(app.router.routes()):
                cors.add(route)

    async def index_handler(self, request):
        """Serve the main HTML page"""
        html_path = Path(__file__).parent / 'static' / 'index.html'

        if not html_path.exists():
            # Generate default HTML if not exists
            html_content = self.generate_default_html()
            html_path.parent.mkdir(parents=True, exist_ok=True)
            html_path.write_text(html_content)

        return web.FileResponse(html_path)

    async def status_handler(self, request):
        """Get system status"""
        status = {
            'bmam_status': self.coordinator.get_system_status(),
            'ui_state': {
                'character_state': self.ui.character.current_state.value,
                'character_emotion': self.ui.character.current_emotion.value,
                'is_listening': self.ui.is_listening,
                'is_processing': self.ui.is_processing,
                'memory_count': len(self.ui.memory_panel.memory_conditions)
            },
            'websocket_connections': len(self.websockets)
        }
        return web.json_response(status)

    async def process_handler(self, request):
        """Process text input"""
        try:
            data = await request.json()
            text = data.get('text', '')

            # Check for voice command
            command_result = await self.command_processor.process_command(text, self.ui)

            if command_result['is_command']:
                return web.json_response(command_result)

            # Process through BMAM
            response = await self.ui.process_voice_input(text.encode())

            # Broadcast to WebSocket clients
            await self.broadcast_update({
                'type': 'response',
                'text': response,
                'timestamp': datetime.now().isoformat()
            })

            return web.json_response({
                'success': True,
                'response': response
            })

        except Exception as e:
            logger.error(f"Process error: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def edit_memory_handler(self, request):
        """Handle memory editing"""
        try:
            data = await request.json()
            index = data.get('index', 0)
            content = data.get('content', '')
            importance = data.get('importance', 0.5)

            success = self.ui.handle_memory_edit(index, content, importance)

            # Broadcast update
            await self.broadcast_update({
                'type': 'memory_update',
                'memories': [
                    {
                        'id': m.id,
                        'content': m.content,
                        'importance': m.importance,
                        'emotion_tags': m.emotion_tags,
                        'is_active': m.is_active
                    }
                    for m in self.ui.memory_panel.get_visible_memories()
                ]
            })

            return web.json_response({
                'success': success
            })

        except Exception as e:
            logger.error(f"Memory edit error: {e}")
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def layout_handler(self, request):
        """Get UI layout specification"""
        layout_spec = self.ui.get_layout_spec()
        return web.json_response(layout_spec)

    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)

        try:
            # Send initial state
            await ws.send_json({
                'type': 'connected',
                'layout': self.ui.get_layout_spec()
            })

            # Start animation loop for this client
            animation_task = asyncio.create_task(
                self.animation_loop(ws)
            )

            # Handle incoming messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.handle_ws_message(ws, data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f'WebSocket error: {ws.exception()}')

        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            animation_task.cancel()
            self.websockets.discard(ws)

        return ws

    async def handle_ws_message(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Handle WebSocket message from client"""
        msg_type = data.get('type')

        if msg_type == 'start_listening':
            # Start voice listening
            asyncio.create_task(self.handle_voice_input(ws))

        elif msg_type == 'stop_listening':
            self.voice.stop_listening()

        elif msg_type == 'text_input':
            text = data.get('text', '')
            response = await self.ui.process_voice_input(text.encode())
            await ws.send_json({
                'type': 'response',
                'text': response
            })

    async def handle_voice_input(self, ws: web.WebSocketResponse):
        """Handle voice input from client"""
        if not self.voice.start_listening():
            await ws.send_json({
                'type': 'error',
                'message': 'Failed to start voice input'
            })
            return

        # Set up amplitude callback
        async def send_amplitude(amp: float):
            await ws.send_json({
                'type': 'amplitude',
                'value': amp
            })

        self.voice.on_amplitude_update = lambda amp: asyncio.create_task(send_amplitude(amp))

        # Listen for speech
        audio_data, _ = await self.voice.listen_for_speech()

        # Transcribe
        text = await self.voice.stt_engine.transcribe(audio_data)

        # Send transcription
        await ws.send_json({
            'type': 'transcription',
            'text': text
        })

        # Process through BMAM
        response = await self.ui.process_voice_input(audio_data)

        # Send response
        await ws.send_json({
            'type': 'response',
            'text': response
        })

        # Speak response
        await self.voice.speak(response, emotion="neutral")

    async def animation_loop(self, ws: web.WebSocketResponse):
        """Send animation updates to client"""
        try:
            while ws in self.websockets:
                # Update UI state
                ui_state = self.ui.update()

                # Send to client
                await ws.send_json({
                    'type': 'animation_update',
                    'character': {
                        'state': ui_state['character'].state.value,
                        'emotion': ui_state['character'].emotion.value,
                        'eye_openness': ui_state['character'].eye_openness,
                        'mouth_openness': ui_state['character'].mouth_openness,
                        'head_tilt': ui_state['character'].head_tilt,
                        'body_bounce': ui_state['character'].body_bounce,
                        'arm_position': ui_state['character'].arm_position
                    },
                    'waveform': ui_state['waveform'],
                    'chat_bubble': ui_state['chat_bubble']
                })

                # 30 FPS
                await asyncio.sleep(1/30)

        except Exception as e:
            logger.error(f"Animation loop error: {e}")

    async def broadcast_update(self, data: Dict[str, Any]):
        """Broadcast update to all WebSocket clients"""
        if self.websockets:
            await asyncio.gather(
                *[ws.send_json(data) for ws in self.websockets],
                return_exceptions=True
            )

    def generate_default_html(self) -> str:
        """Generate default HTML page"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BMAM Voice Anime UI - Yaoguang (摇光明明)</title>
    <link rel="stylesheet" href="/static/character.css">

    <!-- Live2D Dependencies (from GitHub repo) -->
    <script src="https://unpkg.com/core-js-bundle@3.6.1/minified.js"></script>
    <script src="/static/js/lib/live2dcubismcore.min.js"></script>
    <script src="/static/js/live2dv3.js"></script>
    <script src="/static/live2d-viewer-v3.js"></script>

    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
            color: #fff;
            height: 100vh;
            overflow: hidden;
        }

        #app {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }

        #character-container {
            position: absolute;
            left: 35%;
            top: 50%;
            transform: translate(-50%, -50%);
            width: 500px;
            height: 600px;
            z-index: 10;
        }

        #live2d-canvas {
            width: 100%;
            height: 100%;
            border-radius: 20px;
            background: transparent;
        }

        .character-overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }

        #memory-panel {
            position: absolute;
            right: 5%;
            top: 10%;
            width: 35%;
            height: 80%;
            background: rgba(30, 30, 50, 0.85);
            border-radius: 20px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(107, 70, 193, 0.3);
            overflow-y: auto;
        }

        .memory-item {
            background: rgba(107, 70, 193, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 3px solid #6B46C1;
            transition: all 0.3s ease;
        }

        .memory-item:hover {
            background: rgba(107, 70, 193, 0.2);
            transform: translateX(5px);
        }

        #chat-bubble {
            position: absolute;
            left: 35%;
            top: 25%;
            transform: translateX(-50%);
            background: rgba(255, 255, 255, 0.95);
            color: #1A1A2E;
            padding: 15px 20px;
            border-radius: 20px;
            max-width: 300px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
            display: none;
        }

        #waveform {
            position: absolute;
            left: 35%;
            bottom: 15%;
            transform: translateX(-50%);
            width: 300px;
            height: 80px;
            display: flex;
            align-items: center;
            justify-content: space-around;
        }

        .wave-bar {
            width: 6px;
            background: linear-gradient(to top, #00D9FF, #6B46C1);
            border-radius: 3px;
            transition: height 0.1s ease;
        }

        #control-panel {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
        }

        button {
            padding: 10px 20px;
            background: linear-gradient(135deg, #6B46C1, #FF6B9D);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(107, 70, 193, 0.4);
        }

        button:active {
            transform: translateY(0);
        }

        .listening {
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div id="app">
        <div id="character-container">
            <canvas id="live2d-canvas"></canvas>

            <!-- Fallback character (hidden by default) -->
            <div id="character" class="mascot-avatar" aria-label="看板娘风格的摇光明明" style="display: none;">
                <div class="mascot-base-glow"></div>

                <div class="mascot-character">
                    <div class="mascot-hair-back"></div>

                    <div class="mascot-head">
                        <div class="mascot-hair-top"></div>
                        <div class="mascot-face">
                            <div class="mascot-eye left">
                                <span class="mascot-eye-highlight"></span>
                                <span class="mascot-eye-highlight mini"></span>
                            </div>
                            <div class="mascot-eye right">
                                <span class="mascot-eye-highlight"></span>
                                <span class="mascot-eye-highlight mini"></span>
                            </div>
                            <div class="mascot-mouth"></div>
                            <div class="mascot-blush left"></div>
                            <div class="mascot-blush right"></div>
                        </div>
                        <div class="mascot-hair-side left"></div>
                        <div class="mascot-hair-side right"></div>
                        <div class="mascot-hair-tail left"></div>
                        <div class="mascot-hair-tail right"></div>
                    </div>

                    <div class="mascot-body">
                        <div class="mascot-collar"></div>
                        <div class="mascot-ribbon">
                            <div class="mascot-ribbon-left"></div>
                            <div class="mascot-ribbon-right"></div>
                            <div class="mascot-ribbon-center"></div>
                        </div>
                        <div class="mascot-torso"></div>
                        <div class="mascot-skirt"></div>
                    </div>

                    <div class="mascot-arm left">
                        <div class="mascot-sleeve"></div>
                        <div class="mascot-hand"></div>
                    </div>
                    <div class="mascot-arm right">
                        <div class="mascot-sleeve"></div>
                        <div class="mascot-hand"></div>
                    </div>

                    <div class="mascot-leg left">
                        <div class="mascot-sock"></div>
                        <div class="mascot-shoe"></div>
                    </div>
                    <div class="mascot-leg right">
                        <div class="mascot-sock"></div>
                        <div class="mascot-shoe"></div>
                    </div>
                </div>

                <div class="mascot-board">
                    <div class="board-frame">
                        <div class="board-header">BMAM 看板</div>
                        <div class="board-body">
                            <div class="board-line long"></div>
                            <div class="board-line"></div>
                            <div class="board-line short"></div>
                        </div>
                    </div>
                    <div class="board-shadow"></div>
                </div>

                <div class="mascot-sparkle sparkle-1"></div>
                <div class="mascot-sparkle sparkle-2"></div>
                <div class="mascot-sparkle sparkle-3"></div>
                <div class="mascot-shadow"></div>
            </div>

            <div class="character-overlay">
                <div class="emotion-particles"></div>
                <div class="character-nametag">摇光明明 (Yaoguang)</div>
            </div>
        </div>

        <div id="memory-panel">
            <h3 style="margin-bottom: 20px; color: #00D9FF;">BMAM Memory System</h3>
            <div style="font-size: 12px; color: #888; margin-bottom: 15px;">
                Retrieved Memories & Context
            </div>
            <div id="memory-list"></div>
        </div>

        <div id="chat-bubble">
            <span id="chat-text"></span>
        </div>

        <div id="waveform">
            <!-- Wave bars will be generated by JavaScript -->
        </div>

        <div id="control-panel">
            <button id="listen-btn">🎤 Start Listening</button>
            <button id="clear-btn">🗑️ Clear</button>
            <button id="settings-btn">⚙️ Settings</button>
        </div>
    </div>

    <script>
        // WebSocket connection
        let ws = null;
        let isListening = false;

        // Initialize WebSocket
        function initWebSocket() {
            ws = new WebSocket('ws://localhost:8080/ws');

            ws.onopen = () => {
                console.log('Connected to server');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };

            ws.onclose = () => {
                console.log('Disconnected from server');
                setTimeout(initWebSocket, 3000);
            };
        }

        // Handle server messages
        function handleMessage(data) {
            switch(data.type) {
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

        // Listen button handler
        document.getElementById('listen-btn').addEventListener('click', () => {
            if (!isListening) {
                ws.send(JSON.stringify({ type: 'start_listening' }));
                document.getElementById('listen-btn').textContent = '⏹️ Stop';
                const characterEl = document.getElementById('character');
                if (characterEl) {
                    characterEl.classList.add('manual-listening');
                    characterEl.classList.add('listening');
                }
                isListening = true;
            } else {
                ws.send(JSON.stringify({ type: 'stop_listening' }));
                document.getElementById('listen-btn').textContent = '🎤 Start Listening';
                const characterEl = document.getElementById('character');
                if (characterEl) {
                    characterEl.classList.remove('manual-listening');
                    characterEl.classList.remove('listening');
                }
                isListening = false;
            }
        });

        // Initialize Live2D character
        async function initCharacter() {
            try {
                console.log('Initializing Live2D character...');
                window.live2dViewer = await window.initLive2DViewer();
                console.log('Live2D character initialized:', window.live2dViewer ? 'success' : 'failed');
            } catch (error) {
                console.error('Live2D initialization error:', error);
            }
        }

        // Initialize everything
        async function init() {
            // Initialize WebSocket
            initWebSocket();

            // Initialize character
            await initCharacter();

            // Generate initial waveform
            updateWaveform(new Array(32).fill(0));

            console.log('BMAM Voice UI fully initialized');
        }

        // Start initialization when page loads
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    </script>
</body>
</html>'''

    async def start(self):
        """Start the web server"""
        if not WEB_AVAILABLE:
            logger.error("Web dependencies not available")
            return False

        try:
            self.app = web.Application()
            self.setup_routes(self.app)

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

            logger.info(f"Web UI server started at http://{self.host}:{self.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            return False

    async def stop(self):
        """Stop the web server"""
        # Close all WebSocket connections
        for ws in list(self.websockets):
            await ws.close()

        # Stop the site
        if self.site:
            await self.site.stop()

        # Cleanup runner
        if self.runner:
            await self.runner.cleanup()

        # Cleanup voice interface
        self.voice.cleanup()

        logger.info("Web UI server stopped")


async def main():
    """Run the web UI server"""
    from src.coordination.brain_coordinator import BrainInspiredCoordinator

    # Initialize BMAM coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()

    # Create and start web server
    server = WebUIServer(coordinator)

    if await server.start():
        print(f"Voice Anime UI running at http://localhost:8080")
        print("Press Ctrl+C to stop")

        try:
            # Keep server running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await server.stop()
            await coordinator.stop_system()


if __name__ == "__main__":
    asyncio.run(main())
