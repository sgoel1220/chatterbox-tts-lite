import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Creepy Brain Dashboard",
  description: "Monitor creepy pasta audio production pipelines",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <nav className="border-b px-6 py-3 flex items-center gap-6">
          <span className="font-semibold text-lg">🧠 Creepy Brain</span>
          <Link href="/workflows" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Workflows
          </Link>
          <Link href="/gpu-pods" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            GPU Pods
          </Link>
          <Link href="/settings" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Settings
          </Link>
        </nav>
        <main className="flex-1 p-6">{children}</main>
      </body>
    </html>
  );
}
