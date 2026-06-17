import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, Inter } from "next/font/google";

import { ShellGate } from "@/components/shell/shell-gate";
import { ThemeScript } from "@/components/shell/theme-script";
import { TenantProvider } from "@/contexts/tenant-context";
import { ThemeProvider } from "@/contexts/theme-context";

import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Signal — Telemetry",
  description: "Real-time telemetry pipeline dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${fraunces.variable} ${plexMono.variable}`}
    >
      <head>
        <ThemeScript />
      </head>
      <body>
        <ThemeProvider>
          <TenantProvider>
            <ShellGate>{children}</ShellGate>
          </TenantProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}