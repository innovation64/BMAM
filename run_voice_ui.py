#!/usr/bin/env python3
"""
Launch script for BMAM Voice Anime UI
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.coordination.brain_coordinator import BrainInspiredCoordinator
from src.ui.web_ui_server import WebUIServer


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for Voice UI"""

    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                   BMAM Voice Anime UI                        ║
    ║                                                              ║
    ║  Featuring: Yaoguang (摇光明明) - Your Memory Assistant     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    logger.info("Initializing BMAM system...")

    # Initialize BMAM coordinator
    coordinator = BrainInspiredCoordinator()
    await coordinator.initialize()
    logger.info("BMAM coordinator ready")

    # Create and start web server
    server = WebUIServer(coordinator, host="0.0.0.0", port=8080)

    if await server.start():
        print(f"""
    ✅ Voice Anime UI is running!

    🌐 Open your browser and navigate to:
       http://localhost:8080

    📱 Or access from other devices at:
       http://YOUR_IP_ADDRESS:8080

    🎤 Make sure your microphone is connected
    🔊 Check your speakers/headphones for audio output

    Press Ctrl+C to stop the server
        """)

        try:
            # Keep server running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down Voice UI...")
    else:
        logger.error("Failed to start Voice UI server")
        sys.exit(1)

    # Cleanup
    await server.stop()
    await coordinator.stop_system()
    logger.info("Voice UI shutdown complete")


def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []

    try:
        import aiohttp
    except ImportError:
        missing.append("aiohttp")

    try:
        import numpy
    except ImportError:
        missing.append("numpy")

    # Check optional audio dependencies
    audio_missing = []
    try:
        import pyaudio
    except ImportError:
        audio_missing.append("pyaudio")

    try:
        import speech_recognition
    except ImportError:
        audio_missing.append("SpeechRecognition")

    try:
        import gtts
    except ImportError:
        audio_missing.append("gtts")

    try:
        import pydub
    except ImportError:
        audio_missing.append("pydub")

    if missing:
        print(f"❌ Missing required dependencies: {', '.join(missing)}")
        print(f"   Install with: pip install {' '.join(missing)}")
        return False

    if audio_missing:
        print(f"⚠️  Audio features unavailable. Missing: {', '.join(audio_missing)}")
        print(f"   For full voice support, install with:")
        print(f"   pip install -r requirements_voice_ui.txt")

        response = input("\nContinue without voice features? (y/n): ")
        if response.lower() != 'y':
            return False

    return True


if __name__ == "__main__":
    if not check_dependencies():
        sys.exit(1)

    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)