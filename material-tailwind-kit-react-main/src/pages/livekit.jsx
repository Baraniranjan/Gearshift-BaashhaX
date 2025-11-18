import React, { useEffect, useState } from "react";
import {
  ControlBar,
  GridLayout,
  ParticipantTile,
  RoomAudioRenderer,
  useTracks,
  RoomContext,
  AudioTrack,
} from "@livekit/components-react";

import { Room, Track } from "livekit-client";
import "@livekit/components-styles";

const serverUrl = 'wss://baashha-rmtp6wct.livekit.cloud';
const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjMxMTkwNjMsImlkZW50aXR5IjoicXVpY2tzdGFydCB1c2VyIDFkaXhmeSIsImlzcyI6IkFQSU5pZFJNenpVNTJrciIsIm5iZiI6MTc2MzExMTg2Mywic3ViIjoicXVpY2tzdGFydCB1c2VyIDFkaXhmeSIsInZpZGVvIjp7ImNhblB1Ymxpc2giOnRydWUsImNhblB1Ymxpc2hEYXRhIjp0cnVlLCJjYW5TdWJzY3JpYmUiOnRydWUsInJvb20iOiJxdWlja3N0YXJ0IHJvb20iLCJyb29tSm9pbiI6dHJ1ZX19.8iYhdFSMGGZ2mFmsTDXQNiHW8eSa6ETsV2F5sUMl6m0';


export default function LivePage() {
  const [room] = useState(
    () =>
      new Room({
        adaptiveStream: true,
        dynacast: true,
      })
  );

  useEffect(() => {
    let mounted = true;

    const connectRoom = async () => {
      if (mounted) await room.connect(serverUrl, token);
    };

    connectRoom();

    return () => {
      mounted = false;
      room.disconnect();
    };
  }, [room]);

  return (
    <RoomContext.Provider value={room}>
      <div data-lk-theme="default" style={{ height: "100vh" }}>
        <VideoConference />
        <RoomAudioRenderer />
        <ControlBar />
      </div>
    </RoomContext.Provider>
  );
}

function VideoConference() {
  const tracks = useTracks(
    [
      { source: Track.Source.Camera, withPlaceholder: true },
      { source: Track.Source.ScreenShare, withPlaceholder: false },
    ],
    { onlySubscribed: false }
  );

  return (
    <GridLayout tracks={tracks} style={{ height: "calc(100vh - var(--lk-control-bar-height))" }}>
      <ParticipantTile>
        {/* <AudioTrack trackRef={tracks.find((t) => t.source === Track.Source.Microphone)?.trackRef} /> */}
        </ParticipantTile> 
    </GridLayout>
  );
}
