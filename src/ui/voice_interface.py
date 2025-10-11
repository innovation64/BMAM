"""
Voice Interface Integration for BMAM
Handles speech-to-text, text-to-speech, and audio processing
"""

import asyncio
import wave
import io
import json
import struct
import os
import tempfile
from typing import Optional, Callable, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from shutil import which

# Audio processing libraries (to be installed)
# pip install pyaudio speechrecognition gtts pydub

try:
    import pyaudio
    import speech_recognition as sr
    from gtts import gTTS
    from pydub import AudioSegment
    from pydub.playback import play
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Audio libraries not installed. Install with: pip install pyaudio speechrecognition gtts pydub")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


@dataclass
class AudioConfig:
    """Audio configuration settings"""
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    format: int = 8  # pyaudio.paInt16
    record_seconds: int = 5

    # Voice detection
    silence_threshold: float = 100  # RMS threshold for silence (lowered for better detection)
    silence_duration: float = 1.5  # Seconds of silence before stopping

    # TTS settings
    tts_language: str = 'zh-CN'  # Chinese for Yaoguang
    tts_speed: float = 1.0


class VoiceActivityDetector:
    """Detects voice activity in audio stream"""

    def __init__(self, config: AudioConfig):
        self.config = config
        self.silence_buffer = []
        self.is_speaking = False

    def is_silent(self, audio_data: bytes) -> bool:
        """Check if audio chunk is silent"""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        if audio_array.size == 0:
            return True

        # Calculate RMS (Root Mean Square)
        rms = np.sqrt(np.mean(audio_array ** 2))

        return rms < self.config.silence_threshold

    def detect_speech_end(self, audio_data: bytes) -> bool:
        """Detect if speech has ended"""
        if self.is_silent(audio_data):
            self.silence_buffer.append(datetime.now())

            # Check if silence duration exceeded
            if len(self.silence_buffer) > 0:
                silence_time = (datetime.now() - self.silence_buffer[0]).total_seconds()
                if silence_time > self.config.silence_duration:
                    self.is_speaking = False
                    return True
        else:
            self.silence_buffer.clear()
            self.is_speaking = True

        return False


