"use client";

import {
  BadgeIndianRupee,
  CalendarPlus,
  FileCheck2,
  MessageCircle,
  NotebookPen,
  ShieldAlert,
  UserRoundCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function DisabledAction({
  label,
  reason,
  icon: Icon,
}: {
  label: string;
  reason: string;
  icon: typeof MessageCircle;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex">
          <Button variant="ghost" size="sm" disabled>
            <Icon />
            {label}
          </Button>
        </span>
      </TooltipTrigger>
      <TooltipContent>{reason}</TooltipContent>
    </Tooltip>
  );
}

export function CallActionBar({
  onInitiateKyc,
  onScheduleFollowUp,
  onCreateNote,
  onCloseDeal,
  busy = false,
}: {
  onInitiateKyc: () => void;
  onScheduleFollowUp: () => void;
  onCreateNote: () => void;
  onCloseDeal: () => void;
  busy?: boolean;
}) {
  return (
    <div
      className="sticky bottom-3 z-30 mx-auto mt-4 flex w-fit max-w-full items-center gap-1 overflow-x-auto rounded-2xl border border-slate-200 bg-white/95 p-2 shadow-[0_14px_42px_rgba(15,23,42,.12)] backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/95"
      aria-label="Call actions"
    >
      <DisabledAction
        label="WhatsApp"
        icon={MessageCircle}
        reason="External messaging credentials are not configured"
      />
      <Button
        variant="ghost"
        size="sm"
        onClick={onScheduleFollowUp}
        disabled={busy}
      >
        <CalendarPlus />
        Follow-up
      </Button>
      <Button variant="ghost" size="sm" onClick={onInitiateKyc} disabled={busy}>
        <FileCheck2 />
        Initiate KYC
      </Button>
      <Button variant="ghost" size="sm" onClick={onCreateNote}>
        <NotebookPen />
        Create note
      </Button>
      <Button size="sm" onClick={onCloseDeal}>
        <BadgeIndianRupee />
        Close deal
      </Button>
      <DisabledAction
        label="Transfer"
        icon={UserRoundCheck}
        reason="A telephony provider is not configured for call transfer"
      />
      <DisabledAction
        label="Escalate"
        icon={ShieldAlert}
        reason="Use the AI human-transfer recommendation and create an agent task"
      />
    </div>
  );
}
