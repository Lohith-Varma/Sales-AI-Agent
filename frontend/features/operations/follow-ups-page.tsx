"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, CheckCircle2, Loader2, Pencil, PhoneForwarded, Plus, Save, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/states/page-header";
import { ErrorState, StatePanel } from "@/components/states/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { coreApi, queryKeys } from "@/lib/api/client";
import type { CoreFollowUp } from "@/lib/api/contracts";
import { titleCase } from "@/lib/utils";

type FollowUpForm = {
  call_id: string;
  customer_id: string;
  title: string;
  description: string;
  scheduled_at: string;
  channel: string;
  priority: string;
};

type FollowUpEdit = Pick<FollowUpForm, "title" | "description" | "scheduled_at" | "channel" | "priority"> & { id: string };

const initialForm: FollowUpForm = {
  call_id: "",
  customer_id: "",
  title: "Customer follow-up",
  description: "",
  scheduled_at: "",
  channel: "phone",
  priority: "normal",
};

export function FollowUpsPage() {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [editing, setEditing] = useState<FollowUpEdit | null>(null);
  const followUps = useQuery({ queryKey: queryKeys.followUps, queryFn: coreApi.followUps, refetchInterval: 20_000 });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.followUps });
  const create = useMutation({
    mutationFn: () => coreApi.createFollowUp({ ...form, scheduled_at: new Date(form.scheduled_at).toISOString(), description: form.description || undefined }),
    onSuccess: () => {
      toast.success("Follow-up scheduled");
      setCreating(false);
      setForm(initialForm);
      refresh();
    },
    onError: (error) => toast.error("Follow-up could not be scheduled", { description: error.message }),
  });
  const update = useMutation({
    mutationFn: () => {
      if (!editing) throw new Error("No follow-up selected");
      return coreApi.updateFollowUp(editing.id, {
        title: editing.title,
        description: editing.description,
        scheduled_at: new Date(editing.scheduled_at).toISOString(),
        channel: editing.channel,
        priority: editing.priority,
      });
    },
    onSuccess: () => {
      toast.success("Follow-up updated");
      setEditing(null);
      refresh();
    },
    onError: (error) => toast.error("Follow-up could not be updated", { description: error.message }),
  });
  const complete = useMutation({
    mutationFn: (id: string) => coreApi.updateFollowUp(id, { status: "completed" }),
    onSuccess: () => {
      toast.success("Follow-up completed");
      refresh();
    },
    onError: (error) => toast.error("Follow-up could not be updated", { description: error.message }),
  });
  const items = followUps.data?.data ?? [];
  const pending = items.filter((item) => item.status !== "completed");
  const completed = items.filter((item) => item.status === "completed");

  const beginEdit = (item: CoreFollowUp) => {
    setEditing({
      id: item.id,
      title: item.title,
      description: item.description ?? "",
      scheduled_at: toLocalDateTime(item.scheduled_at),
      channel: item.channel,
      priority: item.priority,
    });
  };

  return <div className="space-y-7">
    <PageHeader eyebrow="Customer re-engagement" title="Follow Ups" description="Create, edit, remind, and complete CRM-linked follow-ups stored in the core database." actions={<Button onClick={() => setCreating((value) => !value)}><Plus />Schedule follow-up</Button>} />
    {creating ? <Card className="p-5">
      <h2 className="text-sm font-semibold">New follow-up</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <Field label="Customer ID"><Input value={form.customer_id} onChange={(event) => setForm({ ...form, customer_id: event.target.value })} /></Field>
        <Field label="Call ID"><Input value={form.call_id} onChange={(event) => setForm({ ...form, call_id: event.target.value })} /></Field>
        <Field label="Title"><Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></Field>
        <Field label="Schedule"><Input type="datetime-local" value={form.scheduled_at} onChange={(event) => setForm({ ...form, scheduled_at: event.target.value })} /></Field>
        <Field label="Channel"><ChannelSelect value={form.channel} onChange={(value) => setForm({ ...form, channel: value })} /></Field>
        <Field label="Priority"><PrioritySelect value={form.priority} onChange={(value) => setForm({ ...form, priority: value })} /></Field>
        <div className="md:col-span-2"><Field label="Description"><Textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></Field></div>
      </div>
      <div className="mt-4 flex justify-end"><Button disabled={create.isPending || !form.call_id || !form.customer_id || !form.scheduled_at || !form.title} onClick={() => create.mutate()}>{create.isPending ? <Loader2 className="animate-spin" /> : <CalendarClock />}Save follow-up</Button></div>
    </Card> : null}
    {followUps.isLoading ? <StatePanel title="Loading follow-ups" description="Reading the CRM work queue." icon={Loader2} className="min-h-60" /> : followUps.isError ? <ErrorState title="Follow-ups could not be loaded" description={followUps.error.message} retry={() => void followUps.refetch()} /> : <div className="grid gap-4 xl:grid-cols-[1.3fr_.7fr]">
      <Card className="p-4">
        <div className="flex items-center justify-between px-1 pb-3"><h2 className="text-sm font-semibold">Upcoming and pending</h2><Badge variant="primary">{pending.length}</Badge></div>
        {pending.length ? <div className="divide-y divide-slate-100 dark:divide-slate-800">{pending.map((item) => <div key={item.id}>
          <article className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center">
            <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="text-sm font-medium">{item.title}</p><Badge variant={item.priority === "high" || item.priority === "urgent" ? "warning" : "neutral"}>{titleCase(item.priority)}</Badge><Badge>{titleCase(item.channel)}</Badge></div><p className="mt-1 text-xs text-slate-500">{item.customer_name ?? item.customer_id} · {new Date(item.scheduled_at).toLocaleString()}</p>{item.description ? <p className="mt-2 text-xs text-slate-400">{item.description}</p> : null}</div>
            <div className="flex gap-2"><Button size="sm" variant="ghost" onClick={() => beginEdit(item)} disabled={update.isPending}><Pencil />Edit</Button><Button size="sm" variant="secondary" onClick={() => complete.mutate(item.id)} disabled={complete.isPending}><CheckCircle2 />Complete</Button></div>
          </article>
          {editing?.id === item.id ? <Card className="mb-4 border-blue-200 p-4 shadow-none dark:border-blue-900">
            <div className="grid gap-3 md:grid-cols-2">
              <Field label="Title"><Input value={editing.title} onChange={(event) => setEditing({ ...editing, title: event.target.value })} /></Field>
              <Field label="Schedule"><Input type="datetime-local" value={editing.scheduled_at} onChange={(event) => setEditing({ ...editing, scheduled_at: event.target.value })} /></Field>
              <Field label="Channel"><ChannelSelect value={editing.channel} onChange={(value) => setEditing({ ...editing, channel: value })} /></Field>
              <Field label="Priority"><PrioritySelect value={editing.priority} onChange={(value) => setEditing({ ...editing, priority: value })} /></Field>
              <div className="md:col-span-2"><Field label="Description"><Textarea value={editing.description} onChange={(event) => setEditing({ ...editing, description: event.target.value })} /></Field></div>
            </div>
            <div className="mt-4 flex justify-end gap-2"><Button size="sm" variant="ghost" onClick={() => setEditing(null)}><X />Cancel</Button><Button size="sm" disabled={update.isPending || !editing.title || !editing.scheduled_at} onClick={() => update.mutate()}>{update.isPending ? <Loader2 className="animate-spin" /> : <Save />}Save changes</Button></div>
          </Card> : null}
        </div>)}</div> : <StatePanel title="No pending follow-ups" description="AI-recommended and manually scheduled callbacks appear here." icon={PhoneForwarded} className="min-h-72" />}
      </Card>
      <Card className="p-4"><div className="flex items-center justify-between px-1 pb-3"><h2 className="text-sm font-semibold">Completed</h2><Badge>{completed.length}</Badge></div>{completed.length ? <div className="space-y-2">{completed.map((item) => <div key={item.id} className="rounded-xl bg-slate-50 p-3 text-xs dark:bg-slate-800/60"><p className="font-medium">{item.title}</p><p className="mt-1 text-slate-400">{item.customer_name ?? item.customer_id}</p></div>)}</div> : <StatePanel title="No completed follow-ups" description="Completed work remains linked to its customer and call." icon={CheckCircle2} className="min-h-60" />}</Card>
    </div>}
  </div>;
}

function ChannelSelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-900" value={value} onChange={(event) => onChange(event.target.value)}>{["phone", "sms", "email", "whatsapp"].map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}</select>;
}

function PrioritySelect({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return <select className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm dark:border-slate-700 dark:bg-slate-900" value={value} onChange={(event) => onChange(event.target.value)}>{["low", "normal", "high", "urgent"].map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}</select>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}

function toLocalDateTime(value: string) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}
