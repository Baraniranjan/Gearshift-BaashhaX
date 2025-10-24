import asyncio
import logging
import os

import aiohttp
from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants
from livekit.agents import JobContext, WorkerOptions, cli, vad, stt, ChatContext
from livekit.plugins import openai, silero, assemblyai, sarvam


# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("translation-orchestrator")

# Your LiveKit server details from environment variables
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")

# Configuration for each translation target
TRANSLATION_CONFIG = {
    "kannada": {
        "room_name": "kannada-room",
        "lang_code": "kn-IN",
        "speaker": "anushka",
        "prompt": "You are a live translator. Translate the user's speech from English to Kannada. Respond concisely and accurately with only the translation."
    },
    "tamil": {
        "room_name": "tamil-room",
        "lang_code": "ta-IN",
        "speaker": "anushka",
        "prompt": "You are a live translator. Translate the user's speech from English to Tamil. Respond concisely and accurately with only the translation."
    },
    "hindi": {
        "room_name": "hindi-room",
        "lang_code": "hi-IN",
        "speaker": "anushka",
        "prompt": "You are a live translator. Translate the user's speech from English to Hindi. Respond concisely and accurately with only the translation."
    }
}


class TranslationPipeline:
    """
    A class that encapsulates the full VAD -> STT -> LLM -> TTS pipeline for a single speaker.
    It listens to one audio stream and fans out the translation to multiple languages.
    """

    def __init__(self, stt, llm, tts_engines, audio_sources, translation_rooms):
        self._stt = stt
        self._llm = llm
        self._tts_engines = tts_engines
        self._audio_sources = audio_sources
        self._translation_rooms = translation_rooms
        self._vad = silero.VAD.load(
            min_speech_duration=0.2,  # Very short minimum speech duration
            min_silence_duration=0.7,  # Shorter silence duration
            # padding_duration=200,  # Less padding
            activation_threshold=0.6,  # Lower threshold (more sensitive)
        )
        self._task = None
        self._pipe_audio_task = None
        self._pipe_vad_task = None

    def start(self, audio_stream: rtc.AudioStream):
        """Starts the translation pipeline for a given audio stream."""
        self._task = asyncio.create_task(self._run(audio_stream))

    async def _run(self, audio_stream: rtc.AudioStream):
        """
        The main processing loop for the pipeline. This uses the natural composition
        of the LiveKit Agent plugins to simplify the data flow.
        """
        logger.info("Starting pipeline processing")

        # 1. Create a VAD stream to detect speech.
        vad_stream = self._vad.stream()
        stt_stream = self._stt.stream()

        async def pipe_audio_to_vad():
            try:
                logger.info("Starting audio to VAD pipeline")
                frame_count = 0
                async for event in audio_stream:  # This gives us AudioFrameEvent
                    frame = event.frame  # Extract the actual audio frame
                    frame_count += 1
                    if frame_count % 100 == 0:  # Log every 100 frames
                        logger.info(
                            f"Received {frame_count} audio frames - Sample rate: {frame.sample_rate}Hz, Channels: {frame.num_channels}")
                    vad_stream.push_frame(frame)  # Push the actual frame, not the event
                logger.info(f"Audio stream ended after {frame_count} frames, closing VAD")
            except Exception as e:
                logger.error(f"Error in audio to VAD pipeline: {e}", exc_info=True)
            finally:
                await vad_stream.aclose()

        async def pipe_vad_to_stt():
            try:
                logger.info("Starting VAD to STT pipeline")
                event_count = 0
                async for event in vad_stream:
                    event_count += 1
                    # logger.info(f"VAD event #{event_count}: {event.type}")

                    if event.type == vad.VADEventType.START_OF_SPEECH:
                        logger.info("🎤 Speech started")
                    elif event.type == vad.VADEventType.END_OF_SPEECH:
                        logger.info(f"🎤 Speech ended, pushing {len(event.frames)} frames to STT")
                        for frame in event.frames:
                            stt_stream.push_frame(frame)
                    # elif event.type == vad.VADEventType.INFERENCE_DONE:
                        # logger.info(f"VAD inference done - Speech probability: {event.probability}")

                logger.info(f"VAD stream ended after {event_count} events, closing STT")
            except Exception as e:
                logger.error(f"Error in VAD to STT pipeline: {e}", exc_info=True)
            finally:
                await stt_stream.aclose()

        self._pipe_audio_task = asyncio.create_task(pipe_audio_to_vad())
        self._pipe_vad_task = asyncio.create_task(pipe_vad_to_stt())

        try:
            logger.info("Starting STT event processing")
            async for event in stt_stream:
                logger.info(f"STT event: {event.type}")

                if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                    # Access text via alternatives (this is the correct way)
                    text = event.alternatives[0].text if event.alternatives else ""
                    logger.info(f"STT transcript: '{text}'")

                    if not text or len(text.strip()) < 2:
                        logger.info("Skipping empty or too short transcript")
                        continue

                    logger.info(f"🎤 Speaker said: '{text}'")

                    # Process translations
                    translation_tasks = []
                    for lang, config in TRANSLATION_CONFIG.items():
                        room = self._translation_rooms.get(lang)
                        if not room:
                            logger.warning(f"No room found for language: {lang}")
                            continue

                        task = asyncio.create_task(
                            self._translate_and_publish_task(
                                lang=lang,
                                text=text,
                                llm=self._llm,
                                tts=self._tts_engines[lang],
                                audio_source=self._audio_sources[lang],
                                participant=room.local_participant
                            )
                        )
                        translation_tasks.append(task)

                    if translation_tasks:
                        results = await asyncio.gather(*translation_tasks, return_exceptions=True)
                        for i, result in enumerate(results):
                            if isinstance(result, Exception):
                                logger.error(f"Translation task {i} failed: {result}")
                            else:
                                logger.info(f"Translation task {i} completed successfully")
                    else:
                        logger.warning("No translation tasks created")

                elif event.type == stt.SpeechEventType.INTERIM_TRANSCRIPT:
                    # Optional: Log interim results for debugging
                    text = event.alternatives[0].text if event.alternatives else ""
                    logger.info(f"📝 Interim transcript: '{text}'")

        except Exception as e:
            logger.error(f"Error in STT processing: {e}", exc_info=True)
        finally:
            logger.info("Cleaning up pipeline tasks")

            # Graceful cleanup
            if self._pipe_audio_task and not self._pipe_audio_task.done():
                self._pipe_audio_task.cancel()
            if self._pipe_vad_task and not self._pipe_vad_task.done():
                self._pipe_vad_task.cancel()

            # Wait for tasks to complete
            await asyncio.gather(
                self._pipe_audio_task,
                self._pipe_vad_task,
                return_exceptions=True
            )
            logger.info("Pipeline cleanup completed")

    async def _translate_and_publish_task(self, lang: str, text: str, llm, tts: sarvam.TTS,
                                          audio_source: rtc.AudioSource, participant: rtc.LocalParticipant):
        """
        Handles the translation and TTS publishing for a single language.
        """
        try:
            logger.info(f"Translating to {lang}: '{text}'")
            chat_ctx = ChatContext()
            chat_ctx.add_message(role="system", content=TRANSLATION_CONFIG[lang]["prompt"])
            chat_ctx.add_message(role="user", content=text)
            # The standard OpenAI client uses the 'messages' keyword
            translated_text = ""
            async with llm.chat(chat_ctx=chat_ctx) as stream:
                async for chunk in stream:
                    # CORRECTED: Add a safety check for the delta object
                    if chunk.delta and chunk.delta.content:
                        translated_text += chunk.delta.content
            logger.info(f"Translation completed for {lang}: '{translated_text}'")

            if not translated_text:
                logger.warning(f"Translation for {lang} resulted in empty text.")
                return

            logger.info(f"Translated to {lang}: '{translated_text}'")

            await participant.publish_data(
                payload=translated_text.encode('utf-8'),
                topic=f"subtitles-{lang}"
            )
            logger.info(f"Published subtitle to {lang} data channel.")

            logger.info(f"Synthesizing TTS for '{translated_text}'")
            tts_stream = tts.synthesize(translated_text)

            frame_count = 0
            async for frame in tts_stream:
                # DEBUG: Check the actual frame properties
                if frame_count == 0:
                    logger.info(
                        f"TTS Frame - Sample rate: {frame.frame.sample_rate}Hz, Channels: {frame.frame.num_channels}")
                    logger.info(
                        f"AudioSource - Expected sample rate: {audio_source.sample_rate}Hz, Channels: {audio_source.num_channels}")

                await audio_source.capture_frame(frame.frame)
                frame_count += 1

            logger.info(f"Published {frame_count} audio frames for {lang}.")

        except Exception as e:
            logger.error(f"Error in translation/publishing for {lang}: {e}")

    async def close(self):
        """Shuts down the pipeline task."""
        logger.info("Closing translation pipeline")

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Pipeline task cancelled successfully")
            except Exception as e:
                logger.error(f"Error closing pipeline task: {e}")

        logger.info("Translation pipeline closed")


