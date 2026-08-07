"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, AlertTriangle, BookOpenCheck, Database, FileClock, KeyRound, RefreshCw, ShieldAlert, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/states/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { UnavailableState } from "@/components/states/state-panel";
import { KnowledgeUpload } from "@/features/knowledge/knowledge-upload";
import { aiApi, coreApi, queryKeys } from "@/lib/api/client";
import { titleCase } from "@/lib/utils";

export function AdminPage() {
  const core = useQuery({ queryKey: queryKeys.coreHealth, queryFn: coreApi.health, refetchInterval: 20_000 });
  const ai = useQuery({ queryKey: queryKeys.aiHealth, queryFn: aiApi.health, refetchInterval: 20_000 });
  const ready = useQuery({ queryKey: queryKeys.aiReadiness, queryFn: aiApi.readiness, refetchInterval: 20_000 });
  const refresh = () => { void core.refetch(); void ai.refetch(); void ready.refetch(); };
  return <div className="space-y-7"><PageHeader eyebrow="Platform operations" title="Admin" description="System health and approved knowledge ingestion are connected. User, role, log, and administrative analytics APIs are missing." actions={<Button variant="secondary" onClick={refresh}><RefreshCw />Refresh health</Button>} />
    <div className="flex gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"><ShieldAlert className="mt-0.5 size-5 shrink-0" /><div><p className="text-sm font-semibold">Admin access is not protected</p><p className="mt-1 text-xs leading-5">The backend has no authentication, role, or permission enforcement. Do not expose this route publicly until server-side authorization exists.</p></div></div>
    <section><div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-semibold">System health</h2><Badge variant={core.data && ai.data && ready.data ? "success" : "warning"}>Live service checks</Badge></div><div className="grid gap-4 md:grid-cols-3">{core.isLoading ? <Skeleton className="h-36 rounded-2xl" /> : <HealthCard icon={Database} label="Core sales API" status={core.data?.data.status ?? "unavailable"} detail={core.data ? `${core.data.data.env} · ${new Date(core.data.data.timestamp).toLocaleTimeString()}` : core.error?.message} />}{ai.isLoading ? <Skeleton className="h-36 rounded-2xl" /> : <HealthCard icon={Activity} label={ai.data?.service ?? "AI copilot API"} status={ai.data?.status ?? "unavailable"} detail={ai.data ? `${ai.data.environment} · v${ai.data.version}` : ai.error?.message} />}{ready.isLoading ? <Skeleton className="h-36 rounded-2xl" /> : <HealthCard icon={BookOpenCheck} label="Knowledge retrieval" status={ready.data?.dependencies.chroma?.status ?? ready.data?.status ?? "unavailable"} detail={ready.data?.dependencies.chroma?.detail ?? ready.error?.message} />}</div></section>
    <div className="grid items-start gap-5 xl:grid-cols-[1fr_380px]"><Card className="p-5"><h2 className="text-sm font-semibold">Knowledge management</h2><p className="mt-1 text-xs leading-5 text-slate-500">Index an approved document. Listing, updating, deleting, versioning, and publishing status are not available.</p><div className="mt-5"><KnowledgeUpload /></div></Card><Card className="p-5"><p className="flex items-center gap-2 text-sm font-semibold"><AlertTriangle className="size-4 text-amber-500" />Operational constraints</p><ul className="mt-4 space-y-3 text-xs leading-5 text-slate-500"><li>AI sessions and transcripts are in process memory.</li><li>Core and AI services default to the same port unless configured separately.</li><li>No audit-log query endpoint is available.</li><li>No user identity is attached to frontend writes.</li></ul></Card></div>
    <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4"><UnavailableState capability="User management" endpoint="user list and mutation endpoints" /><UnavailableState capability="Roles and permissions" endpoint="RBAC policies and server enforcement" /><UnavailableState capability="System logs" endpoint="auditable paginated log queries" /><UnavailableState capability="Admin analytics" endpoint="administrative aggregate endpoints" /></div>
    <Card className="p-5"><h2 className="text-sm font-semibold">Required admin contracts</h2><div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{[[UsersRound, "Users"], [KeyRound, "Roles"], [FileClock, "Audit logs"], [Activity, "Platform analytics"]].map(([Icon, label]) => { const Component = Icon as typeof UsersRound; return <div key={String(label)} className="flex items-center gap-3 rounded-xl bg-slate-50 p-3 dark:bg-slate-800/50"><Component className="size-4 text-slate-400" /><div><p className="text-xs font-medium">{String(label)}</p><p className="mt-0.5 text-[10px] text-slate-400">Backend required</p></div></div>; })}</div></Card>
  </div>;
}

function HealthCard({ icon: Icon, label, status, detail }: { icon: typeof Activity; label: string; status: string; detail?: string }) { const healthy = status === "healthy"; return <Card className="p-4"><div className="flex items-start justify-between"><div className="grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-500 dark:bg-slate-800"><Icon className="size-4" /></div><Badge variant={healthy ? "success" : status === "degraded" ? "warning" : "danger"}>{titleCase(status)}</Badge></div><p className="mt-4 text-sm font-semibold">{label}</p><p className="mt-1 truncate text-[11px] text-slate-400">{detail ?? "No details returned"}</p></Card>; }
