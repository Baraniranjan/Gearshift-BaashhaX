import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants
from livekit.agents import JobContext, WorkerOptions, cli, vad, stt
from livekit.plugins import openai, silero, deepgram, sarvam
import openai as openai_client  # For direct API calls

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("translation-orchestrator")

# Your LiveKit server details
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

# Initialize OpenAI client for translations
openai_translation_client = openai_client.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)


class TranslationPipeline:
    """
    A class that encapsulates the full VAD -> STT -> LLM -> TTS pipeline for a single speaker.
    It listens to one audio stream and fans out the translation to multiple languages.
    """

    def __init__(self, stt, tts_engines, audio_sources, translation_rooms):
        self._stt = stt
        self._tts_engines = tts_engines
        self._audio_sources = audio_sources
        self._translation_rooms = translation_rooms
        self._vad = silero.VAD.load(
            min_speech_duration=0.2,
            min_silence_duration=0.7,
            activation_threshold=0.6,
        )
        self._task = None
        self._pipe_audio_task = None
        self._pipe_vad_task = None

    def start(self, audio_stream: rtc.AudioStream):
        """Starts the translation pipeline for a given audio stream."""
        self._task = asyncio.create_task(self._run(audio_stream))

    async def _run(self, audio_stream: rtc.AudioStream):
        """
        The main processing loop for the pipeline.
        """
        logger.info("Starting pipeline processing")

        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                # Create streams
                vad_stream = self._vad.stream()
                stt_stream = self._stt.stream()

                async def pipe_audio_to_vad():
                    try:
                        logger.info("Starting audio to VAD pipeline")
                        frame_count = 0
                        async for event in audio_stream:
                            frame = event.frame
                            frame_count += 1
                            if frame_count % 100 == 0:
                                logger.info(f"Received {frame_count} audio frames")
                            vad_stream.push_frame(frame)
                        logger.info(f"Audio stream ended after {frame_count} frames")
                    except Exception as e:
                        logger.error(f"Error in audio to VAD pipeline: {e}")
                    finally:
                        await vad_stream.aclose()

                async def pipe_vad_to_stt():
                    try:
                        logger.info("Starting VAD to STT pipeline")
                        event_count = 0
                        async for event in vad_stream:
                            event_count += 1
                            logger.info(f"VAD event #{event_count}: {event.type}")

                            if event.type == vad.VADEventType.END_OF_SPEECH:
                                logger.info(f"🎤 Speech ended, pushing {len(event.frames)} frames to STT")
                                for frame in event.frames:
                                    stt_stream.push_frame(frame)
                    except Exception as e:
                        logger.error(f"Error in VAD to STT pipeline: {e}")
                    finally:
                        await stt_stream.aclose()

                # Start background tasks
                self._pipe_audio_task = asyncio.create_task(pipe_audio_to_vad())
                self._pipe_vad_task = asyncio.create_task(pipe_vad_to_stt())

                # Process STT events
                logger.info("Starting STT event processing")
                async for event in stt_stream:
                    logger.info(f"STT event: {event.type}")

                    if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
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

                # If we get here, everything worked
                logger.info("STT processing completed successfully")
                break

            except Exception as e:
                retry_count += 1
                logger.error(f"Error in STT processing (attempt {retry_count}/{max_retries}): {e}")

                if retry_count < max_retries:
                    logger.info(f"Retrying in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    logger.error("Max retries reached, giving up")
                    break
            finally:
                # Cleanup
                if hasattr(self, '_pipe_audio_task') and self._pipe_audio_task:
                    self._pipe_audio_task.cancel()
                if hasattr(self, '_pipe_vad_task') and self._pipe_vad_task:
                    self._pipe_vad_task.cancel()

    async def _translate_and_publish_task(self, lang: str, text: str, tts: sarvam.TTS,
                                          audio_source: rtc.AudioSource, participant: rtc.LocalParticipant):
        """
        Handles the translation and TTS publishing for a single language using OpenAI GPT-4o-mini.
        """
        try:
            logger.info(f"Translating to {lang}: '{text}'")

            # Use OpenAI GPT-4o-mini for translation
            loop = asyncio.get_event_loop()

            def sync_translate():
                response = openai_translation_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": TRANSLATION_CONFIG[lang]["prompt"]},
                        {"role": "user", "content": text}
                    ],
                    max_tokens=200,
                    temperature=0.3  # Lower temperature for consistent translations
                )
                return response.choices[0].message.content

            # Run translation in thread pool to avoid blocking
            translated_text = await loop.run_in_executor(None, sync_translate)

            if not translated_text:
                logger.warning(f"Translation for {lang} resulted in empty text.")
                return

            logger.info(f"Translated to {lang}: '{translated_text}'")

            # Publish subtitle
            await participant.publish_data(
                payload=translated_text.encode('utf-8'),
                topic=f"subtitles-{lang}"
            )
            logger.info(f"Published subtitle to {lang} data channel.")

            # TTS Synthesis
            logger.info(f"Synthesizing TTS for '{translated_text}'")
            tts_stream = await tts.synthesize(translated_text)

            frame_count = 0
            async for frame in tts_stream:
                await audio_source.capture_frame(frame)
                frame_count += 1

            logger.info(f"Published {frame_count} audio frames for {lang}.")

        except Exception as e:
            logger.error(f"Error in translation/publishing for {lang}: {e}", exc_info=True)

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


