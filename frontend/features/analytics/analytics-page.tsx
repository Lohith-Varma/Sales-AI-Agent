"use client";

import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Activity, BarChart3, BrainCircuit, Clock3, Target, Trophy } from "lucide-react";
import { ChartWrapper } from "@/components/data-display/chart-wrapper";
import { PageHeader } from "@/components/states/page-header";
import { ErrorState, StatePanel } from "@/components/states/state-panel";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { coreApi, queryKeys } from "@/lib/api/client";
import { formatDuration, titleCase } from "@/lib/utils";

const colors = ["#2563EB", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#64748B"];

function EmptyChart({ title, icon = BarChart3 }: { title: string; icon?: typeof BarChart3 }) {
  return <StatePanel title={`No ${title.toLowerCase()} data`} description="This chart will populate as calls and AI insights are persisted." icon={icon} className="min-h-56" />;
}

export function AnalyticsPage() {
  const analytics = useQuery({ queryKey: queryKeys.analytics(30), queryFn: () => coreApi.analytics(30), refetchInterval: 30_000 });
  const data = analytics.data?.data;
  if (analytics.isLoading) return <div className="space-y-5"><Skeleton className="h-24 rounded-2xl" /><div className="grid gap-4 lg:grid-cols-2">{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-80 rounded-2xl" />)}</div></div>;
  if (analytics.isError) return <ErrorState title="Analytics could not be loaded" description={analytics.error.message} retry={() => void analytics.refetch()} />;

  return <div className="space-y-7">
    <PageHeader eyebrow="Executive intelligence" title="Analytics" description="Thirty-day call, intent, sentiment, lead-funnel, duration, and agent-performance analytics computed from persisted records." actions={<Badge variant="success">Live database</Badge>} />
    <div className="grid gap-4 sm:grid-cols-3"><Card className="p-4"><p className="text-xs text-slate-500">Average duration</p><p className="mt-2 text-2xl font-semibold">{formatDuration(data?.call_duration.average_seconds ?? 0)}</p></Card><Card className="p-4"><p className="text-xs text-slate-500">Shortest call</p><p className="mt-2 text-2xl font-semibold">{formatDuration(data?.call_duration.minimum_seconds ?? 0)}</p></Card><Card className="p-4"><p className="text-xs text-slate-500">Longest call</p><p className="mt-2 text-2xl font-semibold">{formatDuration(data?.call_duration.maximum_seconds ?? 0)}</p></Card></div>
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartWrapper title="Call volume" description="Persisted inbound and outbound calls by day.">{data?.call_volume.length ? <div className="h-64"><ResponsiveContainer width="100%" height="100%"><LineChart data={data.call_volume}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="date" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fontSize: 10 }} /><Tooltip /><Line type="monotone" dataKey="inbound" stroke="#2563EB" strokeWidth={2} /><Line type="monotone" dataKey="outbound" stroke="#22C55E" strokeWidth={2} /></LineChart></ResponsiveContainer></div> : <EmptyChart title="call volume" icon={Activity} />}</ChartWrapper>
      <ChartWrapper title="Lead funnel" description="Current lead distribution by lifecycle stage.">{data?.lead_funnel.length ? <div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.lead_funnel}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="stage" tickFormatter={titleCase} tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fontSize: 10 }} /><Tooltip labelFormatter={(value) => titleCase(String(value))} /><Bar dataKey="value" fill="#2563EB" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div> : <EmptyChart title="lead funnel" icon={Target} />}</ChartWrapper>
      <ChartWrapper title="Intent distribution" description="Customer intent across persisted AI analyses.">{data?.intent_distribution.length ? <div className="grid h-64 grid-cols-[1fr_150px] items-center"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.intent_distribution} dataKey="value" nameKey="name" innerRadius={52} outerRadius={86}>{data.intent_distribution.map((item, index) => <Cell key={item.name} fill={colors[index % colors.length]} />)}</Pie><Tooltip formatter={(value, name) => [value, titleCase(String(name))]} /></PieChart></ResponsiveContainer><div className="space-y-2">{data.intent_distribution.map((item, index) => <div key={item.name} className="flex items-center justify-between gap-2 text-[11px]"><span className="flex items-center gap-2"><span className="size-2 rounded-full" style={{ backgroundColor: colors[index % colors.length] }} />{titleCase(item.name)}</span><b>{item.value}</b></div>)}</div></div> : <EmptyChart title="intent distribution" icon={BrainCircuit} />}</ChartWrapper>
      <ChartWrapper title="Emotion analysis" description="Customer sentiment across persisted AI analyses.">{data?.sentiment_distribution.length ? <div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.sentiment_distribution} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" allowDecimals={false} tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" tickFormatter={titleCase} width={90} tick={{ fontSize: 10 }} /><Tooltip labelFormatter={(value) => titleCase(String(value))} /><Bar dataKey="value" fill="#8B5CF6" radius={[0, 6, 6, 0]} /></BarChart></ResponsiveContainer></div> : <EmptyChart title="emotion analysis" />}</ChartWrapper>
      <ChartWrapper title="Agent performance" description="Call volume, conversion, and quality by assigned agent.">{data?.agent_performance.length ? <div className="divide-y divide-slate-100 dark:divide-slate-800">{data.agent_performance.map((agent) => <div key={agent.agent} className="grid grid-cols-[1fr_auto_auto] items-center gap-5 py-3 text-xs"><div><p className="font-medium">{agent.agent}</p><p className="mt-1 text-slate-400">{agent.calls} calls</p></div><span>{agent.conversion_rate.toFixed(1)}% conversion</span><Badge variant="primary">{agent.average_score == null ? "No score" : agent.average_score.toFixed(1)}</Badge></div>)}</div> : <EmptyChart title="agent performance" icon={Trophy} />}</ChartWrapper>
      <ChartWrapper title="Call duration range" description="Minimum, average, and maximum completed-call duration."><div className="grid min-h-56 grid-cols-3 place-items-center gap-3 text-center">{[["Minimum", data?.call_duration.minimum_seconds ?? 0], ["Average", data?.call_duration.average_seconds ?? 0], ["Maximum", data?.call_duration.maximum_seconds ?? 0]].map(([label, seconds]) => <div key={String(label)}><Clock3 className="mx-auto size-5 text-slate-400" /><p className="mt-3 text-xs text-slate-400">{label}</p><p className="mt-1 text-lg font-semibold">{formatDuration(Number(seconds))}</p></div>)}</div></ChartWrapper>
    </div>
  </div>;
}
