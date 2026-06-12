import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "X- Audio Guest Booth",
  description: "Operator dashboard for event audio guestbook booths",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
