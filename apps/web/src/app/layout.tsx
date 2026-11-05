import type { Metadata } from "next";
import "@qbank/content-renderer/styles.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Question Bank",
  description: "Multi-coaching question bank platform",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
