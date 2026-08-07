import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function MetricCard({ label, value, description, icon: Icon, trend, unavailable = false }: { label: string; value: string; description: string; icon: LucideIcon; trend?: { value: string; direction: "up" | "down" | "flat" }; unavailable?: boolean }) {
  const TrendIcon = trend?.direction === "up" ? ArrowUpRight : trend?.direction === "down" ? ArrowDownRight : Minus;
  return (
    <Card className={cn("p-5", unavailable && "border-dashed bg-white/70 dark:bg-slate-900/70")}>
      <div className="flex items-start justify-between gap-4"><div className="grid size-9 place-items-center rounded-xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"><Icon className="size-4" /></div>{unavailable ? <Badge>API required</Badge> : trend ? <span className={cn("inline-flex items-center gap-1 text-xs font-semibold", trend.direction === "up" ? "text-emerald-600" : trend.direction === "down" ? "text-red-600" : "text-slate-500")}><TrendIcon className="size-3.5" />{trend.value}</span> : null}</div>
      <p className="mt-5 text-xs font-medium text-slate-500 dark:text-slate-400">{label}</p>
      <p className={cn("mt-1 text-2xl font-semibold tracking-[-0.035em] text-slate-950 dark:text-white", unavailable && "text-slate-300 dark:text-slate-700")}>{value}</p>
      <p className="mt-1.5 text-[11px] leading-4 text-slate-400">{description}</p>
    </Card>
  );
}
