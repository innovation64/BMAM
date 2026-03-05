"""Central voice service orchestrator — STT + TTS + VAD.

Ties together all voice subsystems. Used by both FastAPI and aiohttp
WebSocket handlers to process audio and generate speech.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Optional

from .sentence_splitter import detect_language, split_sentences
from .silero_vad_wrapper import SileroVAD
from .streaming_stt import StreamingSTT
from .tts_backends import TTSBackend, create_tts_backend
from .voice_config import VoiceConfig
from .voice_session import SessionState, VoiceSession

logger = logging.getLogger(__name__)


class VoiceEventType(str, Enum):
    VAD = "voice_vad"
    PARTIAL = "voice_partial"
    TRANSCRIPT = "voice_transcript"
    TTS_START = "voice_tts_start"
    TTS_AUDIO = "voice_tts_audio"
    TTS_END = "voice_tts_end"


@dataclass
class VoiceEvent:
    """A single event emitted during voice processing."""

    type: VoiceEventType
    data: dict = None
    audio: bytes = None  # binary payload for TTS_AUDIO


class VoiceService:
    """Orchestrates VAD, STT, and TTS for voice interactions.

    One instance is shared across all WebSocket connections.
    Per-connection state is held in VoiceSession objects.
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig.from_env()
        self.stt = StreamingSTT(
            model_size=self.config.stt_model,
            device=self.config.stt_device,
            compute_type=self.config.stt_compute_type,
            beam_size_partial=self.config.stt_beam_size_partial,
            beam_size_final=self.config.stt_beam_size_final,
        )
        self.vad = SileroVAD(
            threshold=self.config.vad_threshold,
            sample_rate=self.config.sample_rate,
        )
        self.tts: TTSBackend = create_tts_backend(self.config)
        logger.info("VoiceService initialized (tts=%s)", self.config.tts_backend.value)

    async def process_audio_chunk(
        self, chunk: bytes, session: VoiceSession
    ) -> AsyncIterator[VoiceEvent]:
        """Process an incoming PCM audio chunk from the client.

        Runs VAD on the chunk, accumulates audio, triggers partial/final STT.

        Yields VoiceEvents:
            - VAD events when speech starts/stops
            - PARTIAL events with interim transcription
            - TRANSCRIPT event with final transcription on speech end
        """
        session.append_audio(chunk)

        # --- VAD ---
        is_speech, confidence = self.vad.process_chunk(chunk)
        now = time.monotonic()

        if is_speech and not session.is_speech_active:
            # Speech just started
            session.is_speech_active = True
            session.speech_start_time = now
            session.silence_start_time = 0.0
            session.state = SessionState.LISTENING
            yield VoiceEvent(
                type=VoiceEventType.VAD,
                data={"speaking": True, "confidence": round(confidence, 2)},
            )

        elif not is_speech and session.is_speech_active:
            # Silence detected after speech
            if session.silence_start_time == 0.0:
                session.silence_start_time = now

            silence_ms = (now - session.silence_start_time) * 1000
            if silence_ms >= self.config.vad_min_silence_ms:
                # Speech ended — check minimum speech duration
                speech_duration_ms = (now - session.speech_start_time) * 1000
                if speech_duration_ms >= self.config.vad_min_speech_ms:
                    session.is_speech_active = False
                    yield VoiceEvent(
                        type=VoiceEventType.VAD,
                        data={"speaking": False, "confidence": round(confidence, 2)},
                    )
                    # Run final transcription
                    async for evt in self._run_final_stt(session):
                        yield evt
                else:
                    # Too short — treat as noise, reset
                    session.is_speech_active = False
                    session.reset_audio()
                    yield VoiceEvent(
                        type=VoiceEventType.VAD,
                        data={"speaking": False, "confidence": 0.0},
                    )

        elif is_speech:
            # Ongoing speech — reset silence timer
            session.silence_start_time = 0.0

        # --- Partial STT ---
        if (
            session.is_speech_active
            and session.audio_duration_s > 0.5
            and (now - session.last_partial_time) >= self.config.stt_partial_interval_s
        ):
            session.last_partial_time = now
            partial = await asyncio.get_event_loop().run_in_executor(
                None,
                self.stt.transcribe_partial,
                bytes(session.audio_buffer),
                session.language if session.language != "auto" else None,
            )
            if partial.text and partial.text != session.last_partial_text:
                session.last_partial_text = partial.text
                if partial.language:
                    session.detected_language = partial.language
                yield VoiceEvent(
                    type=VoiceEventType.PARTIAL,
                    data={
                        "text": partial.text,
                        "language": partial.language,
                    },
                )

    async def _run_final_stt(self, session: VoiceSession) -> AsyncIterator[VoiceEvent]:
        """Run final transcription on accumulated audio."""
        if not session.audio_buffer:
            return

        audio_copy = bytes(session.audio_buffer)
        lang = session.language if session.language != "auto" else None

        result = await asyncio.get_event_loop().run_in_executor(
            None, self.stt.transcribe_final, audio_copy, lang,
        )

        session.final_transcript = result.text
        if result.language:
            session.detected_language = result.language

        session.reset_audio()
        self.vad.reset_state()

        if result.text:
            yield VoiceEvent(
                type=VoiceEventType.TRANSCRIPT,
                data={
                    "text": result.text,
                    "language": result.language,
                    "confidence": round(result.confidence, 2),
                },
            )

    async def force_final_stt(self, session: VoiceSession) -> AsyncIterator[VoiceEvent]:
        """Force a final transcription (e.g., when user clicks stop).

        Same as _run_final_stt but public, for explicit voice_stop handling.
        """
        session.is_speech_active = False
        yield VoiceEvent(
            type=VoiceEventType.VAD,
            data={"speaking": False, "confidence": 0.0},
        )
        async for evt in self._run_final_stt(session):
            yield evt

    async def synthesize_streaming(
        self, text: str, session: VoiceSession,
        emotion: Optional[str] = None,
    ) -> AsyncIterator[VoiceEvent]:
        """Split text into sentences and stream TTS audio progressively.

        Args:
            text: Response text to speak.
            session: Current voice session.
            emotion: Optional emotion hint (from brain coordinator) for
                     TTS parameter adjustment.

        Yields:
            TTS_START event, then TTS_AUDIO events with binary data,
            then TTS_END event.
        """
        if not text.strip():
            return

        # Auto-detect language from response text
        lang = session.effective_language
        text_lang = detect_language(text)
        if text_lang != lang:
            lang = text_lang

        voice = self.config.get_tts_voice(lang)

        yield VoiceEvent(
            type=VoiceEventType.TTS_START,
            data={"voice": voice, "language": lang, "emotion": emotion},
        )

        session.state = SessionState.SPEAKING

        try:
            for sentence in split_sentences(text):
                if session.tts_cancelled:
                    logger.debug("TTS cancelled (barge-in)")
                    break

                async for audio_chunk in self.tts.synthesize_stream(
                    sentence, voice, lang
                ):
                    if session.tts_cancelled:
                        break
                    yield VoiceEvent(
                        type=VoiceEventType.TTS_AUDIO,
                        audio=audio_chunk,
                    )
        except asyncio.CancelledError:
            logger.debug("TTS task cancelled")
        except Exception as e:
            logger.error("TTS streaming error: %s", e)

        session.finish_tts()
        yield VoiceEvent(type=VoiceEventType.TTS_END, data={})

    async def close(self) -> None:
        """Release resources."""
        await self.tts.close()
