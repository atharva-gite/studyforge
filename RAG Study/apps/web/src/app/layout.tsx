import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";

import { Shell } from "@/components/shell";

import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
});

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-source",
});

export const metadata: Metadata = {
  title: {
    default: "Folio",
    template: "%s · Folio",
  },
  description: "A course-aware study desk. Upload a course, then keep its material in one place.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${fraunces.variable} ${sourceSans.variable} antialiased`}>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
