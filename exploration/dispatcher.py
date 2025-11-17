import asyncio
import os
import sys
from dotenv import load_dotenv
from livekit import api

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
LIVEKIT_URL = os.environ.get("LIVEKIT_URL")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")
AGENT_NAME = "translation-orchestrator"
# AGENT_NAME = "speech-to-speech-orchestrator"


async def dispatch_agent(room_name: str):
    """
    Explicitly dispatches the translation agent to a specific room.
    """
    if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        raise ValueError("LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET must be set in your .env file.")

    # The URL for the API client should not include the 'wss' protocol
    api_url = LIVEKIT_URL.replace("wss://", "https://").replace("ws://", "http://")

    lkapi = api.LiveKitAPI(api_url, LIVEKIT_API_KEY, LIVEKIT_API_SECRET)

    try:
        print(f"Dispatching agent '{AGENT_NAME}' to room '{room_name}'...")
        dispatch = await lkapi.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=AGENT_NAME,
                room=room_name
            )
        )
        print("Successfully created dispatch:")
        print(dispatch)
    except Exception as e:
        print(f"Error creating dispatch: {e}")
    finally:
        await lkapi.aclose()


if __name__ == "__main__":
    # This script is designed to be run from the command line.
    # It expects one argument: the name of the speaker's room.
    # Example usage: python dispatcher.py main-conference-room

    if len(sys.argv) != 2:
        print("Usage: python dispatcher.py <speaker_room_name>")
        sys.exit(1)

    speaker_room_name = sys.argv[1]
    asyncio.run(dispatch_agent(speaker_room_name))
