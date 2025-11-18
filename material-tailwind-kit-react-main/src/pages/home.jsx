import React from "react";
import {
  Card,
  Input,
  Textarea,
  Checkbox,
  Button,
  IconButton,
  Typography,
} from "@material-tailwind/react";
import { PageTitle, Footer } from "@/widgets/layout";
import { FeatureCard } from "@/widgets/cards";
import { featuresData } from "@/data";

export function Home() {
  return (
    <>
      {/* -------------------- HERO SECTION WITH VIDEO BACKGROUND -------------------- */}
      <div className="relative flex h-screen content-center items-center justify-center pt-16 pb-32">
        {/* Video Background */}
        <video
          autoPlay
          loop
          muted
          playsInline
          className="absolute top-0 left-0 w-full h-full object-cover"
        >
          <source src="/videos/background.mp4" type="video/mp4" />
          Your browser does not support the video tag.
        </video>

        {/* Dark Overlay */}
        <div className="absolute top-0 h-full w-full bg-black/60" />

        {/* Hero Content */}
        <div className="max-w-8xl container relative mx-auto">
          <div className="flex flex-wrap items-center">
            <div className="ml-auto mr-auto w-full px-4 text-center lg:w-8/12">
              <Typography
                variant="h1"
                color="white"
                className="mb-6 font-black"
              >
                Connect in Any Language.
              </Typography>
              <Typography variant="lead" color="white" className="opacity-80">
                Break language barriers instantly. Our platform captures speech,
                transcribes it, translates it into multiple languages, and
                streams personalized audio straight to participants’ phones —
                no headsets, no interpreters, just seamless communication for
                meetings and events of any size.
              </Typography>
            </div>
          </div>
        </div>
      </div>

      {/* -------------------- FEATURES SECTION -------------------- */}
      <section className="-mt-32 bg-white px-4 pb-20 pt-4">
        <div className="container mx-auto">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {featuresData.map(({ color, title, icon, description }) => (
              <FeatureCard
                key={title}
                color={color}
                title={title}
                icon={React.createElement(icon, {
                  className: "w-5 h-5 text-white",
                })}
                description={description}
              />
            ))}
          </div>
        </div>
      </section>

      {/* -------------------- FOOTER -------------------- */}
      <div className="bg-white">
        <Footer />
      </div>
    </>
  );
}
