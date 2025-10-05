import logging, asyncio

from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import openai, silero, assemblyai, sarvam

logger = logging.getLogger("translator")
logger.setLevel(logging.INFO)
load_dotenv()
class TranslatorAgent(Agent):
    def __init__(self, target_lang: str, lang_code: str, speaker: str):
        super().__init__(
            instructions=f"Translate English speech into {target_lang}.",
            stt=assemblyai.STT(),
            llm=openai.LLM.with_azure(),
            tts=sarvam.TTS(target_language_code=lang_code, speaker=speaker),
            vad=silero.VAD.load(max_buffered_speech=3),
        )
        self.target_lang = target_lang
        self.lang_room = f"room-{target_lang.lower()}"

    async def on_enter(self):
        # Start continuous translation into the audience room
        await self.say(
            f"Streaming translation in {self.target_lang}.",
            track_name=f"{self.target_lang}-translation",
            continuous=True
        )

async def entrypoint(ctx: JobContext):
    langs = [
        ("Tamil", "ta-IN", "anushka"),
        ("Kannada", "kn-IN", "anushka"),
        ("Hindi", "hi-IN", "anushka"),
    ]

    sessions = []
    for target_lang, lang_code, speaker in langs:
        session = AgentSession()
        agent = TranslatorAgent(target_lang, lang_code, speaker)

        await session.start(
            agent=agent,
            room=ctx.room,   # connect to speaker room (English)
        )

        # ⚡ Trick: publish into a DIFFERENT room
        await session.forward_tracks(to_room=agent.lang_room)

        sessions.append(session)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
