import type {
  AuthenticatedUser,
  CopilotResult,
  CRMSummary,
  CoreCallCreated,
  CoreClause,
  CoreConsent,
  CoreCustomer,
  CoreHealth,
  CoreFollowUp,
  CoreNotification,
  CoreTask,
  CoreCallSummary,
  DashboardData,
  AnalyticsData,
  PaginatedCustomers,
  ProductRecord,
  CoreTranscript,
  CoreWrapUp,
  IngestionResult,
  KnowledgeDocumentRecord,
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

const tokenKey = "sales-ai.access-token";
export const getAccessToken = () => typeof window === "undefined" ? null : window.sessionStorage.getItem(tokenKey);
export const setAccessToken = (token: string) => { if (typeof window !== "undefined") window.sessionStorage.setItem(tokenKey, token); };
export const clearAccessToken = () => { if (typeof window !== "undefined") window.sessionStorage.removeItem(tokenKey); };

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const token = getAccessToken();
    response = await fetch(url, { ...init, headers: { Accept: "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...init?.headers } });
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
  customers: (search = "") => requestJson<StandardResponse<PaginatedCustomers>>(`/api/core/api/customers?${queryString({ search })}`),
  dashboard: () => requestJson<StandardResponse<DashboardData>>("/api/core/api/dashboard"),
  analytics: (days = 30) => requestJson<StandardResponse<AnalyticsData>>(`/api/core/api/analytics?${queryString({ days })}`),
  calls: () => requestJson<StandardResponse<CoreCallSummary[]>>("/api/core/api/calls"),
  followUps: () => requestJson<StandardResponse<CoreFollowUp[]>>("/api/core/api/follow-ups"),
  createFollowUp: (input: { call_id: string; customer_id: string; scheduled_at: string; title: string; description?: string; channel?: string; priority?: string; reminder_at?: string }) =>
    requestJson<StandardResponse<CoreFollowUp>>("/api/core/api/follow-ups", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) }),
  updateFollowUp: (id: string, input: Partial<Pick<CoreFollowUp, "status" | "scheduled_at" | "title" | "description" | "channel" | "priority" | "reminder_at">>) =>
    requestJson<StandardResponse<CoreFollowUp>>(`/api/core/api/follow-ups/${encodeURIComponent(id)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) }),
  tasks: () => requestJson<StandardResponse<CoreTask[]>>("/api/core/api/tasks"),
  notifications: () => requestJson<StandardResponse<CoreNotification[]>>("/api/core/api/notifications"),
  markNotificationRead: (id: string) => requestJson<StandardResponse<{ id: string; read_at: string }>>(`/api/core/api/notifications/${encodeURIComponent(id)}/read`, { method: "PATCH" }),
  createTask: (input: { title: string; description?: string; customer_id?: string; call_id?: string; priority?: string; due_at?: string }) =>
    requestJson<StandardResponse<CoreTask>>("/api/core/api/tasks", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) }),
  updateTask: (id: string, input: Partial<Pick<CoreTask, "status" | "title" | "description" | "priority" | "due_at">>) =>
    requestJson<StandardResponse<CoreTask>>(`/api/core/api/tasks/${encodeURIComponent(id)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) }),
  saveCallNote: (callId: string, body: string) => requestJson<StandardResponse<{ id: string; updated_at: string }>>(`/api/core/api/calls/${encodeURIComponent(callId)}/note`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ body }) }),
  clauses: () => requestJson<StandardResponse<CoreClause[]>>("/api/core/api/clauses"),
  knowledgeDocuments: () => requestJson<StandardResponse<KnowledgeDocumentRecord[]>>("/api/core/api/knowledge-documents"),
  products: () => requestJson<StandardResponse<ProductRecord[]>>("/api/core/api/products"),
  createKyc: (customerId: string, input: { doc_type: string; status?: "pending" | "verified" | "rejected"; value?: string }) => requestJson<StandardResponse<{ id: string; status: string }>>(`/api/core/api/customers/${encodeURIComponent(customerId)}/kyc`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) }),
  completeSale: (callId: string, input: { product_name: string; amount: number; currency?: string; offer_name?: string; summary?: string }) => requestJson<StandardResponse<{ purchase_id: string; call_id: string; revenue: number }>>(`/api/core/api/calls/${encodeURIComponent(callId)}/complete-sale`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(input) }),
  createCustomer: (input: { name: string; phone_number: string; email?: string; salary?: number }) =>
    requestJson<StandardResponse<{ customer_id: string; name: string; phone_number: string }>>(`/api/core/api/customers?${queryString(input)}`, { method: "POST" }),
  createCall: (customerId: string, direction: "inbound" | "outbound") =>
    requestJson<StandardResponse<CoreCallCreated>>(`/api/core/api/calls?${queryString({ customer_id: customerId, direction })}`, { method: "POST" }),
  logConsent: (callId: string, consentGiven: boolean) =>
    requestJson<StandardResponse<CoreConsent>>(`/api/core/api/consent?${queryString({ call_id: callId, consent_given: consentGiven })}`, { method: "POST" }),
  transcripts: (callId: string) =>
    requestJson<StandardResponse<{ call_id: string; transcripts: CoreTranscript[] }>>(`/api/core/api/calls/${encodeURIComponent(callId)}/transcripts`),
  bookmarkTranscript: (segmentId: string, bookmarked: boolean) => requestJson<StandardResponse<{ bookmarked: boolean }>>(`/api/core/api/transcripts/${encodeURIComponent(segmentId)}/bookmark?${queryString({ bookmarked })}`, { method: "PATCH" }),
  wrapUp: (callId: string, summary: string, outcome: string) =>
    requestJson<StandardResponse<CoreWrapUp>>(`/api/core/api/calls/${encodeURIComponent(callId)}/wrap-up`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ summary, outcome }),
    }),
};

export const authApi = {
  login: (email: string, password: string) => requestJson<{ access_token: string; token_type: string; expires_in: number; user: AuthenticatedUser }>("/api/core/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) }),
  me: () => requestJson<AuthenticatedUser>("/api/core/api/auth/me"),
  users: () => requestJson<AuthenticatedUser[]>("/api/core/api/users"),
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
  completeCall: (sessionId: string) => requestJson<{ crm_summary: CRMSummary; confidence: number; requires_human_review: boolean }>("/api/ai/api/v1/copilot/complete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ session_id: sessionId, ended_at: new Date().toISOString() }) }),
  ingest: async (form: FormData) => {
    const token = getAccessToken();
    const response = await fetch("/api/ai/api/v1/knowledge/ingest", { method: "POST", body: form, headers: token ? { Authorization: `Bearer ${token}` } : undefined });
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
  customers: (search = "") => ["customers", search] as const,
  dashboard: ["dashboard"] as const,
  analytics: (days = 30) => ["analytics", days] as const,
  calls: ["calls"] as const,
  followUps: ["follow-ups"] as const,
  tasks: ["tasks"] as const,
  notifications: ["notifications"] as const,
  clauses: ["clauses"] as const,
  knowledgeDocuments: ["knowledge-documents"] as const,
  products: ["products"] as const,
  transcripts: (id: string) => ["transcripts", id] as const,
};
