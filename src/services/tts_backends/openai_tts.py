"""OpenAI TTS backend — high quality, streaming, requires API key."""

import logging
import os
from typing import AsyncIterator

from src.services.voice_config import AudioFormat
from .base import TTSBackend

logger = logging.getLogger(__name__)


class OpenAITTSBackend(TTSBackend):
    """OpenAI TTS API backend — alloy/nova voices, MP3 streaming."""

    supports_streaming = True
    output_format = AudioFormat.PCM_24K  # nominal; actual is MP3
    actual_format = "mp3"

    def __init__(self, model: str = "tts-1", speed: float = 1.0):
        self.model = model
        self.speed = speed
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )

    async def synthesize_stream(
        self, text: str, voice: str, language: str
    ) -> AsyncIterator[bytes]:
        """Stream audio from OpenAI TTS API.

        OpenAI TTS supports streaming response; we yield chunks as they arrive.
        """
        if not text.strip():
            return

        self._ensure_client()

        try:
            response = await self._client.audio.speech.create(
                model=self.model,
                voice=voice,
                input=text,
                speed=self.speed,
                response_format="mp3",
            )

            # Stream the response content in chunks
            async for chunk in response.iter_bytes(chunk_size=4096):
                yield chunk

        except Exception as e:
            logger.error("OpenAI TTS synthesis error: %s", e)
            raise

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
