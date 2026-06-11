import type { Metadata, Viewport } from "next";
import { AuthProvider } from "@/features/auth/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "FitTrack AI",
    template: "%s | FitTrack AI",
  },
  description:
    "AI-powered personal fitness tracker — workouts, nutrition, measurements, wellness, habits, and progress insights.",
  applicationName: "FitTrack AI",
  keywords: ["fitness", "workout tracker", "nutrition", "health", "goals"],
  robots: { index: false, follow: false }, // Set to true when publicly launched
};

export const viewport: Viewport = {
  themeColor: "#22c55e",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  readonly children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        {/* Skip-navigation link for keyboard and screen-reader users */}
        <a href="#main-content" className="skip-nav">
          Skip to main content
        </a>
        <AuthProvider>
          <div id="main-content">{children}</div>
        </AuthProvider>
      </body>
    </html>
  );
}
