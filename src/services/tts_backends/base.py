"""Abstract base class for TTS backends."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from src.services.voice_config import AudioFormat


class TTSBackend(ABC):
    """Abstract TTS backend — all backends must implement synthesize_stream."""

    supports_streaming: bool = True
    output_format: AudioFormat = AudioFormat.PCM_24K

    @abstractmethod
    async def synthesize_stream(
        self, text: str, voice: str, language: str
    ) -> AsyncIterator[bytes]:
        """Synthesize text to audio, yielding PCM chunks progressively.

        Args:
            text: Text to synthesize (a single sentence or short paragraph).
            voice: Voice identifier (backend-specific).
            language: Language code ("zh" or "en").

        Yields:
            Raw PCM audio bytes (format determined by output_format).
        """
        ...  # pragma: no cover

    async def close(self) -> None:
        """Clean up any resources held by the backend."""
        pass
