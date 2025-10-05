import asyncio
import os
from livekit import rtc
from dotenv import load_dotenv

load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_TOKEN = os.getenv("SPEAKER_TOKEN")

async def main():
    room = rtc.Room()
    await room.connect(LIVEKIT_URL, LIVEKIT_TOKEN)
    print(f"Connected as speaker to room: {room.name}")

    # Create an audio source and track
    source = rtc.AudioSource(sample_rate=48000, num_channels=1)
    audio_track = rtc.LocalAudioTrack.create_audio_track("english-audio", source)

    await room.local_participant.publish_track(audio_track)
    print("Published English audio track")

    # Keep the program running
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
