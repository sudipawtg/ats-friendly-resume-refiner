import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import { QueryProvider } from "@/providers/QueryProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "ResumeForge — AI-Powered Overleaf CV Tailoring",
  description: "Turn one master LaTeX CV into tailored versions for individual jobs or bulk campaigns.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        <QueryProvider>
          <AppShell>{children}</AppShell>
        </QueryProvider>
      </body>
    </html>
  );
}
