import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants
from livekit.agents import JobContext, WorkerOptions, cli, vad
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


async def translate_and_publish(lang: str, text: str, llm: openai.LLM, tts: sarvam.TTS, audio_source: rtc.AudioSource,
                                participant: rtc.LocalParticipant):
    """
    Handles the translation and TTS publishing for a single language.
    """
    try:
        logger.info(f"Translating to {lang}: '{text}'")

        llm_stream = llm.chat(
            messages=[
                {"role": "system", "content": TRANSLATION_CONFIG[lang]["prompt"]},
                {"role": "user", "content": text}
            ]
        )

        translated_text = "".join([chunk.delta.content async for chunk in llm_stream])

        if not translated_text:
            logger.warning(f"Translation for {lang} resulted in empty text.")
            return

        logger.info(f"Translated to {lang}: '{translated_text}'")

        await participant.publish_data(
            payload=translated_text.encode('utf-8'),
            topic=f"subtitles-{lang}"
        )
        logger.info(f"Published subtitle to {lang} data channel.")

        # ADDED LOGGING: Track TTS synthesis and audio frame publishing
        logger.info(f"Synthesizing TTS for '{translated_text}'")
        tts_stream = await tts.synthesize(translated_text)

        frame_count = 0
        async for frame in tts_stream:
            await audio_source.capture_frame(frame)
            frame_count += 1

        logger.info(f"Published {frame_count} audio frames for {lang}.")

    except Exception as e:
        logger.error(f"Error in translation/publishing for {lang}: {e}")


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

            grant = VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_publish_data=True,
            )
            identity = f"translation-publisher-bot-{lang}"
            token = (
                AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
                .with_identity(identity)
                .with_grants(grant)
                .to_jwt()
            )

            await room.connect(LIVEKIT_URL, token)
            translation_rooms[lang] = room
            logger.info(f"Successfully connected to translation room: {room_name}")
        except Exception as e:
            logger.error(f"Failed to connect to room {room_name}: {e}")
            continue

    # 2. Initialize the processing pipeline components
    stt = assemblyai.STT()
    vad_plugin = silero.VAD.load()
    llm = openai.LLM.with_azure()
    tts_engines = {
        lang: sarvam.TTS(target_language_code=config["lang_code"], speaker=config["speaker"])
        for lang, config in TRANSLATION_CONFIG.items()
    }

    # 3. Create audio tracks and data channels for publishing
    audio_sources = {lang: rtc.AudioSource(48000, 1) for lang in TRANSLATION_CONFIG}
    for lang, source in audio_sources.items():
        room = translation_rooms.get(lang)
        if room:
            track = rtc.LocalAudioTrack.create_audio_track(f"{lang}-translation", source)
            await room.local_participant.publish_track(track)
            await room.local_participant.publish_data(payload=b'', topic=f"subtitles-{lang}")
            logger.info(f"Published audio track and data channel for {lang} to room {room.name}")

    async def process_audio_stream(audio_stream: rtc.AudioStream):
        # Create the VAD and STT stream processors.
        # They are initialized without arguments.
        vad_stream = vad_plugin.stream()
        stt_stream = stt.stream()

        # Create two background tasks to handle the audio pipeline:
        # 1. Pipe raw audio from the speaker into the VAD stream.
        # 2. Pipe the detected speech from the VAD stream into the STT stream.

        async def pipe_raw_audio_to_vad():
            """Pushes frames from the incoming audio stream into the VAD."""
            async for frame in audio_stream:
                vad_stream.push_frame(frame)
            await vad_stream.aclose()

        async def pipe_vad_to_stt():
            """Pushes frames from VAD events into the STT engine."""
            async for event in vad_stream:
                if event.type in [vad.VADEventType.START_OF_SPEECH, vad.VADEventType.INFERENCE_DONE, vad.VADEventType.END_OF_SPEECH]:
                    if event.speaking:
                        for frame in event.frames:
                            stt_stream.push_frame(frame)
            await stt_stream.aclose()

        # Start the pipeline tasks to run in the background
        asyncio.create_task(pipe_raw_audio_to_vad())
        asyncio.create_task(pipe_vad_to_stt())

        # Now, consume the final output from the STT stream to get transcripts
        async for event in stt_stream:
            if event.type == assemblyai.STTEventType.FINAL_TRANSCRIPT:
                text = event.transcript.text
                if not text:
                    continue

                logger.info(f"Speaker said: '{text}'")

                translation_tasks = []
                for lang, config in TRANSLATION_CONFIG.items():
                    room = translation_rooms.get(lang)
                    if not room: continue

                    task = asyncio.create_task(
                        translate_and_publish(
                            lang=lang,
                            text=text,
                            llm=llm,
                            tts=tts_engines[lang],
                            audio_source=audio_sources[lang],
                            participant=room.local_participant
                        )
                    )
                    translation_tasks.append(task)

                await asyncio.gather(*translation_tasks)

    # UPDATED: Use on_track_subscribed for reliability
    def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        # Ignore tracks from the agent itself
        if participant.identity == speaker_room.local_participant.identity:
            logger.info(f"Ignoring agent's own track: {participant.identity}")
            return

        # Process audio tracks from other participants (speakers)
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"Subscribed to a new audio track from participant {participant.identity}, starting processing pipeline.")
            # The 'track' object is now guaranteed to be valid
            audio_stream = rtc.AudioStream(track)
            asyncio.create_task(process_audio_stream(audio_stream))

    # UPDATED: Listen for 'track_subscribed' instead of 'track_published'
    speaker_room.on("track_subscribed", on_track_subscribed)

    # REMOVED: This loop is no longer necessary, as 'track_subscribed' will fire
    # for existing participants automatically when auto-subscribe is enabled.

    await ctx.connect()

    logger.info("Orchestrator is running and waiting for speaker.")
    try:
        await asyncio.Event().wait()
    finally:
        logger.info("Shutting down orchestrator.")
        for room in translation_rooms.values():
            await room.disconnect()


if __name__ == "__main__":
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        raise ValueError("LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET must be set in environment variables.")

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="translation-orchestrator"))

