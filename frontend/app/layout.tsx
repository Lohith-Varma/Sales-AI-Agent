import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Pay-in-3 Sales Copilot", template: "%s · Pay-in-3 Copilot" },
  description: "AI-assisted workspace for safe, grounded Pay-in-3 sales conversations.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" suppressHydrationWarning><body className="antialiased"><a href="#main-content" className="fixed left-3 top-3 z-[100] -translate-y-20 rounded-lg bg-slate-950 px-3 py-2 text-sm font-medium text-white transition-transform focus:translate-y-0">Skip to content</a><Providers>{children}</Providers></body></html>;
}
