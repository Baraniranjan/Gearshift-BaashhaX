import React, { useState } from "react";
import {
  Button,
  Dialog,
  DialogHeader,
  DialogBody,
  DialogFooter,
  Input,
  Card,
  Typography,
} from "@material-tailwind/react";

const dummyMeetings = [
  { id: 1, name: "Team Sync", language: ["English"], time: "2025-10-08T11:00" },
  { id: 2, name: "Project Kickoff", language: ["Spanish", "English"], time: "2025-10-09T14:30" },
  { id: 3, name: "Design Review", language: ["French"], time: "2025-10-10T16:00" },
];

export default function SpeakerDashboard() {

  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [startOpen, setStartOpen] = useState(false);

  const [meetings, setMeetings] = useState(dummyMeetings);

  const [scheduleLanguages, setScheduleLanguages] = useState([]);
  const [startLanguages, setStartLanguages] = useState([]);

  const [meetingName, setMeetingName] = useState("");
  const [meetingTime, setMeetingTime] = useState("");

  const languages = ["English", "Spanish", "French", "German", "Japanese", "Hindi"];

  const toggleScheduleLanguage = (lang) => {
    setScheduleLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  };

  const toggleStartLanguage = (lang) => {
    setStartLanguages((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    );
  };

  const handleScheduleMeeting = () => {
    if (meetingName && scheduleLanguages.length > 0 && meetingTime) {
      const newMeeting = {
        id: meetings.length + 1,
        name: meetingName,
        language: scheduleLanguages,
        time: meetingTime,
      };

      setMeetings((prev) => [...prev, newMeeting]);
      setScheduleOpen(false);

      setMeetingName("");
      setMeetingTime("");
      setScheduleLanguages([]);
    }
  };

  return (
    <div className="min-h-screen bg-black/80">

      {/* Wrapper */}
      <div className="p-8 min-h-screen relative z-20">

        {/* Top Buttons */}
        <div className="flex justify-end mb-6 max-w-xl mx-auto w-full">
          <div className="flex gap-4">
            <Button
              color="indigo"
              className="bg-indigo-700 text-white hover:bg-indigo-800"
              onClick={() => setScheduleOpen(true)}
            >
              Schedule Meeting
            </Button>
            <Button
              color="green"
              className="bg-green-700 text-white hover:bg-green-800"
              onClick={() => setStartOpen(true)}
            >
              Start Meeting
            </Button>
          </div>
        </div>

        {/* Table */}
        <div className="flex flex-col items-center">
          <Typography variant="h4" className="text-white mb-6 font-bold">
            Scheduled Meetings
          </Typography>

          <Card className="bg-gray-900 text-white w-full max-w-xl mt-2 shadow-xl border border-gray-700">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-gray-800 text-indigo-200">
                  <th className="py-3 px-4 text-left">Sl No</th>
                  <th className="py-3 px-4 text-left">Meeting Name</th>
                  <th className="py-3 px-4 text-left">Languages</th>
                  <th className="py-3 px-4 text-left">Time</th>
                  <th className="py-3 px-4 text-left">Action</th>
                </tr>
              </thead>

              <tbody>
                {meetings.map((meeting, idx) => (
                  <tr
                    key={meeting.id}
                    className="border-b border-gray-800 hover:bg-gray-800 transition"
                  >
                    <td className="py-2 px-4 text-gray-300">{idx + 1}</td>
                    <td className="py-2 px-4 text-gray-100">{meeting.name}</td>
                    <td className="py-2 px-4 text-gray-400">
                      {meeting.language.join(", ")}
                    </td>
                    <td className="py-2 px-4 text-gray-300">
                      {meeting.time ? new Date(meeting.time).toLocaleString() : "-"}
                    </td>

                    <td className="py-2 px-4">
                      <Button
                      size="sm"
                      color="green"
                      className="bg-green-700 text-white hover:bg-green-800"
                      onClick={() => {
                        window.location.replace("http://localhost:3000/prejoin?role=speaker");
                      }}
                    >
                      Start
                    </Button>
                    </td>
                  </tr>
                ))}
              </tbody>

            </table>
          </Card>
        </div>

        {/* Schedule Modal */}
        <Dialog
          open={scheduleOpen}
          handler={setScheduleOpen}
          size="sm"
          className="bg-gray-900 text-white p-2"
        >
          <DialogHeader className="bg-gray-900 text-indigo-300">
            Schedule Meeting
          </DialogHeader>

          <DialogBody>
            <Typography variant="h6" className="mb-2">Meeting Name</Typography>
            <Input
              label="Meeting Name"
              value={meetingName}
              onChange={(e) => setMeetingName(e.target.value)}
              className="mb-4 bg-gray-800 text-white"
            />

            <Typography variant="h6" className="mb-2">Meeting Time</Typography>
            <Input
              type="datetime-local"
              value={meetingTime}
              onChange={(e) => setMeetingTime(e.target.value)}
              className="mb-4 bg-gray-800 text-white"
            />

            <Typography variant="h6" className="mb-2">Languages</Typography>

            <div className="flex flex-wrap gap-3">
              {languages.map((lang) => (
                <button
                  key={lang}
                  onClick={() => toggleScheduleLanguage(lang)}
                  className={`px-4 py-2 rounded-xl text-sm transition-all border 
                    ${scheduleLanguages.includes(lang)
                      ? "bg-indigo-600 border-indigo-400 text-white shadow-lg"
                      : "bg-gray-800 border-gray-700 text-gray-300"
                    }`}
                >
                  {lang}
                </button>
              ))}
            </div>
          </DialogBody>

          <DialogFooter>
            <Button
              color="indigo"
              className="bg-indigo-700 text-white hover:bg-indigo-800"
              onClick={handleScheduleMeeting}
            >
              Schedule
            </Button>
          </DialogFooter>
        </Dialog>

        {/* Start Modal */}
        <Dialog
          open={startOpen}
          handler={setStartOpen}
          size="sm"
          className="bg-gray-900 text-white p-2"
        >
          <DialogHeader className="bg-gray-900 text-green-300">
            Start Meeting
          </DialogHeader>

          <DialogBody>
            <Typography variant="h6" className="mb-2">Meeting Name</Typography>
            <Input className="mb-4 bg-gray-800 text-white" />

            <Typography variant="h6" className="mb-2">Languages</Typography>

            <div className="flex flex-wrap gap-3">
              {languages.map((lang) => (
                <button
                  key={lang}
                  onClick={() => toggleStartLanguage(lang)}
                  className={`px-4 py-2 rounded-xl text-sm transition-all border 
                    ${startLanguages.includes(lang)
                      ? "bg-green-600 border-green-400 text-white shadow-lg"
                      : "bg-gray-800 border-gray-700 text-gray-300"
                    }`}
                >
                  {lang}
                </button>
              ))}
            </div>
          </DialogBody>

          <DialogFooter>
            <Button
              color="green"
              className="bg-green-700 text-white hover:bg-green-800"
              onClick={() => {
                setStartOpen(false);
                window.location.href = "http://localhost:3000/prejoin?role=speaker";
              }}
            >
              Start
            </Button>
          </DialogFooter>
        </Dialog>

      </div>
    </div>
  );
}
