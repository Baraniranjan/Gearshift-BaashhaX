import asyncio
import logging
import os
import time
import openai as direct_openai  # Add this import

import aiohttp
from dotenv import load_dotenv
from livekit import rtc
from livekit.api import AccessToken, VideoGrants
from livekit.agents import JobContext, WorkerOptions, cli, vad, stt, ChatContext
from livekit.plugins import openai, silero, assemblyai, sarvam, elevenlabs

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Silence noisy loggers completely
noisy_loggers = [
    "httpcore",
    "httpx",
    "openai._base_client",
    "asyncio",
    "livekit",
    "httpcore.connection",
    "httpcore.http11"
]

for logger_name in noisy_loggers:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

# Keep your main logger at INFO level
logger = logging.getLogger("translation-orchestrator")

# Your LiveKit server details from environment variables
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")

# Configuration for each translation target
# TRANSLATION_CONFIG = {
#     "kannada": {
#         "room_name": "kannada-room",
#         "lang_code": "kn-IN",
#         "speaker": "anushka",
#         "prompt": "You are a live translator. Translate the user's speech from English to Kannada. Respond concisely and accurately with only the translation."
#     },
#     "tamil": {
#         "room_name": "tamil-room",
#         "lang_code": "ta-IN",
#         "speaker": "anushka",
#         "prompt": "You are a live translator. Translate the user's speech from English to Tamil. Respond concisely and accurately with only the translation."
#     },
#     "hindi": {
#         "room_name": "hindi-room",
#         "lang_code": "hi-IN",
#         "speaker": "anushka",
#         "prompt": "You are a live translator. Translate the user's speech from English to Hindi. Respond concisely and accurately with only the translation."
#     }
# }
TRANSLATION_CONFIG = {
    "kannada": {
"room_name": "kannada-room",
        "lang_code": "kn-IN",
        "speaker": "anushka",
        "prompt": """You are a professional live interpreter for casual conversations. 

Your task: Translate English speech to natural, conversational Kannada as if you're interpreting for two people having a friendly chat.

Guidelines:
- Use everyday, casual Kannada that people actually speak
- Maintain the speaker's tone and emotion (friendly, excited, serious, etc.)
- If the English is incomplete or cut off, complete the thought naturally in Kannada
- Use appropriate Kannada expressions and idioms when they fit better than literal translation
- Keep the same level of formality as the original English
- If someone says "um", "uh", "you know", translate the meaning, not the filler words

Examples:
English: "Hey, how's it going?" → Kannada: "ಹೇ, ಹೇಗಿದೆ? ಎಲ್ಲಾ ಚೆನ್ನಾಗಿದೆಯಾ?"
English: "That's awesome!" → Kannada: "ಅದು ಸೂಪರ್ ಆಗಿದೆ!"
English: "I'm kinda tired today" → Kannada: "ನಾನು ಇಂದು ಸ್ವಲ್ಪ ಆಯಾಸವಾಗಿದ್ದೇನೆ"

Respond ONLY with the natural Kannada translation."""
    },
    "tamil": {
"room_name": "tamil-room",
        "lang_code": "ta-IN",
        "speaker": "anushka",
        "prompt": """You are a professional live interpreter for casual conversations.

Your task: Translate English speech to natural, conversational Tamil as if you're interpreting for two people having a friendly chat.

Guidelines:
- Use everyday, casual Tamil that people actually speak in daily life
- Maintain the speaker's tone and emotion (friendly, excited, serious, etc.)
- If the English is incomplete or cut off, complete the thought naturally in Tamil
- Use appropriate Tamil expressions and colloquialisms when they fit better than literal translation
- Keep the same level of formality as the original English
- If someone says "um", "uh", "you know", translate the meaning, not the filler words

Examples:
English: "Hey, how's it going?" → Tamil: "ஏய், எப்படி இருக்கீங்க? எல்லாம் நல்லா இருக்கா?"
English: "That's awesome!" → Tamil: "அது அருமையா இருக்கு!"
English: "I'm kinda tired today" → Tamil: "இன்னிக்கு கொஞ்சம் tired ஆ இருக்கேன்"

Respond ONLY with the natural Tamil translation."""
    },
    "hindi": {
"room_name": "hindi-room",
        "lang_code": "hi-IN",
        "speaker": "anushka",
        "prompt": """You are a professional live interpreter for casual conversations.

Your task: Translate English speech to natural, conversational Hindi as if you're interpreting for two people having a friendly chat.

Guidelines:
- Use everyday, casual Hindi that people actually speak in daily conversations
- Maintain the speaker's tone and emotion (friendly, excited, serious, etc.)
- If the English is incomplete or cut off, complete the thought naturally in Hindi
- Use appropriate Hindi expressions, slang, and colloquialisms when they fit better
- Keep the same level of formality as the original English
- Mix in common English words that Hindi speakers naturally use (like "actually", "basically", "really")
- If someone says "um", "uh", "you know", translate the meaning, not the filler words

Examples:
English: "Hey, how's it going?" → Hindi: "अरे यार, कैसा चल रहा है? सब ठीक है ना?"
English: "That's awesome!" → Hindi: "वाह यार, बहुत बढ़िया है!"
English: "I'm kinda tired today" → Hindi: "आज मैं थोड़ा tired feel कर रहा हूँ"

Respond ONLY with the natural Hindi translation."""
    }
}
# Initialize direct OpenAI client
direct_openai_client = direct_openai.OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

