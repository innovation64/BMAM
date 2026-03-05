"""FastAPI WebSocket endpoint — text + voice protocol.

Handles three frame types:
- **Text frames (JSON)**: ``text_input``, ``memory_search``, ``voice_start``,
  ``voice_stop``, ``voice_barge_in``
- **Binary frames**: raw PCM 16kHz 16-bit mono audio chunks from client
- **Binary frames (S→C)**: TTS audio chunks back to client
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from src.api.dependencies import get_adapter, get_voice_service
from src.api.middleware_adapter import MiddlewareAdapter

logger = logging.getLogger(__name__)

router = APIRouter()


def _safe_serialize(obj: Any) -> Any:
    """Best-effort JSON-safe conversion for memory dicts."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


async def _send_json_safe(ws: WebSocket, data: dict) -> bool:
    """Send JSON, returning False if the connection is gone."""
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_json(data)
            return True
    except Exception:
        pass
    return False


async def _send_bytes_safe(ws: WebSocket, data: bytes) -> bool:
    """Send binary frame, returning False if the connection is gone."""
    try:
        if ws.client_state == WebSocketState.CONNECTED:
            await ws.send_bytes(data)
            return True
    except Exception:
        pass
    return False


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """WebSocket endpoint supporting both text chat and streaming voice."""
    adapter: MiddlewareAdapter = get_adapter()
    voice_service = get_voice_service()  # may be None if not configured
    await ws.accept()

    # Per-connection voice session (created lazily on voice_start)
    voice_session = None

    try:
        await _send_json_safe(ws, {
            "type": "connected",
            "message": "BMAM connected",
            "voice_available": voice_service is not None,
        })

        while True:
            message = await ws.receive()

            if "text" in message:
                # --- JSON text frame ---
                raw = message["text"]
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    await _send_json_safe(ws, {
                        "type": "error",
                        "message": "Invalid JSON",
                        "timestamp": datetime.now().isoformat(),
                    })
                    continue

                msg_type = data.get("type")

                if msg_type == "text_input":
                    await _handle_text_input(ws, data, adapter)

                elif msg_type == "memory_search":
                    await _handle_memory_search(ws, data, adapter)

                elif msg_type == "voice_start":
                    voice_session = await _handle_voice_start(
                        ws, data, voice_service
                    )

                elif msg_type == "voice_stop":
                    if voice_session and voice_service:
                        await _handle_voice_stop(
                            ws, voice_service, voice_session, adapter
                        )

                elif msg_type == "voice_barge_in":
                    if voice_session:
                        voice_session.cancel_tts()
                        await _send_json_safe(ws, {
                            "type": "voice_tts_end",
                            "reason": "barge_in",
                        })

                else:
                    await _send_json_safe(ws, {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                        "timestamp": datetime.now().isoformat(),
                    })

            elif "bytes" in message:
                # --- Binary audio frame ---
                if voice_session and voice_service:
                    await _handle_audio_chunk(
                        ws, message["bytes"], voice_service, voice_session,
                        adapter,
                    )

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except Exception as exc:
        logger.error("WebSocket handler error: %s", exc, exc_info=True)


# ─── Text handlers ───────────────────────────────────────────────────────────

