"""Voice service configuration — loaded from environment variables."""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TTSBackendType(str, Enum):
    EDGE = "edge"
    OPENAI = "openai"
    COSYVOICE = "cosyvoice"


class AudioFormat(str, Enum):
    PCM_16K = "pcm_16k"   # 16kHz, 16-bit, mono
    PCM_24K = "pcm_24k"   # 24kHz, 16-bit, mono


# Default TTS voices per backend and language
DEFAULT_VOICES = {
    TTSBackendType.EDGE: {"zh": "zh-CN-XiaoxiaoNeural", "en": "en-US-AriaNeural"},
    TTSBackendType.OPENAI: {"zh": "nova", "en": "alloy"},
    TTSBackendType.COSYVOICE: {"zh": "default", "en": "default"},
}


@dataclass
class VoiceConfig:
    """Central configuration for all voice subsystems."""

    # STT settings
    stt_model: str = "large-v3"
    stt_device: str = "cuda"
    stt_compute_type: str = "float16"

    # TTS settings
    tts_backend: TTSBackendType = TTSBackendType.EDGE
    tts_voice: Optional[str] = None  # None → auto-select by language
    tts_output_format: AudioFormat = AudioFormat.PCM_24K

    # VAD settings
    vad_threshold: float = 0.5
    vad_min_silence_ms: int = 600
    vad_min_speech_ms: int = 250

    # Language
    language: str = "auto"  # "auto" | "zh" | "en"

    # Audio capture
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 100

    # Streaming STT tuning
    stt_partial_interval_s: float = 1.0
    stt_beam_size_partial: int = 1
    stt_beam_size_final: int = 5

    # OpenAI TTS specific
    openai_tts_model: str = "tts-1"
    openai_tts_speed: float = 1.0

    @classmethod
    def from_env(cls) -> "VoiceConfig":
        """Load configuration from environment variables."""
        backend_str = os.getenv("VOICE_TTS_BACKEND", "edge").lower()
        try:
            backend = TTSBackendType(backend_str)
        except ValueError:
            backend = TTSBackendType.EDGE

        return cls(
            stt_model=os.getenv("VOICE_STT_MODEL", "large-v3"),
            stt_device=os.getenv("VOICE_STT_DEVICE", "cuda"),
            stt_compute_type=os.getenv("VOICE_STT_COMPUTE_TYPE", "float16"),
            tts_backend=backend,
            tts_voice=os.getenv("VOICE_TTS_VOICE") or None,
            language=os.getenv("VOICE_LANGUAGE", "auto"),
            vad_threshold=float(os.getenv("VOICE_VAD_THRESHOLD", "0.5")),
            vad_min_silence_ms=int(os.getenv("VOICE_VAD_MIN_SILENCE_MS", "600")),
            vad_min_speech_ms=int(os.getenv("VOICE_VAD_MIN_SPEECH_MS", "250")),
            sample_rate=int(os.getenv("VOICE_SAMPLE_RATE", "16000")),
            openai_tts_model=os.getenv("VOICE_OPENAI_TTS_MODEL", "tts-1"),
            openai_tts_speed=float(os.getenv("VOICE_OPENAI_TTS_SPEED", "1.0")),
        )

    def get_tts_voice(self, language: str) -> str:
        """Resolve TTS voice for given language, with fallback."""
        if self.tts_voice:
            return self.tts_voice
        lang = language if language in ("zh", "en") else "en"
        voices = DEFAULT_VOICES.get(self.tts_backend, {})
        return voices.get(lang, voices.get("en", "default"))

    @property
    def bytes_per_chunk(self) -> int:
        """Number of bytes per audio chunk (16-bit mono PCM)."""
        return int(self.sample_rate * self.chunk_duration_ms / 1000) * 2
