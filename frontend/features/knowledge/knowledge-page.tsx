"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, BookMarked, BookOpenText, Search, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { PageHeader } from "@/components/states/page-header";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState, StatePanel, UnavailableState } from "@/components/states/state-panel";
import { KnowledgeUpload } from "@/features/knowledge/knowledge-upload";
import { coreApi, queryKeys } from "@/lib/api/client";
import { titleCase } from "@/lib/utils";

export function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const clauses = useQuery({ queryKey: queryKeys.clauses, queryFn: coreApi.clauses });
  const categories = useMemo(() => ["all", ...new Set((clauses.data?.data ?? []).map((item) => item.topic))], [clauses.data]);
  const filtered = useMemo(() => (clauses.data?.data ?? []).filter((item) => (category === "all" || item.topic === category) && `${item.title} ${item.body} ${item.source}`.toLowerCase().includes(query.toLowerCase())), [clauses.data, category, query]);
  return <div className="space-y-7"><PageHeader eyebrow="Approved knowledge" title="Knowledge Base" description="Search core product clauses and index approved documents into the AI retrieval collection." />
    <Card className="p-5"><div className="grid gap-3 sm:grid-cols-[1fr_auto]"><div className="relative"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" /><Input value={query} onChange={(event) => setQuery(event.target.value)} className="pl-9" placeholder="Search FAQ, policies, EMI, KYC, and offers" aria-label="Search knowledge" /></div><select value={category} onChange={(event) => setCategory(event.target.value)} className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-900" aria-label="Knowledge category">{categories.map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}</select></div></Card>
    <section><div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-semibold">Product clauses</h2>{clauses.data ? <Badge>{filtered.length} results</Badge> : null}</div>{clauses.isLoading ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-48 rounded-2xl" />)}</div> : clauses.isError ? <ErrorState title="Knowledge could not be loaded" description={clauses.error.message} retry={() => void clauses.refetch()} /> : filtered.length ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{filtered.map((clause) => <Card key={clause.id} className={`p-5 ${clause.stale ? "border-amber-300 dark:border-amber-800" : ""}`}><div className="flex items-start justify-between gap-3"><div className="grid size-9 place-items-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950 dark:text-blue-300"><BookOpenText className="size-4" /></div><Badge variant={clause.stale ? "warning" : "neutral"}>{clause.stale ? <AlertTriangle className="size-3" /> : null}{titleCase(clause.topic)}</Badge></div><h3 className="mt-4 text-sm font-semibold">{clause.title}</h3>{clause.stale ? <p className="mt-2 text-[11px] font-medium text-amber-700 dark:text-amber-300">May be outdated. Verify before quoting.</p> : null}<p className="mt-2 text-xs leading-5 text-slate-500">{clause.body}</p><div className="mt-4 border-t border-slate-100 pt-3 text-[10px] leading-4 text-slate-400 dark:border-slate-800"><p>{clause.source}</p><p>Synced {clause.lastSynced}</p></div></Card>)}</div> : <StatePanel title="No clauses match" description="Change the search or category filter." icon={BookOpenText} />}</section>
    <Card className="p-5"><div className="mb-5"><h2 className="text-sm font-semibold">Index approved knowledge</h2><p className="mt-1 text-xs leading-5 text-slate-500">Uploads are validated and indexed by the AI service. The current API does not return a persistent document catalog.</p></div><KnowledgeUpload /></Card>
    <div className="grid gap-4 lg:grid-cols-3"><UnavailableState capability="AI knowledge search" endpoint="a semantic search HTTP endpoint" /><StatePanel title="Pinned articles are not persisted" description="No pin or document catalog endpoint is available." icon={BookMarked} /><StatePanel title="Recent documents are not queryable" description="Ingestion returns counts but the backend has no list route." icon={Sparkles} /></div>
  </div>;
}
