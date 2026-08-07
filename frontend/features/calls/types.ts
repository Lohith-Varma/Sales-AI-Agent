import type { CopilotResult, CRMSummary, TranscriptSegment, WorkflowStage } from "@/lib/api/contracts";

export interface TranscriptItem extends TranscriptSegment {
  receivedAt: string;
  source: "websocket" | "text_fallback";
}

export interface CallWorkspaceState {
  callId: string;
  startedAt: number;
  transcript: TranscriptItem[];
  latestResult: CopilotResult | null;
  crmSummary: CRMSummary | null;
  workflowStage: WorkflowStage | null;
}
