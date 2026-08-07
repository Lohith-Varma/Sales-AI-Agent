import { cn } from "@/lib/utils";

export function Progress({ value, className, indicatorClassName }: { value: number; className?: string; indicatorClassName?: string }) {
  const normalized = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800", className)} role="progressbar" aria-valuenow={normalized} aria-valuemin={0} aria-valuemax={100}>
      <div className={cn("h-full rounded-full bg-blue-600 transition-[width] duration-200", indicatorClassName)} style={{ width: `${normalized}%` }} />
    </div>
  );
}
