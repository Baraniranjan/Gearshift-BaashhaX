import React, { useState, useEffect, useRef } from "react";
import {
  Button,
  Dialog,
  DialogHeader,
  DialogBody,
  DialogFooter,
  Card,
  Typography,
} from "@material-tailwind/react";
import { motion } from "framer-motion";
import { SpeakerWaveIcon } from "@heroicons/react/24/solid";

const dummyMeetings = [
  { id: 1, name: "New Meeting" },
  { id: 2, name: "Project Kickoff" },
  { id: 3, name: "Weekly Update" },
];

const breakoutRooms = [
  // { id: 1, language: "Kannada" },
  // { id: 2, language: "Tamil" },
  { id: 3, language: "Hindi" },
  { id: 4, language: "Japanese" },
];

export default function AudienceDashboard() {
  const [meetings] = useState(dummyMeetings);
  const [joinModal, setJoinModal] = useState(false);
  const [code, setCode] = useState(["", "", "", ""]);
  const [showRooms, setShowRooms] = useState(false);
  const [inRoom, setInRoom] = useState(false);
  const [volume, setVolume] = useState(0);
  const [displayedText, setDisplayedText] = useState("");

  const inputsRef = useRef([]);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const sourceRef = useRef(null);

  const message =
    "Welcome everyone to the session. We are excited to have you here today. Let's begin our discussion.";

  // Typing animation
  useEffect(() => {
    if (inRoom) {
      const words = message.split(" ");
      let index = 0;
      setDisplayedText("");

      const interval = setInterval(() => {
        if (index < words.length) {
          setDisplayedText((prev) => prev + (prev ? " " : "") + words[index]);
          index++;
        } else {
          clearInterval(interval);
        }
      }, 500);

      return () => clearInterval(interval);
    } else {
      setDisplayedText("");
    }
  }, [inRoom]);

  // Voice visualization
  useEffect(() => {
    if (inRoom) {
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          audioContextRef.current = new (window.AudioContext ||
            window.webkitAudioContext)();
          analyserRef.current = audioContextRef.current.createAnalyser();
          sourceRef.current =
            audioContextRef.current.createMediaStreamSource(stream);
          sourceRef.current.connect(analyserRef.current);

          analyserRef.current.fftSize = 256;
          const bufferLength = analyserRef.current.frequencyBinCount;
          dataArrayRef.current = new Uint8Array(bufferLength);

          const updateVolume = () => {
            analyserRef.current.getByteFrequencyData(dataArrayRef.current);
            const avg =
              dataArrayRef.current.reduce((a, b) => a + b, 0) /
              dataArrayRef.current.length;
            setVolume(avg / 255);
            requestAnimationFrame(updateVolume);
          };
          updateVolume();
        })
        .catch((err) => console.error("Mic access error:", err));
    } else {
      if (audioContextRef.current) {
        audioContextRef.current.close();
        audioContextRef.current = null;
      }
      setVolume(0);
    }
  }, [inRoom]);

  // Code input
  const handleCodeChange = (value, index) => {
    if (!/^[0-9]?$/.test(value)) return;

    const newCode = [...code];
    newCode[index] = value;
    setCode(newCode);

    if (value && index < 3) inputsRef.current[index + 1].focus();

    if (newCode.every((digit) => digit !== "")) {
      setTimeout(() => setShowRooms(true), 200);
    }
  };

  const handleKeyDown = (e, index) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputsRef.current[index - 1].focus();
    }
  };

  return (
    <div className="min-h-screen relative">
      {/* Background */}
      <div className="absolute top-0 left-0 w-full h-full bg-[url('/img/background-3.png')] bg-cover bg-center z-0" />
      <div className="absolute top-0 left-0 w-full h-full bg-black/80 z-10" />
      <div className="relative z-20 p-8 min-h-screen flex flex-col items-center">
        <Typography variant="h3" className="text-white mb-8 font-bold">
          Audience Dashboard
        </Typography>

        {/* Meeting list */}
        <Card className="bg-gray-900 text-white w-full max-w-xl shadow-xl border border-gray-800">
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-800 text-indigo-200">
                  <th className="py-3 px-4 text-left">Sl No</th>
                  <th className="py-3 px-4 text-left">Meeting Name</th>
                  <th className="py-3 px-4 text-left">Action</th>
                </tr>
              </thead>
              <tbody>
                {meetings.map((meeting, idx) => (
                  <tr
                    key={meeting.id}
                    className="border-b border-gray-700 hover:bg-gray-800 transition"
                  >
                    <td className="py-2 px-4 text-gray-300">{idx + 1}</td>
                    <td className="py-2 px-4 text-gray-100">
                      {meeting.name}
                    </td>
                    <td className="py-2 px-4">
                      <Button
                        size="sm"
                        color="indigo"
                        className="bg-indigo-700 text-white hover:bg-indigo-800"
                        onClick={() => {
                          setJoinModal(true);
                          setShowRooms(false);
                          setCode(["", "", "", ""]);
                        }}
                      >
                        Join
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Join Modal */}
        <Dialog
          open={joinModal}
          handler={setJoinModal}
          size="sm"
          className="bg-gray-900 text-white"
        >
          <DialogHeader className="bg-gray-900 text-indigo-300">
            Join Meeting
          </DialogHeader>

          <DialogBody>
            {!showRooms ? (
              <>
                <Typography
                  variant="h6"
                  className="mb-4 text-white text-center"
                >
                  Enter 4-Digit Access Code
                </Typography>

                <div className="flex justify-center gap-4 mb-6">
                  {code.map((digit, index) => (
                    <input
                      key={index}
                      ref={(el) => (inputsRef.current[index] = el)}
                      type="text"
                      maxLength="1"
                      value={digit}
                      onChange={(e) =>
                        handleCodeChange(e.target.value, index)
                      }
                      onKeyDown={(e) => handleKeyDown(e, index)}
                      className="w-12 h-12 text-center text-2xl font-bold rounded-lg bg-gray-800 text-white border border-gray-700 focus:border-indigo-400 focus:outline-none"
                    />
                  ))}
                </div>
              </>
            ) : (
              <>
                <Typography
                  variant="h6"
                  className="mb-4 text-indigo-300 text-center"
                >
                  Choose Your Breakout Room
                </Typography>

                <div className="grid grid-cols-2 gap-4">
                  {breakoutRooms.map((room) => (
                    <Button
                      key={room.id}
                      color="green"
                      className="bg-green-700 hover:bg-green-800 text-white"
                      onClick={() => {
                        setJoinModal(false);
                        setInRoom(true);

                        // 👇 DYNAMIC URL REDIRECT (The important change)
                        const formatted = room.language
                          .toLowerCase()
                          .replace(/\s+/g, "-");
                        window.location.href = `http://localhost:3000/${formatted}-room`;
                      }}
                    >
                      {room.language}
                    </Button>
                  ))}
                </div>
              </>
            )}
          </DialogBody>

          <DialogFooter>
            <Button
              color="red"
              className="bg-red-700 text-white hover:bg-red-800"
              onClick={() => setJoinModal(false)}
            >
              Close
            </Button>
          </DialogFooter>
        </Dialog>

        {/* In-Room Speaker Visualization */}
        <Dialog
          open={inRoom}
          handler={setInRoom}
          size="sm"
          className="bg-gray-900 text-white"
        >
          <DialogHeader className="bg-gray-900 text-green-300 text-center">
            Breakout Room
          </DialogHeader>

          <DialogBody className="flex flex-col items-center justify-center">
            <div className="relative flex items-center justify-center mt-6">
              {[...Array(3)].map((_, i) => (
                <motion.div
                  key={i}
                  className="absolute rounded-full bg-green-500/10"
                  style={{
                    width: 120 + i * 40,
                    height: 120 + i * 40,
                  }}
                  animate={{
                    scale: 1 + volume * 1.5,
                    opacity: 0.1 + volume * 0.5,
                  }}
                  transition={{ duration: 0.2 }}
                />
              ))}
              <motion.div
                className="w-20 h-20 bg-green-700 rounded-full flex items-center justify-center shadow-lg"
                animate={{ scale: 1 + volume * 0.4 }}
                transition={{ duration: 0.1 }}
              >
                <SpeakerWaveIcon className="text-white w-10 h-10" />
              </motion.div>
            </div>

            <Typography
              variant="h6"
              className="mt-6 text-gray-300 text-center px-4 min-h-[80px]"
            >
              {displayedText}
            </Typography>
          </DialogBody>

          <DialogFooter>
            <Button
              color="red"
              className="bg-red-700 text-white hover:bg-red-800"
              onClick={() => setInRoom(false)}
            >
              Leave Room
            </Button>
          </DialogFooter>
        </Dialog>
      </div>
    </div>
  );
}
