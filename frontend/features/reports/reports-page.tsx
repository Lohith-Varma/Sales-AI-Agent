"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileBarChart, ShieldCheck, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/states/page-header";
import { ErrorState } from "@/components/states/state-panel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { coreApi, queryKeys } from "@/lib/api/client";

export function ReportsPage() {
  const analytics = useQuery({ queryKey: queryKeys.analytics(30), queryFn: () => coreApi.analytics(30) });
  const dashboard = useQuery({ queryKey: queryKeys.dashboard, queryFn: coreApi.dashboard });
  if (analytics.isLoading || dashboard.isLoading) return <div className="grid gap-4 lg:grid-cols-3">{Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-56 rounded-2xl" />)}</div>;
  if (analytics.isError || dashboard.isError || !analytics.data || !dashboard.data) return <ErrorState title="Reports could not be generated" description={(analytics.error ?? dashboard.error)?.message ?? "The reporting data is unavailable."} retry={() => { void analytics.refetch(); void dashboard.refetch(); }} />;
  const data = analytics.data.data;
  const metrics = dashboard.data.data.metrics;
  const converted = dashboard.data.data.recent_activity.filter((item) => item.outcome?.toLowerCase() === "converted").length;
  const bestAgent = [...data.agent_performance].sort((a, b) => b.conversion_rate - a.conversion_rate)[0];
  const complianceCalls = dashboard.data.data.recent_activity.length;

  const exportCsv = () => {
    const rows: Array<Array<string | number>> = [
      ["report_period_days", data.period_days],
      ["today_calls", metrics.today_calls],
      ["active_calls", metrics.active_calls],
      ["conversion_rate_percent", metrics.conversion_rate],
      ["revenue", metrics.revenue],
      ["pending_follow_ups", metrics.pending_follow_ups],
      ["ai_suggestion_usage_percent", metrics.ai_suggestion_usage_rate],
      [],
      ["date", "inbound_calls", "outbound_calls", "total_calls"],
      ...data.call_volume.map((item) => [item.date, item.inbound, item.outbound, item.total]),
    ];
    const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `sales-copilot-report-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const reports = [
    { title: "Sales performance", icon: FileBarChart, value: `${metrics.conversion_rate.toFixed(1)}% conversion`, detail: `${converted} recent conversions · ₹${metrics.revenue.toLocaleString("en-IN")} persisted revenue` },
    { title: "Agent quality", icon: UsersRound, value: bestAgent ? `${bestAgent.agent}: ${bestAgent.conversion_rate.toFixed(1)}%` : "No completed agent calls", detail: bestAgent ? `${bestAgent.calls} calls · ${bestAgent.average_score?.toFixed(1) ?? "No"} average score` : "Agent ranks appear after completed calls." },
    { title: "Compliance", icon: ShieldCheck, value: `${complianceCalls} recent calls`, detail: "Detailed compliance scores and warnings are retained per call and appear in Call History." },
  ];

  return <div className="space-y-7"><PageHeader eyebrow="Operational reporting" title="Reports" description="Thirty-day operational reports generated from persisted calls, leads, revenue, and AI usage." actions={<Button variant="secondary" onClick={exportCsv}><Download />Export CSV</Button>} /><div className="grid gap-4 lg:grid-cols-3">{reports.map(({ title, icon: Icon, value, detail }) => <Card key={title} className="p-5"><div className="grid size-10 place-items-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300"><Icon className="size-4" /></div><h2 className="mt-4 text-sm font-semibold">{title}</h2><p className="mt-4 text-xl font-semibold">{value}</p><p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p></Card>)}</div><Card className="overflow-hidden"><div className="border-b border-slate-200 px-5 py-4 dark:border-slate-800"><h2 className="text-sm font-semibold">Daily call volume</h2><p className="mt-1 text-xs text-slate-500">Persisted inbound and outbound calls for the report period.</p></div><div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="bg-slate-50 text-slate-500 dark:bg-slate-900"><tr><th className="px-5 py-3">Date</th><th className="px-5 py-3">Inbound</th><th className="px-5 py-3">Outbound</th><th className="px-5 py-3">Total</th></tr></thead><tbody>{data.call_volume.map((item) => <tr key={item.date} className="border-t border-slate-100 dark:border-slate-800"><td className="px-5 py-3 font-medium">{item.date}</td><td className="px-5 py-3">{item.inbound}</td><td className="px-5 py-3">{item.outbound}</td><td className="px-5 py-3">{item.total}</td></tr>)}</tbody></table></div></Card></div>;
}
