"use client";

import { BellRing, CalendarClock, Mail, MessageCircle, PhoneForwarded, Plus, Smartphone } from "lucide-react";
import { PageHeader } from "@/components/states/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatePanel, UnavailableState } from "@/components/states/state-panel";

export function FollowUpsPage() {
  return <div className="space-y-7"><PageHeader eyebrow="Customer re-engagement" title="Follow Ups" description="A FollowUp database model exists, but no API route exposes its records, scheduling, status, or delivery actions." actions={<Button disabled><Plus />Schedule follow-up</Button>} /><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[[MessageCircle, "WhatsApp", "No send endpoint"], [Smartphone, "SMS", "No send endpoint"], [Mail, "Email", "No send endpoint"], [BellRing, "Reminders", "No reminder endpoint"]].map(([Icon, label, status]) => { const Component = Icon as typeof MessageCircle; return <Card key={String(label)} className="p-4"><div className="flex items-center justify-between"><div className="grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-500 dark:bg-slate-800"><Component className="size-4" /></div><Badge>{String(status)}</Badge></div><p className="mt-4 text-sm font-semibold">{String(label)}</p><p className="mt-1 text-xs text-slate-400">Not connected</p></Card>; })}</div><div className="grid gap-4 xl:grid-cols-[1.3fr_.7fr]"><Card className="p-4"><div className="flex items-center justify-between px-1 pb-3"><h2 className="text-sm font-semibold">Follow-up timeline</h2><Button variant="secondary" size="sm" disabled>Priority</Button></div><StatePanel title="Follow-up records are not queryable" description="The frontend cannot populate priority, channel, reminder, or status without a list endpoint." icon={PhoneForwarded} className="min-h-80" /></Card><Card className="p-4"><h2 className="px-1 pb-3 text-sm font-semibold">Schedule</h2><StatePanel title="No reminder schedule" description="Scheduling mutations and delivery status are unavailable." icon={CalendarClock} className="min-h-80" /></Card></div><UnavailableState capability="Realtime follow-up updates" endpoint="follow-up events or a Socket.IO namespace" /></div>;
}
