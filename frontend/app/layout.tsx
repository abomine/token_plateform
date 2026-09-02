import type { ReactNode } from "react";
import "./globals.css";

export const metadata = {
  title: "ComputeMarket B2B",
  description: "Spend and earn credits for LLM compute and micro-tasks.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
