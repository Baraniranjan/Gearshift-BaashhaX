import os
import sys
from datetime import timedelta
from dotenv import load_dotenv
from livekit.api import AccessToken, VideoGrants

# Load environment variables from a .env file in the same directory
load_dotenv()

# --- Configuration ---
# Get your LiveKit server details from environment variables
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET")

def generate_token(room_name: str, participant_identity: str) -> str:
    """
    Generates a LiveKit access token for a given room and participant.
    """
    if not all([LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
        raise ValueError("LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be set in your .env file.")

    # Define the permissions for the token.
    # For simplicity in testing, we'll grant permissions to publish and subscribe.
    # In a real application, you might give audience members subscribe-only permissions.
    grant = VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )

    # Create the AccessToken object
    token = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(participant_identity)
        .with_ttl(timedelta(hours=1))  # The token will be valid for 1 hour
        .with_grants(grant)
    )

    # Return the token as a JWT string
    return token.to_jwt()

if __name__ == "__main__":
    # This script is designed to be run from the command line.
    # It expects two arguments: the room name and the participant's identity.
    # Example usage: python token_generator.py my-cool-room user123

    if len(sys.argv) != 3:
        print("Usage: python token_generator.py <room_name> <participant_identity>")
        sys.exit(1)

    # Get the arguments from the command line
    room_name_arg = sys.argv[1]
    participant_identity_arg = sys.argv[2]

    # Generate the token
    try:
        jwt_token = generate_token(room_name_arg, participant_identity_arg)
        print("\n--- LiveKit Access Token ---")
        print(f"Room: {room_name_arg}")
        print(f"Identity: {participant_identity_arg}")
        print("\nToken:")
        print(jwt_token)
        print("\nThis token is valid for 1 hour.")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
