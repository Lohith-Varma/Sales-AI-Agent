"use client";

import { Download, FileBarChart, FileSpreadsheet, FileText, ShieldCheck, UsersRound } from "lucide-react";
import { PageHeader } from "@/components/states/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatePanel } from "@/components/states/state-panel";

export function ReportsPage() {
  const reports = [["Sales performance", "Conversion, pipeline, and revenue attribution", FileBarChart], ["Agent quality", "Agent ranking, talking ratio, and outcome quality", UsersRound], ["Compliance", "Guardrail decisions and disclosure adherence", ShieldCheck]] as const;
  return <div className="space-y-7"><PageHeader eyebrow="Operational reporting" title="Reports" description="Report generation and exports require persisted aggregate data and export endpoints that are not present." actions={<Button variant="secondary" disabled><Download />Export center</Button>} /><div className="grid gap-4 lg:grid-cols-3">{reports.map(([title, description, Icon]) => <Card key={title} className="p-5"><div className="grid size-10 place-items-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300"><Icon className="size-4" /></div><h2 className="mt-4 text-sm font-semibold">{title}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{description}</p><div className="mt-5 flex gap-2"><Button variant="secondary" size="sm" disabled><FileText />PDF</Button><Button variant="secondary" size="sm" disabled><FileSpreadsheet />Excel</Button></div></Card>)}</div><StatePanel title="No report runs are available" description="The backend exposes neither report definitions nor export jobs. Generating client-side reports from synthetic data is intentionally disabled." icon={FileBarChart} className="min-h-80" /></div>;
}