class AudioProcessor:
    """Processes audio for amplitude visualization"""

    @staticmethod
    def get_amplitude(audio_data: bytes) -> float:
        """Get normalized amplitude from audio data"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        if audio_array.size == 0:
            return 0.0

        # Calculate amplitude (0-1)
        max_val = np.max(np.abs(audio_array))
        normalized = max_val / 32768.0  # Normalize to 0-1

        return min(1.0, normalized)

    @staticmethod
    def apply_filters(audio_data: bytes) -> bytes:
        """Apply noise reduction filters"""
        audio_array = np.frombuffer(audio_data, dtype=np.int16).copy()

        # Simple noise gate
        threshold = 100
        audio_array[np.abs(audio_array) < threshold] = 0

        return audio_array.tobytes()


class SpeechToTextEngine:
    """Handles speech-to-text conversion"""

    def __init__(self, config: AudioConfig):
        self.config = config
        self.recognizer = sr.Recognizer() if AUDIO_AVAILABLE else None

        # Configure recognizer
        if self.recognizer:
            self.recognizer.energy_threshold = config.silence_threshold
            self.recognizer.dynamic_energy_threshold = True

    async def transcribe(self, audio_data: bytes) -> str:
        """Convert audio to text"""
        if not AUDIO_AVAILABLE or not self.recognizer:
            return "Speech recognition not available"

        try:
            # Convert bytes to AudioData
            audio = sr.AudioData(
                audio_data,
                self.config.sample_rate,
                2  # Sample width
            )

            # Use Google Speech Recognition (free)
            # For production, consider using OpenAI Whisper or other services
            text = await asyncio.to_thread(
                self.recognizer.recognize_google,
                audio,
                language='zh-CN'  # Chinese language
            )

            return text

        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            return f"Speech recognition error: {e}"


class TextToSpeechEngine:
    """Handles text-to-speech conversion"""

    def __init__(self, config: AudioConfig):
        self.config = config
        self.voice_cache = {}  # Cache generated audio
        self.ffmpeg_available = bool(which('ffmpeg') or which('ffmpeg.exe'))
        self.ffprobe_available = bool(which('ffprobe') or which('ffprobe.exe') or which('avprobe'))
        self._gtts_enabled = AUDIO_AVAILABLE and self.ffmpeg_available and self.ffprobe_available
        self._pyttsx3_enabled = PYTTSX3_AVAILABLE

        if not self._gtts_enabled and not self._pyttsx3_enabled:
            print("TTS warning: ffmpeg/ffprobe not found and pyttsx3 unavailable; speech playback will be disabled.")

    async def synthesize(self, text: str, emotion: str = "neutral") -> bytes:
        """Convert text to speech audio"""
        if not AUDIO_AVAILABLE:
            return b''

        # Check cache
        cache_key = f"{text}_{emotion}"
        if cache_key in self.voice_cache:
            return self.voice_cache[cache_key]

        try:
            speed = self._resolve_speed(emotion)

            if self._gtts_enabled:
                audio_bytes = await self._synthesize_with_gtts(text, speed)
                if audio_bytes:
                    self.voice_cache[cache_key] = audio_bytes
                    return audio_bytes
                else:
                    # Disable gTTS path after failure to avoid repeated errors
                    self._gtts_enabled = False

            if self._pyttsx3_enabled:
                audio_bytes = await self._synthesize_with_pyttsx3(text, speed)
                if audio_bytes:
                    self.voice_cache[cache_key] = audio_bytes
                    return audio_bytes

            if not self._gtts_enabled and not self._pyttsx3_enabled:
                print("TTS error: No available synthesis backend (install ffmpeg or pyttsx3)")

        except Exception as e:
            print(f"TTS error: {e}")

        return b''

    def _resolve_speed(self, emotion: str) -> float:
        speed = self.config.tts_speed
        if emotion == "excited":
            speed = max(0.5, speed * 1.2)
        elif emotion == "concerned":
            speed = max(0.5, speed * 0.9)
        return speed

    async def _synthesize_with_gtts(self, text: str, speed: float) -> bytes:
        try:
            tts = gTTS(
                text=text,
                lang=self.config.tts_language,
                slow=False
            )

            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)

            audio = AudioSegment.from_mp3(audio_buffer)
            audio = audio.set_frame_rate(self.config.sample_rate)
            audio = audio.set_channels(self.config.channels)

            if speed != 1.0:
                audio = audio.speedup(playback_speed=speed)

            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format='wav')
            wav_buffer.seek(0)
            return wav_buffer.read()
        except Exception as e:
            print(f"TTS error (gTTS path failed): {e}")
            return b''

    async def _synthesize_with_pyttsx3(self, text: str, speed: float) -> bytes:
        if not PYTTSX3_AVAILABLE:
            return b''

        def generate() -> bytes:
            engine = pyttsx3.init()
            try:
                base_rate = engine.getProperty('rate')
                target_rate = int(base_rate * speed)
                engine.setProperty('rate', max(80, target_rate))

                # Attempt to select a Chinese voice if available
                desired = self.config.tts_language.lower()
                for voice in engine.getProperty('voices'):
                    voice_id = getattr(voice, 'id', '').lower()
                    voice_name = getattr(voice, 'name', '').lower()
                    if 'zh' in voice_id or 'chinese' in voice_name or desired in voice_id:
                        engine.setProperty('voice', voice.id)
                        break

                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                    tmp_path = tmp.name

                engine.save_to_file(text, tmp_path)
                engine.runAndWait()

                with open(tmp_path, 'rb') as f:
                    data = f.read()
                return data

            finally:
                try:
                    engine.stop()
                except Exception:
                    pass
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)

        try:
            return await asyncio.to_thread(generate)
        except Exception as e:
            print(f"TTS error (pyttsx3 fallback failed): {e}")
            return b''


class VoiceInterface:
    """Main voice interface for BMAM integration"""

    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self.stt_engine = SpeechToTextEngine(self.config)
        self.tts_engine = TextToSpeechEngine(self.config)
        self.vad = VoiceActivityDetector(self.config)
        self.audio_processor = AudioProcessor()

        # PyAudio instance
        self.audio = pyaudio.PyAudio() if AUDIO_AVAILABLE else None
        self.stream = None

        # Callbacks
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_amplitude_update: Optional[Callable[[float], None]] = None

    def start_listening(self) -> bool:
        """Start audio input stream"""
        if not AUDIO_AVAILABLE or not self.audio:
            return False

        try:
            self.stream = self.audio.open(
                format=self.config.format,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size
            )
            return True
        except Exception as e:
            print(f"Failed to start audio stream: {e}")
            return False

    def stop_listening(self):
        """Stop audio input stream"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    async def listen_for_speech(self) -> Tuple[bytes, float]:
        """Listen for speech until silence detected"""
        if not self.stream:
            return b'', 0.0

        audio_chunks = []
        max_amplitude = 0.0

        # Notify speech start
        if self.on_speech_start:
            self.on_speech_start()

        while True:
            try:
                # Read audio chunk
                audio_data = await asyncio.to_thread(
                    self.stream.read,
                    self.config.chunk_size,
                    exception_on_overflow=False
                )

                # Apply filters
                audio_data = self.audio_processor.apply_filters(audio_data)

                # Get amplitude for visualization
                amplitude = self.audio_processor.get_amplitude(audio_data)
                max_amplitude = max(max_amplitude, amplitude)

                # Update amplitude callback
                if self.on_amplitude_update:
                    self.on_amplitude_update(amplitude)

                # Add to buffer
                audio_chunks.append(audio_data)

                # Check for speech end
                if self.vad.detect_speech_end(audio_data):
                    break

            except Exception as e:
                print(f"Audio read error: {e}")
                break

        # Notify speech end
        if self.on_speech_end:
            self.on_speech_end()

        # Combine audio chunks
        full_audio = b''.join(audio_chunks)

        return full_audio, max_amplitude

    async def speak(self, text: str, emotion: str = "neutral") -> bool:
        """Play synthesized speech"""
        if not AUDIO_AVAILABLE:
            return False

        try:
            # Synthesize speech
            audio_data = await self.tts_engine.synthesize(text, emotion)

            if not audio_data:
                return False

            # Play audio
            audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
            await asyncio.to_thread(play, audio_segment)

            return True

        except Exception as e:
            print(f"Speech playback error: {e}")
            return False

    def cleanup(self):
        """Clean up audio resources"""
        self.stop_listening()
        if self.audio:
            self.audio.terminate()


