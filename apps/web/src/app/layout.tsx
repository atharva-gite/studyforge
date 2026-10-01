import type { Metadata } from "next";
import { IBM_Plex_Mono, Source_Sans_3, Syne } from "next/font/google";

import { Shell } from "@/components/shell";

import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  variable: "--font-syne",
});

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source",
});

const plex = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex",
});

export const metadata: Metadata = {
  title: {
    default: "StudyForge",
    template: "%s · StudyForge",
  },
  description: "A course corpus for grounded retrieval. Upload material, then ask only from indexed evidence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${syne.variable} ${sourceSans.variable} ${plex.variable} antialiased`}>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
