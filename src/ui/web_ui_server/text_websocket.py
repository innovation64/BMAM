"""
Text Web UI Server WebSocket — text + voice protocol.
Handles both JSON text frames and binary audio frames (voice streaming).
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from aiohttp import web, WSMsgType

logger = logging.getLogger(__name__)


class TextWebSocketMixin:
    """Text-mode WebSocket handler with voice streaming support."""

    async def websocket_handler(self, request):
        """Handle WebSocket connections (text + voice)."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.websockets.add(ws)

        # Per-connection voice session
        voice_session = None

        try:
            voice_svc = getattr(self, '_voice_service', None)

            await ws.send_json({
                'type': 'connected',
                'message': 'BMAM Text Mode connected',
                'voice_available': voice_svc is not None,
            })

            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_type = data.get('type')

                    if msg_type == 'voice_start':
                        voice_session = await self._handle_voice_start(
                            ws, data, voice_svc
                        )
                    elif msg_type == 'voice_stop':
                        if voice_session and voice_svc:
                            await self._handle_voice_stop(
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
                        await self._handle_text_ws_message(ws, data)

                elif msg.type == WSMsgType.BINARY:
                    # Binary frame → PCM audio chunk
                    if voice_session and voice_svc:
                        await self._handle_audio_chunk(
                            ws, msg.data, voice_svc, voice_session
                        )

                elif msg.type == WSMsgType.ERROR:
                    logger.error('WebSocket error: %s', ws.exception())

        except Exception as e:
            logger.error("WebSocket handler error: %s", e)
        finally:
            self.websockets.discard(ws)

        return ws

    async def _handle_text_ws_message(
        self, ws: web.WebSocketResponse, data: Dict[str, Any]
    ):
        """Route text-mode WebSocket messages."""
        msg_type = data.get('type')

        if msg_type == 'text_input':
            text = data.get('text', '')
            if not text:
                return

            try:
                async def _status_callback(stage: str, details: str, color: str = None):
                    try:
                        await ws.send_json({
                            'type': 'brain_status',
                            'stage': stage,
                            'details': details,
                            'color': color,
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception:
                        pass

                result = await self.coordinator.process_user_input(
                    text,
                    context={'status_callback': _status_callback}
                )

                from .text_handlers import _serialize_memories

                await ws.send_json({
                    'type': 'response',
                    'text': result.response,
                    'full_result': {
                        'success': result.success,
                        'agents_involved': result.agents_involved,
                        'memories_retrieved': _serialize_memories(
                            result.memories_retrieved
                        ),
                        'activation_trace': result.activation_trace or [],
                        'routing_decision': result.routing_decision or {},
                        'processing_time': result.processing_time,
                        'insights': result.insights or {},
                    },
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error("Text WS processing error: %s", e)
                await ws.send_json({
                    'type': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                })

        elif msg_type == 'memory_search':
            query = data.get('query', '')
            k = data.get('k', 10)
            if not query:
                return

            try:
                results = await self.coordinator.smart_retrieve(query, k=k)
                from .text_handlers import _serialize_memories

                await ws.send_json({
                    'type': 'memory_search_result',
                    'data': _serialize_memories(results),
                    'query': query
                })
            except Exception as e:
                logger.error("Memory search WS error: %s", e)
                await ws.send_json({
                    'type': 'error',
                    'message': str(e)
                })

    # ─── Voice helpers ────────────────────────────────────────────────────

    async def _handle_voice_start(self, ws, data, voice_svc):
        """Create a voice session."""
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

    async def _handle_audio_chunk(self, ws, chunk, voice_svc, session):
        """Process a binary PCM audio chunk."""
        from src.services.voice_service import VoiceEventType

        async for event in voice_svc.process_audio_chunk(chunk, session):
            if event.type == VoiceEventType.VAD:
                await ws.send_json({'type': 'voice_vad', **event.data})
            elif event.type == VoiceEventType.PARTIAL:
                await ws.send_json({'type': 'voice_partial', **event.data})
            elif event.type == VoiceEventType.TRANSCRIPT:
                await ws.send_json({'type': 'voice_transcript', **event.data})
                await self._process_voice_transcript(
                    ws, event.data['text'], voice_svc, session
                )

    async def _handle_voice_stop(self, ws, voice_svc, session):
        """Force final STT on explicit stop."""
        from src.services.voice_service import VoiceEventType

        async for event in voice_svc.force_final_stt(session):
            if event.type == VoiceEventType.VAD:
                await ws.send_json({'type': 'voice_vad', **event.data})
            elif event.type == VoiceEventType.TRANSCRIPT:
                await ws.send_json({'type': 'voice_transcript', **event.data})
                await self._process_voice_transcript(
                    ws, event.data['text'], voice_svc, session
                )

    async def _process_voice_transcript(self, ws, text, voice_svc, session):
        """Run brain processing + TTS on transcribed text."""
        if not text.strip():
            return

        from src.services.voice_session import SessionState
        from src.services.voice_service import VoiceEventType

        session.state = SessionState.PROCESSING

        try:
            async def _status_callback(stage, details, color=None):
                try:
                    await ws.send_json({
                        'type': 'brain_status',
                        'stage': stage,
                        'details': details,
                        'color': color,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception:
                    pass

            result = await self.coordinator.process_user_input(
                text,
                context={'status_callback': _status_callback}
            )

            from .text_handlers import _serialize_memories

            await ws.send_json({
                'type': 'response',
                'text': result.response,
                'full_result': {
                    'success': result.success,
                    'agents_involved': result.agents_involved,
                    'memories_retrieved': _serialize_memories(
                        result.memories_retrieved
                    ),
                    'activation_trace': result.activation_trace or [],
                    'routing_decision': result.routing_decision or {},
                    'processing_time': result.processing_time,
                    'insights': result.insights or {},
                },
                'timestamp': datetime.now().isoformat()
            })

            # Stream TTS
            async def _tts_stream():
                async for event in voice_svc.synthesize_streaming(
                    result.response, session
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