async def _handle_text_input(
    ws: WebSocket, data: Dict[str, Any], adapter: MiddlewareAdapter
) -> None:
    """Process a user text message through the brain pipeline."""
    text = data.get("text", "")
    if not text:
        return

    try:
        async def status_callback(stage: str, details: str, color: str = None):
            await _send_json_safe(ws, {
                "type": "brain_status",
                "stage": stage,
                "details": details,
                "color": color,
                "timestamp": datetime.now().isoformat(),
            })

        user_id = data.get("user_id", "default")
        context = data.get("context") or {}
        context["user_id"] = user_id

        result = await adapter.coordinator.process_user_input(
            user_input=text,
            context=context,
            status_callback=status_callback,
        )

        memories = _safe_serialize(result.memories_retrieved or [])

        await _send_json_safe(ws, {
            "type": "response",
            "text": result.response,
            "full_result": {
                "success": result.success,
                "agents_involved": result.agents_involved or [],
                "memories_retrieved": memories,
                "activation_trace": result.activation_trace or [],
                "routing_decision": _safe_serialize(
                    result.routing_decision or {}
                ),
                "processing_time": result.processing_time,
                "insights": _safe_serialize(result.insights or {}),
            },
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as exc:
        logger.error("Text WS processing error: %s", exc)
        await _send_json_safe(ws, {
            "type": "error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat(),
        })


async def _handle_memory_search(
    ws: WebSocket, data: Dict[str, Any], adapter: MiddlewareAdapter
) -> None:
    """Run memory search and return results."""
    query = data.get("query", "")
    k = data.get("k", 10)
    if not query:
        return

    try:
        results = await adapter.coordinator.smart_retrieve(query, k=k)
        serialized = _safe_serialize(results)

        await _send_json_safe(ws, {
            "type": "memory_search_result",
            "data": serialized,
            "query": query,
        })
    except Exception as exc:
        logger.error("Memory search WS error: %s", exc)
        await _send_json_safe(ws, {
            "type": "error",
            "message": str(exc),
        })


# ─── Voice handlers ──────────────────────────────────────────────────────────

async def _handle_voice_start(ws, data, voice_service):
    """Create a new voice session."""
    if voice_service is None:
        await _send_json_safe(ws, {
            "type": "error",
            "message": "Voice service not available",
        })
        return None

    from src.services.voice_session import VoiceSession

    session = VoiceSession(
        session_id=str(uuid.uuid4()),
        language=data.get("language", "auto"),
    )
    await _send_json_safe(ws, {
        "type": "voice_start_ack",
        "session_id": session.session_id,
    })
    return session


async def _handle_audio_chunk(ws, chunk, voice_service, session, adapter):
    """Process a binary PCM audio chunk through VAD + STT."""
    from src.services.voice_service import VoiceEventType

    async for event in voice_service.process_audio_chunk(chunk, session):
        if event.type == VoiceEventType.VAD:
            await _send_json_safe(ws, {
                "type": "voice_vad",
                **event.data,
            })
        elif event.type == VoiceEventType.PARTIAL:
            await _send_json_safe(ws, {
                "type": "voice_partial",
                **event.data,
            })
        elif event.type == VoiceEventType.TRANSCRIPT:
            await _send_json_safe(ws, {
                "type": "voice_transcript",
                **event.data,
            })
            # Auto-process transcript through brain coordinator + TTS
            await _process_voice_transcript(
                ws, event.data["text"], voice_service, session, adapter
            )


async def _handle_voice_stop(ws, voice_service, session, adapter):
    """User explicitly stopped recording — force final STT."""
    from src.services.voice_service import VoiceEventType

    async for event in voice_service.force_final_stt(session):
        if event.type == VoiceEventType.VAD:
            await _send_json_safe(ws, {"type": "voice_vad", **event.data})
        elif event.type == VoiceEventType.TRANSCRIPT:
            await _send_json_safe(ws, {
                "type": "voice_transcript",
                **event.data,
            })
            await _process_voice_transcript(
                ws, event.data["text"], voice_service, session, adapter
            )


async def _process_voice_transcript(
    ws, text, voice_service, session, adapter
):
    """Run brain processing on the transcript, then stream TTS response."""
    if not text.strip():
        return

    from src.services.voice_session import SessionState

    session.state = SessionState.PROCESSING

    try:
        # Stream brain status
        async def status_callback(stage: str, details: str, color: str = None):
            await _send_json_safe(ws, {
                "type": "brain_status",
                "stage": stage,
                "details": details,
                "color": color,
                "timestamp": datetime.now().isoformat(),
            })

        result = await adapter.coordinator.process_user_input(
            user_input=text,
            context={"user_id": "voice_user"},
            status_callback=status_callback,
        )

        memories = _safe_serialize(result.memories_retrieved or [])

        # Send text response
        await _send_json_safe(ws, {
            "type": "response",
            "text": result.response,
            "full_result": {
                "success": result.success,
                "agents_involved": result.agents_involved or [],
                "memories_retrieved": memories,
                "activation_trace": result.activation_trace or [],
                "routing_decision": _safe_serialize(
                    result.routing_decision or {}
                ),
                "processing_time": result.processing_time,
                "insights": _safe_serialize(result.insights or {}),
            },
            "timestamp": datetime.now().isoformat(),
        })

        # Stream TTS audio
        from src.services.voice_service import VoiceEventType

        async def _tts_stream():
            async for event in voice_service.synthesize_streaming(
                result.response, session
            ):
                if session.tts_cancelled:
                    break
                if event.type == VoiceEventType.TTS_START:
                    await _send_json_safe(ws, {
                        "type": "voice_tts_start",
                        **event.data,
                    })
                elif event.type == VoiceEventType.TTS_AUDIO:
                    await _send_bytes_safe(ws, event.audio)
                elif event.type == VoiceEventType.TTS_END:
                    await _send_json_safe(ws, {
                        "type": "voice_tts_end",
                        **(event.data or {}),
                    })

        tts_task = asyncio.create_task(_tts_stream())
        session.start_tts(tts_task)
        await tts_task

    except Exception as exc:
        logger.error("Voice transcript processing error: %s", exc)
        await _send_json_safe(ws, {
            "type": "error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat(),
        })
    finally:
        session.finish_tts()
