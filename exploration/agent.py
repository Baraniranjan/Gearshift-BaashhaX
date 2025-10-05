import asyncio
import os
from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents.utils import AsyncQueue
from livekit.plugins import (
    deepgram,  # For Speech-to-Text (STT)
    openai,  # For translation
    elevenlabs,  # For Text-to-Speech (TTS)
)

# Load environment variables from a .env file
load_dotenv()

# We'll use a single queue to process all speech events.
# This ensures that translations are handled sequentially.
_speech_queue = AsyncQueue()


# Function to get API keys from environment variables
def get_api_key(key_name):
    api_key = os.getenv(key_name)
    if not api_key:
        print(f"ERROR: {key_name} environment variable is not set.")
        exit(1)
    return api_key


# Define the LiveKit Agent's entrypoint. This is the main function
# that will run when the agent connects to a room.
async def entrypoint(ctx: agents.JobContext):
    # Connect to the LiveKit room
    await ctx.connect()

    # LiveKit Agents provide a convenient way to integrate services.
    # We will instantiate our STT, LLM, and TTS models using the plugins.
    stt = deepgram.STT(api_key=get_api_key('DEEPGRAM_API_KEY'))
    # We use a simple instruction prompt to guide the LLM's translation behavior.
    llm = openai.LLM(api_key=get_api_key('OPENAI_API_KEY'),
                     instructions="You are a helpful translator. Translate the given English text to Hindi. Only provide the translated text, do not add any extra phrases or explanations.")
    # We'll select a voice that supports Hindi.
    tts = elevenlabs.TTS(api_key=get_api_key('ELEVENLABS_API_KEY'), voice="Rachana")

    print(f"Agent '{ctx.room.local_participant.identity}' has joined the room '{ctx.room.name}'")

    # This async task will continuously process the speech events from the queue.
    asyncio.create_task(process_speech_events(ctx.room, llm, tts))

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.RemoteTrack, publication: rtc.RemoteTrackPublication,
                            participant: rtc.RemoteParticipant):
        # We only want to process audio tracks from human participants.
        if track.kind == rtc.TrackKind.KIND_AUDIO and not participant.is_agent:
            print(f"Subscribed to audio track from '{participant.identity}'")
            asyncio.create_task(process_audio_track(track, stt, participant.identity))


async def process_audio_track(track: rtc.RemoteTrack, stt: deepgram.STT, identity: str):
    audio_stream = rtc.AudioStream(track)
    # Get a streaming STT instance from the plugin
    stt_stream = stt.stream()

    async with asyncio.TaskGroup() as tg:
        # Task to push audio frames to the STT stream
        tg.create_task(push_audio_frames(audio_stream, stt_stream))
        # Task to process the STT results
        tg.create_task(process_stt_events(stt_stream, identity))


async def push_audio_frames(audio_stream, stt_stream):
    async for audio_event in audio_stream:
        # Push the audio frames to the STT stream
        stt_stream.push_frame(audio_event.frame)
    stt_stream.end_input()
    print("Audio stream ended")


async def process_stt_events(stt_stream, identity):
    async for speech_event in stt_stream:
        # We only care about the final, complete transcript
        if speech_event.type == agents.stt.SpeechEventType.FINAL_TRANSCRIPT:
            transcript = speech_event.alternatives[0].text
            print(f"[{identity}] Said: {transcript}")
            # Add the transcript to our processing queue
            await _speech_queue.put({'identity': identity, 'text': transcript})


async def process_speech_events(room: rtc.Room, llm: openai.LLM, tts: elevenlabs.TTS):
    while True:
        try:
            event = await _speech_queue.get()
            identity = event['identity']
            english_text = event['text']

            # --- Translation Step (English to Hindi) ---
            print(f"Translating for '{identity}': {english_text}")
            llm_response = await llm.chat(history=[openai.ChatContext(text=english_text)])
            # Assuming the LLM returns only the translated text.
            translated_text = llm_response.text_content
            print(f"Translated to Hindi: {translated_text}")

            # --- Text-to-Speech Step (Hindi audio) ---
            print("Generating Hindi audio...")
            # Generate the Hindi audio stream from the translated text.
            tts_stream = await tts.synthesize(text=translated_text, voice_id="Rachana")

            # Publish the new audio back into the room as a new track.
            # Participants in the conference can subscribe to this track to hear the translation.
            track = rtc.LocalAudioTrack.create_audio_track("hindi-translation", tts_stream)
            await room.local_participant.publish_track(track)
            print("Published translated audio track.")

            # Wait for the audio to finish playing before unpublishing the track.
            await tts_stream.wait_for_completion()
            await room.local_participant.unpublish_track(track)

        except Exception as e:
            print(f"An error occurred during processing: {e}")


# This boilerplate runs the agent.
if __name__ == "__main__":
    cli = agents.cli
    cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint
    ))
