import type { Metadata } from "next";
import { IBM_Plex_Sans } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { DISCLAIMER } from "@/lib/brand";

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Ledgerly",
  description: "Sort rental statements into Schedule E lines.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={plex.variable}>
      <body className="min-h-screen">
        <Providers>{children}</Providers>
        <footer className="mx-auto max-w-6xl px-4 py-8 text-xs text-muted">{DISCLAIMER}</footer>
      </body>
    </html>
  );
}