class VoiceCommandProcessor:
    """Processes voice commands for BMAM control"""

    def __init__(self):
        self.commands = {
            "编辑记忆": self._handle_edit_memory,
            "显示记忆": self._handle_show_memory,
            "清除记忆": self._handle_clear_memory,
            "保存状态": self._handle_save_state,
            "切换模式": self._handle_switch_mode
        }

    async def process_command(self, text: str, ui_controller) -> Dict[str, Any]:
        """Process voice command"""
        text_lower = text.lower()

        # Check for command triggers
        for trigger, handler in self.commands.items():
            if trigger in text:
                return await handler(text, ui_controller)

        # Not a command
        return {'is_command': False}

    async def _handle_edit_memory(self, text: str, ui_controller) -> Dict[str, Any]:
        """Handle memory editing command"""
        # Extract memory index and new content
        # Example: "编辑记忆第一条改为..."

        return {
            'is_command': True,
            'action': 'edit_memory',
            'success': True
        }

    async def _handle_show_memory(self, text: str, ui_controller) -> Dict[str, Any]:
        """Handle memory display command"""
        return {
            'is_command': True,
            'action': 'show_memory',
            'success': True
        }

    async def _handle_clear_memory(self, text: str, ui_controller) -> Dict[str, Any]:
        """Handle memory clearing command"""
        return {
            'is_command': True,
            'action': 'clear_memory',
            'success': True
        }

    async def _handle_save_state(self, text: str, ui_controller) -> Dict[str, Any]:
        """Handle state saving command"""
        return {
            'is_command': True,
            'action': 'save_state',
            'success': True
        }

    async def _handle_switch_mode(self, text: str, ui_controller) -> Dict[str, Any]:
        """Handle mode switching command"""
        return {
            'is_command': True,
            'action': 'switch_mode',
            'success': True
        }


async def test_voice_interface():
    """Test the voice interface"""
    print("Testing Voice Interface...")

    # Create voice interface
    voice = VoiceInterface()

    # Set up callbacks
    voice.on_speech_start = lambda: print("🎤 Listening...")
    voice.on_speech_end = lambda: print("🔇 Processing...")
    voice.on_amplitude_update = lambda amp: print(f"📊 Amplitude: {'█' * int(amp * 20)}")

    # Start listening
    if voice.start_listening():
        print("Voice interface ready. Speak now...")

        # Listen for speech
        audio_data, max_amp = await voice.listen_for_speech()
        print(f"Max amplitude: {max_amp:.2f}")

        # Transcribe
        text = await voice.stt_engine.transcribe(audio_data)
        print(f"Transcribed: {text}")

        # Speak response
        response = f"你说的是：{text}"
        await voice.speak(response, emotion="neutral")

    # Cleanup
    voice.cleanup()
    print("Test complete!")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_voice_interface())
