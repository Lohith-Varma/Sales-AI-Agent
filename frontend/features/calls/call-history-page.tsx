"use client";

import { useQuery } from "@tanstack/react-query";
import { AudioLines, BrainCircuit, FileText, Gauge, History, Search, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/states/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState, StatePanel, UnavailableState } from "@/components/states/state-panel";
import { coreApi, queryKeys } from "@/lib/api/client";
import { formatPercent, titleCase } from "@/lib/utils";

export function CallHistoryPage() {
  const [input, setInput] = useState("");
  const [callId, setCallId] = useState("");
  const transcripts = useQuery({ queryKey: queryKeys.transcripts(callId), queryFn: () => coreApi.transcripts(callId), enabled: Boolean(callId), retry: false });
  return <div className="space-y-7"><PageHeader eyebrow="Conversation records" title="Call History" description="Retrieve the encrypted-at-rest transcript for a known call ID. The backend does not expose a paginated call list or recording metadata." />
    <Card className="p-4"><form onSubmit={(event) => { event.preventDefault(); if (input.trim()) setCallId(input.trim()); }} className="flex flex-col gap-2 sm:flex-row"><div className="relative flex-1"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input value={input} onChange={(event) => setInput(event.target.value)} className="pl-9" placeholder="Enter a call UUID" aria-label="Call ID" /></div><Button type="submit"><Search />Load transcript</Button></form></Card>
    {!callId ? <StatePanel title="No call selected" description="Enter a known call UUID. The backend has no endpoint to browse all calls." icon={History} className="min-h-72" /> : transcripts.isLoading ? <div className="space-y-3"><Skeleton className="h-20 rounded-2xl" /><Skeleton className="h-20 w-4/5 rounded-2xl" /><Skeleton className="h-20 rounded-2xl" /></div> : transcripts.isError ? <ErrorState title="Call transcript could not be loaded" description={transcripts.error.message} retry={() => void transcripts.refetch()} /> : <div className="grid items-start gap-4 xl:grid-cols-[1fr_340px]"><Card className="overflow-hidden"><div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800"><div><h2 className="text-sm font-semibold">Transcript</h2><p className="mt-1 text-[11px] text-slate-400">Call {callId}</p></div><Badge>{transcripts.data?.data.transcripts.length ?? 0} segments</Badge></div><div className="max-h-[660px] space-y-3 overflow-y-auto bg-slate-50/60 p-4 dark:bg-slate-950/30">{transcripts.data?.data.transcripts.length ? transcripts.data.data.transcripts.map((line, index) => <article key={`${line.timestamp}-${index}`} className={`flex ${line.speaker === "agent" ? "justify-end" : "justify-start"}`}><div className={`max-w-[84%] rounded-2xl border px-3.5 py-3 ${line.speaker === "agent" ? "border-blue-600 bg-blue-600 text-white" : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900"}`}><div className="mb-1.5 flex items-center justify-between gap-4"><span className="text-[10px] font-semibold uppercase tracking-wider opacity-70">{titleCase(line.speaker)}</span><time className="text-[10px] opacity-60">{new Date(line.timestamp).toLocaleString()}</time></div><p className="text-sm leading-6">{line.text}</p>{line.confidence != null ? <p className="mt-2 text-[10px] opacity-60">{formatPercent(line.confidence)} confidence</p> : null}</div></article>) : <StatePanel title="Transcript is empty" description="The call exists, but no transcript segments were persisted." icon={FileText} className="min-h-60" />}</div></Card><div className="space-y-4"><UnavailableState capability="Call recording" endpoint="a recording URL or audio stream endpoint" /><UnavailableState capability="AI call summary" endpoint="a persisted post-call summary endpoint" /><Card className="p-4"><p className="text-xs font-semibold">Unavailable call intelligence</p><div className="mt-3 grid grid-cols-2 gap-2">{[[BrainCircuit, "Intent timeline"], [ShieldCheck, "Compliance score"], [Gauge, "Agent score"], [AudioLines, "Replay markers"]].map(([Icon, label]) => { const Component = Icon as typeof BrainCircuit; return <div key={String(label)} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800/60"><Component className="size-3.5 text-slate-400" /><p className="mt-2 text-[10px] text-slate-400">{String(label)}</p><p className="mt-1 text-xs font-semibold text-slate-300 dark:text-slate-700">—</p></div>; })}</div></Card></div></div>}
  </div>;
}
