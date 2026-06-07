import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResuMate Pro",
  description: "AI-based recruitment assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
