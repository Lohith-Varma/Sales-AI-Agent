import type {
  CopilotResult,
  CoreCallCreated,
  CoreClause,
  CoreConsent,
  CoreCustomer,
  CoreHealth,
  CoreTranscript,
  CoreWrapUp,
  IngestionResult,
  ServiceHealth,
  SessionCreated,
  StandardResponse,
} from "@/lib/api/contracts";

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly code?: string, public readonly retryable = false) {
    super(message);
    this.name = "ApiError";
  }
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { ...init, headers: { Accept: "application/json", ...init?.headers } });
  } catch {
    throw new ApiError("The service could not be reached. Check your connection and try again.", 0, "network_error", true);
  }

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const body = payload as { message?: string; detail?: string | Array<{ msg?: string }>; code?: string; retryable?: boolean } | null;
    const detail = Array.isArray(body?.detail) ? body.detail.map((item) => item.msg).filter(Boolean).join(", ") : body?.detail;
    throw new ApiError(body?.message ?? detail ?? `Request failed with status ${response.status}.`, response.status, body?.code, body?.retryable);
  }
  return payload as T;
}

function queryString(values: Record<string, string | number | boolean | null | undefined>) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) if (value != null && value !== "") query.set(key, String(value));
  return query.toString();
}

export const coreApi = {
  health: () => requestJson<StandardResponse<CoreHealth>>("/api/core/api/health"),
  customer: (customerId: string) => requestJson<StandardResponse<CoreCustomer>>(`/api/core/api/customers/${encodeURIComponent(customerId)}`),
  clauses: () => requestJson<StandardResponse<CoreClause[]>>("/api/core/api/clauses"),
  createCustomer: (input: { name: string; phone_number: string; email?: string; salary?: number }) =>
    requestJson<StandardResponse<{ customer_id: string; name: string; phone_number: string }>>(`/api/core/api/customers?${queryString(input)}`, { method: "POST" }),
  createCall: (customerId: string, direction: "inbound" | "outbound") =>
    requestJson<StandardResponse<CoreCallCreated>>(`/api/core/api/calls?${queryString({ customer_id: customerId, direction })}`, { method: "POST" }),
  logConsent: (callId: string, consentGiven: boolean) =>
    requestJson<StandardResponse<CoreConsent>>(`/api/core/api/consent?${queryString({ call_id: callId, consent_given: consentGiven })}`, { method: "POST" }),
  transcripts: (callId: string) =>
    requestJson<StandardResponse<{ call_id: string; transcripts: CoreTranscript[] }>>(`/api/core/api/calls/${encodeURIComponent(callId)}/transcripts`),
  wrapUp: (callId: string, summary: string, outcome: string) =>
    requestJson<StandardResponse<CoreWrapUp>>(`/api/core/api/calls/${encodeURIComponent(callId)}/wrap-up`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary, outcome }),
    }),
};

export const aiApi = {
  health: () => requestJson<ServiceHealth>("/api/ai/health"),
  readiness: () => requestJson<ServiceHealth>("/api/ai/ready"),
  createSession: (input: { sales_agent_id: string; external_lead_id?: string; language?: string }) =>
    requestJson<SessionCreated>("/api/ai/api/v1/copilot/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  analyzeText: (input: { session_id: string; sequence_number: number; customer_utterance: string }) =>
    requestJson<CopilotResult>("/api/ai/api/v1/copilot/analyze-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  ingest: async (form: FormData) => {
    const response = await fetch("/api/ai/api/v1/knowledge/ingest", { method: "POST", body: form });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const body = payload as { message?: string; detail?: string; code?: string; retryable?: boolean } | null;
      throw new ApiError(body?.message ?? body?.detail ?? "The document could not be indexed.", response.status, body?.code, body?.retryable);
    }
    return payload as { result: IngestionResult };
  },
};

export const queryKeys = {
  coreHealth: ["health", "core"] as const,
  aiHealth: ["health", "ai"] as const,
  aiReadiness: ["health", "ai", "ready"] as const,
  customer: (id: string) => ["customer", id] as const,
  clauses: ["clauses"] as const,
  transcripts: (id: string) => ["transcripts", id] as const,
};
