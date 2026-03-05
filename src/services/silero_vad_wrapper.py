"""Silero VAD wrapper — lightweight CPU-based voice activity detection."""

import logging
from typing import Tuple

import numpy as np
import torch

logger = logging.getLogger(__name__)


class SileroVAD:
    """Wraps the Silero VAD model for speech/silence detection on PCM audio."""

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._model = None
        self._state = None

    def _ensure_loaded(self) -> None:
        """Lazy-load the Silero VAD model on first use."""
        if self._model is not None:
            return

        logger.info("Loading Silero VAD model ...")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
            trust_repo=True,
        )
        self._model = model
        self._get_speech_timestamps = utils[0]
        self.reset_state()
        logger.info("Silero VAD ready")

    def reset_state(self) -> None:
        """Reset the internal VAD model state (call between utterances)."""
        if self._model is not None:
            self._model.reset_states()

    def process_chunk(self, pcm_bytes: bytes) -> Tuple[bool, float]:
        """Process a single PCM chunk and return (is_speech, confidence).

        Args:
            pcm_bytes: Raw PCM 16-bit signed little-endian audio.

        Returns:
            Tuple of (is_speech: bool, confidence: float 0..1).
        """
        self._ensure_loaded()

        # Convert bytes to float32 tensor in [-1, 1]
        audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        audio_float = audio_int16.astype(np.float32) / 32768.0
        tensor = torch.from_numpy(audio_float)

        # Silero expects 512 samples at 16kHz (32ms) as minimum window.
        # If chunk is shorter, pad with zeros.
        if len(tensor) < 512:
            tensor = torch.nn.functional.pad(tensor, (0, 512 - len(tensor)))

        # Run VAD — returns a float probability of speech
        with torch.no_grad():
            confidence = self._model(tensor, self.sample_rate).item()

        is_speech = confidence >= self.threshold
        return is_speech, confidence
