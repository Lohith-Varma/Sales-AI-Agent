"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const Sheet = Dialog.Root;
export const SheetTrigger = Dialog.Trigger;
export const SheetClose = Dialog.Close;

export function SheetContent({ children, className, side = "right", title = "Panel", description }: { children: React.ReactNode; className?: string; side?: "left" | "right"; title?: string; description?: string }) {
  return (
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/25 backdrop-blur-[2px] data-[state=open]:animate-in data-[state=closed]:animate-out" />
      <Dialog.Content className={cn("fixed inset-y-0 z-50 w-[min(92vw,460px)] overflow-y-auto border-slate-200 bg-white p-5 shadow-2xl outline-none dark:border-slate-800 dark:bg-slate-950", side === "right" ? "right-0 border-l" : "left-0 border-r", className)}>
        <Dialog.Title className="sr-only">{title}</Dialog.Title>
        <Dialog.Description className="sr-only">{description ?? `${title} panel`}</Dialog.Description>
        {children}
        <Dialog.Close className="absolute right-4 top-4 grid size-8 place-items-center rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 dark:hover:bg-slate-800 dark:hover:text-white" aria-label="Close panel"><X className="size-4" /></Dialog.Close>
      </Dialog.Content>
    </Dialog.Portal>
  );
}
