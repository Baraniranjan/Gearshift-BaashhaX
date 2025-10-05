import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from livekit import api

# Load env vars
load_dotenv()
API_KEY = os.getenv("LIVEKIT_API_KEY")
API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL")

app = FastAPI()

class TokenRequest(BaseModel):
    identity: str
    room: str
    can_publish: bool = False
    can_subscribe: bool = True


@app.post("/get_token")
def get_token(req: TokenRequest):
    # 1️⃣ create grants
    grants = api.VideoGrants(
        room=req.room,
        room_join=True,
        can_publish=req.can_publish,
        can_subscribe=req.can_subscribe,
    )

    # 2️⃣ build token
    token = (
        api.AccessToken(API_KEY, API_SECRET)
        .with_identity(req.identity)
        .with_grants(grants)
        .to_jwt()
    )

    return {"url": LIVEKIT_URL, "token": token}