async def translate_with_openai(text: str, prompt: str) -> str:
    """Translate text using direct OpenAI client"""
    try:
        loop = asyncio.get_event_loop()

        def sync_translate():
            response = direct_openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=200,
                temperature=0.3
            )
            return response.choices[0].message.content

        # Run sync function in thread pool
        result = await loop.run_in_executor(None, sync_translate)
        return result or ""

    except Exception as e:
        logger.error(f"OpenAI translation failed: {e}")
        return ""


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
        # Create streams
        vad_stream = self._vad.stream()
        stt_stream = self._stt.stream()

        async def pipe_audio_to_vad():
            try:
                async for event in audio_stream:
                    frame = event.frame
                    vad_stream.push_frame(frame)
            except Exception as e:
                logger.error(f"Error in audio pipeline: {e}")
            finally:
                await vad_stream.aclose()

        async def pipe_vad_to_stt():
            try:
                async for event in vad_stream:
                    if event.type == vad.VADEventType.END_OF_SPEECH:
                        for frame in event.frames:
                            stt_stream.push_frame(frame)
            except Exception as e:
                logger.error(f"Error in VAD pipeline: {e}")
            finally:
                await stt_stream.aclose()

        self._pipe_audio_task = asyncio.create_task(pipe_audio_to_vad())
        self._pipe_vad_task = asyncio.create_task(pipe_vad_to_stt())

        try:
            async for event in stt_stream:
                if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                    stt_start_time = time.time()
                    text = event.alternatives[0].text if event.alternatives else ""
                    stt_duration = (time.time() - stt_start_time) * 1000  # Convert to ms

                    if not text or len(text.strip()) < 2:
                        continue

                    logger.info(f"🎤 STT ({stt_duration:.0f}ms): '{text}'")

                    # Process translations
                    translation_tasks = []
                    for lang, config in TRANSLATION_CONFIG.items():
                        room = self._translation_rooms.get(lang)
                        if not room:
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

        except Exception as e:
            logger.error(f"STT processing error: {e}")
        finally:
            # Cleanup
            if self._pipe_audio_task and not self._pipe_audio_task.done():
                self._pipe_audio_task.cancel()
            if self._pipe_vad_task and not self._pipe_vad_task.done():
                self._pipe_vad_task.cancel()

            await asyncio.gather(
                self._pipe_audio_task,
                self._pipe_vad_task,
                return_exceptions=True
            )

    async def _translate_and_publish_task(self, lang: str, text: str, llm, tts: sarvam.TTS,
                                          audio_source: rtc.AudioSource, participant: rtc.LocalParticipant):
        """
        Handles the translation and TTS publishing for a single language.
        """
        try:
            # Translation timing
            translation_start_time = time.time()

            # Use direct OpenAI instead of LiveKit LLM
            translated_text = await translate_with_openai(text, TRANSLATION_CONFIG[lang]["prompt"])

            translation_duration = (time.time() - translation_start_time) * 1000  # Convert to ms

            if not translated_text:
                logger.warning(f"❌ {lang.upper()} translation failed: empty result")
                return

            logger.info(f"🌐 {lang.upper()} ({translation_duration:.0f}ms): '{translated_text}'")

            # Publish subtitle
            await participant.publish_data(
                payload=translated_text.encode('utf-8'),
                topic=f"subtitles-{lang}"
            )

            # TTS timing
            tts_start_time = time.time()
            tts_stream = tts.synthesize(translated_text)

            frame_count = 0
            async for frame in tts_stream:
                await audio_source.capture_frame(frame.frame)
                frame_count += 1

            tts_duration = (time.time() - tts_start_time) * 1000  # Convert to ms
            logger.info(f"🔊 {lang.upper()} TTS ({tts_duration:.0f}ms): {frame_count} frames")

        except Exception as e:
            logger.error(f"❌ {lang.upper()} pipeline error: {e}")

    async def close(self):
        """Shuts down the pipeline task."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Pipeline close error: {e}")


async def entrypoint(ctx: JobContext):
    """
    The main entrypoint for the Orchestrator Agent.
    """
    logger.info("🚀 Starting translation orchestrator")
    speaker_room = ctx.room

    async with aiohttp.ClientSession() as http_session:
        # 1. Setup connections to all translation rooms
        translation_rooms = {}
        for lang, config in TRANSLATION_CONFIG.items():
            room_name = config["room_name"]
            try:
                room = rtc.Room()
                grant = VideoGrants(room_join=True, room=room_name, can_publish=True, can_publish_data=True)
                identity = f"translation-publisher-bot-{lang}"
                token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET).with_identity(identity).with_grants(
                    grant).to_jwt()
                await room.connect(LIVEKIT_URL, token)
                translation_rooms[lang] = room
            except Exception as e:
                logger.error(f"❌ Failed to connect to {room_name}: {e}")
                continue

        logger.info(f"✅ Connected to {len(translation_rooms)} translation rooms")

        # 2. Initialize the processing pipeline components
        stt_instance = assemblyai.STT(http_session=http_session)
        llm = None  # We use direct OpenAI instead
        tts_engines = {
            lang: sarvam.TTS(target_language_code=config["lang_code"], speaker=config["speaker"],
                             http_session=http_session,model="bulbul:v2")
            for lang, config in TRANSLATION_CONFIG.items()
        }
        # tts_engines = {
        #     "hindi": elevenlabs.TTS(model="eleven_flash_v2_5"),  # Adam voice
        #     "tamil": elevenlabs.TTS(model="eleven_flash_v2_5"),  # Bella voice
        #     "kannada": elevenlabs.TTS(model="eleven_flash_v2_5"),  # Antoni voice
        # }
        # tts_engines = {
        #     "hindi": openai.TTS(voice="alloy"),
        #     "tamil": openai.TTS(voice="echo"),
        #     "kannada": openai.TTS(voice="fable"),
        # }

        # 3. Create audio tracks and data channels for publishing
        audio_sources = {}
        for lang, config in TRANSLATION_CONFIG.items():
            room = translation_rooms.get(lang)
            if room:
                audio_source = rtc.AudioSource(22050, 1) #22050
                audio_sources[lang] = audio_source
                track = rtc.LocalAudioTrack.create_audio_track(f"{lang}-translation", audio_source)
                await room.local_participant.publish_track(track)

        # Dictionary to store an active pipeline for each participant
        pipelines: dict[str, TranslationPipeline] = {}

        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication,
                                participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                if participant.identity in pipelines:
                    return

                logger.info(f"👤 Speaker joined: {participant.identity}")
                audio_stream = rtc.AudioStream(track)

                pipeline = TranslationPipeline(
                    stt=stt_instance,
                    llm=llm,
                    tts_engines=tts_engines,
                    audio_sources=audio_sources,
                    translation_rooms=translation_rooms,
                )
                pipelines[participant.identity] = pipeline
                pipeline.start(audio_stream)

        def on_participant_disconnected(participant: rtc.RemoteParticipant):
            if participant.identity in pipelines:
                logger.info(f"👋 Speaker left: {participant.identity}")
                pipeline = pipelines.pop(participant.identity)
                asyncio.create_task(pipeline.close())

        speaker_room.on("track_subscribed", on_track_subscribed)
        speaker_room.on("participant_disconnected", on_participant_disconnected)

        await ctx.connect()
        logger.info("⏳ Waiting for speakers...")

        try:
            await asyncio.Event().wait()
        finally:
            logger.info("🛑 Shutting down orchestrator")
            for pipeline in pipelines.values():
                await pipeline.close()
            for room in translation_rooms.values():
                await room.disconnect()


if __name__ == "__main__":
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        raise ValueError("LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET must be set in environment variables.")

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name="translation-orchestrator"))