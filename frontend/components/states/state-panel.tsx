import type { LucideIcon } from "lucide-react";
import { AlertCircle, Boxes, CircleSlash2, RefreshCw, WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Props = { title: string; description: string; icon?: LucideIcon; className?: string; action?: { label: string; onClick: () => void } };

export function StatePanel({ title, description, icon: Icon = Boxes, className, action }: Props) {
  return (
    <div className={cn("flex min-h-44 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 px-6 py-8 text-center dark:border-slate-800 dark:bg-slate-900/40", className)}>
      <div className="mb-3 grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"><Icon className="size-4" /></div>
      <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      <p className="mt-1 max-w-md text-xs leading-5 text-slate-500 dark:text-slate-400">{description}</p>
      {action ? <Button variant="secondary" size="sm" className="mt-4" onClick={action.onClick}><RefreshCw />{action.label}</Button> : null}
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", description, retry, className }: { title?: string; description: string; retry?: () => void; className?: string }) {
  return <StatePanel title={title} description={description} icon={AlertCircle} className={className} action={retry ? { label: "Try again", onClick: retry } : undefined} />;
}

export function OfflineState({ className }: { className?: string }) {
  return <StatePanel title="You are offline" description="Live data and actions will resume when your connection returns." icon={WifiOff} className={className} />;
}

export function UnavailableState({ capability, endpoint, className }: { capability: string; endpoint: string; className?: string }) {
  return <StatePanel title={`${capability} is not available`} description={`The current backend does not expose ${endpoint}. No synthetic data is shown.`} icon={CircleSlash2} className={className} />;
}
