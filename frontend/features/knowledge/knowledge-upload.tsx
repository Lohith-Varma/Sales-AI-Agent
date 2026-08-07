"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp, Loader2, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { aiApi, queryKeys } from "@/lib/api/client";

export function KnowledgeUpload({ compact = false }: { compact?: boolean }) {
  const queryClient = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [version, setVersion] = useState("");
  const upload = useMutation({ mutationFn: async () => { if (!file) throw new Error("Choose a document first."); const form = new FormData(); form.append("file", file); if (title.trim()) form.append("title", title.trim()); if (version.trim()) form.append("version", version.trim()); return aiApi.ingest(form); }, onSuccess: (response) => { toast.success("Knowledge indexed", { description: `${response.result.chunk_count} chunks added to ${response.result.collection_name}.` }); setFile(null); setTitle(""); setVersion(""); if (inputRef.current) inputRef.current.value = ""; void queryClient.invalidateQueries({ queryKey: queryKeys.aiReadiness }); }, onError: (error) => toast.error("Document indexing failed", { description: error.message }) });
  return <form onSubmit={(event) => { event.preventDefault(); upload.mutate(); }} className="space-y-3"><div className={`grid gap-3 ${compact ? "" : "sm:grid-cols-2"}`}><div className="space-y-1.5"><Label htmlFor={compact ? "admin-doc" : "knowledge-doc"}>Approved document</Label><Input ref={inputRef} id={compact ? "admin-doc" : "knowledge-doc"} type="file" accept=".pdf,.txt,.md,.json" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="cursor-pointer file:mr-3 file:border-0 file:bg-transparent file:text-xs file:font-medium" /></div><div className="space-y-1.5"><Label htmlFor={compact ? "admin-title" : "knowledge-title"}>Title (optional)</Label><Input id={compact ? "admin-title" : "knowledge-title"} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Policy title" /></div><div className="space-y-1.5"><Label htmlFor={compact ? "admin-version" : "knowledge-version"}>Version (optional)</Label><Input id={compact ? "admin-version" : "knowledge-version"} value={version} onChange={(event) => setVersion(event.target.value)} placeholder="e.g. 5.3" /></div>{!compact ? <div className="flex items-end"><p className="rounded-xl bg-slate-50 p-3 text-[11px] leading-4 text-slate-500 dark:bg-slate-800">PDF, TXT, Markdown, and JSON up to the backend&apos;s configured 20 MB limit.</p></div> : null}</div><Button type="submit" disabled={!file || upload.isPending} className={compact ? "w-full" : undefined}>{upload.isPending ? <Loader2 className="animate-spin" /> : file ? <FileUp /> : <UploadCloud />}Index document</Button></form>;
}
