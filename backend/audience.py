import asyncio, os
from livekit import rtc
from dotenv import load_dotenv

load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
AUDIENCE_TOKEN = os.getenv("AUDIENCE_TOKEN")  # JWT generated for audience
PREFERRED_LANG = os.getenv("LANGUAGE", "ta-IN")  # Tamil, Kannada, or Hindi

async def main():
    room = rtc.Room()

    await room.connect(LIVEKIT_URL, AUDIENCE_TOKEN)
    print(f"Connected as audience in room: {room.name}")

    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        # subscribe only to the preferred language track
        if track.kind == rtc.TrackKind.KIND_AUDIO and publication.name == PREFERRED_LANG:
            print(f"Subscribed to {PREFERRED_LANG} audio track")
            audio_stream = rtc.AudioStream(track)
            # play the audio chunk or forward to UI
            # e.g., audio_stream.play() in some GUI library

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
