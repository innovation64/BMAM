"""
Audio Processing Mixin
音频处理器 - 负责处理浏览器音频数据和格式转换
"""

import asyncio
import base64
import tempfile
import os
import logging
from typing import Dict, Any

try:
    from aiohttp import web
except ImportError:
    pass

logger = logging.getLogger(__name__)


class AudioProcessingMixin:
    """音频处理和格式转换"""

    async def handle_browser_audio(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """处理从浏览器接收的音频数据"""
        try:
            # Get base64 audio data
            audio_base64 = data.get('audio', '')
            audio_format = data.get('format', 'webm')

            if not audio_base64:
                await ws.send_json({
                    'type': 'error',
                    'message': 'No audio data received'
                })
                return

            # Decode base64 audio
            audio_bytes = base64.b64decode(audio_base64)
            logger.info(f"Received {len(audio_bytes)} bytes of {audio_format} audio")

            # Save to temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{audio_format}') as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name

            try:
                # Convert audio format if needed (webm to wav)
                wav_path = await self.convert_audio_to_wav(tmp_path)

                # Read WAV file
                with open(wav_path, 'rb') as f:
                    wav_audio = f.read()

                # Send to speech recognition
                await ws.send_json({
                    'type': 'processing',
                    'message': 'Transcribing audio...'
                })

                text = await self.voice.stt_engine.transcribe(wav_audio)

                if text:
                    logger.info(f"Transcribed text: {text}")

                    # Send transcription to client
                    await ws.send_json({
                        'type': 'transcription',
                        'text': text
                    })

                    # Process through BMAM
                    await ws.send_json({
                        'type': 'processing',
                        'message': 'Processing with BMAM...'
                    })

                    response = await self.ui.process_voice_input(text.encode())

                    # Send response
                    await ws.send_json({
                        'type': 'response',
                        'text': response
                    })
                else:
                    await ws.send_json({
                        'type': 'error',
                        'message': '无法识别语音，请再试一次'
                    })

                # Cleanup
                if os.path.exists(wav_path) and wav_path != tmp_path:
                    os.unlink(wav_path)

            finally:
                # Cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Error processing browser audio: {e}", exc_info=True)
            await ws.send_json({
                'type': 'error',
                'message': f'音频处理错误: {str(e)}'
            })

    async def convert_audio_to_wav(self, input_path: str) -> str:
        """
        将音频文件转换为WAV格式

        Args:
            input_path: 输入音频文件路径

        Returns:
            转换后的WAV文件路径
        """
        try:
            from pydub import AudioSegment

            # Detect format from extension
            ext = input_path.split('.')[-1].lower()

            # Load audio
            if ext == 'webm':
                audio = AudioSegment.from_file(input_path, format='webm')
            else:
                audio = AudioSegment.from_file(input_path)

            # Convert to mono, 16kHz (optimal for speech recognition)
            audio = audio.set_channels(1)
            audio = audio.set_frame_rate(16000)
            audio = audio.set_sample_width(2)  # 16-bit

            # Export as WAV
            output_path = input_path.replace(f'.{ext}', '.wav')
            audio.export(output_path, format='wav')

            logger.info(f"Converted {input_path} to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Audio conversion error: {e}")
            # If conversion fails, return original path
            return input_path

    async def handle_voice_input(self, ws: web.WebSocketResponse):
        """处理来自客户端的语音输入"""
        if not self.voice.start_listening():
            await ws.send_json({
                'type': 'error',
                'message': 'Failed to start voice input'
            })
            return

        # Set up amplitude callback
        async def send_amplitude(amp: float):
            await ws.send_json({
                'type': 'amplitude',
                'value': amp
            })

        self.voice.on_amplitude_update = lambda amp: asyncio.create_task(send_amplitude(amp))

        # Listen for speech
        audio_data, _ = await self.voice.listen_for_speech()

        # Transcribe
        text = await self.voice.stt_engine.transcribe(audio_data)

        # Send transcription
        await ws.send_json({
            'type': 'transcription',
            'text': text
        })

        # Process through BMAM
        response = await self.ui.process_voice_input(audio_data)

        # Send response
        await ws.send_json({
            'type': 'response',
            'text': response
        })

        # Speak response
        await self.voice.speak(response, emotion="neutral")
