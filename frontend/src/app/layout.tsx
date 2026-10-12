import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CodeLens — Grounded Codebase Explanation Engine",
  description: "AST-Aware, Graph-Expanded, and Line-Cited Codebase Intelligence Engine",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full bg-zinc-950">
      <body className="h-full w-full bg-zinc-950 text-zinc-100 antialiased overflow-hidden">
        {children}
      </body>
    </html>
  );
}
