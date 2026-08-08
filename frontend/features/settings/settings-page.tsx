"use client";

import { Bell, BrainCircuit, Check, LockKeyhole, LogOut, Moon, SlidersHorizontal, Sun, UserRound, Volume2 } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/states/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { UnavailableState } from "@/components/states/state-panel";
import { useUIStore } from "@/lib/stores/ui-store";
import { authApi, clearAccessToken, coreApi, getAccessToken } from "@/lib/api/client";
import { cn } from "@/lib/utils";

function Toggle({ checked, onCheckedChange, label, description, disabled = false }: { checked: boolean; onCheckedChange: (checked: boolean) => void; label: string; description: string; disabled?: boolean }) { return <div className="flex items-center justify-between gap-4 py-3"><div><p className={cn("text-sm font-medium", disabled && "text-slate-400")}>{label}</p><p className="mt-0.5 text-xs leading-5 text-slate-500">{description}</p></div><button type="button" role="switch" aria-label={label} aria-checked={checked} disabled={disabled} onClick={() => onCheckedChange(!checked)} className={cn("relative h-6 w-11 shrink-0 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2", checked ? "bg-blue-600" : "bg-slate-200 dark:bg-slate-700", disabled && "opacity-45")}><span className={cn("absolute top-0.5 size-5 rounded-full bg-white shadow-sm transition-transform", checked ? "translate-x-5" : "translate-x-0.5")} /></button></div>; }

export function SettingsPage() {
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const [themeMounted, setThemeMounted] = useState(false);
  const density = useUIStore((state) => state.density);
  const reduceDataMotion = useUIStore((state) => state.reduceDataMotion);
  const showConfidence = useUIStore((state) => state.showConfidence);
  const autoOpenReferences = useUIStore((state) => state.autoOpenReferences);
  const setDensity = useUIStore((state) => state.setDensity);
  const setReduceDataMotion = useUIStore((state) => state.setReduceDataMotion);
  const setShowConfidence = useUIStore((state) => state.setShowConfidence);
  const setAutoOpenReferences = useUIStore((state) => state.setAutoOpenReferences);
  const health = useQuery({ queryKey: ["settings", "security"], queryFn: coreApi.health });
  const identity = useQuery({ queryKey: ["auth", "me"], queryFn: authApi.me, enabled: Boolean(getAccessToken()), retry: false });
  useEffect(() => setThemeMounted(true), []);
  return <div className="space-y-7"><PageHeader eyebrow="Workspace configuration" title="Settings" description="Interface and AI-display preferences are saved on this device. Identity and security posture are read from the core service." />
      <div className="grid items-start gap-5 xl:grid-cols-[1fr_360px]"><div className="space-y-5"><Card className="p-5"><div className="flex items-center gap-2"><SlidersHorizontal className="size-4 text-blue-600" /><h2 className="text-sm font-semibold">Appearance and workspace</h2><Badge className="ml-auto">Saved locally</Badge></div><Separator className="my-4" /><p className="text-xs font-medium text-slate-500">Theme</p><div className="mt-2 grid grid-cols-2 gap-2"><Button variant={themeMounted && resolvedTheme === "light" ? "default" : "secondary"} onClick={() => setTheme("light")}><Sun />Light{themeMounted && resolvedTheme === "light" ? <Check /> : null}</Button><Button variant={themeMounted && resolvedTheme === "dark" ? "default" : "secondary"} onClick={() => setTheme("dark")}><Moon />Dark{themeMounted && resolvedTheme === "dark" ? <Check /> : null}</Button></div><p className="mt-5 text-xs font-medium text-slate-500">Density</p><div className="mt-2 grid grid-cols-2 gap-2"><Button variant={density === "comfortable" ? "default" : "secondary"} onClick={() => setDensity("comfortable")}>Comfortable</Button><Button variant={density === "compact" ? "default" : "secondary"} onClick={() => setDensity("compact")}>Compact</Button></div><Separator className="my-4" /><Toggle checked={reduceDataMotion} onCheckedChange={setReduceDataMotion} label="Reduce live data motion" description="Minimize non-essential transitions for long calls." /></Card>
      <Card className="p-5"><div className="flex items-center gap-2"><BrainCircuit className="size-4 text-blue-600" /><h2 className="text-sm font-semibold">AI preferences</h2><Badge className="ml-auto">Saved locally</Badge></div><Separator className="my-4" /><Toggle checked={showConfidence} onCheckedChange={setShowConfidence} label="Show confidence scores" description="Display aggregate and per-agent confidence in copilot cards." /><Toggle checked={autoOpenReferences} onCheckedChange={setAutoOpenReferences} label="Prioritize knowledge references" description="Keep grounded source cards visible beside suggestions." /></Card>
      <div className="grid gap-5 lg:grid-cols-2"><UnavailableState capability="CRM integration" endpoint="integration configuration and credential routes" /><UnavailableState capability="Voice settings" endpoint="voice-provider and device preference routes" /></div></div>
      <div className="space-y-5"><Card className="p-5"><p className="flex items-center gap-2 text-sm font-semibold"><UserRound className="size-4 text-blue-600" />Profile</p><div className="mt-4 flex items-center gap-3"><div className="grid size-11 place-items-center rounded-xl bg-slate-900 text-xs font-semibold text-white">{identity.data ? identity.data.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() : "SA"}</div><div><p className="text-sm font-medium">{identity.data?.display_name ?? "Development workspace"}</p><p className="text-xs text-slate-400">{identity.data ? `${identity.data.email} · ${identity.data.role}` : "Authentication bypass is limited to non-production"}</p></div></div>{identity.data ? <Button variant="secondary" size="sm" className="mt-4" onClick={() => { clearAccessToken(); router.replace("/login"); }}><LogOut />Sign out</Button> : null}</Card><Card className="p-5"><p className="flex items-center gap-2 text-sm font-semibold"><Bell className="size-4 text-blue-600" />Notifications</p><Separator className="my-4" /><Toggle checked={false} onCheckedChange={() => undefined} label="Call alerts" description="Operational notifications are generated server-side; per-user preferences are not configured." disabled /><Toggle checked={false} onCheckedChange={() => undefined} label="Follow-up reminders" description="The scheduler creates due reminder notifications from persisted follow-ups." disabled /></Card><Card className="p-5"><p className="flex items-center gap-2 text-sm font-semibold"><LockKeyhole className="size-4 text-blue-600" />Security</p><p className="mt-3 text-xs leading-5 text-slate-500">JWT authentication, role-protected user routes, internal-service keys, request rate limits, encrypted sensitive fields, and production secret validation are implemented.</p><Badge className="mt-3" variant={health.data?.data.auth_required ? "success" : "warning"}>{health.data?.data.auth_required ? "Authentication enforced" : "Development bypass"}</Badge></Card><Card className="p-5"><p className="flex items-center gap-2 text-sm font-semibold"><Volume2 className="size-4 text-blue-600" />Audio format</p><p className="mt-3 text-xs leading-5 text-slate-500">Live microphone streaming uses the AI service&apos;s mono 16 kHz PCM16 contract with bounded frames, heartbeats, reconnect, and backpressure.</p></Card></div></div>
  </div>;
}