async def entrypoint(ctx: JobContext):
    """
    The main entrypoint for the Orchestrator Agent.
    """
    logger.info("Starting multi-language translation orchestrator agent")
    speaker_room = ctx.room
    logger.info(f"Agent joined speaker room: {speaker_room.name}")

    # 1. Setup connections to all translation rooms
    translation_rooms = {}
    for lang, config in TRANSLATION_CONFIG.items():
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

    # 2. Initialize the processing pipeline components
    stt_instance = deepgram.STT(
        model="nova-2",
        language="en",
        smart_format=True,
        interim_results=True,
    )

    tts_engines = {
        lang: sarvam.TTS(target_language_code=config["lang_code"], speaker=config["speaker"])
        for lang, config in TRANSLATION_CONFIG.items()
    }

    # 3. Create audio tracks and data channels for publishing
    audio_sources = {}
    for lang, config in TRANSLATION_CONFIG.items():
        room = translation_rooms.get(lang)
        if room:
            audio_source = rtc.AudioSource(24000, 1)
            audio_sources[lang] = audio_source

            track = rtc.LocalAudioTrack.create_audio_track(f"{lang}-translation", audio_source)
            options = rtc.TrackPublishOptions()
            options.source = rtc.TrackSource.SOURCE_MICROPHONE

            await room.local_participant.publish_track(track, options)
            logger.info(f"Published audio track for {lang} to room {room.name}")

    # Dictionary to store an active pipeline for each participant
    pipelines: dict[str, TranslationPipeline] = {}

    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication,
                            participant: rtc.RemoteParticipant):
        logger.info(f"Track subscribed - Kind: {track.kind}, Participant: {participant.identity}")

        if track.kind == rtc.TrackKind.KIND_AUDIO:
            if participant.identity in pipelines:
                logger.warning(f"Pipeline already exists for participant: {participant.identity}")
                return

            logger.info(f"Starting translation pipeline for participant: {participant.identity}")
            audio_stream = rtc.AudioStream(track)

            pipeline = TranslationPipeline(
                stt=stt_instance,
                tts_engines=tts_engines,
                audio_sources=audio_sources,
                translation_rooms=translation_rooms,
            )
            pipelines[participant.identity] = pipeline
            pipeline.start(audio_stream)
        else:
            logger.info(f"Ignoring non-audio track: {track.kind}")

    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        if participant.identity in pipelines:
            logger.info(f"Closing translation pipeline for disconnected participant: {participant.identity}")
            pipeline = pipelines.pop(participant.identity)
            asyncio.create_task(pipeline.close())

    speaker_room.on("track_subscribed", on_track_subscribed)
    speaker_room.on("participant_disconnected", on_participant_disconnected)

    await ctx.connect()

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

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="speech-to-speech-orchestrator"))