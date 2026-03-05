"""Streaming STT wrapper around faster-whisper for GPU-accelerated transcription."""

import io
import logging
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    text: str
    language: str
    is_partial: bool
    confidence: float = 0.0


class StreamingSTT:
    """faster-whisper based STT with partial and final transcription modes.

    - Partial: fast, greedy (beam=1), called every ~1s during speech.
    - Final: accurate (beam=5), called on speech-end from VAD.
    """

    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        beam_size_partial: int = 1,
        beam_size_final: int = 5,
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.beam_size_partial = beam_size_partial
        self.beam_size_final = beam_size_final
        self._model = None

    def _ensure_loaded(self) -> None:
        """Lazy-load the whisper model on first use."""
        if self._model is not None:
            return

        logger.info(
            "Loading faster-whisper model=%s device=%s compute=%s ...",
            self.model_size, self.device, self.compute_type,
        )
        from faster_whisper import WhisperModel

        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
        )
        logger.info("faster-whisper model ready")

    def _pcm_to_float(self, pcm_bytes: bytes) -> np.ndarray:
        """Convert 16-bit PCM bytes to float32 numpy array in [-1, 1]."""
        audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        return audio_int16.astype(np.float32) / 32768.0

    def transcribe_partial(
        self, pcm_bytes: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Fast partial transcription for real-time feedback.

        Args:
            pcm_bytes: Raw PCM 16kHz 16-bit mono audio.
            language: Optional language hint ("zh", "en", or None for auto).

        Returns:
            TranscriptionResult with is_partial=True.
        """
        self._ensure_loaded()

        audio = self._pcm_to_float(pcm_bytes)
        if len(audio) < 1600:  # < 0.1s
            return TranscriptionResult(text="", language="", is_partial=True)

        lang = language if language and language != "auto" else None
        segments, info = self._model.transcribe(
            audio,
            beam_size=self.beam_size_partial,
            language=lang,
            vad_filter=False,
            without_timestamps=True,
        )

        text_parts = []
        for seg in segments:
            text_parts.append(seg.text.strip())

        text = " ".join(text_parts).strip()
        detected_lang = info.language if info else (language or "")

        return TranscriptionResult(
            text=text,
            language=detected_lang,
            is_partial=True,
            confidence=info.language_probability if info else 0.0,
        )

    def transcribe_final(
        self, pcm_bytes: bytes, language: Optional[str] = None
    ) -> TranscriptionResult:
        """Accurate final transcription after speech ends.

        Args:
            pcm_bytes: Complete utterance PCM 16kHz 16-bit mono audio.
            language: Optional language hint.

        Returns:
            TranscriptionResult with is_partial=False.
        """
        self._ensure_loaded()

        audio = self._pcm_to_float(pcm_bytes)
        if len(audio) < 1600:  # < 0.1s
            return TranscriptionResult(text="", language="", is_partial=False)

        t0 = time.monotonic()
        lang = language if language and language != "auto" else None

        segments, info = self._model.transcribe(
            audio,
            beam_size=self.beam_size_final,
            language=lang,
            vad_filter=True,
            without_timestamps=True,
        )

        text_parts = []
        for seg in segments:
            text_parts.append(seg.text.strip())

        text = " ".join(text_parts).strip()
        detected_lang = info.language if info else (language or "")
        elapsed = time.monotonic() - t0

        logger.info(
            "STT final: %.1fs audio → %.2fs processing, lang=%s, text=%r",
            len(audio) / 16000, elapsed, detected_lang, text[:80],
        )

        return TranscriptionResult(
            text=text,
            language=detected_lang,
            is_partial=False,
            confidence=info.language_probability if info else 0.0,
        )
