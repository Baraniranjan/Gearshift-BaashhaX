import React from "react";
import { useNavigate } from "react-router-dom";
import { MicrophoneIcon, UserGroupIcon } from "@heroicons/react/24/solid";

export default function LoginSelection() {
  const navigate = useNavigate();
  return (
    <div className="relative flex flex-col items-center justify-center min-h-screen">
      {/* Background image and overlay for dark theme */}
      <div className="absolute top-0 left-0 w-full h-full bg-[url('/img/background-3.png')] bg-cover bg-center z-0" />
      <div className="absolute top-0 left-0 w-full h-full bg-black/80 z-10" />
      <div className="relative z-20 flex flex-col items-center justify-center w-full h-full min-h-screen px-4 animate-fade-in">
        <h2 className="text-4xl font-extrabold text-white mb-4 drop-shadow-lg">
          Login As
        </h2>
        <p className="text-lg text-gray-300 mb-10 text-center max-w-xl">
          Choose your role to get started. Speakers can manage meetings, audiences
          can join and participate. Enjoy a seamless experience!
        </p>
        <div className="flex gap-8 flex-col md:flex-row">
          <div
            className="bg-white/10 backdrop-blur-lg border border-indigo-700 rounded-2xl shadow-2xl p-8 cursor-pointer hover:scale-105 md:hover:scale-102 hover:shadow-indigo-500/40 transition-transform w-60 flex flex-col items-center group"
            style={{ transition: "transform 0.2s" }}
            onClick={() => navigate("/speaker-dashboard")}
          >
            <MicrophoneIcon className="h-12 w-12 text-indigo-400 mb-3 drop-shadow-lg" />
            <span className="text-3xl font-bold mb-3 text-indigo-300 group-hover:text-indigo-400 transition">
              Speaker
            </span>
            <p className="text-white text-center mb-6 text-base font-medium leading-tight">
              Login as a speaker to manage your sessions and content. You can
              schedule, start, and control meetings with ease.
            </p>
          </div>
          <div
            className="bg-white/10 backdrop-blur-lg border border-blue-700 rounded-2xl shadow-2xl p-8 cursor-pointer hover:scale-105 md:hover:scale-102 hover:shadow-blue-500/40 transition-transform w-60 flex flex-col items-center group"
            style={{ transition: "transform 0.2s" }}
            onClick={() => navigate("/audience-dashboard")}
          >
            <UserGroupIcon className="h-12 w-12 text-blue-400 mb-3 drop-shadow-lg" />
            <span className="text-3xl font-bold mb-3 text-blue-300 group-hover:text-blue-400 transition">
              Audience
            </span>
            <p className="text-white text-center mb-6 text-base font-medium leading-tight">
              Login as an audience member to join and participate in sessions. View
              meeting details and interact with speakers.
            </p>
          </div>
        </div>
      </div>
      {/* Simple fade-in animation */}
      <style>{`
        .animate-fade-in {
          animation: fadeIn 1s ease;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .hover\:scale-105:hover {
          transform: scale(1.03);
        }
      `}</style>
    </div>
  );
}
