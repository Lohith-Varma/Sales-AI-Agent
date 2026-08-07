"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { BarChart3, BookOpenText, Bot, CalendarClock, ChartNoAxesCombined, ChevronLeft, CircleGauge, History, ListTodo, PanelLeftClose, Settings2, ShieldCheck, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { navigation } from "@/lib/constants/navigation";
import { useUIStore } from "@/lib/stores/ui-store";
import { cn } from "@/lib/utils";

const icons = [CircleGauge, Bot, History, UsersRound, BookOpenText, BarChart3, ListTodo, CalendarClock, ChartNoAxesCombined, Settings2, ShieldCheck];

export function Sidebar({ mobile = false, onNavigate }: { mobile?: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  const collapsed = useUIStore((state) => state.sidebarCollapsed) && !mobile;
  const setCollapsed = useUIStore((state) => state.setSidebarCollapsed);

  return (
    <aside className={cn("flex h-full flex-col bg-slate-950 text-slate-300", mobile ? "w-full" : "sticky top-0 h-screen transition-[width] duration-200", collapsed ? "w-20" : "w-[280px]")}> 
      <div className={cn("flex h-[72px] items-center border-b border-white/8", collapsed ? "justify-center px-3" : "justify-between px-5")}>
        <Link href="/dashboard" className="flex min-w-0 items-center gap-3" onClick={onNavigate} aria-label="Pay-in-3 workspace home">
          <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-blue-600 text-white shadow-[0_6px_18px_rgba(37,99,235,.3)]"><Bot className="size-4.5" /></span>
          {!collapsed ? <span className="min-w-0"><span className="block truncate text-sm font-semibold tracking-[-0.01em] text-white">Pay-in-3 Copilot</span><span className="block truncate text-[11px] text-slate-500">Sales workspace</span></span> : null}
        </Link>
        {!mobile && !collapsed ? <Button variant="ghost" size="icon-sm" className="text-slate-500 hover:bg-white/8 hover:text-white" onClick={() => setCollapsed(true)} aria-label="Collapse sidebar"><PanelLeftClose /></Button> : null}
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label="Primary navigation">
        {navigation.map((item, index) => {
          const Icon = icons[index] ?? CircleGauge;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const link = <Link href={item.href} onClick={onNavigate} aria-current={active ? "page" : undefined} className={cn("relative flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium outline-none transition-colors duration-150 hover:bg-white/6 hover:text-white focus-visible:ring-2 focus-visible:ring-blue-500", active ? "text-white" : "text-slate-400", collapsed && "justify-center px-0")}>
            {active ? <motion.span layoutId={mobile ? "mobile-active-nav" : "active-nav"} className="absolute inset-0 rounded-xl bg-white/9 shadow-[inset_0_0_0_1px_rgba(255,255,255,.035)]" transition={{ duration: 0.18 }} /> : null}
            <Icon className={cn("relative z-10 size-[17px] shrink-0", active && "text-blue-400")} />
            {!collapsed ? <span className="relative z-10 flex-1 truncate">{item.label}</span> : null}
            {!collapsed && item.label === "Live Calls" ? <span className="relative z-10 size-1.5 rounded-full bg-emerald-400" aria-label="Realtime available" /> : null}
          </Link>;
          return collapsed ? <Tooltip key={item.href}><TooltipTrigger asChild>{link}</TooltipTrigger><TooltipContent side="right">{item.label}</TooltipContent></Tooltip> : <div key={item.href}>{link}</div>;
        })}
      </nav>
      <div className="border-t border-white/8 p-3">
        {collapsed ? <Button variant="ghost" size="icon" className="w-full text-slate-500 hover:bg-white/8 hover:text-white" onClick={() => setCollapsed(false)} aria-label="Expand sidebar"><ChevronLeft className="rotate-180" /></Button> : <div className="rounded-xl border border-white/8 bg-white/[.035] p-3"><div className="flex items-center gap-2 text-xs font-medium text-slate-300"><span className="size-2 rounded-full bg-amber-400" />Backend auth unavailable</div><p className="mt-1.5 text-[11px] leading-4 text-slate-500">Access is not protected until server authentication is implemented.</p></div>}
      </div>
    </aside>
  );
}
