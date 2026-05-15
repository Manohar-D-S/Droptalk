import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AquaCascade AI",
  description: "Cascading Groundwater Recharge Mapping System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
