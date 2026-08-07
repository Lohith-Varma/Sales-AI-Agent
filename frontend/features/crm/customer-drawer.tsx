"use client";

import { CalendarClock, LockKeyhole, Mail, MapPin, Phone, ShieldCheck, UserRound } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import type { CoreCustomer } from "@/lib/api/contracts";
import { getInitials } from "@/lib/utils";

export function CustomerDrawer({ customer, open, onOpenChange, requestedId }: { customer: CoreCustomer | null; open: boolean; onOpenChange: (open: boolean) => void; requestedId: string }) {
  if (!customer) return null;
  const fallback = requestedId.trim() !== customer.id;
  return <Sheet open={open} onOpenChange={onOpenChange}><SheetContent className="w-[min(96vw,560px)]" title={`${customer.name} profile`}>
    <div className="pr-10"><div className="flex items-center gap-4"><div className="grid size-14 place-items-center rounded-2xl bg-blue-50 text-base font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-300">{getInitials(customer.name)}</div><div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h2 className="truncate text-xl font-semibold tracking-tight text-slate-950 dark:text-white">{customer.name}</h2><Badge variant="success"><ShieldCheck className="size-3" />KYC on file</Badge></div><p className="mt-1 break-all text-xs text-slate-400">{customer.id}</p></div></div>
      {fallback ? <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300">The backend returned customer <b>{customer.id}</b> for requested ID <b>{requestedId}</b>. This is its documented demo fallback, not an exact match.</div> : null}
      <Separator className="my-5" /><div className="grid gap-3 sm:grid-cols-2"><ProfileField icon={Phone} label="Phone" value={customer.phone} /><ProfileField icon={Mail} label="Email" value={customer.email ?? "Not provided"} /><ProfileField icon={MapPin} label="Location" value={customer.city} /><ProfileField icon={UserRound} label="Occupation" value="API not available" muted /></div>
      <section className="mt-6"><h3 className="flex items-center gap-2 text-sm font-semibold"><LockKeyhole className="size-4 text-blue-600" />KYC fields</h3><p className="mt-1 text-xs text-slate-500">Sensitive fields are displayed exactly as returned by the core API. Do not re-request verified data.</p><div className="mt-3 space-y-2">{customer.kycFields.map((field) => <Card key={field.label} className="flex items-center justify-between gap-4 rounded-xl px-4 py-3 shadow-none"><span className="text-xs font-medium text-slate-500">{field.label}</span><span className="text-xs font-semibold text-slate-800 dark:text-slate-200">{field.value}</span></Card>)}</div></section>
      <section className="mt-6"><h3 className="flex items-center gap-2 text-sm font-semibold"><CalendarClock className="size-4 text-blue-600" />Customer timeline</h3><div className="relative mt-4 space-y-4 border-l border-slate-200 pl-5 dark:border-slate-800">{customer.interactions.map((interaction, index) => <article key={`${interaction.date}-${index}`} className="relative"><span className="absolute -left-[25px] top-1 size-2 rounded-full bg-blue-600 ring-4 ring-white dark:ring-slate-950" /><div className="flex items-center justify-between gap-3"><p className="text-xs font-semibold text-slate-900 dark:text-slate-100">{interaction.outcome}</p><time className="text-[11px] text-slate-400">{interaction.date}</time></div><p className="mt-1 text-xs leading-5 text-slate-500">{interaction.note}</p></article>)}</div></section>
      <section className="mt-6 grid grid-cols-2 gap-3">{["Lead score", "Past purchases", "EMI eligibility", "Tags"].map((item) => <Card key={item} className="rounded-xl border-dashed p-3 shadow-none"><p className="text-[11px] font-medium text-slate-500">{item}</p><p className="mt-1 text-xs text-slate-400">API not available</p></Card>)}</section>
    </div>
  </SheetContent></Sheet>;
}

function ProfileField({ icon: Icon, label, value, muted = false }: { icon: typeof Phone; label: string; value: string; muted?: boolean }) { return <div className="rounded-xl bg-slate-50 p-3 dark:bg-slate-900"><p className="flex items-center gap-1.5 text-[11px] font-medium text-slate-400"><Icon className="size-3.5" />{label}</p><p className={`mt-1 truncate text-xs font-semibold ${muted ? "text-slate-400" : "text-slate-800 dark:text-slate-200"}`}>{value}</p></div>; }
