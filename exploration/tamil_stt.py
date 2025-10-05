import logging
import asyncio
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
import os

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    RoomOutputOptions,
    StopResponse,
    WorkerOptions,
    cli,
    llm,
)
from livekit.plugins import assemblyai

load_dotenv()

logger = logging.getLogger("tamil_transcriber")


class TamilTranscriber(Agent):
    def __init__(self):
        super().__init__(
            instructions="Translate speech to Tamil",
            stt=assemblyai.STT(),
        )
        self.azure_client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-35-turbo")

    async def on_user_turn_completed(self, chat_ctx: llm.ChatContext, new_message: llm.ChatMessage):
        user_transcript = new_message.text_content
        logger.info(f"Original -> {user_transcript}")

        # Translate to Tamil
        tamil_text = await self.translate_to_tamil(user_transcript)
        logger.info(f"Tamil -> {tamil_text}")

        # Return Tamil text as agent response (will show in playground)
        return tamil_text+" ending "

    async def translate_to_tamil(self, text: str) -> str:
        try:
            response = await self.azure_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Translate to spanish. Return only the spanish translation, no explanations."
                    },
                    {"role": "user", "content": text}
                ],
                max_tokens=500,
                temperature=0,
                timeout=5
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Tamil translation error: {e}")
            return text


async def entrypoint(ctx: JobContext):
    logger.info(f"Starting Tamil transcriber for playground, room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    session = AgentSession()

    await session.start(
        agent=TamilTranscriber(),
        room=ctx.room,
        room_output_options=RoomOutputOptions(
            transcription_enabled=True,  # Hide English
            audio_enabled=False,
        ),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))