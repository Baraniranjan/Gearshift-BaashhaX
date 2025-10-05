import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import openai, silero, assemblyai, sarvam

# load environment variables
load_dotenv()

logger = logging.getLogger("multi-translation")
logger.setLevel(logging.INFO)


# --------- Base Translator Agent ---------
class TranslatorAgent(Agent):
    def __init__(self, target_lang: str, lang_code: str, speaker: str):
        super().__init__(
            instructions=f"""
                You are a translator. Translate the user's speech from English to {target_lang}.
                Respond only with the translation in {target_lang}.
            """,
            stt=assemblyai.STT(),
            llm=openai.LLM.with_azure(),
            tts=sarvam.TTS(
                target_language_code=lang_code,
                speaker=speaker,
            ),
            vad=silero.VAD.load(max_buffered_speech=3),
        )
        self.track_name = f"{target_lang} Translation"

    async def on_enter(self):
        # When generating replies, publish them with a track name
        await self.session.generate_reply(track_name=self.track_name)



# --------- Entry Point: Create 3 agents in same room ---------
async def entrypoint(ctx: JobContext):
    # Kannada agent
    kn_session = AgentSession()
    await kn_session.start(agent=TranslatorAgent("Kannada", "kn-IN", "anushka"), room=ctx.room)

    # Tamil agent
    ta_session = AgentSession()
    await ta_session.start(agent=TranslatorAgent("Tamil", "ta-IN", "anushka"), room=ctx.room)

    # Hindi agent
    hi_session = AgentSession()
    await hi_session.start(agent=TranslatorAgent("Hindi", "hi-IN", "anushka"), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
