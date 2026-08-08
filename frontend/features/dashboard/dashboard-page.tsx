"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, CalendarClock, CircleDollarSign, Clock3, HeartHandshake, PhoneCall, Sparkles, Target } from "lucide-react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip as ChartTooltip } from "recharts";
import { ChartWrapper } from "@/components/data-display/chart-wrapper";
import { MetricCard } from "@/components/data-display/metric-card";
import { PageHeader } from "@/components/states/page-header";
import { ErrorState, StatePanel } from "@/components/states/state-panel";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { aiApi, coreApi, queryKeys } from "@/lib/api/client";
import { formatDuration, titleCase } from "@/lib/utils";

export function DashboardPage() {
  const dashboard = useQuery({ queryKey: queryKeys.dashboard, queryFn: coreApi.dashboard, refetchInterval: 15_000 });
  const core = useQuery({ queryKey: queryKeys.coreHealth, queryFn: coreApi.health, refetchInterval: 30_000 });
  const ai = useQuery({ queryKey: queryKeys.aiHealth, queryFn: aiApi.health, refetchInterval: 30_000 });
  const ready = useQuery({ queryKey: queryKeys.aiReadiness, queryFn: aiApi.readiness, refetchInterval: 30_000 });
  const data = dashboard.data?.data;
  const serviceData = [
    { name: "Core API", value: core.data?.data.status === "healthy" ? 1 : 0, color: "#22C55E" },
    { name: "AI API", value: ai.data?.status === "healthy" ? 1 : 0, color: "#2563EB" },
    { name: "Knowledge", value: ready.data?.dependencies.chroma?.status === "healthy" ? 1 : 0, color: "#0F172A" },
  ];
  const healthyCount = serviceData.reduce((sum, service) => sum + service.value, 0);
  const serviceLoading = core.isLoading || ai.isLoading || ready.isLoading;
  const metrics = data ? [
    ["Today's Calls", String(data.metrics.today_calls), "Calls created today", PhoneCall],
    ["Active Calls", String(data.metrics.active_calls), "Calls currently in progress", Activity],
    ["Conversion Rate", `${data.metrics.conversion_rate.toFixed(1)}%`, "Converted completed calls", Target],
    ["Revenue Generated", new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(data.metrics.revenue), "Persisted revenue attribution", CircleDollarSign],
    ["Pending Follow-ups", String(data.metrics.pending_follow_ups), "Pending or scheduled callbacks", CalendarClock],
    ["Average Call Duration", formatDuration(data.metrics.average_duration_seconds), "Completed-call average", Clock3],
    ["Customer Satisfaction", data.metrics.customer_satisfaction == null ? "—" : data.metrics.customer_satisfaction.toFixed(1), "Average recorded score", HeartHandshake],
    ["AI Suggestion Usage", `${data.metrics.ai_suggestion_usage_rate.toFixed(1)}%`, `${data.metrics.ai_suggestions} persisted suggestions`, Sparkles],
  ] as const : [];

  return <div className="space-y-7">
    <PageHeader eyebrow="Command center" title="Good morning, Sales Agent" description="Live call, conversion, follow-up, revenue, satisfaction, and AI-usage metrics from the core database." />
    <section aria-labelledby="business-metrics">
      <div className="mb-3 flex items-center justify-between"><h2 id="business-metrics" className="text-sm font-semibold">Business overview</h2><Badge variant="success">Database-backed</Badge></div>
      {dashboard.isLoading ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-40 rounded-2xl" />)}</div> : dashboard.isError ? <ErrorState title="Dashboard could not be loaded" description={dashboard.error.message} retry={() => void dashboard.refetch()} /> : <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(([label, value, description, icon]) => <MetricCard key={label} label={label} value={value} description={description} icon={icon} />)}</div>}
    </section>
    <div className="grid gap-4 xl:grid-cols-[.8fr_1.2fr]">
      <ChartWrapper title="Platform readiness" description="Live checks against the core, AI, and retrieval services.">{serviceLoading ? <Skeleton className="h-56" /> : <div className="grid min-h-56 grid-cols-[160px_1fr] items-center gap-3"><div className="relative h-40"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={serviceData.map((item) => ({ ...item, value: item.value || .04 }))} innerRadius={50} outerRadius={70} dataKey="value" stroke="none">{serviceData.map((entry) => <Cell key={entry.name} fill={entry.value ? entry.color : "#E5E7EB"} />)}</Pie><ChartTooltip /></PieChart></ResponsiveContainer><div className="pointer-events-none absolute inset-0 grid place-items-center text-center"><span><b className="block text-2xl">{healthyCount}/3</b><span className="text-[10px] text-slate-400">ready</span></span></div></div><div className="space-y-3">{serviceData.map((service) => <div key={service.name} className="flex items-center justify-between gap-3 text-sm"><span className="flex items-center gap-2 text-slate-600 dark:text-slate-300"><span className="size-2 rounded-full" style={{ backgroundColor: service.value ? service.color : "#CBD5E1" }} />{service.name}</span><Badge variant={service.value ? "success" : "warning"}>{service.value ? "Healthy" : "Unavailable"}</Badge></div>)}</div></div>}</ChartWrapper>
      <ChartWrapper title="Conversion funnel" description="Current persisted lead-stage totals.">{data?.lead_funnel.length ? <div className="space-y-3 py-4">{data.lead_funnel.map((item) => <div key={item.stage} className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3 dark:bg-slate-800/60"><span className="text-sm">{titleCase(item.stage)}</span><Badge variant="primary">{item.count}</Badge></div>)}</div> : <StatePanel title="No leads yet" description="Lead totals appear after customer creation." icon={Target} className="min-h-56" />}</ChartWrapper>
    </div>
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartWrapper title="Recent activity" description="Latest persisted call and CRM changes.">{data?.recent_activity.length ? <div className="divide-y divide-slate-100 dark:divide-slate-800">{data.recent_activity.map((item) => <div key={item.call_id} className="flex items-center justify-between gap-4 py-3 text-xs"><div><p className="font-medium">{item.customer_name ?? "Unknown customer"}</p><p className="mt-1 text-slate-400">{item.outcome ? titleCase(item.outcome) : titleCase(item.status)}</p></div><Badge>{titleCase(item.status)}</Badge></div>)}</div> : <StatePanel title="No call activity" description="Started calls appear here immediately." icon={Activity} className="min-h-52" />}</ChartWrapper>
      <ChartWrapper title="Upcoming follow-ups" description="Callbacks and reminders due next.">{data?.upcoming_follow_ups.length ? <div className="divide-y divide-slate-100 dark:divide-slate-800">{data.upcoming_follow_ups.map((item) => <div key={item.id} className="flex items-center justify-between gap-4 py-3 text-xs"><div><p className="font-medium">{item.customer_name ?? item.title}</p><p className="mt-1 text-slate-400">{new Date(item.scheduled_at).toLocaleString()}</p></div><Badge variant={item.priority === "high" || item.priority === "urgent" ? "warning" : "neutral"}>{titleCase(item.priority)}</Badge></div>)}</div> : <StatePanel title="No upcoming follow-ups" description="AI-recommended or manually scheduled callbacks appear here." icon={CalendarClock} className="min-h-52" />}</ChartWrapper>
    </div>
  </div>;
}
