"""
Web UI Server WebSocket — multimedia mode with voice streaming support.
Handles animation loop, text input, and binary audio frames.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from aiohttp import web, WSMsgType

logger = logging.getLogger(__name__)


class WebSocketMixin:
    """WebSocket connection handler with animation loop + voice streaming."""

    async def websocket_handler(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)

        voice_session = None

        try:
            await ws.send_json({
                'type': 'connected',
                'layout': self.ui.get_layout_spec(),
                'voice_available': getattr(self, '_voice_service', None) is not None,
            })

            # Start animation loop for this client
            animation_task = asyncio.create_task(self.animation_loop(ws))

            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_type = data.get('type')

                    if msg_type == 'voice_start':
                        voice_svc = getattr(self, '_voice_service', None)
                        voice_session = await self._handle_voice_start_mm(
                            ws, data, voice_svc
                        )
                    elif msg_type == 'voice_stop':
                        voice_svc = getattr(self, '_voice_service', None)
                        if voice_session and voice_svc:
                            await self._handle_voice_stop_mm(
                                ws, voice_svc, voice_session
                            )
                    elif msg_type == 'voice_barge_in':
                        if voice_session:
                            voice_session.cancel_tts()
                            await ws.send_json({
                                'type': 'voice_tts_end',
                                'reason': 'barge_in',
                            })
                    else:
                        await self.handle_ws_message(ws, data)

                elif msg.type == WSMsgType.BINARY:
                    voice_svc = getattr(self, '_voice_service', None)
                    if voice_session and voice_svc:
                        await self._handle_audio_chunk_mm(
                            ws, msg.data, voice_svc, voice_session
                        )

                elif msg.type == WSMsgType.ERROR:
                    logger.error('WebSocket error: %s', ws.exception())

        except Exception as e:
            logger.error("WebSocket handler error: %s", e)
        finally:
            animation_task.cancel()
            self.websockets.discard(ws)

        return ws

    async def handle_ws_message(
        self, ws: web.WebSocketResponse, data: Dict[str, Any]
    ):
        """Handle non-voice WebSocket messages."""
        msg_type = data.get('type')

        if msg_type == 'start_listening':
            await ws.send_json({
                'type': 'listening_started',
                'message': 'Listening for audio...',
            })

        elif msg_type == 'stop_listening':
            self.voice.stop_listening()
            await ws.send_json({
                'type': 'listening_stopped',
                'message': 'Stopped listening',
            })

        elif msg_type == 'audio_data':
            await self.handle_browser_audio(ws, data)

        elif msg_type == 'text_input':
            text = data.get('text', '')
            if hasattr(self.ui, 'process_text_input_full'):
                result = await self.ui.process_text_input_full(text)
                await ws.send_json({
                    'type': 'response',
                    'text': result['response'],
                })
                if result.get('brain_activity'):
                    await ws.send_json({
                        'type': 'brain_activity',
                        'regions': result['brain_activity']['regions'],
                        'reasoning_chain': result['brain_activity']['reasoning_chain'],
                    })
            else:
                response = await self.ui.process_text_input(text)
                await ws.send_json({
                    'type': 'response',
                    'text': response,
                })

    # ─── Voice helpers (multimedia mode) ──────────────────────────────────

    async def _handle_voice_start_mm(self, ws, data, voice_svc):
        if voice_svc is None:
            await ws.send_json({
                'type': 'error',
                'message': 'Voice service not available',
            })
            return None

        from src.services.voice_session import VoiceSession

        session = VoiceSession(
            session_id=str(uuid.uuid4()),
            language=data.get('language', 'auto'),
        )
        await ws.send_json({
            'type': 'voice_start_ack',
            'session_id': session.session_id,
        })
        return session

    async def _handle_audio_chunk_mm(self, ws, chunk, voice_svc, session):
        from src.services.voice_service import VoiceEventType

        async for event in voice_svc.process_audio_chunk(chunk, session):
            if event.type == VoiceEventType.VAD:
                await ws.send_json({'type': 'voice_vad', **event.data})
            elif event.type == VoiceEventType.PARTIAL:
                await ws.send_json({'type': 'voice_partial', **event.data})
            elif event.type == VoiceEventType.TRANSCRIPT:
                await ws.send_json({'type': 'voice_transcript', **event.data})
                # Process through brain + TTS
                await self._process_transcript_mm(
                    ws, event.data['text'], voice_svc, session
                )

    async def _handle_voice_stop_mm(self, ws, voice_svc, session):
        from src.services.voice_service import VoiceEventType

        async for event in voice_svc.force_final_stt(session):
            if event.type == VoiceEventType.VAD:
                await ws.send_json({'type': 'voice_vad', **event.data})
            elif event.type == VoiceEventType.TRANSCRIPT:
                await ws.send_json({'type': 'voice_transcript', **event.data})
                await self._process_transcript_mm(
                    ws, event.data['text'], voice_svc, session
                )

    async def _process_transcript_mm(self, ws, text, voice_svc, session):
        """Process transcript through the UI's voice pipeline, then stream TTS."""
        if not text.strip():
            return

        from src.services.voice_session import SessionState
        from src.services.voice_service import VoiceEventType

        session.state = SessionState.PROCESSING

        try:
            brain_activity = None
            if hasattr(self.ui, 'process_text_input_full'):
                result = await self.ui.process_text_input_full(text)
                response = result['response']
                brain_activity = result.get('brain_activity')
            else:
                response = await self.ui.process_text_input(text)

            await ws.send_json({
                'type': 'response',
                'text': response,
            })

            if brain_activity:
                await ws.send_json({
                    'type': 'brain_activity',
                    'regions': brain_activity['regions'],
                    'reasoning_chain': brain_activity['reasoning_chain'],
                })

            # Stream TTS
            async def _tts_stream():
                async for event in voice_svc.synthesize_streaming(
                    response, session
                ):
                    if session.tts_cancelled:
                        break
                    if event.type == VoiceEventType.TTS_START:
                        await ws.send_json({
                            'type': 'voice_tts_start', **event.data
                        })
                    elif event.type == VoiceEventType.TTS_AUDIO:
                        await ws.send_bytes(event.audio)
                    elif event.type == VoiceEventType.TTS_END:
                        await ws.send_json({
                            'type': 'voice_tts_end', **(event.data or {})
                        })

            tts_task = asyncio.create_task(_tts_stream())
            session.start_tts(tts_task)
            await tts_task

        except Exception as e:
            logger.error("Voice transcript processing error: %s", e)
            await ws.send_json({
                'type': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
        finally:
            session.finish_tts()