async def test_audio_stream(audio_stream):
    """Test function to verify audio stream is working"""
    logger.info("Testing audio stream...")
    frame_count = 0
    start_time = asyncio.get_event_loop().time()

    try:
        async for event in audio_stream:
            frame_count += 1
            current_time = asyncio.get_event_loop().time()

            if frame_count == 1:
                # Access the frame from the event
                frame = event.frame
                logger.info(
                    f"First audio frame received: {frame.samples_per_channel} samples, {frame.sample_rate}Hz, {frame.num_channels} channels")

            if current_time - start_time > 5:  # Test for 5 seconds
                break

        logger.info(f"Audio test completed: {frame_count} frames in 5 seconds")
        return frame_count > 0
    except Exception as e:
        logger.error(f"Audio stream test failed: {e}", exc_info=True)
        return False


async def test_audio_stream_wrapper(audio_stream, participant_id):
    """Wrapper to test audio stream without interfering with main pipeline"""
    logger.info(f"Testing audio stream for participant: {participant_id}")
    # This is just for testing - create a separate stream
    test_stream = rtc.AudioStream(audio_stream._track)
    has_audio = await test_audio_stream(test_stream)
    logger.info(f"Audio test result for {participant_id}: {has_audio}")

async def entrypoint(ctx: JobContext):
    """
    The main entrypoint for the Orchestrator Agent.
    """
    logger.info("Starting multi-language translation orchestrator agent")
    speaker_room = ctx.room
    logger.info(f"Agent joined speaker room: {speaker_room.name}")


    async with aiohttp.ClientSession() as http_session:


        # 1. Setup connections to all translation rooms
        translation_rooms = {}
        for lang, config in TRANSLATION_CONFIG.items():
            # ... (connection logic remains the same)
            room_name = config["room_name"]
            logger.info(f"Attempting to connect to translation room: {room_name}")
            try:
                room = rtc.Room()
                grant = VideoGrants(room_join=True, room=room_name, can_publish=True, can_publish_data=True)
                identity = f"translation-publisher-bot-{lang}"
                token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET).with_identity(identity).with_grants(grant).to_jwt()
                await room.connect(LIVEKIT_URL, token)
                translation_rooms[lang] = room
                logger.info(f"Successfully connected to translation room: {room_name}")
            except Exception as e:
                logger.error(f"Failed to connect to room {room_name}: {e}")
                continue

        logger.info(f"Connected to {len(translation_rooms)} translation rooms")
        for lang, room in translation_rooms.items():
            logger.info(f"Room {lang}: {room.name} - Connected: {room.connection_state}")

        # 2. Initialize the processing pipeline components
        stt_instance = assemblyai.STT(http_session=http_session)  # This creates the AssemblyAI STT instance
        llm = openai.LLM.with_azure() #model='gpt-5-mini'
        tts_engines = {
            lang: sarvam.TTS(target_language_code=config["lang_code"], speaker=config["speaker"],http_session=http_session)
            for lang, config in TRANSLATION_CONFIG.items()
        }

        # 3. Create audio tracks and data channels for publishing
        audio_sources = {}
        for lang, config in TRANSLATION_CONFIG.items():
            room = translation_rooms.get(lang)
            if room:
                # Create audio source with proper sample rate
                audio_source = rtc.AudioSource(22050, 1)  # Match TTS output sample rate
                audio_sources[lang] = audio_source

                # Create and publish audio track
                track = rtc.LocalAudioTrack.create_audio_track(f"{lang}-translation", audio_source)
                # options = rtc.TrackPublishOptions()
                # options.source = rtc.TrackSource.SOURCE_MICROPHONE

                # audio_source = rtc.AudioSource(24000, 1)
                # audio_sources[lang] = audio_source
                # track = rtc.LocalAudioTrack.create_audio_track(f"{lang}-translation", audio_source)
                # await room.local_participant.publish_track(track)

                await room.local_participant.publish_track(track)
                logger.info(f"Published audio track for {lang} to room {room.name}")
        logger.info(f"Created {len(audio_sources)} audio sources")
        for lang in audio_sources:
            logger.info(f"Audio source created for: {lang}")
        # Dictionary to store an active pipeline for each participant
        pipelines: dict[str, TranslationPipeline] = {}

        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication,
                                participant: rtc.RemoteParticipant):
            logger.info(f"Track subscribed - Kind: {track.kind}, Participant: {participant.identity}")
            logger.info(f"Track details - Muted: {track.muted}, Source: {publication.source}")

            if track.kind == rtc.TrackKind.KIND_AUDIO:
                if participant.identity in pipelines:
                    logger.warning(f"Pipeline already exists for participant: {participant.identity}")
                    return

                logger.info(f"Starting translation pipeline for participant: {participant.identity}")
                audio_stream = rtc.AudioStream(track)

                asyncio.create_task(test_audio_stream_wrapper(audio_stream, participant.identity))

                # Test audio stream first
                asyncio.create_task(test_audio_stream_wrapper(audio_stream, participant.identity))

                pipeline = TranslationPipeline(
                    stt=stt_instance,
                    llm=llm,
                    tts_engines=tts_engines,
                    audio_sources=audio_sources,
                    translation_rooms=translation_rooms,
                )
                pipelines[participant.identity] = pipeline
                pipeline.start(audio_stream)
            else:
                logger.info(f"Ignoring non-audio track: {track.kind}")

        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            # The speaker has left, clean up their translation pipeline
            if participant.identity in pipelines:
                logger.info(f"Closing translation pipeline for disconnected participant: {participant.identity}")
                pipeline = pipelines.pop(participant.identity)
                asyncio.create_task(pipeline.close())

        speaker_room.on("track_subscribed", on_track_subscribed)
        speaker_room.on("participant_disconnected", on_participant_disconnected)

        await ctx.connect()

        async def log_room_status():
            while True:
                await asyncio.sleep(10)  # Log every 10 seconds
                logger.info(f"Speaker room participants: {len(speaker_room.remote_participants)}")
                for participant in speaker_room.remote_participants.values():
                    logger.info(f"Participant {participant.identity}: {len(participant.track_publications)} tracks")
                    for pub in participant.track_publications.values():
                        logger.info(f"  Track: {pub.source}, Muted: {pub.muted}, Subscribed: {pub.subscribed}")

        asyncio.create_task(log_room_status())

        logger.info("Orchestrator is running and waiting for speaker.")
        try:
            await asyncio.Event().wait()
        finally:
            logger.info("Shutting down orchestrator.")
            for pipeline in pipelines.values():
                await pipeline.close()
            for room in translation_rooms.values():
                await room.disconnect()


if __name__ == "__main__":
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        raise ValueError("LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET must be set in environment variables.")

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="translation-orchestrator"))

