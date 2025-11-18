import { Typography } from "@material-tailwind/react";

const year = new Date().getFullYear();

export function Footer() {
  return (
    <footer className="relative px-4 py-6">
      <div className="container mx-auto">
        <hr className="my-6 border-gray-300" />
        <div className="flex flex-wrap items-center justify-center">
          <div className="mx-auto w-full px-4 text-center">
            <Typography
              variant="small"
              className="font-normal text-blue-gray-500"
            >
              Copyright © {year} Baashha X{" "}
              <a
                href="https://www.creative-tim.com?ref=mtk"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-gray-500 transition-colors hover:text-blue-500"
              >
              </a>
            </Typography>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
