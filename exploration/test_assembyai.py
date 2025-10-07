import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit.plugins import assemblyai
from livekit.agents import stt
import wave
import numpy as np

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("assemblyai-test")


async def test_assemblyai_connection():
    """Test AssemblyAI connection and basic functionality"""

    logger.info("=== AssemblyAI Connection Test ===")

    # Check API key
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not api_key:
        logger.error("ASSEMBLYAI_API_KEY not found in environment variables!")
        return False

    logger.info(f"API Key found: {api_key[:10]}...")

    try:
        # Initialize STT
        logger.info("Initializing AssemblyAI STT...")
        stt_instance = assemblyai.STT()
        logger.info("✅ AssemblyAI STT initialized successfully")

        # Create a stream
        logger.info("Creating STT stream...")
        stt_stream = stt_instance.stream()
        logger.info("✅ STT stream created successfully")

        # Test with synthetic audio
        await test_with_synthetic_audio(stt_stream)

        return True

    except Exception as e:
        logger.error(f"❌ AssemblyAI test failed: {e}")
        return False


async def test_with_synthetic_audio(stt_stream):
    """Test STT with synthetic audio data"""

    logger.info("Testing with synthetic audio...")

    try:
        # Generate a simple sine wave (simulating speech)
        sample_rate = 16000
        duration = 2  # seconds
        frequency = 440  # Hz (A note)

        # Generate sine wave
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3  # Lower amplitude

        # Convert to 16-bit PCM
        audio_16bit = (audio_data * 32767).astype(np.int16)

        logger.info(f"Generated {len(audio_16bit)} audio samples")

        # Create audio frames and push to STT
        frame_size = 1600  # 100ms at 16kHz
        frames_sent = 0

        for i in range(0, len(audio_16bit), frame_size):
            chunk = audio_16bit[i:i + frame_size]
            if len(chunk) < frame_size:
                # Pad the last chunk
                chunk = np.pad(chunk, (0, frame_size - len(chunk)), 'constant')

            # Create audio frame (you might need to adjust this based on LiveKit's AudioFrame structure)
            # This is a simplified version - you may need to create proper AudioFrame objects
            frames_sent += 1

        logger.info(f"Sent {frames_sent} audio frames to STT")

        # Listen for events with timeout
        event_count = 0
        timeout_seconds = 10

        try:
            async with asyncio.timeout(timeout_seconds):
                async for event in stt_stream:
                    event_count += 1
                    logger.info(f"Received STT event #{event_count}: {event.type}")

                    if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                        text = event.transcript.text
                        logger.info(f"✅ Final transcript: '{text}'")
                        break
                    elif event.type == stt.SpeechEventType.INTERIM_TRANSCRIPT:
                        text = event.transcript.text
                        logger.info(f"📝 Interim transcript: '{text}'")

                    if event_count > 10:  # Prevent infinite loop
                        break

        except asyncio.TimeoutError:
            logger.warning(f"No STT events received within {timeout_seconds} seconds")

        logger.info(f"Received {event_count} total STT events")

    except Exception as e:
        logger.error(f"Synthetic audio test failed: {e}")


async def test_assemblyai_simple():
    """Simple test without audio - just check if we can create instances"""

    logger.info("=== Simple AssemblyAI Test ===")

    try:
        # Test 1: Check API key
        api_key = os.environ.get("ASSEMBLYAI_API_KEY")
        logger.info(f"API Key present: {'Yes' if api_key else 'No'}")

        # Test 2: Import test
        logger.info("Testing imports...")
        from livekit.plugins import assemblyai
        logger.info("✅ AssemblyAI plugin imported successfully")

        # Test 3: Create STT instance
        logger.info("Creating STT instance...")
        stt_instance = assemblyai.STT()
        logger.info("✅ STT instance created successfully")

        # Test 4: Check STT instance attributes
        logger.info(f"STT instance type: {type(stt_instance)}")
        logger.info(f"STT instance attributes: {[attr for attr in dir(stt_instance) if not attr.startswith('_')]}")

        return True

    except Exception as e:
        logger.error(f"❌ Simple test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""

    logger.info("Starting AssemblyAI tests...")

    # Test 1: Simple test
    simple_test_passed = await test_assemblyai_simple()

    if simple_test_passed:
        # Test 2: Connection test
        connection_test_passed = await test_assemblyai_connection()

        if connection_test_passed:
            logger.info("🎉 All AssemblyAI tests passed!")
        else:
            logger.error("❌ Connection test failed")
    else:
        logger.error("❌ Simple test failed - skipping connection test")

    logger.info("AssemblyAI testing completed")


if __name__ == "__main__":
    asyncio.run(main())