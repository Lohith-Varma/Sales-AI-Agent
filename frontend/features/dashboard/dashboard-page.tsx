"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Bot, CalendarClock, CircleDollarSign, Clock3, HeartHandshake, PhoneCall, Sparkles, Target } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as ChartTooltip } from "recharts";
import { PageHeader } from "@/components/states/page-header";
import { MetricCard } from "@/components/data-display/metric-card";
import { ChartWrapper } from "@/components/data-display/chart-wrapper";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { StatePanel, UnavailableState } from "@/components/states/state-panel";
import { aiApi, coreApi, queryKeys } from "@/lib/api/client";

const metrics = [
  ["Today's Calls", PhoneCall, "Requires a call aggregate endpoint"],
  ["Active Calls", Activity, "Requires an active-call list endpoint"],
  ["Conversion Rate", Target, "Requires outcome analytics"],
  ["Revenue Generated", CircleDollarSign, "Requires revenue attribution"],
  ["Pending Follow-ups", CalendarClock, "Requires follow-up list API"],
  ["Average Call Duration", Clock3, "Requires call aggregate endpoint"],
  ["Customer Satisfaction", HeartHandshake, "Requires feedback metrics"],
  ["AI Suggestions Used", Sparkles, "Requires suggestion telemetry"],
] as const;

export function DashboardPage() {
  const core = useQuery({ queryKey: queryKeys.coreHealth, queryFn: coreApi.health, refetchInterval: 30_000 });
  const ai = useQuery({ queryKey: queryKeys.aiHealth, queryFn: aiApi.health, refetchInterval: 30_000 });
  const ready = useQuery({ queryKey: queryKeys.aiReadiness, queryFn: aiApi.readiness, refetchInterval: 30_000 });
  const serviceData = [
    { name: "Core API", value: core.data?.data.status === "healthy" ? 1 : 0, color: "#22C55E" },
    { name: "AI API", value: ai.data?.status === "healthy" ? 1 : 0, color: "#2563EB" },
    { name: "Knowledge", value: ready.data?.dependencies.chroma?.status === "healthy" ? 1 : 0, color: "#0F172A" },
  ];
  const healthyCount = serviceData.reduce((sum, service) => sum + service.value, 0);
  const loading = core.isLoading || ai.isLoading || ready.isLoading;

  return <div className="space-y-7"><PageHeader eyebrow="Command center" title="Good morning, Sales Agent" description="Your live service state is connected below. Business metrics remain intentionally blank until the backend exposes their contracts." />
    <section aria-labelledby="business-metrics"><div className="mb-3 flex items-center justify-between"><h2 id="business-metrics" className="text-sm font-semibold text-slate-900 dark:text-slate-100">Business overview</h2><Badge>8 backend contracts pending</Badge></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, icon, description]) => <MetricCard key={label} label={label} value="—" description={description} icon={icon} unavailable />)}</div></section>
    <div className="grid gap-4 xl:grid-cols-[.8fr_1.2fr]">
      <ChartWrapper title="Platform readiness" description="Live checks against both committed FastAPI services.">{loading ? <Skeleton className="h-56" /> : <div className="grid min-h-56 grid-cols-[160px_1fr] items-center gap-3"><div className="relative h-40"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={serviceData.map((item) => ({ ...item, value: item.value || .04 }))} innerRadius={50} outerRadius={70} dataKey="value" stroke="none">{serviceData.map((entry) => <Cell key={entry.name} fill={entry.value ? entry.color : "#E5E7EB"} />)}</Pie><ChartTooltip /></PieChart></ResponsiveContainer><div className="pointer-events-none absolute inset-0 grid place-items-center text-center"><span><b className="block text-2xl text-slate-950 dark:text-white">{healthyCount}/3</b><span className="text-[10px] text-slate-400">ready</span></span></div></div><div className="space-y-3">{serviceData.map((service) => <div key={service.name} className="flex items-center justify-between gap-3 text-sm"><span className="flex items-center gap-2 text-slate-600 dark:text-slate-300"><span className="size-2 rounded-full" style={{ backgroundColor: service.value ? service.color : "#CBD5E1" }} />{service.name}</span><Badge variant={service.value ? "success" : "warning"}>{service.value ? "Healthy" : "Unavailable"}</Badge></div>)}</div></div>}</ChartWrapper>
      <ChartWrapper title="Conversion funnel" description="Lead-stage totals and conversion rates."><UnavailableState capability="Conversion funnel" endpoint="a lead-stage analytics endpoint" className="min-h-56" /></ChartWrapper>
    </div>
    <div className="grid gap-4 lg:grid-cols-3"><ChartWrapper title="Daily calls" description="Daily inbound and outbound volume."><UnavailableState capability="Daily calls" endpoint="a time-series calls endpoint" className="min-h-52" /></ChartWrapper><ChartWrapper title="Agent performance" description="Conversion, quality, and compliance by agent."><UnavailableState capability="Agent performance" endpoint="an agent analytics endpoint" className="min-h-52" /></ChartWrapper><ChartWrapper title="Lead status" description="Current lead distribution by lifecycle stage."><UnavailableState capability="Lead status" endpoint="a paginated lead aggregate endpoint" className="min-h-52" /></ChartWrapper></div>
    <div className="grid gap-4 xl:grid-cols-3"><ChartWrapper title="Recent activity" description="Customer, call, and CRM changes."><StatePanel title="No activity feed contract" description="The backend does not expose an activity endpoint." icon={Activity} className="min-h-52" /></ChartWrapper><ChartWrapper title="Upcoming follow-ups" description="Callbacks and reminders due next."><StatePanel title="Follow-ups are not queryable" description="The database model exists, but it has no API route." icon={CalendarClock} className="min-h-52" /></ChartWrapper><ChartWrapper title="Recent AI recommendations" description="Grounded recommendations from active calls."><StatePanel title="No recommendation history" description="Copilot results are available only during active in-memory sessions." icon={Bot} className="min-h-52" /></ChartWrapper></div>
  </div>;
}
