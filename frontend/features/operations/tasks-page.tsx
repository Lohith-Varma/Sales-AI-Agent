"use client";

import { CalendarDays, CircleCheck, Clock3, KanbanSquare, Plus, TimerOff } from "lucide-react";
import { PageHeader } from "@/components/states/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { StatePanel, UnavailableState } from "@/components/states/state-panel";

const columns = [["Upcoming", CalendarDays], ["Today", Clock3], ["Completed", CircleCheck], ["Overdue", TimerOff]] as const;

export function TasksPage() {
  return <div className="space-y-7"><PageHeader eyebrow="Work queue" title="Tasks" description="The task board is contract-ready, but the backend has no task routes or realtime task events." actions={<><Button variant="secondary" disabled><CalendarDays />Calendar view</Button><Button disabled><Plus />New task</Button></>} /><div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-4">{columns.map(([title, Icon]) => <Card key={title} className="min-h-[420px] p-3"><div className="flex items-center justify-between px-2 py-2"><h2 className="flex items-center gap-2 text-xs font-semibold"><Icon className="size-3.5 text-slate-400" />{title}</h2><span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-400 dark:bg-slate-800">0</span></div><StatePanel title={`No ${title.toLowerCase()} tasks`} description="No task list endpoint is available. Synthetic tasks are not shown." icon={KanbanSquare} className="mt-2 min-h-80 border-0 bg-slate-50 dark:bg-slate-950/40" /></Card>)}</div><UnavailableState capability="Task calendar" endpoint="task CRUD, due-date, status, and calendar endpoints" /></div>;
}
