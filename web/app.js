async function fetchToken(roomName, identity) {
  const resp = await fetch(`/get_token?room=${roomName}&identity=${identity}`);
  return await resp.text();
}

async function connectToRoom(token) {
  const room = new Livekit.Room();
  await room.connect(`${LIVEKIT_URL}`, token);
  return room;
}
