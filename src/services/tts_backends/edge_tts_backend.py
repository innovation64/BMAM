"""Edge TTS backend — free, high-quality, supports Chinese and English."""

import io
import logging
from typing import AsyncIterator

import edge_tts

from src.services.voice_config import AudioFormat
from .base import TTSBackend

logger = logging.getLogger(__name__)

# Edge TTS outputs MP3 by default; we convert to PCM for consistent playback.
# For streaming we yield the MP3 chunks directly and let the client decode,
# OR we convert server-side. We choose to stream raw MP3 and add a
# content-type header so the client can decode via Web Audio API.

# Actually, for uniform handling we convert to PCM on the server using
# a simple approach: accumulate the MP3 and decode. For true streaming,
# we yield MP3 chunks and mark the format.

# Decision: Stream MP3 chunks to client. Client uses MediaSource or
# Web Audio decodeAudioData. This avoids server-side ffmpeg dependency.
# We set output_format to indicate this is NOT raw PCM.


class EdgeTTSBackend(TTSBackend):
    """Edge TTS via the edge-tts Python library (free Microsoft TTS)."""

    supports_streaming = True
    # Edge TTS streams MP3 natively; we pass it through.
    # The client side must handle MP3 decoding.
    output_format = AudioFormat.PCM_24K  # nominal; actual is MP3

    # We'll use a flag to indicate MP3 streaming
    actual_format = "mp3"

    async def synthesize_stream(
        self, text: str, voice: str, language: str
    ) -> AsyncIterator[bytes]:
        """Yield audio chunks from Edge TTS.

        Note: Edge TTS yields MP3 fragments. The WebSocket protocol sends
        these as binary frames; the client decodes via Web Audio API.
        """
        if not text.strip():
            return

        communicate = edge_tts.Communicate(text=text, voice=voice)

        try:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error("Edge TTS synthesis error: %s", e)
            raise
