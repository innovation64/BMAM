"""TTS backend factory — creates the appropriate backend from config."""

import logging

from src.services.voice_config import TTSBackendType, VoiceConfig
from .base import TTSBackend
from .edge_tts_backend import EdgeTTSBackend
from .openai_tts import OpenAITTSBackend

logger = logging.getLogger(__name__)


def create_tts_backend(config: VoiceConfig) -> TTSBackend:
    """Instantiate the configured TTS backend.

    Args:
        config: VoiceConfig with tts_backend set.

    Returns:
        An initialized TTSBackend instance.
    """
    if config.tts_backend == TTSBackendType.OPENAI:
        logger.info("Using OpenAI TTS backend (model=%s)", config.openai_tts_model)
        return OpenAITTSBackend(
            model=config.openai_tts_model,
            speed=config.openai_tts_speed,
        )
    elif config.tts_backend == TTSBackendType.COSYVOICE:
        # CosyVoice is a placeholder — falls back to Edge TTS for now
        logger.warning("CosyVoice backend not yet implemented, falling back to Edge TTS")
        return EdgeTTSBackend()
    else:
        logger.info("Using Edge TTS backend (free)")
        return EdgeTTSBackend()


__all__ = ["TTSBackend", "create_tts_backend", "EdgeTTSBackend", "OpenAITTSBackend"]
