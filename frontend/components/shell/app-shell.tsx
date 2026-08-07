"use client";

import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { CommandPalette } from "@/components/shell/command-palette";
import { ConnectionBanner } from "@/components/states/connection-banner";
import { useUIStore } from "@/lib/stores/ui-store";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const density = useUIStore((state) => state.density);
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="flex min-h-screen"><div className="hidden lg:block"><Sidebar /></div><div className="min-w-0 flex-1"><ConnectionBanner /><Topbar /><main className={cn("mx-auto w-full max-w-[1720px]", density === "compact" ? "p-4 sm:p-5" : "p-4 sm:p-6 lg:p-8")}>{children}</main></div></div>
      <CommandPalette />
    </div>
  );
}
