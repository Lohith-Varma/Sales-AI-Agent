import type { ReactNode } from "react";

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description: string; actions?: ReactNode }) {
  return (
    <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
      <div className="max-w-3xl">
        {eyebrow ? <p className="mb-1 text-xs font-semibold uppercase tracking-[0.14em] text-blue-600">{eyebrow}</p> : null}
        <h1 className="text-2xl font-semibold tracking-[-0.035em] text-slate-950 sm:text-[28px] dark:text-white">{title}</h1>
        <p className="mt-1.5 max-w-2xl text-sm leading-6 text-slate-500 dark:text-slate-400">{description}</p>
      </div>
      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
