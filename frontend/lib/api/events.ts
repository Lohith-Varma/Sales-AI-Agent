import type { AIServerEvent } from "@/lib/api/contracts";

const eventTypes = new Set(["session_ready", "transcript", "copilot_result", "crm_summary", "status", "error", "pong"]);

export function parseAIServerEvent(raw: string): AIServerEvent {
  const parsed: unknown = JSON.parse(raw);
  if (!parsed || typeof parsed !== "object" || !("type" in parsed) || typeof parsed.type !== "string" || !eventTypes.has(parsed.type)) {
    throw new Error("Received an unsupported realtime event.");
  }
  return parsed as AIServerEvent;
}
