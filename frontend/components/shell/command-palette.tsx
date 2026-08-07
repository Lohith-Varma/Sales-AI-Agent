"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Search } from "lucide-react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { navigation } from "@/lib/constants/navigation";
import { useUIStore } from "@/lib/stores/ui-store";

export function CommandPalette() {
  const router = useRouter();
  const open = useUIStore((state) => state.commandOpen);
  const setOpen = useUIStore((state) => state.setCommandOpen);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setOpen(!open); }
      if (event.key === "/" && !(event.target instanceof HTMLInputElement) && !(event.target instanceof HTMLTextAreaElement)) { event.preventDefault(); setOpen(true); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open, setOpen]);

  const filtered = useMemo(() => navigation.filter((item) => item.label.toLowerCase().includes(query.toLowerCase())), [query]);
  const navigate = (href: string) => { router.push(href); setOpen(false); setQuery(""); };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent title="Command palette" description="Search and navigate the workspace" className="top-[12vh]">
        <div className="flex items-center gap-2 border-b border-slate-200 px-4 pr-12 dark:border-slate-800"><Search className="size-4 text-slate-400" /><Input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search pages and actions…" className="h-13 border-0 px-0 shadow-none focus:ring-0" aria-label="Search commands" /></div>
        <div className="max-h-[420px] overflow-y-auto p-2">
          <p className="px-2 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-400">Navigate</p>
          {filtered.map((item) => <button key={item.href} onClick={() => navigate(item.href)} className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:text-slate-200 dark:hover:bg-slate-800"><span>{item.label}</span><span className="flex items-center gap-3 text-xs text-slate-400"><kbd className="rounded border border-slate-200 bg-white px-1.5 py-0.5 font-sans dark:border-slate-700 dark:bg-slate-900">{item.shortcut}</kbd><ArrowRight className="size-3.5" /></span></button>)}
          {filtered.length === 0 ? <p className="px-3 py-8 text-center text-sm text-slate-500">No matching pages.</p> : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
