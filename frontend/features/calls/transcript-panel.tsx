"use client";

import { useVirtualizer } from "@tanstack/react-virtual";
import { Bookmark, Check, Copy, Search, Sparkles, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { TranscriptItem } from "@/features/calls/types";
import { useUIStore } from "@/lib/stores/ui-store";
import { cn, formatPercent, titleCase } from "@/lib/utils";

const EMPTY_BOOKMARKS: string[] = [];

function speakerLabel(speaker: TranscriptItem["speaker"]) { return speaker === "sales_agent" ? "Agent" : speaker === "unknown" ? "Customer" : titleCase(speaker); }

export function TranscriptPanel({ callId, items, searching = false }: { callId: string; items: TranscriptItem[]; searching?: boolean }) {
  const [query, setQuery] = useState("");
  const [copied, setCopied] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  // useSyncExternalStore requires a stable snapshot while a call has no bookmarks.
  const bookmarks = useUIStore((state) => state.transcriptBookmarks[callId] ?? EMPTY_BOOKMARKS);
  const toggleBookmark = useUIStore((state) => state.toggleBookmark);
  const filtered = useMemo(() => items.filter((item) => item.text.toLowerCase().includes(query.toLowerCase())), [items, query]);
  const virtualizer = useVirtualizer({ count: filtered.length, getScrollElement: () => scrollRef.current, estimateSize: () => 104, overscan: 8 });

  useEffect(() => { if (!query && filtered.length) virtualizer.scrollToIndex(filtered.length - 1, { align: "end", behavior: "smooth" }); }, [filtered.length, query, virtualizer]);
  const copyAll = async () => { await navigator.clipboard.writeText(items.map((item) => `[${speakerLabel(item.speaker)}] ${item.text}`).join("\n\n")); setCopied(true); toast.success("Transcript copied"); setTimeout(() => setCopied(false), 1500); };

  return <section className="flex min-h-[560px] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,.04)] dark:border-slate-800 dark:bg-slate-900" aria-label="Live transcript">
    <div className="border-b border-slate-200 p-4 dark:border-slate-800"><div className="flex items-center justify-between gap-3"><div><p className="text-sm font-semibold">Live transcript</p><p className="mt-0.5 text-[11px] text-slate-400">Streaming from the structured copilot service</p></div><div className="flex items-center gap-1"><Badge variant="success"><span className="size-1.5 animate-pulse rounded-full bg-emerald-500" />Live</Badge><Button variant="ghost" size="icon-sm" onClick={copyAll} disabled={!items.length} aria-label="Copy full transcript">{copied ? <Check /> : <Copy />}</Button></div></div><div className="relative mt-3"><Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-400" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search transcript" className="h-9 pl-8 pr-8 text-xs" aria-label="Search transcript" />{query ? <button onClick={() => setQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:text-slate-700" aria-label="Clear transcript search"><X className="size-3.5" /></button> : null}</div></div>
    <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto bg-slate-50/60 dark:bg-slate-950/40" role="log" aria-live="polite" aria-relevant="additions text">
      {searching && items.length === 0 ? <div className="space-y-3 p-4">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className={cn("h-20 w-[78%] rounded-2xl", index % 2 && "ml-auto")} />)}</div> : filtered.length === 0 ? <div className="grid h-full min-h-96 place-items-center p-8 text-center"><div><div className="mx-auto grid size-11 place-items-center rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300"><Sparkles className="size-4" /></div><p className="mt-3 text-sm font-semibold">{query ? "No matching transcript" : "Waiting for the conversation"}</p><p className="mt-1 max-w-xs text-xs leading-5 text-slate-500">{query ? "Try a different word or clear the search." : "Start microphone streaming or use text mode to send a customer utterance."}</p></div></div> : <div className="relative w-full p-4" style={{ height: virtualizer.getTotalSize() }}>{virtualizer.getVirtualItems().map((row) => { const item = filtered[row.index]; if (!item) return null; const agent = item.speaker === "sales_agent"; const bookmarked = bookmarks.includes(item.segment_id); return <article key={item.segment_id} ref={virtualizer.measureElement} data-index={row.index} className={cn("absolute left-0 top-0 flex w-full px-4 pb-3", agent ? "justify-end" : "justify-start")} style={{ transform: `translateY(${row.start}px)` }}><div className={cn("group max-w-[86%] rounded-2xl border px-3.5 py-3 shadow-[0_1px_2px_rgba(15,23,42,.025)]", agent ? "border-blue-600 bg-blue-600 text-white" : "border-slate-200 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100")}><div className="mb-1.5 flex items-center justify-between gap-4"><span className={cn("text-[10px] font-semibold uppercase tracking-[0.1em]", agent ? "text-blue-100" : "text-slate-400")}>{speakerLabel(item.speaker)}</span><div className="flex items-center gap-1"><time className={cn("text-[10px]", agent ? "text-blue-100" : "text-slate-400")}>{new Date(item.receivedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time><button onClick={() => toggleBookmark(callId, item.segment_id)} className={cn("rounded p-1 opacity-0 transition group-hover:opacity-100 focus:opacity-100", bookmarked && "opacity-100")} aria-label={bookmarked ? "Remove bookmark" : "Bookmark transcript section"}><Bookmark className={cn("size-3", bookmarked && "fill-current text-amber-500")} /></button></div></div><p className="text-sm leading-6">{item.text}</p>{item.confidence != null ? <p className={cn("mt-2 text-[10px]", agent ? "text-blue-100" : "text-slate-400")}>{formatPercent(item.confidence)} speech confidence</p> : null}</div></article>; })}</div>}
    </div>
  </section>;
}
