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
            # Notify client that listening started
            await ws.send_json({
                'type': 'listening_started',
                'message': 'Listening for audio...'
            })

        elif msg_type == 'stop_listening':
            self.voice.stop_listening()
            await ws.send_json({
                'type': 'listening_stopped',
                'message': 'Stopped listening'
            })

        elif msg_type == 'audio_data':
            # Handle audio data from browser
            await self.handle_browser_audio(ws, data)

        elif msg_type == 'text_input':
            text = data.get('text', '')
            response = await self.ui.process_voice_input(text.encode())
            await ws.send_json({
                'type': 'response',
                'text': response
            })

    async def handle_browser_audio(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Handle audio data received from browser"""
        import base64
        import tempfile
        import os

        try:
            # Get base64 audio data
            audio_base64 = data.get('audio', '')
            audio_format = data.get('format', 'webm')

            if not audio_base64:
                await ws.send_json({
                    'type': 'error',
                    'message': 'No audio data received'
                })
                return

            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_base64)
            logger.info(f"Received {len(audio_bytes)} bytes of {audio_format} audio")

            # Save to temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{audio_format}') as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name

            try:
                # Convert audio format if needed (webm to wav)
                wav_path = await self.convert_audio_to_wav(tmp_path)

                # Read WAV file
                with open(wav_path, 'rb') as f:
                    wav_audio = f.read()

                # Send to speech recognition
                await ws.send_json({
                    'type': 'processing',
                    'message': 'Transcribing audio...'
                })

                text = await self.voice.stt_engine.transcribe(wav_audio)

                if text:
                    logger.info(f"Transcribed text: {text}")

                    # Send transcription to client
                    await ws.send_json({
                        'type': 'transcription',
                        'text': text
                    })

                    # Process through BMAM
                    await ws.send_json({
                        'type': 'processing',
                        'message': 'Processing with BMAM...'
                    })

                    response = await self.ui.process_voice_input(text.encode())

                    # Send response
                    await ws.send_json({
                        'type': 'response',
                        'text': response
                    })
                else:
                    await ws.send_json({
                        'type': 'error',
                        'message': '无法识别语音，请再试一次'
                    })

                # Cleanup
                if os.path.exists(wav_path) and wav_path != tmp_path:
                    os.unlink(wav_path)

            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Error processing browser audio: {e}", exc_info=True)
            await ws.send_json({
                'type': 'error',
                'message': f'音频处理错误: {str(e)}'
            })

    async def convert_audio_to_wav(self, input_path: str) -> str:
        """Convert audio file to WAV format"""
        try:
            from pydub import AudioSegment

            # Detect format from extension
            ext = input_path.split('.')[-1].lower()

            # Load audio
            if ext == 'webm':
                audio = AudioSegment.from_file(input_path, format='webm')
            else:
                audio = AudioSegment.from_file(input_path)

            # Convert to mono, 16kHz (optimal for speech recognition)
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)
            audio = audio.set_sample_width(2)  # 16-bit

            # Export as WAV
            output_path = input_path.replace(f'.{ext}', '.wav')
            audio.export(output_path, format='wav')

            logger.info(f"Converted {input_path} to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            # If conversion fails, return original path
            return input_path

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
            <button id="init-audio-btn" style="background: linear-gradient(135deg, #FF6B9D, #FFC93D); font-weight: bold;">🎤 Initialize Microphone</button>
            <button id="listen-btn" style="display: none;">🎤 Start Listening</button>
            <button id="clear-btn">🗑️ Clear</button>
            <button id="settings-btn">⚙️ Settings</button>
        </div>

        <!-- Permission notice -->
        <div id="permission-notice" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(255, 107, 157, 0.95); color: white; padding: 30px; border-radius: 20px; text-align: center; max-width: 400px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); z-index: 1000;">
            <div style="font-size: 48px; margin-bottom: 15px;">🎤</div>
            <div style="font-size: 20px; font-weight: bold; margin-bottom: 10px;">麦克风权限需要</div>
            <div style="font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                BMAM Voice UI 需要访问您的麦克风来进行语音交互。<br>
                点击下方按钮后，浏览器会请求麦克风权限，请点击"允许"。
            </div>
            <button onclick="startAudioInit()" style="background: white; color: #FF6B9D; border: none; padding: 12px 30px; border-radius: 25px; font-size: 16px; font-weight: bold; cursor: pointer; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                🎤 启用麦克风
            </button>
            <div style="font-size: 12px; margin-top: 15px; opacity: 0.8;">
                如果浏览器没有弹出权限请求，请检查地址栏左侧的图标
            </div>
        </div>

        <!-- Audio Debug Panel -->
        <div id="audio-debug" style="position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.8); padding: 15px; border-radius: 10px; font-family: monospace; font-size: 12px; display: none;">
            <div style="color: #00D9FF; margin-bottom: 10px; font-weight: bold;">🎤 Audio Debug</div>
            <div>Status: <span id="debug-status">Idle</span></div>
            <div>Amplitude: <span id="debug-amplitude">0%</span></div>
            <div>Microphone: <span id="debug-mic">Not initialized</span></div>
            <div style="margin-top: 10px;">
                <div style="width: 200px; height: 10px; background: #333; border-radius: 5px; overflow: hidden;">
                    <div id="debug-meter" style="width: 0%; height: 100%; background: linear-gradient(to right, #00D9FF, #6B46C1); transition: width 0.1s;"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
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

        // Settings button handler
        document.getElementById('settings-btn').addEventListener('click', () => {
            const debugPanel = document.getElementById('audio-debug');
            if (debugPanel) {
                debugPanel.style.display = debugPanel.style.display === 'none' ? 'block' : 'none';
            }
        });

        // Clear button handler
        document.getElementById('clear-btn').addEventListener('click', () => {
            const memoryList = document.getElementById('memory-list');
            if (memoryList) {
                memoryList.innerHTML = '';
            }
            const chatBubble = document.getElementById('chat-bubble');
            if (chatBubble) {
                chatBubble.style.display = 'none';
            }
        });

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
