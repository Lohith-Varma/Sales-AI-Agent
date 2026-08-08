"use client";

import { usePathname } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Menu, Moon, Search, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { aiApi, authApi, coreApi, getAccessToken, queryKeys } from "@/lib/api/client";
import { navigation } from "@/lib/constants/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { Sidebar } from "@/components/shell/sidebar";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useUIStore } from "@/lib/stores/ui-store";

function StatusDot({ healthy }: { healthy: boolean }) { return <span className={`size-1.5 rounded-full ${healthy ? "bg-emerald-500" : "bg-amber-500"}`} />; }

export function Topbar() {
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const { resolvedTheme, setTheme } = useTheme();
  const [themeMounted, setThemeMounted] = useState(false);
  const setCommandOpen = useUIStore((state) => state.setCommandOpen);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const core = useQuery({ queryKey: queryKeys.coreHealth, queryFn: coreApi.health, refetchInterval: 30_000, retry: 1 });
  const ai = useQuery({ queryKey: queryKeys.aiHealth, queryFn: aiApi.health, refetchInterval: 30_000, retry: 1 });
  const notifications = useQuery({ queryKey: queryKeys.notifications, queryFn: coreApi.notifications, refetchInterval: 30_000, retry: 1 });
  const identity = useQuery({ queryKey: ["auth", "me"], queryFn: authApi.me, enabled: Boolean(getAccessToken()), retry: false });
  const markRead = useMutation({ mutationFn: coreApi.markNotificationRead, onSuccess: () => void queryClient.invalidateQueries({ queryKey: queryKeys.notifications }) });
  const current = navigation.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  const coreHealthy = core.data?.data.status === "healthy";
  const aiHealthy = ai.data?.status === "healthy";
  const unread = notifications.data?.data.filter((item) => !item.read_at) ?? [];
  const initials = identity.data ? identity.data.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() : "SA";
  useEffect(() => setThemeMounted(true), []);

  return (
    <header className="sticky top-0 z-40 flex h-[72px] items-center gap-3 border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl sm:px-6 dark:border-slate-800 dark:bg-slate-950/90">
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}><Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu /></Button><SheetContent side="left" className="w-[280px] border-0 p-0" title="Navigation"><Sidebar mobile onNavigate={() => setMobileOpen(false)} /></SheetContent></Sheet>
      <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">{current?.label ?? "Sales workspace"}</p><p className="hidden text-xs text-slate-400 sm:block">Pay-in-3 agent operations</p></div>
      <button onClick={() => setCommandOpen(true)} className="hidden h-9 w-[min(34vw,340px)] items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 text-left text-sm text-slate-400 transition hover:border-slate-300 hover:bg-white md:flex dark:border-slate-800 dark:bg-slate-900 dark:hover:bg-slate-800" aria-label="Open global search"><Search className="size-4" /><span className="flex-1">Search workspace</span><kbd className="rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] dark:border-slate-700 dark:bg-slate-950">⌘K</kbd></button>
      <div className="hidden items-center gap-2 xl:flex"><Badge variant={coreHealthy ? "success" : "warning"}><StatusDot healthy={coreHealthy} />Core {coreHealthy ? "connected" : "unavailable"}</Badge><Badge variant={aiHealthy ? "primary" : "warning"}><StatusDot healthy={aiHealthy} />AI {aiHealthy ? "ready" : "unavailable"}</Badge></div>
      <Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")} aria-label="Toggle dark mode">{themeMounted && resolvedTheme === "dark" ? <Sun /> : <Moon />}</Button></TooltipTrigger><TooltipContent>Toggle theme</TooltipContent></Tooltip>
      <Sheet open={notificationOpen} onOpenChange={setNotificationOpen}><Tooltip><TooltipTrigger asChild><Button variant="ghost" size="icon" className="relative" aria-label="Notifications" onClick={() => setNotificationOpen(true)}><Bell />{unread.length ? <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-red-500" /> : null}</Button></TooltipTrigger><TooltipContent>{unread.length} unread notifications</TooltipContent></Tooltip><SheetContent side="right" className="w-full max-w-sm p-5" title="Notifications"><div className="space-y-4"><div><h2 className="text-lg font-semibold">Notifications</h2><p className="mt-1 text-xs text-slate-500">Generated by persisted sales and reminder events. Select a new item to mark it read.</p></div><div className="space-y-3">{notifications.data?.data.length ? notifications.data.data.map((item) => <button type="button" key={item.id} onClick={() => { if (!item.read_at) markRead.mutate(item.id); }} className="w-full rounded-xl border border-slate-200 p-3 text-left dark:border-slate-800"><div className="flex items-center justify-between gap-3"><p className="text-xs font-semibold">{item.title}</p>{!item.read_at ? <Badge variant="primary">New</Badge> : null}</div><p className="mt-2 text-xs leading-5 text-slate-500">{item.body}</p><p className="mt-2 text-[10px] text-slate-400">{new Date(item.created_at).toLocaleString()}</p></button>) : <p className="rounded-xl bg-slate-50 p-4 text-xs text-slate-500 dark:bg-slate-900">No notifications have been generated.</p>}</div></div></SheetContent></Sheet>
      <Tooltip><TooltipTrigger asChild><button className="grid size-9 place-items-center rounded-xl bg-slate-900 text-xs font-semibold text-white ring-2 ring-white dark:bg-slate-700 dark:ring-slate-950" aria-label="Agent profile">{initials}</button></TooltipTrigger><TooltipContent>{identity.data ? `${identity.data.display_name} · ${identity.data.role}` : "Development workspace"}</TooltipContent></Tooltip>
    </header>
  );
}
