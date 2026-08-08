"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, CheckCircle2, CircleCheck, Clock3, Loader2, Plus, TimerOff } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { PageHeader } from "@/components/states/page-header";
import { ErrorState, StatePanel } from "@/components/states/state-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { coreApi, queryKeys } from "@/lib/api/client";
import type { CoreTask } from "@/lib/api/contracts";
import { titleCase } from "@/lib/utils";

const columns = [["upcoming", CalendarDays], ["today", Clock3], ["completed", CircleCheck], ["overdue", TimerOff]] as const;

export function TasksPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const tasks = useQuery({ queryKey: queryKeys.tasks, queryFn: coreApi.tasks, refetchInterval: 20_000 });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: queryKeys.tasks });
  const create = useMutation({ mutationFn: () => coreApi.createTask({ title, due_at: dueAt ? new Date(dueAt).toISOString() : undefined }), onSuccess: () => { setTitle(""); setDueAt(""); toast.success("Task created"); refresh(); }, onError: (error) => toast.error("Task could not be created", { description: error.message }) });
  const complete = useMutation({ mutationFn: (id: string) => coreApi.updateTask(id, { status: "completed" }), onSuccess: () => { toast.success("Task completed"); refresh(); }, onError: (error) => toast.error("Task could not be updated", { description: error.message }) });
  if (tasks.isError) return <ErrorState title="Tasks could not be loaded" description={tasks.error.message} retry={() => void tasks.refetch()} />;
  const items = tasks.data?.data ?? [];

  return <div className="space-y-7"><PageHeader eyebrow="Work queue" title="Tasks" description="CRM-linked and general work items persisted in the core database." />
    <Card className="p-4"><div className="grid gap-3 sm:grid-cols-[1fr_220px_auto]"><Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="New task title" aria-label="New task title" /><Input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} aria-label="Task due date" /><Button onClick={() => create.mutate()} disabled={!title.trim() || create.isPending}>{create.isPending ? <Loader2 className="animate-spin" /> : <Plus />}New task</Button></div></Card>
    {tasks.isLoading ? <StatePanel title="Loading tasks" description="Reading the work queue." icon={Loader2} className="min-h-72" /> : <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">{columns.map(([status, Icon]) => { const matching = items.filter((item) => item.status === status); return <Card key={status} className="min-h-[420px] p-3"><div className="flex items-center justify-between px-2 py-2"><h2 className="flex items-center gap-2 text-xs font-semibold"><Icon className="size-3.5 text-slate-400" />{titleCase(status)}</h2><Badge>{matching.length}</Badge></div>{matching.length ? <div className="mt-2 space-y-2">{matching.map((item) => <TaskCard key={item.id} item={item} onComplete={() => complete.mutate(item.id)} completing={complete.isPending} />)}</div> : <StatePanel title={`No ${status} tasks`} description="This column is synchronized with the task API." icon={Icon} className="mt-2 min-h-72 border-0 bg-slate-50 dark:bg-slate-950/40" />}</Card>; })}</div>}
  </div>;
}

function TaskCard({ item, onComplete, completing }: { item: CoreTask; onComplete: () => void; completing: boolean }) { return <article className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900"><div className="flex items-start justify-between gap-2"><p className="text-xs font-semibold leading-5">{item.title}</p><Badge variant={item.priority === "high" || item.priority === "urgent" ? "warning" : "neutral"}>{titleCase(item.priority)}</Badge></div>{item.customer_name ? <p className="mt-2 text-[11px] text-slate-500">{item.customer_name}</p> : null}{item.due_at ? <p className="mt-1 text-[10px] text-slate-400">Due {new Date(item.due_at).toLocaleString()}</p> : null}{item.status !== "completed" ? <Button className="mt-3 w-full" variant="secondary" size="sm" onClick={onComplete} disabled={completing}><CheckCircle2 />Complete</Button> : null}</article>; }
