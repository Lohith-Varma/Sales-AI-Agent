"use client";

import { useQuery } from "@tanstack/react-query";
import { BarChart3, Download, FileSpreadsheet, FileText, LineChart, PieChart, Trophy, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/states/page-header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { ChartWrapper } from "@/components/data-display/chart-wrapper";
import { UnavailableState } from "@/components/states/state-panel";
import { aiApi, coreApi, queryKeys } from "@/lib/api/client";

const charts = [
  ["Conversion", "Conversion by day, product, and channel", BarChart3, "a conversion analytics endpoint"],
  ["Agent ranking", "Ranked sales and quality performance", Trophy, "an agent ranking endpoint"],
  ["Lead funnel", "Lead movement through lifecycle stages", UsersRound, "a lead funnel endpoint"],
  ["Call volume", "Inbound and outbound time series", LineChart, "a call volume endpoint"],
  ["Emotion analysis", "Customer sentiment distribution over time", PieChart, "a sentiment aggregate endpoint"],
  ["Talking ratio", "Agent-to-customer speaking balance", BarChart3, "dual-channel speaker analytics"],
  ["Intent distribution", "Customer intent across conversations", PieChart, "an intent aggregate endpoint"],
  ["Sales forecast", "Forecast from qualified pipeline", LineChart, "a forecasting endpoint"],
] as const;

export function AnalyticsPage() {
  const core = useQuery({ queryKey: queryKeys.coreHealth, queryFn: coreApi.health });
  const ai = useQuery({ queryKey: queryKeys.aiHealth, queryFn: aiApi.health });
  return <div className="space-y-7"><PageHeader eyebrow="Executive intelligence" title="Analytics" description="The application is ready to render business analytics, but the backend currently exposes no aggregate or time-series contracts." actions={<><Button variant="secondary" disabled><Download />CSV</Button><Button variant="secondary" disabled><FileSpreadsheet />Excel</Button><Button variant="secondary" disabled><FileText />PDF</Button></>} />
    <div className="grid gap-4 sm:grid-cols-2"><Card className="flex items-center justify-between p-4"><div><p className="text-xs text-slate-500">Core data service</p><p className="mt-1 text-sm font-semibold">{core.data?.data.status ?? (core.isLoading ? "Checking…" : "Unavailable")}</p></div><Badge variant={core.data?.data.status === "healthy" ? "success" : "warning"}>Live check</Badge></Card><Card className="flex items-center justify-between p-4"><div><p className="text-xs text-slate-500">AI analysis service</p><p className="mt-1 text-sm font-semibold">{ai.data?.status ?? (ai.isLoading ? "Checking…" : "Unavailable")}</p></div><Badge variant={ai.data?.status === "healthy" ? "success" : "warning"}>Live check</Badge></Card></div>
    <div className="grid gap-4 lg:grid-cols-2">{charts.map(([title, description, , endpoint]) => <ChartWrapper key={title} title={title} description={description}><UnavailableState capability={title} endpoint={endpoint} className="min-h-56" /></ChartWrapper>)}</div>
    <p className="text-center text-xs text-slate-400">Export actions are disabled because exporting blank or synthetic financial analytics would be misleading.</p>
  </div>;
}
