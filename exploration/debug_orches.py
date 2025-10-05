import asyncio
import logging
import os
from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants
from livekit.agents import JobContext, WorkerOptions, cli
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

        tts_stream = await tts.synthesize(translated_text)

        async for frame in tts_stream:
            await audio_source.capture_frame(frame)

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

            # CRITICAL FIX: Ensure a unique identity for each room connection
            grant = VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_publish_data=True,
            )
            identity = f"translation-publisher-bot-{lang}"
            token = (
                AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
                .with_identity(identity)  # Unique identity
                .with_grants(grant)
                .to_jwt()
            )

            # ADDED FOR DEBUGGING: Log the identity being used for the connection
            logger.info(f"Generated token for room '{room_name}' with unique identity: '{identity}'")

            await room.connect(LIVEKIT_URL, token)
            translation_rooms[lang] = room
            logger.info(f"Successfully connected to translation room: {room_name}")
        except Exception as e:
            logger.error(f"Failed to connect to room {room_name}: {e}")
            continue

    # 2. Initialize the processing pipeline components
    stt = assemblyai.STT()
    vad = silero.VAD.load()
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
            # This is the line that was failing because the connection was closed.
            await room.local_participant.publish_track(track)
            await room.local_participant.publish_data(payload=b'', topic=f"subtitles-{lang}")
            logger.info(f"Published audio track and data channel for {lang} to room {room.name}")

    async def process_audio_stream(audio_stream: rtc.AudioStream):
        vad_stream = vad.stream(audio_stream)
        stt_stream = stt.stream(vad_stream)

        async for event in stt_stream:
            if event.type == assemblyai.STT.EventType.FINAL_TRANSCRIPT:
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

    def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
        if participant.identity == ctx.agent.identity or publication.kind != rtc.TrackKind.AUDIO:
            return

        logger.info(f"New audio track from participant {participant.identity}, starting processing pipeline.")
        audio_stream = rtc.AudioStream(publication.track)
        asyncio.create_task(process_audio_stream(audio_stream))

    speaker_room.on("track_published", on_track_published)

    # Handle participants who are already in the room
    for participant in speaker_room.remote_participants.values():
        for publication in participant.tracks.values():
            if publication.kind == rtc.TrackKind.AUDIO:
                on_track_published(publication, participant)

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

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

