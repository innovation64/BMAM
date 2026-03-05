"""Per-connection voice state management."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SessionState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"


@dataclass
class VoiceSession:
    """Tracks state for a single WebSocket voice connection."""

    session_id: str
    state: SessionState = SessionState.IDLE
    language: str = "auto"

    # Audio accumulation for STT
    audio_buffer: bytearray = field(default_factory=bytearray)
    last_audio_time: float = 0.0

    # VAD state
    is_speech_active: bool = False
    speech_start_time: float = 0.0
    silence_start_time: float = 0.0

    # STT state
    last_partial_time: float = 0.0
    last_partial_text: str = ""
    final_transcript: str = ""

    # TTS state — used for barge-in cancellation
    tts_task: Optional[asyncio.Task] = field(default=None, repr=False)
    tts_cancelled: bool = False

    # Detected language from STT
    detected_language: Optional[str] = None

    def reset_audio(self) -> None:
        """Clear audio buffer and VAD state after final transcription."""
        self.audio_buffer.clear()
        self.is_speech_active = False
        self.speech_start_time = 0.0
        self.silence_start_time = 0.0
        self.last_partial_time = 0.0
        self.last_partial_text = ""

    def append_audio(self, chunk: bytes) -> None:
        """Append PCM audio data to the buffer."""
        self.audio_buffer.extend(chunk)
        self.last_audio_time = time.monotonic()

    def cancel_tts(self) -> None:
        """Cancel in-flight TTS playback (barge-in)."""
        self.tts_cancelled = True
        if self.tts_task and not self.tts_task.done():
            self.tts_task.cancel()
        self.tts_task = None

    def start_tts(self, task: asyncio.Task) -> None:
        """Register a new TTS streaming task."""
        self.cancel_tts()
        self.tts_cancelled = False
        self.tts_task = task
        self.state = SessionState.SPEAKING

    def finish_tts(self) -> None:
        """Mark TTS as complete."""
        self.tts_task = None
        self.tts_cancelled = False
        self.state = SessionState.IDLE

    @property
    def audio_duration_s(self) -> float:
        """Accumulated audio duration in seconds (assumes 16kHz 16-bit mono)."""
        return len(self.audio_buffer) / (16000 * 2)

    @property
    def effective_language(self) -> str:
        """Return detected language or configured language."""
        if self.detected_language:
            return self.detected_language
        if self.language != "auto":
            return self.language
        return "zh"  # default to Chinese
