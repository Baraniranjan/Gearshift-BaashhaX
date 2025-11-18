import { Home, Profile, SignIn, SignUp } from "@/pages";

import { LoginSelection } from "@/pages";
import { SpeakerDashboard } from "@/pages";
import { AudienceDashboard } from "@/pages";

export const routes = [
  {
    name: "home",
    path: "/home",
    element: <Home />,
  },
  {
    name: "profile",
    path: "/profile",
    element: <Profile />,
  },
  {
    name: "Sign In",
    path: "/sign-in",
    element: <SignIn />,
  },
  {
    name: "Sign Up",
    path: "/sign-up",
    element: <SignUp />,
  },
  {
    name: "Login Selection",
    path: "/login-selection",
    element: <LoginSelection />,
  },
  {
    name: "Speaker Dashboard",
    path: "/speaker-dashboard",
    element: <SpeakerDashboard />,
  },
  {
    name: "Audience Dashboard",
    path: "/audience-dashboard",
    element: <AudienceDashboard />,
  },
  {
    name: "Docs",
    href: "https://www.material-tailwind.com/docs/react/installation",
    target: "_blank",
    element: "",
  },
];

export default routes;
